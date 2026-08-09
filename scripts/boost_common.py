#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "libclang",
# ]
# ///
"""boost_common.py — shared plumbing for the M2 module-export generators.

Handles the M1 vendored layout: all library headers live under deps/boost/boost/
(the aggregated include root; libs/<lib>/ has no include/). This module knows
the target library list, resolves each library's public headers, builds one
"bundle" translation unit per library (mirroring the future .cppm GMF include
set), and provides libclang helpers shared by gen_exports.py / gen_audit.py.
"""

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPS = ROOT / "deps" / "boost"
BOOST_ROOT = DEPS / "boost"          # aggregated include root (all lib headers)
SCRIPTS = ROOT / "scripts"
LIBS_JSON = SCRIPTS / "libs.json"
CURATED_DIR = SCRIPTS / "curated"
GEN_DIR = ROOT / "src" / "gen_exports"
AUDIT_DIR = ROOT / "target" / "gen" / "audit"

# M3 header-only libraries, then M4 compiled libraries (plan order).
LIBS_M3 = [
    "optional", "variant", "variant2", "any", "core", "container_hash",
    "mp11", "static_string", "scope", "scope_exit", "type_traits",
    "algorithm", "iterator", "range", "io", "rational", "endian",
    "tuple", "system",
]
LIBS_M4 = [
    "filesystem", "regex", "thread", "chrono", "program_options",
    "stacktrace", "json", "url",
]
TARGET_LIBS = LIBS_M3 + LIBS_M4

# clang command-line used for every bundle TU (same as M0 probe 4).
CLANG_ARGS = [
    "-std=c++23",
    "-Ideps/boost",
    "--target=x86_64-w64-mingw32",
    "-DBOOST_ALL_NO_LIB",
    "-D_WIN32_WINNT=0x0A00",
    "-w",
]


# ---------------------------------------------------------------------------
# libclang bootstrap
# ---------------------------------------------------------------------------

_CI = None


def load_libclang():
    """Import clang.cindex, honouring LIBCLANG_PATH (file or directory form)
    or LLVM_PATH; falls back to a libclang.dll next to clang.exe on PATH."""
    import clang.cindex as ci
    env = os.environ.get("LIBCLANG_PATH") or os.environ.get("LLVM_PATH")
    if env:
        p = Path(env)
        if p.is_dir() and (p / "libclang.dll").is_file():
            ci.Config.set_library_path(str(p))
        else:
            ci.Config.set_library_file(env)
        return ci
    try:
        ci.Index.create()          # default (bundled) resolution works?
        return ci
    except Exception:
        pass
    # Common dev setup: libclang.dll next to clang.exe on PATH (scoop/LLVM).
    import shutil
    exe = shutil.which("clang")
    if exe:
        dll = Path(exe).resolve().parent / "libclang.dll"
        if dll.is_file():
            ci.Config.set_library_file(str(dll))
            return ci
    raise RuntimeError(
        "libclang not found — set LIBCLANG_PATH to the directory containing "
        "libclang.dll (e.g. pip install libclang, or a local LLVM install)")


def get_ci():
    """Cached libclang module (loads on first use)."""
    global _CI
    if _CI is None:
        _CI = load_libclang()
    return _CI


# ---------------------------------------------------------------------------
# header resolution (official tarball layout: all headers under boost/boost/)
# ---------------------------------------------------------------------------

def resolve_headers_heuristic(lib: str):
    """Public-root header set for a library: boost/<lib>/**.hpp minus detail/
    subtrees and amalgamation helpers (src.hpp), plus the aggregate single
    header boost/<lib>.hpp when it exists.

    detail/ headers are excluded deliberately: they are not self-contained
    (they rely on the root headers having set up macros and dependencies first)
    and every detail header reachable through public API is included
    transitively by the root headers. src.hpp is kept: for json it is the
    documented way to pull the .ipp implementations into one TU (header-only
    mode) — exactly what the module GMF wants; url's src.hpp is a #error stub
    and is dropped by the standalone-compile filter.

    The bundle TU / .cppm GMF includes the include-DAG sources of this set
    (see gfm_headers_of), mirroring what an upstream consumer's #include
    exposes."""
    headers = set()
    d = BOOST_ROOT / lib
    if d.is_dir():
        headers.update(p for p in d.rglob("*.hpp") if p.is_file()
                       and "detail" not in p.relative_to(BOOST_ROOT).parts)
    single = BOOST_ROOT / (lib + ".hpp")
    if single.is_file():
        headers.add(single)

    def key(p: Path):
        rel = p.relative_to(BOOST_ROOT).as_posix()
        return (0, rel) if p == single else (1, rel)

    return sorted(headers, key=key)


def _rel(path: Path) -> str:
    return path.relative_to(BOOST_ROOT.parent).as_posix()


def load_libs_json():
    """libs.json: {lib: [rel-header-path, ...]} — committed, curated."""
    if LIBS_JSON.exists():
        return json.loads(LIBS_JSON.read_text(encoding="utf-8"))
    return None


def headers_of(lib: str):
    """Header set for a library, from libs.json when present else heuristic."""
    db = load_libs_json()
    if db and lib in db:
        return [BOOST_ROOT.parent / rel for rel in db[lib]]
    return resolve_headers_heuristic(lib)


def gfm_headers_of(lib: str):
    """GMF/bundle include list for a library: the include-DAG sources of its
    header set (plus one representative per include cycle).

    Non-detail root headers are not mutually ordered by name (chrono's
    duration_get.hpp uses duration_units.hpp without including it — upstream
    both come via the chrono/io.hpp aggregate), so a flat alphabetical list
    does not compile. Including only the aggregate entry points — headers no
    other set member includes — pulls everything else in upstream order, and
    mirrors what an upstream consumer's #include surface looks like."""
    headers = headers_of(lib)
    names = {str(h.resolve()).lower() for h in headers}
    relmap = {str(h.resolve()).lower(): h for h in headers}

    # in-set include edges: which headers include which (by resolved path)
    inc_of = {}            # rel(lower) -> set of included lower paths
    for h in headers:
        key = str(h.resolve()).lower()
        inc_of.setdefault(key, set())
        try:
            text = h.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in _INC_RE.finditer(text):
            inc = str((BOOST_ROOT.parent / m.group(1)).resolve()).lower()
            if inc in names and inc != key:
                inc_of[key].add(inc)

    # SCCs (Tarjan-lite via iterative DFS) on the reverse edges:
    # a header X is a "source" if no other set member includes it.
    sources = [h for h in headers
               if not any(key in incs for key, incs in inc_of.items()
                          if str(h.resolve()).lower() in incs
                          and key != str(h.resolve()).lower())]
    # hmm — simpler: a header is included by another if its key appears in
    # any other header's include set.
    included_by_other = {k for incs in inc_of.values() for k in incs}
    sources = [h for h in headers if str(h.resolve()).lower() not in included_by_other]

    if not sources:
        return sorted(headers)          # fully cyclic set — fall back

    # ensure every header is reachable: repeatedly add sources of the
    # remaining unreached subset (breaks include cycles one representative
    # per cycle).
    reached = set()

    def reach_from(seed_key):
        stack = [seed_key]
        while stack:
            k = stack.pop()
            if k in reached:
                continue
            reached.add(k)
            stack.extend(inc_of.get(k, ()))

    chosen = []
    for h in sources:
        key = str(h.resolve()).lower()
        reach_from(key)
        chosen.append(h)
    missing = [h for h in headers if str(h.resolve()).lower() not in reached]
    while missing:
        # sources of the missing subset
        sub = {str(h.resolve()).lower(): h for h in missing}
        for k in list(sub):
            if any(k in inc_of.get(other, ()) for other in sub if other != k):
                continue
            h = sub[k]
            reach_from(k)
            chosen.append(h)
        missing = [h for h in headers if str(h.resolve()).lower() not in reached]
    return sorted(chosen, key=lambda p: p.as_posix())


def scan_libs_json():
    """Regenerate libs.json from the heuristic, dropping root headers that do
    not compile standalone (legacy opt-in headers — e.g.
    boost/algorithm/string/std/rope_traits.hpp requires the SGI <rope> header
    that modern libstdc++ no longer ships). The bundle TU check cannot be
    trusted for these: libclang silently swallows some missing-include fatals,
    while a standalone parse reports them (verified empirically). Human-curate
    the result afterwards if needed."""
    db = {}
    for lib in TARGET_LIBS:
        kept, dropped = standalone_compile_filter(resolve_headers_heuristic(lib))
        db[lib] = [_rel(p) for p in kept]
        for h, why in dropped:
            print("  drop {}: {}".format(_rel(h), why))
    return db


def standalone_compile_filter(headers):
    """Return (kept, dropped) — root headers whose standalone parse produces a
    severe diagnostic located under deps/boost/ are dropped (they cannot be
    part of any compilable module GMF). System-header noise (e.g. the missing
    mm_malloc.h inside mingw's malloc.h) is ignored. NB: libclang reports
    paths relative to the CWD, so locations are resolved before comparison."""
    ci = get_ci()
    idx = ci.Index.create()
    boost_prefix = str((BOOST_ROOT).resolve()).lower()
    kept, dropped = [], []
    for i, h in enumerate(headers):
        tmp = GEN_DIR.parent.parent / "target" / "gen" / ("standalone_%d.cpp" % i)
        tmp.write_text("#include <{}>\n".format(
            h.relative_to(BOOST_ROOT.parent).as_posix()), encoding="utf-8")
        tu = idx.parse(str(tmp.resolve()), args=CLANG_ARGS,
                       options=ci.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
        bad = [d for d in tu.diagnostics
               if d.severity >= ci.Diagnostic.Error and d.location.file
               and str(Path(d.location.file.name).resolve()).lower().startswith(boost_prefix)]
        if bad:
            dropped.append((h, bad[0].spelling[:100]))
        else:
            kept.append(h)
        tmp.unlink(missing_ok=True)
    return kept, dropped


def build_file_to_lib():
    """Map every header file (absolute, normalized) to its owning target lib.

    Prefix-based: every file under boost/<lib>/ (including detail/ subtrees,
    which are enumerated but not GMF-included) plus the boost/<lib>.hpp
    aggregate belongs to the library."""
    mapping = {}
    for lib in TARGET_LIBS:
        d = BOOST_ROOT / lib
        if d.is_dir():
            for p in d.rglob("*.hpp"):
                mapping[str(p.resolve()).lower()] = lib
        single = BOOST_ROOT / (lib + ".hpp")
        if single.is_file():
            mapping[str(single.resolve()).lower()] = lib
    return mapping


def home_lib_of_file(path: Path, file_to_lib) -> str:
    """Owner target lib of a file; 'shared' when owned by no target lib."""
    try:
        return file_to_lib.get(str(path.resolve()).lower(), "shared")
    except OSError:
        return "shared"


# ---------------------------------------------------------------------------
# include-based dependency graph / topological order
# ---------------------------------------------------------------------------

_INC_RE = re.compile(r'^\s*#\s*include\s*[<"](boost/[A-Za-z0-9_./]+)', re.MULTILINE)


def _lib_of_include(rel: str):
    """boost/<x>... -> target lib x ('' when not a target lib root)."""
    top = rel[len("boost/"):].split("/")[0]
    if "." in top or top == "detail":
        return ""
    return top if top in TARGET_LIBS else ""


def dep_graph():
    """{lib: set(lib)} — which target libs' headers a lib's own headers include."""
    graph = {lib: set() for lib in TARGET_LIBS}
    for lib in TARGET_LIBS:
        for h in headers_of(lib):
            try:
                text = h.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for m in _INC_RE.finditer(text):
                dep = _lib_of_include(m.group(1))
                if dep and dep != lib:
                    graph[lib].add(dep)
    return graph


def topo_order():
    """Dependencies first; cycles broken by TARGET_LIBS stable order."""
    graph = dep_graph()
    order, done = [], set()

    def visit(lib, stack):
        if lib in done or lib in stack:
            return
        stack.add(lib)
        for dep in sorted(graph[lib]):
            visit(dep, stack)
        stack.discard(lib)
        done.add(lib)
        order.append(lib)

    for lib in TARGET_LIBS:
        visit(lib, set())
    return order


# ---------------------------------------------------------------------------
# libclang cursor helpers
# ---------------------------------------------------------------------------

def iter_descendants(cursor):
    """Depth-first over the cursor subtree, skipping FRIEND_DECL subtrees."""
    ci = get_ci()
    stack = [cursor]
    while stack:
        cur = stack.pop()
        for child in cur.get_children():
            try:
                is_friend = child.kind == ci.CursorKind.FRIEND_DECL
            except ValueError:
                is_friend = False      # cursor kinds unknown to older bindings
            if is_friend:
                continue
            yield child
            stack.append(child)


def kind_of(cursor):
    """Cursor kind or None when the loaded bindings do not know it."""
    try:
        return cursor.kind
    except Exception:
        return None


def linkage_ok(cursor):
    """External linkage only (static / anonymous-namespace entities cannot be
    exported through a using-declaration)."""
    try:
        return cursor.linkage == get_ci().LinkageKind.EXTERNAL
    except Exception:
        return False


def namespace_chain(cursor):
    """Namespace names from the TU down to the entity, e.g. ['boost','mp11'].

    Returns [] when the entity is not namespace-scoped (class member, friend,
    local, or inside an anonymous namespace)."""
    ci = get_ci()
    chain = []
    cur = cursor
    while True:
        parent = cur.semantic_parent
        if parent is None or parent == cur:
            return []
        pk = kind_of(parent)
        if pk == ci.CursorKind.TRANSLATION_UNIT:
            return chain[::-1]
        if pk != ci.CursorKind.NAMESPACE:
            return []
        try:
            if parent.is_anonymous():
                return []
        except Exception:
            return []
        chain.append(parent.spelling)
        cur = parent


def qualified_name(cursor):
    """Full qualified name like boost::mp11::mp_list; '' when the entity is not
    reachable through plain qualified names (members include the class name,
    e.g. boost::X::Inner; anonymous namespaces yield '')."""
    ci = get_ci()
    parts = []
    cur = cursor
    while True:
        parent = cur.semantic_parent
        if parent is None or parent == cur:
            return ""
        pk = kind_of(parent)
        if pk == ci.CursorKind.TRANSLATION_UNIT:
            # cur is the outermost namespace; parts holds the chain below it
            # bottom-up, so reverse it under cur's name for top-down order.
            if not cur.spelling:
                return ""
            return "::".join([cur.spelling] + parts[::-1])
        if pk == ci.CursorKind.NAMESPACE:
            try:
                if parent.is_anonymous():
                    return ""
            except Exception:
                return ""
        if pk not in (ci.CursorKind.NAMESPACE,
                      ci.CursorKind.CLASS_DECL,
                      ci.CursorKind.STRUCT_DECL,
                      ci.CursorKind.UNION_DECL,
                      ci.CursorKind.ENUM_DECL,
                      ci.CursorKind.CLASS_TEMPLATE,
                      ci.CursorKind.TYPE_ALIAS_DECL,
                      ci.CursorKind.TYPEDEF_DECL):
            return ""
        if pk == ci.CursorKind.ENUM_DECL and cur.spelling.startswith("(unnamed"):
            # Anonymous enums contribute no name to qualified names:
            # their enumerators are members of the enclosing namespace/class.
            cur = parent
            continue
        parts.append(cur.spelling)
        cur = parent


def cursor_file(cursor):
    try:
        return Path(cursor.location.file.name)
    except Exception:
        return None


def usr_of(cursor):
    try:
        return cursor.get_usr()
    except Exception:
        return None


def tokens_of(tu, cursor):
    """Token list over a cursor's extent, tolerant of the two libclang
    binding generations (extent= vs ranges=[...])."""
    try:
        return list(tu.get_tokens(extent=cursor.extent))
    except TypeError:
        return list(tu.get_tokens(ranges=[cursor.extent]))
    except Exception:
        return []


def is_specialization(cursor):
    """True for explicit instantiation / explicit specialization decls."""
    try:
        ci = get_ci()
        r = ci.conf.lib.clang_getSpecializedCursorTemplate(cursor)
        return r is not None and r.kind != ci.CursorKind.INVALID
    except Exception:
        return False
