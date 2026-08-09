#!/usr/bin/env python3
"""import_boost.py — import the pinned official Boost release into deps/boost/.

Fetches boost_1_91_0.tar.gz (verified against a pinned SHA-256), then extracts
into deps/boost/ only the content needed for a module packaging build:
the aggregated include root boost/, the library sources libs/ (pruned of
docs/examples/Jamfiles/CI files), tools/cmake, CMakeLists.txt, LICENSE and
README. Everything else in the tarball is dropped.

Run it again to refresh: the old deps/boost/ is removed first and the import
is fully deterministic, so any change can always be reverted by re-running.

Usage:
    python script/import_boost.py                  # default: pinned URL + target/vendor-import
    python script/import_boost.py --tarball X.tgz  # use an existing archive elsewhere
    python script/import_boost.py --url https://... # mirror override
"""

import argparse
import hashlib
import os
import sys
import tarfile
import urllib.request
from pathlib import Path

VERSION = "1.91.0"
TARBALL_NAME = "boost_{}.tar.gz".format(VERSION.replace(".", "_"))
DEFAULT_URL = "https://archives.boost.io/release/{}/source/{}".format(VERSION, TARBALL_NAME)
PIN_SHA256 = "5734305f40a76c30f951c9abd409a45a2a19fb546efe4162119250bbe4d3a463"

ROOT = Path(__file__).resolve().parent.parent
DST = ROOT / "deps" / "boost"
WORK = ROOT / "target" / "vendor-import"
DEFAULT_TARBALL = WORK / TARBALL_NAME

# Top-level tarball entries that are imported at all (anything else is dropped).
KEEP_ROOT = {"boost", "libs", "tools", "CMakeLists.txt", "LICENSE_1_0.txt", "README.md"}

# Directory names deleted at any depth (same semantics as the retired
# clean-boost.ps1): docs, examples, website assets and CI config.
PRUNED_DIRS = {
    "doc", "docs", "example", "examples", "more", "status",
    ".github", ".travis", ".circleci", ".ci", ".appveyor", ".azure-pipelines",
}

# File names deleted at any depth: standalone docs, Jamfile/build files and CI config.
PRUNED_FILES = {
    "index.html", "index.htm", "INSTALL", "bootstrap.bat", "bootstrap.sh",
    "Jamroot", "boost-build.jam", "boostcpp.jam", "bootstrap.jam",
    "Jamfile.v2", "build.jam",
    "appveyor.yml", ".travis.yml", ".appveyor.yml", ".cirrus.yml", "azure-pipelines.yml",
}

# Image/style files deleted only at the boost root (test data images inside
# library test/ directories are left untouched).
ROOT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".css"}

# Doc-only web files deleted at any depth.
ANYWHERE_EXTENSIONS = {".htm", ".html"}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")

    def report(count, block_size, total_size):
        done = count * block_size
        if total_size > 0:
            print("  {:.1f} / {:.1f} MB".format(done / 1e6, total_size / 1e6), end="\r")
        else:
            print("  {:.1f} MB".format(done / 1e6), end="\r")

    print("downloading {}".format(url))
    urllib.request.urlretrieve(url, tmp, reporthook=report)
    print()
    os.replace(tmp, dest)


def keep_rel_path(parts: tuple, is_dir: bool = False) -> bool:
    """Decide whether a tarball member (path components below the top dir) is imported."""
    if not parts:
        return False
    if parts[0] not in KEEP_ROOT:
        return False
    # tools/ is cleared except tools/cmake (referenced by CMakeLists.txt).
    if parts[0] == "tools":
        return len(parts) >= 2 and parts[1] == "cmake"
    # A directory member is dropped by its own name too (tar dir members carry
    # a trailing slash that pathlib strips, so its name is the last part).
    if any(part in PRUNED_DIRS for part in (parts if is_dir else parts[:-1])):
        return False
    name = parts[-1]
    if name in PRUNED_FILES:
        return False
    if Path(name).suffix.lower() in ANYWHERE_EXTENSIONS:
        return False
    if len(parts) == 1 and Path(name).suffix.lower() in ROOT_EXTENSIONS:
        return False
    return True


def extract_selected(tf: tarfile.TarFile) -> tuple:
    """Extract the pruned tree into DST. Returns (imported, pruned, bytes)."""
    imported = pruned = 0
    total_bytes = 0
    for member in tf.getmembers():
        parts = Path(member.name).parts
        if len(parts) < 2 or parts[0].startswith("boost_"):
            parts = parts[1:] if len(parts) >= 2 else ()
        else:
            print("warning: unexpected tarball layout: {}".format(member.name))
            parts = ()
        if not keep_rel_path(parts, member.isdir()):
            pruned += 1
            continue
        if member.isdir():
            (DST / Path(*parts)).mkdir(parents=True, exist_ok=True)
            continue
        if not member.isreg():
            print("warning: skipping non-regular member: {}".format(member.name))
            pruned += 1
            continue
        src = tf.extractfile(member)
        if src is None:
            print("warning: cannot read member: {}".format(member.name))
            pruned += 1
            continue
        dst = DST / Path(*parts)
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(dst, "wb") as out:
            while True:
                chunk = src.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
                total_bytes += len(chunk)
        imported += 1
    return imported, pruned, total_bytes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tarball", type=Path, default=DEFAULT_TARBALL,
                    help="path to the boost tarball (default: {})".format(DEFAULT_TARBALL))
    ap.add_argument("--url", default=DEFAULT_URL, help="download URL for the tarball")
    args = ap.parse_args()

    tarball: Path = args.tarball
    if not tarball.exists():
        download(args.url, tarball)

    print("verifying sha256 of {}".format(tarball))
    actual = sha256_of(tarball)
    if actual != PIN_SHA256:
        print("error: sha256 mismatch\n  expected: {}\n  actual:   {}".format(PIN_SHA256, actual),
              file=sys.stderr)
        return 1
    print("sha256 OK: {}".format(actual))

    if DST.exists():
        print("removing old {}".format(DST))
        import shutil
        shutil.rmtree(DST)
    DST.mkdir(parents=True)

    with tarfile.open(tarball, "r:gz") as tf:
        imported, pruned, total_bytes = extract_selected(tf)

    libs = sum(1 for p in (DST / "libs").iterdir() if p.is_dir())
    print("imported {} files ({:.1f} MB) into {}, skipped {} members, {} libraries"
          .format(imported, total_bytes / 1e6, DST, pruned, libs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
