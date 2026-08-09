#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "libclang",
# ]
# ///
"""gen_exports.py — generate export using-lists for the Boost module layer.

For each target library, parses one "bundle" TU that includes all of the
library's public headers (the future .cppm GMF include set), collects every
namespace-scope boost:: entity with external linkage declared in those headers,
computes a dependency closure over the entity signatures (cross-library: e.g.
filesystem pulls boost::system::error_code), and emits src/gen_exports/<lib>.inc
containing M0-verified `export namespace boost { using ...; }` blocks.

Cross-module dedup: libraries are processed dependencies-first (include-based
topological order); the first library to claim an entity's USR owns it, later
libraries omit it and record `export import boost.<home>;` hints in <lib>.deps.

Usage:
    python scripts/gen_exports.py --scan            # regenerate scripts/libs.json
    python scripts/gen_exports.py                   # all 27 target libs
    python scripts/gen_exports.py --libs optional system --full-closure
    python scripts/gen_exports.py --emit-cppm       # also draft src/<lib>.cppm
"""

import argparse
import json
import sys
from collections import deque
from pathlib import Path

import boost_common as bc

ci = None


# ---------------------------------------------------------------------------
# entity collection (one bundle TU per library)
# ---------------------------------------------------------------------------

# Cursor kinds that can be exported as namespace-scope entities.
EXPORT_KINDS = (
    "CLASS_DECL", "STRUCT_DECL", "UNION_DECL", "ENUM_DECL",
    "ENUM_CONSTANT_DECL",
    "FUNCTION_DECL", "FUNCTION_TEMPLATE", "VAR_DECL",
    "TYPEDEF_DECL", "TYPE_ALIAS_DECL", "TYPE_ALIAS_TEMPLATE_DECL",
    "CONCEPT_DECL",
)

MEMBER_KINDS = (
    "CXX_METHOD", "CONSTRUCTOR", "DESTRUCTOR", "CONVERSION_FUNCTION",
    "FIELD_DECL",
)

# Lexical parents that can host a namespace-scope entity: anything else
# (function bodies, compound statements, templates of expressions) is local.
_LEXICAL_OK = (
    "NAMESPACE", "CLASS_DECL", "STRUCT_DECL", "UNION_DECL", "ENUM_DECL",
    "CLASS_TEMPLATE", "CLASS_TEMPLATE_PARTIAL_SPECIALIZATION",
    "TRANSLATION_UNIT", "LINKAGE_SPEC",
)


def _kind_name(cursor):
    try:
        return str(cursor.kind).replace("CursorKind.", "")
    except Exception:
        return "UNKNOWN"


def is_export_kind(cursor):
    return _kind_name(cursor) in EXPORT_KINDS


def entity_record(cursor, home):
    """Stable dict describing one exportable entity."""
    kind = _kind_name(cursor)
    # Enumerators are injected into the enum's enclosing namespace (upstream
    # spelling: boost::red), so they group under the enum's namespace chain.
    ns = (bc.namespace_chain(cursor.semantic_parent)
          if kind == "ENUM_CONSTANT_DECL" else bc.namespace_chain(cursor))
    return {
        "name": cursor.spelling,
        "qname": bc.qualified_name(cursor),
        "usr": bc.usr_of(cursor),
        "ns": ns,
        "file": str(bc.cursor_file(cursor)) if bc.cursor_file(cursor) else "",
        "home": home,
        "kind": kind,
    }


def _is_scoped_enum(cursor, tu):
    """Scoped enums (enum class/struct, incl. macro-generated ones like
    boost::thread's BOOST_SCOPED_ENUM_*) do not inject their enumerators into
    the enclosing scope. Uses clang_EnumDecl_isScoped (macro-generated enums
    have no tokens over their extent, so token sniffing fails for them)."""
    try:
        ci = bc.get_ci()
        r = ci.conf.lib.clang_EnumDecl_isScoped(cursor)
        return bool(r)
    except Exception:
        pass
    try:
        for tok in bc.tokens_of(tu, cursor):
            if tok.spelling == "enum":
                continue
            if tok.spelling in ("class", "struct"):
                return True
            return False
    except Exception:
        return False
    return False


DECL_KINDS = set(EXPORT_KINDS) | set(MEMBER_KINDS) | {
    "PARM_DECL", "CXX_BASE_SPECIFIER", "ENUM_DECL", "NAMESPACE",
}


def build_usr_index(tu):
    """One pass over the whole TU building {usr: cursor} for every decl.

    Closure lookups then become O(1) instead of re-walking the AST per entity
    (which made json/url generation quadratic). FRIEND_DECL subtrees are
    skipped: friend functions are re-exported through their class by ADL and
    cannot be using-exported."""
    idx = {}

    def rec(cursor):
        if _kind_name(cursor) in DECL_KINDS:
            usr = bc.usr_of(cursor)
            if usr and usr not in idx:
                idx[usr] = cursor
        for child in cursor.get_children():
            if bc.kind_of(child) == ci.CursorKind.FRIEND_DECL:
                continue
            rec(child)

    rec(tu.cursor)
    return idx


def _is_explicit_specialization(cursor, tu):
    """Explicit specializations (`template<> ...`) of templates are not
    exportable via using-declarations. clang_getSpecializedCursorTemplate
    returns null for them (unlike explicit instantiations), so detect the
    empty template-parameter list via the token stream of the decl extent."""
    try:
        toks = bc.tokens_of(tu, cursor)
    except Exception:
        return False
    if len(toks) < 3:
        return False
    return toks[0].spelling == "template" and toks[1].spelling == "<" and \
        toks[2].spelling in (">", ">>")


def collect_candidates(lib, tu, file_to_lib, usr_index):
    """External-linkage namespace-scope boost:: entities reachable through the
    library's bundle TU, owned by this library or by no target library
    ('shared'). Entities owned by other target libraries are pulled in by the
    closure instead (they are exported by their own module, reached via the
    export-import chain recorded in <lib>.deps). Returns {usr: record}."""
    found = {}

    def visit(cursor):
        if not is_export_kind(cursor):
            return
        f = bc.cursor_file(cursor)
        if f is None:
            return
        home = bc.home_lib_of_file(f, file_to_lib)
        if home not in (lib, "shared"):
            return
        if not bc.linkage_ok(cursor):
            return
        if bc.is_specialization(cursor):
            return
        if _is_explicit_specialization(cursor, tu):
            return
        if cursor.spelling.startswith("<"):
            return          # C++17 deduction guides (spelled "<deduction guide for X>")
        # Declarations whose lexical context is inside a function body are
        # body-local (e.g. clang's vexing-parse artifact: a local
        # `std::string cat_name(...)` reported as a namespace-scope function
        # with external linkage in cpp_regex_traits.hpp:966).
        if _kind_name(cursor.lexical_parent) not in _LEXICAL_OK:
            return
        # friend-in-class declarations (operators etc.): lexical parent is the
        # class while the semantic parent is a namespace; they are re-exported
        # through the class by ADL (M0 §1) and cannot be using-exported.
        pk = bc.kind_of(cursor.lexical_parent)
        if pk in (ci.CursorKind.CLASS_DECL, ci.CursorKind.STRUCT_DECL,
                  ci.CursorKind.UNION_DECL, ci.CursorKind.CLASS_TEMPLATE):
            return
        qn = bc.qualified_name(cursor)
        if not qn.startswith("boost::"):
            return
        if _kind_name(cursor) == "ENUM_CONSTANT_DECL":
            # Enumerators of enums nested in classes are class members
            # (exported with their class, e.g. isref::value_type::value);
            # only namespace-scope enums inject their enumerators into the
            # enclosing namespace. Scoped (enum class) enumerators come with
            # the enum itself.
            enum = cursor.semantic_parent
            if not bc.namespace_chain(enum):
                return
            if _is_scoped_enum(enum, tu):
                return
        elif not bc.namespace_chain(cursor):
            return          # class member: exported with its class
        usr = bc.usr_of(cursor)
        if not usr or usr in found:
            return
        # Prefer the first (definition) declaration seen per entity.
        found[usr] = entity_record(cursor, home)

    for usr, cursor in usr_index.items():
        visit(cursor)
    return found


# ---------------------------------------------------------------------------
# dependency closure
# ---------------------------------------------------------------------------

def referenced_types(cursor):
    """Yield the types referenced by a namespace-scope entity's declaration:
    function params/return, base classes, typedef/variable types."""
    kinds = set()
    try:
        kind = cursor.kind
    except Exception:
        kind = None

    if kind == ci.CursorKind.FUNCTION_DECL:
        kinds = {"FUNCTION_DECL"}
    elif kind == ci.CursorKind.FUNCTION_TEMPLATE:
        kinds = {"FUNCTION_TEMPLATE"}
    elif kind in (ci.CursorKind.CLASS_DECL, ci.CursorKind.STRUCT_DECL,
                  ci.CursorKind.UNION_DECL,
                  ci.CursorKind.CLASS_TEMPLATE,
                  ci.CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION):
        kinds = {"CLASS"}
    elif kind in (ci.CursorKind.TYPEDEF_DECL, ci.CursorKind.TYPE_ALIAS_DECL,
                  ci.CursorKind.TYPE_ALIAS_TEMPLATE_DECL, ci.CursorKind.VAR_DECL):
        kinds = {"TYPE"}
    elif kind == ci.CursorKind.CONCEPT_DECL:
        return

    for child in cursor.get_children():
        ck = bc.kind_of(child)
        if ck == ci.CursorKind.PARM_DECL:
            yield child.type
        elif ck == ci.CursorKind.CXX_BASE_SPECIFIER:
            yield child.type
        elif ck == ci.CursorKind.FIELD_DECL and "CLASS" in kinds:
            yield child.type
        elif _kind_name(child) in ("CXX_METHOD", "CONSTRUCTOR", "DESTRUCTOR",
                                   "CONVERSION_FUNCTION", "STATIC_DATA_MEMBER"):
            yield child.type

    # Return type of functions / underlying type of typedefs/vars.
    try:
        t = cursor.type
        if t is not None and t.kind != ci.TypeKind.INVALID:
            if kind == ci.CursorKind.FUNCTION_DECL or \
               _kind_name(cursor) == "CXX_METHOD" or \
               _kind_name(cursor) == "CONVERSION_FUNCTION":
                try:
                    yield t.get_result()
                except Exception:
                    pass
            elif "TYPE" in kinds:
                yield t
    except Exception:
        pass


def iter_type_types(t):
    """Walk a clang Type recursively, yielding the leaf (canonicalized) types
    reachable through pointers, references, functions and template args."""
    try:
        t = t.get_canonical()
    except Exception:
        return
    kind = t.kind
    if kind == ci.TypeKind.INVALID:
        return
    if kind in (ci.TypeKind.POINTER, ci.TypeKind.LVALUEREFERENCE,
                ci.TypeKind.RVALUEREFERENCE, ci.TypeKind.MEMBERPOINTER):
        try:
            yield from iter_type_types(t.get_pointee())
        except Exception:
            pass
        return
    if kind == ci.TypeKind.FUNCTIONPROTO:
        try:
            yield from iter_type_types(t.get_result())
        except Exception:
            pass
        return
    if kind in (ci.TypeKind.CONSTANTARRAY, ci.TypeKind.INCOMPLETEARRAY,
                ci.TypeKind.VARIABLEARRAY, ci.TypeKind.DEPENDENTSIZEDARRAY):
        try:
            yield from iter_type_types(t.get_pointee())
        except Exception:
            pass
        return
    try:
        n = t.get_num_template_arguments()
        if n >= 0:
            for i in range(n):
                yield from iter_type_types(t.get_template_argument_type(i))
            # Template types: the template itself is not a leaf we need; the
            # instantiation decl carries the args above.
    except Exception:
        pass
    yield t


def closure_from(cands, tu, usr_index):
    """BFS over candidate entity signatures; returns {usr: record} for every
    boost:: entity reachable through their declarations (exported entities and
    closure pulls alike)."""
    records = dict(cands)
    queue = deque(cands.values())
    seen = set(cands)

    while queue:
        rec = queue.popleft()
        cursor = usr_index.get(rec["usr"])
        if cursor is None:
            continue
        for t in referenced_types(cursor):
            for leaf in iter_type_types(t):
                try:
                    decl = leaf.get_declaration()
                    if decl is None or not decl.spelling and not decl.location.file:
                        continue
                except Exception:
                    continue
                qn = bc.qualified_name(decl)
                if not qn.startswith("boost::"):
                    continue
                # Promote members to their containing class, friends to their
                # namespace-level home.
                target = _promote(decl)
                usr = bc.usr_of(target)
                if not usr or usr in seen:
                    continue
                qnt = bc.qualified_name(target)
                if not qnt.startswith("boost::"):
                    continue
                f = bc.cursor_file(target)
                home = bc.home_lib_of_file(f, _FILE_TO_LIB) if f else "shared"
                seen.add(usr)
                records[usr] = entity_record(target, home)
                queue.append(records[usr])
    return records


def _promote(cursor):
    """Climb from a member cursor to the namespace-scope entity containing it."""
    cur = cursor
    while True:
        parent = cur.semantic_parent
        if parent is None or parent == cur:
            return cursor
        pk = bc.kind_of(parent)
        if pk in (ci.CursorKind.CLASS_DECL,
                  ci.CursorKind.STRUCT_DECL,
                  ci.CursorKind.UNION_DECL,
                  ci.CursorKind.CLASS_TEMPLATE):
            cur = parent
            continue
        return cur


_FILE_TO_LIB = {}


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------

def emit_inc(lib, records, out_dir, full_closure, claimed, extra_deps=()):
    """Write src/gen_exports/<lib>.inc with M0-verified export block spelling.

    Cross-module dedup (first wins): entities already claimed by an earlier
    module are dropped from the export list and recorded in <lib>.deps as
    `export import boost.<home>;` hints. Within one library, duplicate
    qualified names collapse into a single using-declaration (which imports
    every overload of the name — M0 rule for free operators).

    extra_deps: target libraries whose headers the bundle TU pulls in but
    whose entities may not appear in any signature (e.g. boost::swap) — the
    M3 .cppm must export-import those modules for a complete surface.

    Returns (exported_count, deps_hints).
    """
    own = [r for r in records.values() if r["home"] == lib]
    pulled = [r for r in records.values()
              if r["home"] != lib and r["usr"] not in claimed]
    deps = sorted({r["home"] for r in records.values()
                   if r["home"] != lib and r["home"] != "shared"
                   and r["usr"] in claimed} | (set(extra_deps) if not full_closure else set()))

    # qname dedup (one using per qualified name; overloads come along).
    exports, seen = [], set()
    for rec in sorted(own + pulled, key=lambda r: r["qname"]):
        if rec["qname"] in seen:
            continue
        seen.add(rec["qname"])
        exports.append(rec)

    groups = {}
    for rec in exports:
        groups.setdefault(tuple(rec["ns"]), []).append(rec)

    lines = [
        "// GENERATED by scripts/gen_exports.py — DO NOT EDIT",
        "// lib={} boost=1.91.0 target=x86_64-w64-mingw32 entities={}".format(
            lib, len(exports)),
        "",
    ]
    for key in sorted(groups):
        depth = len(key)
        opens = " ".join("namespace {} {{".format(n) for n in key)
        lines.append("export " + opens)
        for rec in sorted(groups[key], key=lambda r: r["qname"]):
            lines.append("  using {};".format(rec["qname"]))
        lines.append("}" * depth)
        lines.append("")

    (out_dir / "src" / "gen_exports").mkdir(parents=True, exist_ok=True)
    (out_dir / "src" / "gen_exports" / (lib + ".inc")).write_text(
        "\n".join(lines), encoding="utf-8")

    if deps:
        (out_dir / "src" / "gen_exports" / (lib + ".deps")).write_text(
            "\n".join("boost." + d for d in deps) + "\n", encoding="utf-8")
    return len(exports), deps


def emit_cppm(lib, out_dir, gfm_headers=None):
    """Draft src/<lib>.cppm: GMF include of the aggregate (DAG-source, gate-
    pruned) headers + export blocks from the .inc. M3 owns the final form
    (macro consistency, export import wiring for the .deps)."""
    headers = gfm_headers if gfm_headers is not None else bc.gfm_headers_of(lib)
    deps = out_dir / "src" / "gen_exports" / (lib + ".deps")
    imports = ""
    if deps.exists():
        imports = "\n".join(
            "export import {};".format(line.strip())
            for line in deps.read_text(encoding="utf-8").splitlines() if line.strip())
    lines = [
        "// GENERATED by scripts/gen_exports.py — DO NOT EDIT (draft; M3 owns final form)",
        "module;",
    ]
    lines += ["#include <{}>".format(h.relative_to(bc.DEPS).as_posix())
              for h in headers]
    lines += [
        "",
        "export module boost.{};".format(lib),
        "",
    ]
    if imports:
        lines += [imports, ""]
    lines += [
        '#include "gen_exports/{}.inc"'.format(lib),
        "",
        # NB: no `module :private;` — private module fragments are not yet
        # implemented by gcc, and nothing here needs hiding.
        "",
    ]
    (out_dir / "src" / (lib + ".cppm")).write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    global ci, _FILE_TO_LIB
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scan", action="store_true",
                    help="regenerate scripts/libs.json from the heuristic and exit")
    ap.add_argument("--libs", nargs="*", default=None,
                    help="subset of target libraries (default: all 27)")
    ap.add_argument("--out", type=Path, default=bc.ROOT,
                    help="repo root (src/gen_exports written below it)")
    ap.add_argument("--full-closure", action="store_true",
                    help="emit the complete closure per module (no cross-module dedup)")
    ap.add_argument("--emit-cppm", action="store_true",
                    help="also draft src/<lib>.cppm (M3 owns final form)")
    args = ap.parse_args()

    if args.scan:
        db = bc.scan_libs_json()
        bc.LIBS_JSON.write_text(json.dumps(db, indent=1, sort_keys=True) + "\n",
                                encoding="utf-8")
        total = sum(len(v) for v in db.values())
        print("wrote {} with {} headers across {} libraries"
              .format(bc.LIBS_JSON, total, len(db)))
        return 0

    ci = bc.get_ci()
    _FILE_TO_LIB = bc.build_file_to_lib()

    libs = args.libs or bc.TARGET_LIBS
    for lib in libs:
        if lib not in bc.TARGET_LIBS:
            print("error: unknown library '{}'".format(lib), file=sys.stderr)
            return 1

    order = bc.topo_order()
    print("processing order: {}".format(" -> ".join(order)))

    claimed = {}
    summary = {}
    for lib in order:
        if lib not in libs:
            continue
        headers = bc.headers_of(lib)
        gfm_headers = bc.gfm_headers_of(lib)
        print("parsing {} ({} headers, {} in GFM)...".format(
            lib, len(headers), len(gfm_headers)), flush=True)
        tu, gfm_final = _parse_bundle(lib, gfm_headers)
        if tu is None:
            print("error: parse failed for {}".format(lib), file=sys.stderr)
            return 1
        usr_index = build_usr_index(tu)
        cands = collect_candidates(lib, tu, _FILE_TO_LIB, usr_index)
        records = closure_from(cands, tu, usr_index)
        if args.full_closure:
            claimed.clear()
        exports, deps = emit_inc(lib, records, args.out, args.full_closure,
                                 claimed, extra_deps=bc.dep_graph()[lib])
        for rec in records.values():
            claimed.setdefault(rec["usr"], lib)
        summary[lib] = {"candidates": len(cands),
                        "closure": len(records),
                        "exported": exports,
                        "deps": sorted(deps)}
        if args.emit_cppm:
            emit_cppm(lib, args.out, gfm_final)
        print("  candidates={} closure={} exported={} deps={}"
              .format(len(cands), len(records), exports, sorted(deps) or "-"))

    out = args.out / "target" / "gen" / "gen_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print("report -> {}".format(out))
    return 0


def _parse_bundle(lib, headers):
    """One TU including the GFM headers (like the future .cppm GMF), gated by
    the real clang++ driver.

    libclang's missing-include reporting is unreliable once an include chain
    gets long (verified: a fatal 'file not found' surfaced for a bare header
    but not when the same header was reached after many others), so the bundle
    is additionally syntax-checked with clang++ — the same engine the module
    build uses. Gate failures identify source headers that must not be
    included directly on this platform (e.g. both boost/thread/pthread and
    win32/thread_heap_alloc.hpp define heap_new; the aggregate selects one via
    a computed include): those files are pruned from the GFM set and the
    bundle re-checked. Returns None when the include set cannot be made to
    compile, else the TU for the final (pruned) include set.
    """
    import subprocess
    _ci = bc.get_ci()
    idx = _ci.Index.create()
    bundle = Path(bc.ROOT / "target" / "gen" / "bundles" /
                  (lib + ".cpp")).resolve()
    bundle.parent.mkdir(parents=True, exist_ok=True)
    gfm = list(headers)

    def write_bundle():
        bundle.write_text(
            "\n".join("#include <{}>".format(
                h.relative_to(bc.DEPS).as_posix()) for h in gfm) + "\n",
            encoding="utf-8")

    def gate():
        r = subprocess.run(["clang++", "-std=c++23", "-fsyntax-only", "-w",
                            "--target=x86_64-w64-mingw32", "-DBOOST_ALL_NO_LIB",
                            "-Ideps/boost", str(bundle)],
                           capture_output=True, text=True, cwd=str(bc.ROOT))
        return r

    for attempt in range(6):
        write_bundle()
        r = gate()
        if r.returncode == 0:
            break
        offenders = set()
        for line in r.stderr.splitlines():
            head = line.split(":")[0].strip().replace("\\", "/")
            if not head.endswith(".hpp"):
                continue
            for h in gfm:
                if h.relative_to(bc.DEPS).as_posix() in head:
                    offenders.add(h)
        if not offenders:
            print("    clang++ gate FAILED for {}:".format(lib))
            for line in r.stderr.splitlines()[:8]:
                print("      {}".format(line.strip()))
            return None
        for h in sorted(offenders, key=lambda p: p.as_posix()):
            print("    gate pruned from GFM: {}".format(
                h.relative_to(bc.DEPS).as_posix()))
            gfm.remove(h)
    else:
        print("    clang++ gate FAILED for {} (still failing after pruning):".format(lib))
        for line in r.stderr.splitlines()[:8]:
            print("      {}".format(line.strip()))
        return None

    tu = idx.parse(str(bundle), args=bc.CLANG_ARGS,
                   options=_ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    errs = [d for d in tu.diagnostics if d.severity >= _ci.Diagnostic.Error]
    if errs:
        print("    libclang: {} errors (non-fatal)".format(len(errs)))
        for d in errs[:6]:
            print("      {}: {}".format(d.location, d.spelling))
    return tu, gfm


if __name__ == "__main__":
    sys.exit(main())
