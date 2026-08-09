#!/usr/bin/env python3
"""gen_audit.py — audit target libraries for entities that cannot be exported.

Reports, per library:
  - namespace-scope `static` / internal-linkage functions (the static-inline
    manual-replacement list — M0: 27 target libs should be ~0)
  - anonymous-namespace entities
  - explicit specializations of templates (exported via the primary template
    only; a specialization declared here is lost to module consumers)
  - friend operators (informational: re-exported through the class by ADL)

Output: target/gen/audit/<lib>.txt + stdout summary.

Usage:
    python scripts/gen_audit.py [--libs optional system ...] [--out target/gen]
"""

import argparse
import sys
from pathlib import Path

import boost_common as bc

ci = None


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
                    help="subset of target libraries (default: all 27)")
    ap.add_argument("--out", type=Path, default=bc.AUDIT_DIR)
    args = ap.parse_args()

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
