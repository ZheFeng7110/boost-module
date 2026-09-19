#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""fetch_mingw_sysroot.py — fetch the pinned MinGW-w64 GCC sysroot used by the
export generator.

Why this exists
---------------
`gen_exports.py` drives libclang and the real clang++ driver with
`--target=x86_64-w64-mingw32 --sysroot=...` (see boost_common.GEN_TARGET) to
reproduce the committed mingw-flavor `src/gen_exports/*.inc` snapshots. The
generator only ever runs `-fsyntax-only` and never links, so it needs the
target's *headers* (mingw-w64 CRT + GCC libstdc++) but **not** the MinGW
binutils/compiler. Downloading a sysroot therefore replaces a local MinGW
installation entirely.

Pinned source
-------------
WinLibs (https://winlibs.com) x86_64 posix-seh UCRT, GCC 16.1.0 /
mingw-w64 14.0.0 r4 — the flavor the committed snapshot was generated with.
The archive sha256 is pinned below; the version must not be bumped casually,
because mingw-w64/libstdc++ updates change Boost's preprocessor branches and
therefore the generated `.inc`/`.deps` output.

    uv run scripts/fetch_mingw_sysroot.py            # fetch + verify + probe
    uv run scripts/fetch_mingw_sysroot.py --check    # probe an existing tree
    uv run scripts/fetch_mingw_sysroot.py --print-path
    uv run scripts/fetch_mingw_sysroot.py --force    # re-download

Preferring 7z: the .7z asset is ~2.5x smaller than the .zip. The script uses
it when a pure-Python 7z backend is importable (and when a `7z`/`7za`
executable is on PATH); otherwise it falls back to the .zip. To opt in:

    uv run --with py7zr scripts/fetch_mingw_sysroot.py

The sysroot lands under `scripts/_deps/` (gitignored) and is picked up
automatically by `scripts/boost_common.py` when `BOOST_MODULE_GEN_SYSROOT`
is unset.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPS_DIR = ROOT / "scripts" / "_deps"
ARCHIVE_DIR = DEPS_DIR / "_archives"
MARKER = DEPS_DIR / "mingw-sysroot.json"
TARGET = "x86_64-w64-mingw32"

# Pinned release: https://github.com/brechtsanders/winlibs_mingw
# tag 16.1.0posix-14.0.0-ucrt-r4
_TAG = "16.1.0posix-14.0.0-ucrt-r4"
_STEM = "winlibs-x86_64-posix-seh-gcc-16.1.0-mingw-w64ucrt-14.0.0-r4"
_BASE = ("https://github.com/brechtsanders/winlibs_mingw/releases/download/"
         + _TAG + "/")

VERSION = "winlibs x86_64 posix-seh UCRT - gcc 16.1.0 / mingw-w64 14.0.0 r4"

# format -> (filename, sha256). Compression preference: 7z > (tar.xz) > zip.
ARCHIVES = {
    "7z": (_STEM + ".7z",
           "08b46777f127b92f4ca9ca057b317331178133d028513d1c3632f9cdcfde9ae7"),
    "zip": (_STEM + ".zip",
            "c406a22f8cac82559a3a1d96b62ff603f666499fb5ff4784e87b4eb6fa37dede"),
}


# ---------------------------------------------------------------------------
# extraction backends
# ---------------------------------------------------------------------------

def _have_py7zr():
    try:
        import py7zr  # noqa: F401
        return True
    except Exception:
        return False


def _which_7z():
    return shutil.which("7z") or shutil.which("7za") or shutil.which("7zr")


def _sevenzip_backend():
    """Return 'py7zr', 'cli', or None for 7z extraction."""
    if _have_py7zr():
        return "py7zr"
    if _which_7z():
        return "cli"
    return None


def pick_format(requested):
    """Resolve --archive auto/7z/zip against available backends."""
    if requested == "7z":
        if _sevenzip_backend() is None:
            raise SystemExit(
                "fetch_mingw_sysroot: 7z requested but no backend found.\n"
                "  install one of: pip/uv `py7zr`, or a 7z/7za executable,\n"
                "  or use --archive zip (larger download).")
        return "7z"
    if requested == "zip":
        return "zip"
    # auto: prefer 7z (smaller) when extractable, else zip.
    return "7z" if _sevenzip_backend() is not None else "zip"


def _safe_join(base, name):
    """Reject absolute/..-escaping archive member names."""
    name = name.replace("\\", "/")
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        raise SystemExit("unsafe absolute path in archive: {!r}".format(name))
    target = (base / name).resolve()
    if base.resolve() not in target.parents and target != base.resolve():
        raise SystemExit("unsafe path traversal in archive: {!r}".format(name))
    return target


def _extract_zip(path, dest):
    import zipfile
    with zipfile.ZipFile(path) as z:
        for m in z.infolist():
            _safe_join(dest, m.filename)
        z.extractall(dest)


def _extract_tar(path, dest):
    import tarfile
    with tarfile.open(path, "r:*") as t:
        for m in t.getmembers():
            _safe_join(dest, m.name)
        try:
            t.extractall(dest, filter="data")   # py>=3.12
        except TypeError:
            t.extractall(dest)


def _extract_sevenzip(path, dest, backend):
    if backend == "py7zr":
        import py7zr
        with py7zr.SevenZipFile(path, mode="r") as z:
            for n in z.getnames():
                _safe_join(dest, n)
            z.extractall(dest)
        return
    exe = _which_7z()
    r = subprocess.run([exe, "x", "-y", "-o" + str(dest), str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("7z extraction failed:\n{}".format(r.stderr[:500]))


def extract(path, dest, fmt):
    dest.mkdir(parents=True, exist_ok=True)
    if fmt == "zip":
        _extract_zip(path, dest)
    elif fmt == "7z":
        _extract_sevenzip(path, dest, _sevenzip_backend())
    else:
        _extract_tar(path, dest)


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------

def _sha256_of(path, label):
    h = hashlib.sha256()
    total = path.stat().st_size
    read = 0
    with path.open("rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
            read += len(chunk)
            pct = read * 100 // total if total else 100
            print("\r  {} {:3d}%".format(label, pct), end="", flush=True,
                  file=sys.stderr)
    print(file=sys.stderr)
    return h.hexdigest()


def _progress(label, done, total):
    if total:
        print("\r  {} {:3d}% ({:.0f}/{:.0f} MiB)".format(
            label, done * 100 // total, done / 1048576, total / 1048576),
            end="", file=sys.stderr, flush=True)


def _head_total(url):
    req = urllib.request.Request(url, headers={"User-Agent": "boost-module"},
                                 method="HEAD")
    with urllib.request.urlopen(req) as r:
        cl = r.headers.get("Content-Length")
    return int(cl) if cl else 0


def _single_stream(url, dest, label, total):
    req = urllib.request.Request(url, headers={"User-Agent": "boost-module"})
    read = 0
    with urllib.request.urlopen(req) as r, dest.open("wb") as out:
        total = total or int(r.headers.get("Content-Length") or 0)
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            read += len(chunk)
            _progress(label, read, total)
    print(file=sys.stderr)


def _parallel_stream(url, dest, label, total, jobs):
    """Range-download `jobs` chunks concurrently, then concatenate.

    GitHub's release CDN throttles a single connection hard; ranges lift the
    aggregate throughput several-fold. Raises on any failure so the caller can
    fall back to a single stream.
    """
    parts = [dest.with_name(dest.name + ".part{}".format(i))
             for i in range(jobs)]
    counter = [0]
    lock = threading.Lock()
    try:
        def worker(i):
            start = total * i // jobs
            end = total * (i + 1) // jobs - 1
            req = urllib.request.Request(url, headers={
                "User-Agent": "boost-module",
                "Range": "bytes={}-{}".format(start, end),
            })
            with urllib.request.urlopen(req) as r:
                if getattr(r, "status", 206) != 206:
                    raise RuntimeError(
                        "server ignored Range (status {})".format(
                            getattr(r, "status", "?")))
                with parts[i].open("wb") as out:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        out.write(chunk)
                        with lock:
                            counter[0] += len(chunk)
                            _progress(label, counter[0], total)

        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as ex:
            for f in [ex.submit(worker, i) for i in range(jobs)]:
                f.result()
        with dest.open("wb") as out:
            for p in parts:
                with p.open("rb") as pf:
                    shutil.copyfileobj(pf, out, 1 << 20)
        print(file=sys.stderr)
    finally:
        for p in parts:
            try:
                p.unlink()
            except OSError:
                pass


def _download(url, dest, label, jobs):
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        total = _head_total(url)
    except Exception:
        total = 0
    if jobs > 1 and total > 8 << 20:
        try:
            _parallel_stream(url, dest, label, total, jobs)
            return
        except Exception as e:
            print("\n  parallel download failed ({}); retrying single-stream"
                  .format(e), file=sys.stderr)
    _single_stream(url, dest, label, total)


def fetch_archive(fmt, force, jobs):
    filename, sha = ARCHIVES[fmt]
    url = _BASE + filename
    dest = ARCHIVE_DIR / filename
    if dest.is_file() and not force:
        if _sha256_of(dest, "verify " + filename) == sha:
            print("  cached {} (sha256 ok)".format(filename))
            return dest
        print("  cached {} has wrong sha256, re-downloading".format(filename),
              file=sys.stderr)
    print("  downloading {} ({} MiB, {} connections)".format(
        filename, "~105" if fmt == "7z" else "~260", jobs), file=sys.stderr)
    _download(url, dest, filename, jobs)
    actual = _sha256_of(dest, "verify " + filename)
    if actual != sha:
        raise SystemExit(
            "fetch_mingw_sysroot: sha256 mismatch for {}\n"
            "  expected {}\n  actual   {}".format(filename, sha, actual))
    return dest


# ---------------------------------------------------------------------------
# sysroot discovery / probe
# ---------------------------------------------------------------------------

def _is_sysroot(p):
    return ((p / TARGET / "include" / "windows.h").is_file()
            and (p / "include").is_dir())


def find_sysroot(base=None):
    """Locate the extracted sysroot root (the dir passed to --sysroot).

    WinLibs unpacks to <base>/mingw64/ with the target tree directly under it.
    Scans a couple of levels defensively.
    """
    base = base or DEPS_DIR
    if _is_sysroot(base):
        return base
    for depth in (1, 2, 3):
        for p in sorted(base.glob("/".join(["*"] * depth))):
            if p.is_dir() and _is_sysroot(p):
                return p
    return None


def probe(root, target=TARGET, quiet=False):
    """Syntax-check a TU that pulls mingw CRT + libstdc++ through the sysroot."""
    clangxx = os.environ.get("CXX") or shutil.which("clang++")
    if not clangxx:
        print("  warning: clang++ not found on PATH; skipping probe",
              file=sys.stderr)
        return True
    src = ("#include <windows.h>\n"
           "#include <cstddef>\n"
           "#include <string>\n"
           "#include <vector>\n"
           "int probe() { std::vector<std::string> v; "
           "v.emplace_back(\"x\"); return (int)v.size(); }\n")
    cmd = [clangxx, "--target=" + target, "--sysroot=" + str(root),
           "-std=c++23", "-w", "-fsyntax-only", "-x", "c++", "-"]
    r = subprocess.run(cmd, input=src, capture_output=True, text=True,
                       cwd=str(ROOT))
    if r.returncode != 0:
        print("  probe FAILED ({} {})".format(target, root), file=sys.stderr)
        for line in (r.stderr or "").splitlines()[:12]:
            print("    {}".format(line), file=sys.stderr)
        return False
    if not quiet:
        print("  probe ok: {} + libstdc++ headers resolve".format(TARGET))
    return True


def write_marker(root, fmt, sha):
    marker = {
        "version": VERSION,
        "target": TARGET,
        "root": str(root.relative_to(ROOT)) if root.is_relative_to(ROOT)
                else str(root),
        "archive": fmt,
        "sha256": sha,
    }
    MARKER.write_text(json.dumps(marker, indent=1, sort_keys=True) + "\n",
                      encoding="utf-8")


def current_root():
    """Existing sysroot root: marker first, then a filesystem scan."""
    if MARKER.is_file():
        try:
            data = json.loads(MARKER.read_text(encoding="utf-8"))
            root = ROOT / data["root"]
            if _is_sysroot(root):
                return root
        except Exception:
            pass
    return find_sysroot()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    # keep stdout/stderr interleaved sensibly when the log is redirected
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archive", choices=("auto", "7z", "zip"), default="auto",
                    help="archive format (default: prefer 7z when extractable)")
    ap.add_argument("--force", action="store_true",
                    help="re-download even if a verified archive is cached")
    ap.add_argument("--jobs", type=int, default=8,
                    help="parallel range connections for the download "
                         "(default 8; 1 disables)")
    ap.add_argument("--check", action="store_true",
                    help="only probe an existing sysroot, never download")
    ap.add_argument("--print-path", action="store_true",
                    help="print the sysroot root and exit")
    ap.add_argument("--no-probe", action="store_true",
                    help="skip the clang++ syntax probe")
    args = ap.parse_args()

    if args.print_path:
        root = current_root()
        if root is None:
            print("fetch_mingw_sysroot: no sysroot under {}".format(DEPS_DIR),
                  file=sys.stderr)
            return 1
        print(root)
        return 0

    if args.check:
        root = current_root()
        if root is None:
            print("fetch_mingw_sysroot: no sysroot under {}".format(DEPS_DIR),
                  file=sys.stderr)
            return 1
        print("sysroot: {}".format(root))
        return 0 if (args.no_probe or probe(root)) else 1

    root = current_root()
    if root is not None:
        print("sysroot already present: {}".format(root))
        return 0 if (args.no_probe or probe(root)) else 1

    fmt = pick_format(args.archive)
    _filename, sha = ARCHIVES[fmt]
    print("fetching {} ({})".format(VERSION, fmt))
    archive = fetch_archive(fmt, args.force, max(1, args.jobs))

    print("  extracting into {}".format(DEPS_DIR))
    extract(archive, DEPS_DIR, fmt)

    root = find_sysroot()
    if root is None:
        raise SystemExit(
            "fetch_mingw_sysroot: extracted but no sysroot root found under "
            "{} (looked for {}/include/windows.h)".format(DEPS_DIR, TARGET))
    write_marker(root, fmt, sha)
    print("sysroot: {}".format(root))

    if not args.no_probe and not probe(root):
        return 1
    print("done: scripts/boost_common.py will use this sysroot by default.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
