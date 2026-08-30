#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "libclang",
# ]
# ///
"""gen_audit.py — audit target libraries for entities that cannot be exported.

Default mode (linkage audit), per library:
  - namespace-scope `static` / internal-linkage functions (the static-inline
    manual-replacement list — M0: 27 target libs should be ~0)
  - anonymous-namespace entities
  - explicit specializations of templates (exported via the primary template
    only; a specialization declared here is lost to module consumers)
  - friend operators (informational: re-exported through the class by ADL)

Output: target/gen/audit/<lib>.txt + stdout summary.

--macros mode (M10, T3 boundary check): macro-surface statistics per library —
  how many macros the library's own public header set #defines (minus #undefs),
  bucketed by canonical macro family (BOOST_PP_/BOOST_MPL_/BOOST_FUSION_...),
  and — for module libs — the entity count of the generated module export list
  for contrast. This is the plan's T3 input ("公共 API 宏注入面"): macro-driven
  libraries keep their macros as the API and stay include-only (a named module
  can never export macros), while module libs keep a minimal macro face inside
  their GMF that never reaches consumers.

Output: target/gen/audit/macro_surface.txt + stdout table.

Usage:
    python scripts/gen_audit.py [--libs optional system ...] [--out target/gen]
    python scripts/gen_audit.py --macros [--libs ...]
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import boost_common as bc

ci = None

# ---------------------------------------------------------------------------
# --macros mode (M10): macro-surface statistics
# ---------------------------------------------------------------------------

# Canonical macro family per macro-driven candidate lib (plan §2: "公共 API
# 宏注入面 (BOOST_PP_/BOOST_FUSION_/BOOST_SPIRIT_ 等族)"); function_types
# upstream spells its config macros BOOST_FT_*, foreach has the bare
# BOOST_FOREACH object macro plus a BOOST_FOREACH_* namespace.
_LIB_MACRO_FAMILY = {
    "preprocessor": ("BOOST_PP_", "BOOST_PREPROCESSOR_"),
    "mpl": ("BOOST_MPL_",),
    "fusion": ("BOOST_FUSION_",),
    "proto": ("BOOST_PROTO_",),
    "spirit": ("BOOST_SPIRIT_",),
    "phoenix": ("BOOST_PHOENIX_",),
    "xpressive": ("BOOST_XPRESSIVE_",),
    "lambda": ("BOOST_LAMBDA_",),
    "lambda2": ("BOOST_LAMBDA2_",),
    "bind": ("BOOST_BIND_",),
    "typeof": ("BOOST_TYPEOF_",),
    "vmd": ("BOOST_VMD_",),
    "parameter": ("BOOST_PARAMETER_",),
    "metaparse": ("BOOST_METAPARSE_",),
    "function_types": ("BOOST_FT_", "BOOST_FUNCTION_TYPES_"),
    "tti": ("BOOST_TTI_",),
    "local_function": ("BOOST_LOCAL_FUNCTION_",),
    "msm": ("BOOST_MSM_",),
    "foreach": ("BOOST_FOREACH",),
    # predef's API is its detection families (BOOST_OS_/BOOST_COMP_/...)
    "predef": ("BOOST_PREDEF", "BOOST_OS_", "BOOST_COMP_", "BOOST_ARCH_",
               "BOOST_HW_", "BOOST_LIB_", "BOOST_PLAT_", "BOOST_ENDIAN_",
               "BOOST_LANG_"),
    "static_assert": ("BOOST_STATIC_ASSERT",),
    "hof": ("BOOST_HOF_",),
    "units": ("BOOST_UNITS_",),
}
# Longest-first so nested families bucket correctly (BOOST_LAMBDA2_ before
# BOOST_LAMBDA_).
_FAMILY_PREFIXES = sorted(
    {p for fams in _LIB_MACRO_FAMILY.values() for p in fams},
    key=len, reverse=True)

_DEFINE_RE = re.compile(
    r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)(\([^)\n]*\))?", re.MULTILINE)
_UNDEF_RE = re.compile(r"^[ \t]*#[ \t]*undef[ \t]+([A-Za-z_]\w*)", re.MULTILINE)


def macro_surface_of(lib, headers):
    """(kinds {name: 'function'|'object'}, header count) — macros #defined in
    the library's own header set minus names #undef'd within the same set.
    Text-level scan: the macro face is a preprocessor notion, not an AST one."""
    kinds, undefed = {}, set()
    n = 0
    for h in headers:
        try:
            text = h.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        n += 1
        for m in _DEFINE_RE.finditer(text):
            kinds[m.group(1)] = "function" if m.group(2) else "object"
        undefed.update(m.group(1) for m in _UNDEF_RE.finditer(text))
    for name in undefed:
        kinds.pop(name, None)
    return kinds, n


def _macro_family(name):
    for prefix in _FAMILY_PREFIXES:
        if name.startswith(prefix):
            return prefix
    return "other"


def _inc_entity_count(lib):
    """Exported-entity count from the generated module export list header
    ('// lib=core ... entities=267'), or None for non-module libs."""
    inc = bc.GEN_DIR / (lib + ".inc")
    if not inc.is_file():
        return None
    m = re.search(r"entities=(\d+)",
                  inc.read_text(encoding="utf-8", errors="ignore")[:400])
    return int(m.group(1)) if m else None


def macro_headers_of(lib):
    """Header set for the macro audit: libs.json entry (module libs), else the
    non-detail heuristic; predef-style pure-.h libs (no .hpp under the root at
    all) get the matching .h set."""
    headers = bc.headers_of(lib)
    if headers:
        return headers
    d = bc.BOOST_ROOT / lib
    out = []
    if d.is_dir():
        out = [p for p in d.rglob("*.h") if p.is_file()
               and "detail" not in p.relative_to(bc.BOOST_ROOT).parts]
    single = bc.BOOST_ROOT / (lib + ".h")
    if single.is_file():
        out.append(single)
    return out


def macros_audit(libs, out):
    """Aggregate macro-surface report → out/'macro_surface.txt' + stdout."""
    rows = []
    for lib in libs:
        kinds, n_headers = macro_surface_of(lib, macro_headers_of(lib))
        fam_counts = Counter(_macro_family(name) for name in kinds)
        own_prefixes = _LIB_MACRO_FAMILY.get(lib, ())
        own = sum(1 for name in kinds
                  if any(name.startswith(p) for p in own_prefixes))
        top = ", ".join("{} {}".format(fam, cnt)
                        for fam, cnt in fam_counts.most_common(3))
        rows.append((lib, n_headers, len(kinds),
                     sum(1 for k in kinds.values() if k == "function"),
                     own, _inc_entity_count(lib), top))
        print("{}: headers={} macros={} (function-like={}) own-family={} "
              "top: {}".format(lib, n_headers, len(kinds),
                               rows[-1][3], own, top))

    t3 = set(bc.LIBS_T3 + bc.LIBS_INCLUDE_ONLY_M9)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "macro_surface.txt", "w", encoding="utf-8") as fh:
        fh.write("# boost-module macro-surface audit (boost 1.91.0) — M10 T3 "
                 "boundary check\n")
        fh.write("# macros = unique names #defined in the library's own "
                 "public header set (libs.json for module libs,\n")
        fh.write("#   boost/<lib>/**.hpp non-detail heuristic otherwise), "
                 "minus #undef'd names.\n")
        fh.write("# Module libs keep this face inside their GMF (macros never "
                 "reach module consumers); include-only\n")
        fh.write("# libs inject it into every consumer TU — hence no module "
                 "(plan §2, user decision §5.3).\n")
        fh.write("# exports = entities in the generated module export list "
                 "(module libs only).\n\n")
        fh.write("{:<18} {:>8} {:>7} {:>9} {:>6} {:>8}\n".format(
            "lib", "headers", "macros", "func-like", "own", "exports"))
        for lib, n_headers, total, nfun, own, exports, _top in rows:
            fh.write("{:<18} {:>8} {:>7} {:>9} {:>6} {:>8}\n".format(
                lib + ("*" if lib in t3 else ""), n_headers, total, nfun,
                own, exports if exports is not None else "-"))
        fh.write("\n# * = include-only (T3 candidate or M9 downgrade)\n")
    print("wrote {}".format(out / "macro_surface.txt"))
    return 0


def _is_explicit_specialization(cursor, tu):
    """`template<>` explicit specializations (see gen_exports for rationale)."""
    try:
        toks = bc.tokens_of(tu, cursor)
    except Exception:
        return False
    if len(toks) < 3:
        return False
    return toks[0].spelling == "template" and toks[1].spelling == "<" and \
        toks[2].spelling in (">", ">>")


def audit_lib(lib, headers, out_dir):
    idx = ci.Index.create()
    bundle = Path(bc.ROOT / "target" / "gen" / "bundles" / (lib + ".cpp"))
    tu = idx.parse(str(bundle), args=bc.CLANG_ARGS,
                   options=ci.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES |
                           ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    file_to_lib = bc.build_file_to_lib()

    static_fns, anon, specs, friends = [], [], [], []

    def rec(cursor, in_anon_ns):
        try:
            kind = str(cursor.kind).replace("CursorKind.", "")
        except Exception:
            kind = "UNKNOWN"
        if kind not in ("NAMESPACE", "FUNCTION_DECL", "FUNCTION_TEMPLATE",
                        "CLASS_DECL", "STRUCT_DECL", "UNION_DECL", "ENUM_DECL",
                        "VAR_DECL", "TYPEDEF_DECL", "TYPE_ALIAS_DECL",
                        "FRIEND_DECL"):
            # expressions/statements: recurse without per-node file lookups
            for child in cursor.get_children():
                rec(child, in_anon_ns)
            return
        f = bc.cursor_file(cursor)
        in_lib = f is not None and bc.home_lib_of_file(f, file_to_lib) == lib

        if kind == "NAMESPACE" and cursor.is_anonymous():
            for child in cursor.get_children():
                rec(child, True)
            return
        if in_lib:
            loc = "{}:{}".format(f.name, cursor.location.line)
            if in_anon_ns and bc.qualified_name(cursor).startswith("boost::"):
                anon.append("{} {}".format(loc, bc.qualified_name(cursor)))
            if kind in ("FUNCTION_DECL", "FUNCTION_TEMPLATE"):
                if bc.namespace_chain(cursor) and not bc.linkage_ok(cursor):
                    static_fns.append("{} {} (linkage={})"
                                      .format(loc, bc.qualified_name(cursor),
                                              cursor.linkage.name))
            if kind in ("FUNCTION_DECL", "FUNCTION_TEMPLATE", "CLASS_DECL",
                        "STRUCT_DECL", "UNION_DECL", "CLASS_TEMPLATE",
                        "CLASS_TEMPLATE_PARTIAL_SPECIALIZATION"):
                if (bc.is_specialization(cursor) or
                        _is_explicit_specialization(cursor, tu)) and \
                        bc.qualified_name(cursor).startswith("boost::"):
                    specs.append("{} {}".format(loc, bc.qualified_name(cursor)))
        for child in cursor.get_children():
            try:
                is_friend = child.kind == ci.CursorKind.FRIEND_DECL
            except ValueError:
                is_friend = False
            if is_friend and in_lib:
                friends.append("{}:{}".format(f.name, child.location.line))
                continue
            rec(child, in_anon_ns)

    rec(tu.cursor, False)

    out = out_dir / (lib + ".txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# audit {} (boost 1.91.0)\n".format(lib))
        fh.write("# {} static/internal free functions\n".format(len(static_fns)))
        fh.write("\n".join(sorted(static_fns)) + "\n\n")
        fh.write("# {} anonymous-namespace entities\n".format(len(anon)))
        fh.write("\n".join(sorted(anon)) + "\n\n")
        fh.write("# {} explicit specializations\n".format(len(specs)))
        fh.write("\n".join(sorted(specs)) + "\n\n")
        fh.write("# {} friend operator decls (info)\n".format(len(friends)))
        fh.write("\n".join(sorted(friends)) + "\n")
    return len(static_fns), len(anon), len(specs), len(friends)


def main() -> int:
    global ci
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--libs", nargs="*", default=None,
                    help="subset of libraries (default: all target libs, "
                         "+T3/include-only candidates in --macros mode)")
    ap.add_argument("--out", type=Path, default=bc.AUDIT_DIR)
    ap.add_argument("--macros", action="store_true",
                    help="macro-surface statistics (M10 T3 boundary check) "
                         "instead of the linkage audit")
    args = ap.parse_args()

    if args.macros:
        libs = args.libs if args.libs is not None else \
            bc.TARGET_LIBS + bc.LIBS_T3 + bc.LIBS_INCLUDE_ONLY_M9
        return macros_audit(libs, args.out)

    ci = bc.get_ci()
    libs = args.libs or bc.TARGET_LIBS
    total = [0, 0, 0, 0]
    for lib in libs:
        headers = bc.headers_of(lib)
        n = audit_lib(lib, headers, args.out)
        total = [t + x for t, x in zip(total, n)]
        print("{}: static={} anon={} specs={} friends={}".format(lib, *n))
    print("TOTAL: static={} anon={} specs={} friends={}".format(*total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
