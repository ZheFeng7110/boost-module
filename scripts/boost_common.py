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

# M3 header-only libraries, then M4 compiled libraries (plan order), then the
# M9 T1a batch (regular header-only libs, no src/ TU, no public macro surface).
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
# M9 T1a (boost-mcpp-all-libs-features-plan.md §2): 58 regular header-only
# libraries. Excluded: predef (pure .h macro lib → T3 include-only), coroutine2
# (depends on boost/context → T4), property_map_parallel (no headers in the
# aggregated boost/ include root), static_assert (pure macro lib with 0
# exported entities; its module name is ALSO invalid C++ — `static_assert` is a
# keyword, clang rejects `export module boost.static_assert;` — so it stays
# include-only like the T3 macro libs), hof + units (their public API is
# internal-linkage `static constexpr` objects — boost::hof::compose/_1 and
# boost::units::si::meter etc. — which a module cannot export via using-
# declarations; include-only, recorded in the M9 doc), plus the T1b
# heavy-template opt-in batch (M12) and the T2 compiled batch (M11).
LIBS_T1A = [
    "align", "array", "assert", "assign", "bimap", "bloom",
    "callable_traits", "circular_buffer", "compat", "concept_check",
    "config", "convert", "crc", "decimal", "describe",
    "dll", "dynamic_bitset", "flyweight", "format", "function",
    "functional", "hash2", "heap", "histogram", "icl",
    "integer", "intrusive", "leaf", "lexical_cast", "lockfree",
    "logic", "move", "multi_array", "multi_index", "openmethod",
    "outcome", "parser", "pfr", "poly_collection", "pool",
    "property_map", "property_tree", "ptr_container", "ratio",
    "safe_numerics", "signals2", "smart_ptr", "sort", "statechart",
    "stl_interfaces", "throw_exception", "tokenizer",
    "type_index", "unordered", "utility", "uuid", "winapi",
    "yap",
]
# M11 T2 (boost-mcpp-all-libs-features-plan.md §2/§4): compiled libraries —
# one module each plus its libs/<lib>/src TUs (see the M11 design doc §2 for
# the per-lib TU table: exclusions for external-library backends, per-OS dirs
# and upstream CMake deviations). math has src/tr1 only (deprecated std::tr1
# wrappers; upstream CMake is INTERFACE) — its feature ships no TU.
LIBS_T2 = [
    "atomic", "charconv", "cobalt", "container", "contract", "date_time",
    "graph", "iostreams", "log", "math", "nowide", "process",
    "random", "serialization", "test", "timer", "type_erasure", "wave",
]
# M12 T1b (boost-mcpp-all-libs-features-plan.md §2/§4): heavy-template
# header-only opt-in libraries. All twelve ship no src/ TU (verified:
# header-only upstream too), so their features are module-interface-only.
# opt-in: NOT in DEFAULT_CANDIDATES (plan §5.2 keeps the lean 18-lib core).
# asio lands here as a module of its own (its detail surface was already
# reachable through cobalt/process since M11, guarded by WIN32_LEAN_AND_MEAN
# in CLANG_ARGS). compute/mysql/redis moved to T4 (user decision 2026-09-03):
# their core surfaces hard-require external SDK headers (OpenCL / OpenSSL)
# that are absent from the vendored tree — same boundary as M13's
# external-dependency libraries.
LIBS_T1B = [
    "accumulators", "asio", "beast", "geometry", "gil",
    "hana", "interprocess", "mqtt5", "multiprecision", "numeric",
    "polygon", "qvm",
]
TARGET_LIBS = LIBS_M3 + LIBS_M4 + LIBS_T1A + LIBS_T2 + LIBS_T1B

# M10 T3 (boost-mcpp-all-libs-features-plan.md §2): macro-driven include-only
# libraries — no module, no feature, no build work (user decision §5.3). Their
# public API surface is macro-injection-driven (BOOST_PP_/BOOST_FUSION_/
# BOOST_SPIRIT_... families); a named module can neither export macros nor
# stay in sync with the config-macro-driven re-configuration these headers
# perform, so consumers #include them directly (import + include mixing is
# standard-compliant). The boundary is verified by gen_audit.py --macros.
LIBS_T3 = [
    "preprocessor", "mpl", "fusion", "proto", "spirit", "xpressive",
    "lambda", "lambda2", "bind", "typeof", "vmd", "phoenix", "parameter",
    "metaparse", "function_types", "tti", "local_function", "msm", "foreach",
]
# M13 T4 (boost-mcpp-all-libs-features-plan.md §2/§4): external-dependency /
# asm libraries — no module without the external SDK (M13 milestone).
# M12 addition (user decision 2026-09-03): compute (every real header includes
# CL/cl.h — OpenCL SDK), mysql + redis (boost/mysql.hpp / boost/redis.hpp and
# the connection core hard-require OpenSSL) — moved out of the T1b batch.
LIBS_T4 = [
    "mpi", "python", "parameter_python", "graph_parallel", "locale",
    "context", "fiber", "coroutine",
    "compute", "mysql", "redis",
]
# M9 downgrades to include-only (plan §2 note + 2026-08-17 M9 doc §1): pure
# macro libs (predef: .h only; static_assert: module name is a keyword) and
# internal-linkage constexpr-object APIs (hof, units) — same consumer rule
# as T3, recorded in the M9 doc.
LIBS_INCLUDE_ONLY_M9 = ["predef", "static_assert", "hof", "units"]
# M11 downgrade to include-only: exception — the clone_impl<T> member bodies
# attached to the boost.exception CMI as lazily loaded pendings trip gcc 16.1
# ("recursive lazy load / failed to load pendings for clone_impl") in ANY
# consumer TU that includes <memory>/<string>/<functional> — i.e. every real
# consumer. Explicit instantiations in the module TU do not dodge it. The API
# is header-only, so consumers #include <boost/exception/all.hpp> (T3 rule).
LIBS_INCLUDE_ONLY_M11 = ["exception"]

# clang command-line used for every bundle TU (same as M0 probe 4).
# The libclang resource dir (-I .../lib/clang/<ver>/include) is appended at
# load time: without it libclang cannot find its own builtin headers (e.g.
# mm_malloc.h), the mingw <malloc.h> chain breaks, the std surface degrades,
# and every declaration touching std::size_t/std types silently drops out of
# the AST (mp11's mp_at_c/mp_iota_c were lost this way in M2).
CLANG_ARGS = [
    "-std=c++23",
    "-Ideps/boost",
    "--target=x86_64-w64-mingw32",
    "-DBOOST_ALL_NO_LIB",
    "-D_WIN32_WINNT=0x0A00",
    # M11: asio (cobalt/log/process TUs) errors "WinSock.h has already been
    # included" when windows.h pulled winsock1 before asio's winsock2 — which
    # any boost.winapi -> windows.h chain does. WIN32_LEAN_AND_MEAN makes
    # windows.h skip winsock.h entirely; asio then includes winsock2.h itself
    # (defining _WINSOCKAPI_ instead is wrong: asio treats it as evidence that
    # winsock1 is already in and hard-errors, verified).
    "-DWIN32_LEAN_AND_MEAN",
    "-w",
]


def _append_resource_dir():
    """Locate the libclang.dll's bundled clang resource dir (bin/libclang.dll
    ↔ ../lib/clang/<ver>/include) and add it to CLANG_ARGS (idempotent).
    pip's libclang wheel ships no resource dir at all — then the caller must
    point LIBCLANG_PATH at a full LLVM install; without it parses degrade
    silently (see CLANG_ARGS note)."""
    try:
        import clang.cindex as ci
        # Two loading modes: set_library_path(dir) leaves library_path set,
        # set_library_file(dll) sets library_file with library_path None
        # (clang-on-PATH fallback and LIBCLANG_PATH=<file> form).
        if ci.Config.library_file:
            dll = Path(ci.Config.library_file)
        elif ci.Config.library_path:
            dll = Path(ci.Config.library_path) / "libclang.dll"
        else:
            return
    except Exception:
        return
    if not dll.is_file():
        return
    for base in (dll.parent.parent / "lib" / "clang",
                 dll.parent / "lib" / "clang",
                 dll.parent.parent / "include" / "clang"):
        try:
            vers = sorted([p for p in base.glob("*/include")
                           if (p / "stddef.h").is_file()],
                          key=lambda p: p.name, reverse=True)
        except Exception:
            continue
        if not vers:
            continue
        inc = "-I{}".format(vers[0])
        if inc not in CLANG_ARGS:
            CLANG_ARGS.append(inc)
        return


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
        _append_resource_dir()
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
        added = False
        for k in list(sub):
            if any(k in inc_of.get(other, ()) for other in sub if other != k):
                continue
            h = sub[k]
            reach_from(k)
            chosen.append(h)
            added = True
        if not added:
            # Every remaining header is included by another member of the
            # remaining subset — a pure include cycle with no entry source
            # (first seen with boost.math, M11). Pick one representative so
            # the loop terminates; its transitive in-set includes are pulled
            # in by reach_from, the rest of the cycle on a later pass.
            h = sorted(sub.values(), key=lambda p: p.as_posix())[0]
            reach_from(str(h.resolve()).lower())
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
    """boost/<x>... -> target lib x ('' when not a target lib root).

    Handles both directory roots (boost/<lib>/...) and single-header
    aggregates (boost/<lib>.hpp, e.g. boost/tokenizer.hpp / boost/crc.hpp)."""
    top = rel[len("boost/"):].split("/")[0]
    if "." in top:
        # single-header aggregate include (boost/<lib>.hpp)
        stem = top.rsplit(".", 1)[0]
        return stem if stem in TARGET_LIBS else ""
    if top == "detail":
        return ""
    return top if top in TARGET_LIBS else ""


def dep_graph(headers_by_lib=None):
    """{lib: set(lib)} — which target libs' headers a lib's headers include.

    headers_by_lib overrides the header set per lib (defaults to libs.json /
    heuristic). The generator passes the clang++-gate-pruned GFM set here so
    deps reachable only through headers pruned from the module (e.g. the regex
    family in algorithm, dropped for the gcc abi-tag workaround) do not leak
    into <lib>.deps.

    The walk is transitive through headers NOT owned by any target library
    (e.g. icl/gregorian.hpp -> boost/date_time/... -> boost/tokenizer.hpp —
    date_time is a T2 lib not yet a target, and single-header aggregates were
    invisible to the direct-include mapping): every non-target boost header
    reached from a lib's header set is scanned for further includes, and the
    walk stops at target-owned roots and system/std headers. This keeps the
    topological order (and first-wins claiming) consistent with what the
    module GMF actually compiles."""
    file_to_lib = build_file_to_lib()
    graph = {lib: set() for lib in TARGET_LIBS}
    for lib in TARGET_LIBS:
        headers = (headers_by_lib.get(lib) if headers_by_lib else None) \
            or headers_of(lib)
        visited = set()
        queue = list(headers)
        while queue:
            h = queue.pop()
            try:
                key = str(h.resolve()).lower()
            except OSError:
                continue
            if key in visited:
                continue
            visited.add(key)
            try:
                text = h.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for m in _INC_RE.finditer(text):
                rel = m.group(1)
                dep = _lib_of_include(rel)
                if dep:
                    if dep != lib:
                        graph[lib].add(dep)
                    continue            # target-owned root: don't recurse
                # non-target include: recurse through vendored boost headers
                # (e.g. boost/date_time/..., boost/mpl/..., boost/version.hpp)
                # when the file exists under the include root.
                p = BOOST_ROOT.parent / rel
                if p.suffix != ".hpp" or not p.is_file():
                    continue
                if str(p.resolve()).lower() in visited:
                    continue
                queue.append(p)
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
    exported through a using-declaration). Typedefs/aliases have no linkage
    concept at all (libclang reports NO_LINKAGE for them), yet a namespace-
    scope typedef name is a namespace member that a using-declaration can
    re-export (e.g. boost::endian::big_uint16_t) — so they pass unconditionally."""
    try:
        k = str(cursor.kind).replace("CursorKind.", "")
        if k in ("TYPEDEF_DECL", "TYPE_ALIAS_DECL"):
            return True
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
