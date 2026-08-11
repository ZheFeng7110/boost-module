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
# Per-library extra preprocessor defines applied to the bundle TU (libclang
# parse AND the clang++ gate), so the .inc snapshot matches the module TU's
# macro state — e.g. stacktrace.cppm GMF defines BOOST_STACKTRACE_LINK
# (M4: link mode, impl in libs/stacktrace/src/basic.cpp), so the exported
# surface must be generated under the same macro.
EXTRA_DEFINES = {
    "stacktrace": ["BOOST_STACKTRACE_LINK"],
}

# Per-library GMF override (exact include set, relative to deps/boost/): the
# module TU's real GMF when it deliberately diverges from the libs.json root
# set. json: M4 moves the compiled definitions into libs/json/src/src.cpp, so
# the module GMF (and thus the .inc snapshot) must not include src.hpp (which
# pulls the .ipp implementation declarations).
GMF_OVERRIDE = {
    "json": ["boost/json/debug_printers.hpp", "boost/json.hpp"],
}

EXPORT_KINDS = (
    "CLASS_DECL", "STRUCT_DECL", "UNION_DECL", "ENUM_DECL",
    "ENUM_CONSTANT_DECL",
    "FUNCTION_DECL", "FUNCTION_TEMPLATE", "VAR_DECL",
    "TYPEDEF_DECL", "TYPE_ALIAS_DECL", "TYPE_ALIAS_TEMPLATE_DECL",
    "CLASS_TEMPLATE", "CLASS_TEMPLATE_PARTIAL_SPECIALIZATION",
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
    # using-declarations / directives: namespace-scope `using boost::X;` /
    # `using namespace boost::X;` re-exports that give entities their public
    # spelling (ADL-barrier pattern — see collect_injections).
    "USING_DECLARATION", "USING_DIRECTIVE",
}


def _index_key(cursor):
    """usr_index key — real USRs for entities; a location-based fallback for
    using-directives (clang gives them no USR at all)."""
    usr = bc.usr_of(cursor)
    if usr:
        return usr
    if _kind_name(cursor) == "USING_DIRECTIVE":
        f = bc.cursor_file(cursor)
        if f is not None:
            # line+column: two directives on the same source line must not
            # share a key (first index entry wins and would swallow the rest).
            return "dir:{}:{}:{}".format(f, cursor.location.line,
                                         cursor.location.column)
    return None


def build_usr_index(tu):
    """One pass over the whole TU building {usr: cursor} for every decl.

    Closure lookups then become O(1) instead of re-walking the AST per entity
    (which made json/url generation quadratic). FRIEND_DECL subtrees are
    skipped: friend functions are re-exported through their class by ADL and
    cannot be using-exported."""
    idx = {}

    def rec(cursor):
        if _kind_name(cursor) in DECL_KINDS:
            key = _index_key(cursor)
            if key and key not in idx:
                idx[key] = cursor
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
# using-injection collection (M3 round-3 generator fix)
# ---------------------------------------------------------------------------

def _enclosing_ns(cursor):
    """Namespace chain of a using-* declaration's lexical parent, e.g.
    ['boost','tuples'] — the scope the injected name lands in."""
    parts = []
    cur = cursor.lexical_parent
    while cur is not None:
        if bc.kind_of(cur) != ci.CursorKind.NAMESPACE:
            break
        try:
            if cur.is_anonymous():
                return []
        except Exception:
            return []
        parts.append(cur.spelling)
        cur = cur.semantic_parent
    return parts[::-1]


def _using_target_name(cursor, tu):
    """Injected name of a namespace-scope using-declaration, derived from its
    token stream. Boost writes two shapes:

      `using boost::iterators::counting_iterator;`   (fully qualified)
      `using range::count;`  inside `namespace boost` (relative — injects
      boost::range::count into boost::count)

    libclang's USING_DECLARATION carries no usable referenced target, its
    spelling holds only the last name segment, and the token extent starts at
    'using' and often omits the trailing ';' — so the tokens are joined and
    the missing prefix is reconstructed from the lexical parent chain.

    Returns the injected qualified name ('' when the shape is not usable)."""
    try:
        toks = bc.tokens_of(tu, cursor)
    except Exception:
        return ""
    toks = [t.spelling for t in toks]
    if not toks or toks[0] != "using" or (len(toks) > 1 and toks[1] == "namespace"):
        return ""
    # The token extent can include the terminating ';' and — on a
    # multi-statement line — everything after it. Cut at the first ';' so
    # trailing content cannot corrupt the reconstructed qualified name.
    if ";" in toks:
        toks = toks[:toks.index(";")]
    rel = "".join(toks[1:]).rstrip(";")
    if not rel or rel.startswith("::") or rel.startswith("std::"):
        return ""
    if rel.startswith("boost::"):
        return rel
    # Relative: prefix with the enclosing namespace chain.
    parts = _enclosing_ns(cursor)
    if not parts or parts[0] != "boost":
        return ""
    return "::".join(parts) + "::" + rel.split("::")[-1]


def _using_namespace_target(cursor, tu):
    """Target namespace of a namespace-scope `using namespace X;` directive
    (boost's ADL-barrier variant: `using namespace range_adl_barrier;` inside
    namespace boost). Returns the target's qualified name (''
    when unusable)."""
    try:
        toks = bc.tokens_of(tu, cursor)
    except Exception:
        return ""
    toks = [t.spelling for t in toks]
    if len(toks) < 3 or toks[0] != "using" or toks[1] != "namespace":
        return ""
    rel = "".join(toks[2:]).rstrip(";")
    if not rel or rel.startswith("::") or rel.startswith("std::"):
        return ""
    if rel.startswith("boost::"):
        return rel
    parts = _enclosing_ns(cursor)
    if not parts or parts[0] != "boost":
        return ""
    return "::".join(parts) + "::" + rel


def collect_injections(tu, lib, file_to_lib, claimed, usr_index):
    """Namespace-scope `using boost::X;` declarations that re-export entities
    under their public spelling. Boost uses this pervasively to hide
    implementation namespaces while keeping the API at a fixed qualified name:
      - boost::range_adl_barrier::{count,find,...}  → boost::count
      - boost::iterators::{counting_iterator,...}   → boost::counting_iterator
      - boost::system::detail::*, boost::optional_detail::* → boost::*

    Such names never appear as declaration entities (the generator would only
    see boost::range_adl_barrier::count), so consumers would lose the public
    spelling. The public name is collected as its own record: the module
    purview can `export using boost::count;` because the GMF (which includes
    exactly the bundle headers) makes the name visible — using-declarations
    are reachable exactly when their file is in the GFM include-DAG, so a
    record produced here always compiles.

    claimed: {public_qname: lib} — cross-module dedup for injected names
    (first wins, like USR claiming). Returns {qname: record}."""
    out = {}
    directives = []          # (target_chain, inject_prefix) pairs
    for usr, cursor in usr_index.items():
        kind = _kind_name(cursor)
        if kind not in ("USING_DECLARATION", "USING_DIRECTIVE"):
            continue
        if _kind_name(cursor.lexical_parent) != "NAMESPACE":
            continue
        f = bc.cursor_file(cursor)
        if f is None:
            continue
        if bc.home_lib_of_file(f, file_to_lib) not in (lib, "shared"):
            continue
        if kind == "USING_DECLARATION":
            q = _using_target_name(cursor, tu)
            if not q:
                continue
            if q in claimed:
                continue
            claimed[q] = lib
            out[q] = {
                "name": q.rsplit("::", 1)[-1],
                "qname": q,
                "usr": "inject:" + q,      # not a real USR — excluded from closure
                "ns": q.split("::")[:-1],
                "file": str(f),
                "home": lib,
                "kind": "USING_INJECT",
            }
        else:
            tgt = _using_namespace_target(cursor, tu)
            if not tgt:
                continue
            parts = _enclosing_ns(cursor)
            if not parts:
                continue
            directives.append((tgt.split("::"), "::".join(parts), f))
    for tgt_chain, prefix, df in directives:
        for usr, cursor in usr_index.items():
            if not is_export_kind(cursor):
                continue
            try:
                chain = bc.namespace_chain(cursor)
            except Exception:
                continue
            if chain != tgt_chain:
                continue
            q = prefix + "::" + cursor.spelling
            if not q.startswith("boost::") or q in claimed:
                continue
            claimed[q] = lib
            out[q] = {
                "name": cursor.spelling,
                "qname": q,
                "usr": "inject:" + q,
                "ns": q.split("::")[:-1],
                "file": str(df),
                "home": lib,
                "kind": "USING_INJECT",
            }
    return out


def collect_curated(lib, claimed):
    """scripts/curated/<lib>.txt — hand-written blind-spot overrides (M2 §2.3,
    read-out implemented in M3). One qualified name per line; lines starting
    with '#' are comments. Records are emitted exactly like using-injections
    (`export using boost::xxx;`), so every listed name must be visible in the
    module's GMF (it is, when the header chain that declares it is included).

    Use cases:
      - entities reachable only through template bodies (closure walks
        declarations, not bodies — e.g. boost::typeindex::* behind
        any_cast's body in boost/any.hpp);
      - boost-namespace aliases of std entities that the canonicalization in
        the closure resolves away (type_info → std::type_info).
      - cross-module re-export overrides: an entity already claimed by an
        earlier-processed module (first-wins) can be force-listed here when
        the module's exported template BODIES require it — e.g.
        boost::any's any_cast body compares typeinfo, so the typeindex
        operator set must be reachable from consumers importing only
        boost.any even though the 27-lib run claims it for boost.variant.
        Re-exporting the same entity from two modules is legal (they denote
        the same declaration); M3 did exactly that before cross-module
        dedup existed."""
    f = bc.CURATED_DIR / (lib + ".txt")
    if not f.exists():
        return {}
    out = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        q = line.strip()
        if not q or q.startswith("#"):
            continue
        if not q.startswith("boost::"):
            continue
        claimed.setdefault(q, lib)
        out[q] = {
            "name": q.rsplit("::", 1)[-1],
            "qname": q,
            "usr": "inject:" + q,
            "ns": q.split("::")[:-1],
            "file": str(f),
            "home": lib,
            "kind": "CURATED",
        }
    return out


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
    claimed_inject = {}
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
        injects = collect_injections(tu, lib, _FILE_TO_LIB, claimed_inject,
                                     usr_index)
        curated = collect_curated(lib, claimed_inject)
        records = closure_from(dict(cands, **injects, **curated), tu, usr_index)
        if args.full_closure:
            claimed.clear()
            claimed_inject.clear()
        exports, deps = emit_inc(lib, records, args.out, args.full_closure,
                                 claimed, extra_deps=bc.dep_graph(
                                     {lib: gfm_final})[lib])
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
    if lib in GMF_OVERRIDE:
        gfm = [bc.DEPS / h for h in GMF_OVERRIDE[lib]]

    def write_bundle():
        bundle.write_text(
            "\n".join("#include <{}>".format(
                h.relative_to(bc.DEPS).as_posix()) for h in gfm) + "\n",
            encoding="utf-8")

    extra = ["-D" + d for d in EXTRA_DEFINES.get(lib, ())]

    def gate():
        r = subprocess.run(["clang++", "-std=c++23", "-fsyntax-only", "-w",
                            "--target=x86_64-w64-mingw32", "-DBOOST_ALL_NO_LIB",
                            "-Ideps/boost"] + extra + [str(bundle)],
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

    tu = idx.parse(str(bundle), args=bc.CLANG_ARGS + extra,
                   options=_ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    errs = [d for d in tu.diagnostics if d.severity >= _ci.Diagnostic.Error]
    if errs:
        print("    libclang: {} errors (non-fatal)".format(len(errs)))
        for d in errs[:6]:
            print("      {}: {}".format(d.location, d.spelling))
    return tu, gfm


if __name__ == "__main__":
    sys.exit(main())
