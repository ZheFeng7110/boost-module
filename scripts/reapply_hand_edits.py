#!/usr/bin/env python3
"""Re-apply hand edits that scripts/gen_exports.py --emit-cppm overwrites.

Run after ANY full regeneration:

    uv run scripts/gen_exports.py --emit-cppm
    uv run python scripts/reapply_hand_edits.py

Idempotent: each patch is applied only when its anchor is still present
(regeneration restores the anchor). See the M3 doc §3/§5 and the M4 doc §7.

Known costs (M3 §8): .inc platform guards and the .cppm hand-edits below.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def patch(rel, old, new, *, required=True):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    if new in s:
        print(f"  skip   {rel} (already applied)")
        return False
    n = s.count(old)
    if n == 1:
        p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")
        print(f"  patched {rel}")
        return True
    if n == 0:
        if not required:
            print(f"  skip   {rel} (anchor not present, not required)")
            return False
        raise SystemExit(f"{rel}: anchor not found\n  anchor: {old[:80]!r}")
    raise SystemExit(f"{rel}: expected 1 anchor, found {n}\n  anchor: {old[:80]!r}")


def restore_from_git(rel):
    r = subprocess.run(["git", "checkout", "--", rel], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode == 0:
        print(f"  restored {rel} (from git, M3 final form)")
    else:
        print(f"  git checkout failed for {rel}: {r.stderr[:200]}", file=sys.stderr)


def strip_log_version_namespace(rel):
    """Rewrite log.inc to be inline-namespace-agnostic (M11 CI fix, POSIX legs).

    The mingw snapshot qualifies every log entity with the version inline
    namespace `v2s_mt_nt62` (boost/log/detail/config.hpp picks the name by
    platform: v2s_mt_nt62 on Windows, v2s_mt_posix on POSIX). Inline namespaces
    are transparent for qualified lookup from the enclosing namespace, so:

      - `export namespace ... { namespace log { namespace v2s_mt_nt62 { ... }`
        openers drop the `namespace v2s_mt_nt62 {` segment (and its matching
        `}` — the last brace of the block's closing line);
      - `using boost::log::v2s_mt_nt62::X;` lines re-qualify as
        `using boost::log::X;` (resolves through whichever inline namespace is
        active on the compiling platform).

    Idempotent: no-op when `v2s_mt_nt62` is absent.
    """
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    if "v2s_mt_nt62" not in s:
        print(f"  skip   {rel} (no v2s_mt_nt62)")
        return False
    OPEN = " namespace log { namespace v2s_mt_nt62 {"
    out = []
    pending = 0  # dropped openers awaiting one `}` removal at their closer
    for line in s.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        if OPEN in stripped:
            stripped = stripped.replace(OPEN, " namespace log {")
            pending += 1
            out.append(stripped + "\n")
            continue
        body = stripped.rstrip()
        if pending and body and set(body) == {"}"}:
            stripped = body[:-1] + stripped[len(body):]
            pending -= 1
        stripped = stripped.replace("boost::log::v2s_mt_nt62::", "boost::log::")
        out.append(stripped + "\n")
    p.write_text("".join(out), encoding="utf-8", newline="\n")
    print(f"  stripped {rel} (version inline namespace, {pending} unclosed)")
    return True


def guard_entity_lines(rel, cond, names):
    """Wrap each `  using boost::...;` line whose entity appears in `names`
    (as a ::-delimited segment) in `#if cond` / `#endif`. Idempotent — a line
    already sitting between a #if/#endif pair is left alone.

    M6: the committed .inc files are a mingw-flavor snapshot, so Windows-only
    entities (guarded by #if defined(_WIN32) in the upstream headers) must not
    be exported on POSIX. This mirrors the upstream header condition in the
    module surface instead of hard-coding per-platform .inc files.
    """
    import re
    p = ROOT / rel
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    out = []
    changed = 0
    for i, line in enumerate(lines):
        prev_is_if = bool(out) and out[-1].lstrip().startswith("#if ")
        next_is_endif = (i + 1 < len(lines)) and lines[i + 1].lstrip().startswith("#endif")
        if prev_is_if or next_is_endif:
            out.append(line)
            continue
        stripped = line.strip()
        m = re.fullmatch(r"using boost::([A-Za-z0-9_:]+);", stripped)
        if m is None:
            out.append(line)
            continue
        segments = m.group(1).split("::")
        if any(seg in names for seg in segments):
            out.append(f"#if {cond}\n")
            out.append(line)
            out.append("#endif\n")
            changed += 1
        else:
            out.append(line)
    if changed:
        p.write_text("".join(out), encoding="utf-8", newline="\n")
        print(f"  guarded {changed} entity line(s) in {rel}")


def main():
    print("reapplying hand edits...")

    # ---- .cppm (M3 §3 + M4 §7) ----
    patch("src/core.cppm",
          "export module boost.core;\n\n#include \"gen_exports/core.inc\"",
          "export module boost.core;\n\n"
          "// 对象宏 re-homing (M3): 宏无法跨模块导出。上游 <boost/version.hpp> 的对象宏\n"
          "// 以 boost:: 命名空间 constexpr 重置于此 (拼写保持): 消费者 import 后可用\n"
          "// boost::BOOST_VERSION。值须与 deps/boost/boost/version.hpp 一致 — tests/macros.cpp\n"
          "// 在旁路头 (include/boost-module/macros.hpp) 参与下交叉校验。\n"
          "// 注意: 同一 TU 中若定义了同名宏 (include <boost-module/macros.hpp>), 宏展开会\n"
          "// 吞掉 boost::BOOST_VERSION 拼写 (→ boost::109100), 两种拼写互斥, 二选一。\n"
          "export namespace boost {\n"
          "  constexpr int BOOST_VERSION = 109100;\n"
          "  constexpr const char* BOOST_LIB_VERSION = \"1_91\";\n"
          "}\n\n"
          "#include \"gen_exports/core.inc\"",
          required=False)  # git restore below covers it
    patch("src/json.cppm",
          "module;\n#include <boost/json/debug_printers.hpp>\n#include <boost/json/src.hpp>",
          "module;\n// M4: 定义移入库 TU src/src.cpp, GMF 不再 include src.hpp (防双定义) — 2026-08-11-m4-compiled-libs.md §4\n"
          "#include <boost/json/debug_printers.hpp>\n#include <boost/json.hpp>",
          required=False)
    patch("src/stacktrace.cppm",
          "module;\n#include <boost/stacktrace.hpp>",
          "module;\n// M4: BOOST_STACKTRACE_LINK 切到外链模式, 定义来自 libs/stacktrace/src/basic.cpp — 2026-08-11-m4-compiled-libs.md §3\n"
          "#define BOOST_STACKTRACE_LINK\n#include <boost/stacktrace.hpp>")
    # scope.cppm: no `export import boost.core;` — gcc 16.1.0 ICEs when this
    # GMF include set (unique_fd.hpp etc.) re-exports boost.core (M3 §3.2).
    patch("src/scope.cppm",
          "export module boost.scope;\n\nexport import boost.core;\n",
          "export module boost.scope;\n\n"
          "// NB: no `export import boost.core;` — gcc 16.1.0 ICEs (Segmentation fault at\n"
          "// the export-module line) when this GMF include set (which pulls\n"
          "// unique_fd.hpp, whose entities depend on boost.core) is combined with\n"
          "// re-exporting boost.core. scope.inc carries no boost::core:: entities (they\n"
          "// are claimed by boost.core itself), so consumers import boost.core on their\n"
          "// own. (Clang has no such issue; tracked as a gcc bug for M6 CI.)\n")

    # M9: winapi.cppm — boost/winapi/* headers are Windows-only (basic_types.hpp
    # #errors "Win32 functions not available" off-Windows). The winapi module
    # is in the default closure (system/thread imply it + `export import
    # boost.winapi;`), so on POSIX it must compile as a valid empty module.
    # Guards mirror basic_types.hpp. Three patches: open the GMF guard at the
    # first include, close it before `export module`, and guard the .inc.
    patch("src/winapi.cppm",
          "module;\n#include <boost/winapi/bcrypt.hpp>",
          "module;\n"
          "// M9 platform guard: boost/winapi/* #error off-Windows (basic_types.hpp).\n"
          "#if defined(_WIN32) || defined(__CYGWIN__)\n"
          "#include <boost/winapi/bcrypt.hpp>")
    patch("src/winapi.cppm",
          "#include <boost/winapi/waitable_timer.hpp>\n\nexport module boost.winapi;",
          "#include <boost/winapi/waitable_timer.hpp>\n#endif\n\nexport module boost.winapi;")
    patch("src/winapi.cppm",
          '#include "gen_exports/winapi.inc"\n',
          '#if defined(_WIN32) || defined(__CYGWIN__)\n'
          '#include "gen_exports/winapi.inc"\n'
          '#endif\n')

    # M9: safe_numerics.cppm — checked_result_operations.hpp calls std::terminate
    # without including <exception>; on libstdc++/libc++ <cassert> does not
    # transitively pull <exception> (it does on MSVC STL), so the GMF compile
    # fails on POSIX. Add the missing include upfront.
    patch("src/safe_numerics.cppm",
          "module;\n#include <boost/safe_numerics/automatic.hpp>",
          "module;\n"
          "// M9: checked_result_operations.hpp uses std::terminate without <exception>;\n"
          "// libstdc++/libc++ <cassert> doesn't transitively include it (MSVC STL does).\n"
          "#include <exception>\n"
          "#include <boost/safe_numerics/automatic.hpp>")

    # ---- .inc platform guards (M3 §5) ----
    # M9: int128_type/uint128_type are declared in boost/config/suffix.hpp, so
    # with boost.config as a module they moved from core.inc to config.inc.
    patch("src/gen_exports/config.inc",
          "  using boost::int128_type;",
          "#if defined(BOOST_HAS_INT128)\n  // M3 hand-guard (M9: moved to config.inc): suffix.hpp defines int128_type only where BOOST_HAS_INT128.\n  using boost::int128_type;\n#endif")
    patch("src/gen_exports/config.inc",
          "  using boost::uint128_type;",
          "#if defined(BOOST_HAS_INT128)\n  // M3 hand-guard (M9: moved to config.inc): suffix.hpp defines uint128_type only where BOOST_HAS_INT128.\n  using boost::uint128_type;\n#endif")
    patch("src/gen_exports/core.inc",
          "  using boost::core::detail::copysign_impl;",
          "#if defined(__GNUC__)\n  // M3 hand-guard: boost/core/cmath.hpp defines copysign_impl only on gcc-like compilers.\n  using boost::core::detail::copysign_impl;\n#endif")
    # M6 platform guards: snapshot = mingw flavor; Windows-only entities are absent
    # on POSIX (or live in a different namespace), so the module TU must not export
    # them there. Guards mirror the upstream header conditions.
    patch("src/gen_exports/core.inc",
          "  using boost::core::detail::sp_thread_sleep;\n  using boost::core::detail::sp_thread_yield;",
          "#if defined(_WIN32) || defined(__WIN32__) || defined(__CYGWIN__)\n"
          "  // M6 platform guard: sp_thread_sleep/yield live in boost::core::detail only on Windows;\n"
          "  // on POSIX (nanosleep/sched_yield branch of the header) they are declared in boost::core.\n"
          "  using boost::core::detail::sp_thread_sleep;\n"
          "  using boost::core::detail::sp_thread_yield;\n"
          "#else\n"
          "  using boost::core::sp_thread_sleep;\n"
          "  using boost::core::sp_thread_yield;\n"
          "#endif")
    patch("src/gen_exports/system.inc",
          "  using boost::system::detail::is_value_convertible_to;\n"
          "  using boost::system::detail::local_free;\n"
          "  using boost::system::detail::lock_guard;\n"
          "  using boost::system::detail::message_cp_win32;\n"
          "  using boost::system::detail::reference_to_temporary;",
          "  using boost::system::detail::is_value_convertible_to;\n"
          "#if defined(BOOST_WINDOWS_API)\n"
          "  // M6 platform guard: snapshot = mingw flavor; these boost/system/detail entities\n"
          "  // exist only under BOOST_WINDOWS_API (system_category_message_win32.hpp / condition).\n"
          "  using boost::system::detail::local_free;\n"
          "  using boost::system::detail::message_cp_win32;\n"
          "#endif\n"
          "  using boost::system::detail::lock_guard;\n"
          "  using boost::system::detail::reference_to_temporary;")
    patch("src/gen_exports/system.inc",
          "  using boost::system::detail::system_cat_holder;\n"
          "  using boost::system::detail::system_category_condition_win32;\n"
          "  using boost::system::detail::system_category_message_win32;\n"
          "  using boost::system::detail::system_error_category;\n"
          "  using boost::system::detail::system_error_category_message;\n"
          "  using boost::system::detail::unknown_message_win32;",
          "  using boost::system::detail::system_cat_holder;\n"
          "#if defined(BOOST_WINDOWS_API)\n"
          "  // M6 platform guard: as above.\n"
          "  using boost::system::detail::system_category_condition_win32;\n"
          "  using boost::system::detail::system_category_message_win32;\n"
          "#endif\n"
          "  using boost::system::detail::system_error_category;\n"
          "  using boost::system::detail::system_error_category_message;\n"
          "#if defined(BOOST_WINDOWS_API)\n"
          "  // M6 platform guard: as above.\n"
          "  using boost::system::detail::unknown_message_win32;\n"
          "#endif")
    patch("src/gen_exports/system.inc",
          "export namespace boost { namespace system { namespace windows_error {\n"
          "  using boost::system::windows_error::make_error_code;",
          "#if defined(BOOST_WINDOWS_API)\n"
          "export namespace boost { namespace system { namespace windows_error {\n"
          "  using boost::system::windows_error::make_error_code;")
    patch("src/gen_exports/system.inc",
          "  using boost::system::windows_error::windows_error_code::wrong_disk;\n}}}\n\nexport namespace boost { namespace variant2 {",
          "  using boost::system::windows_error::windows_error_code::wrong_disk;\n}}}\n#endif\n\nexport namespace boost { namespace variant2 {")

    # M6: program_options winmain splitter — <boost/program_options/winmain.hpp>
    # is pulled into the GMF only on Windows.
    patch("src/gen_exports/program_options.inc",
          "  using boost::program_options::split_winmain;",
          "#if defined(_WIN32)\n  // M6 platform guard: winmain.hpp (split_winmain) is Windows-only.\n  using boost::program_options::split_winmain;\n#endif")

    # M7c: gcc 16.1.0 module consumers emit a partial vtable for clone_impl<T>
    # (virtual base clone_base) whose thunk slots stay undefined — gcc never
    # emits the thunks in a module consumer TU (ELF link: undefined reference
    # to the virtual/non-virtual thunks, cf. linux-gcc CI). extern-template
    # declarations visible through the module interface suppress the consumer's
    # implicit instantiation; the complete vtable + thunks come from the
    # explicit instantiation in src/boost_thread_extras.cpp.
    patch("src/gen_exports/thread.inc",
          "  using boost::broken_promise;\n"
          "  using boost::call_once;",
          "  using boost::broken_promise;\n"
          "  // M7c: gcc 16.1.0 module consumers emit a partial vtable for clone_impl<T>\n"
          "  // (virtual base clone_base) whose thunk slots stay undefined — gcc never\n"
          "  // emits the thunks in a module consumer TU. These extern-template\n"
          "  // declarations suppress the consumer's implicit instantiation; the complete\n"
          "  // vtable + thunks come from the explicit instantiation in\n"
          "  // src/boost_thread_extras.cpp (same pattern as boost_system_extras.cpp).\n"
          "  extern template class boost::exception_detail::clone_impl<boost::broken_promise>;\n"
          "  extern template class boost::exception_detail::clone_impl<boost::unknown_exception>;\n"
          "  extern template class boost::exception_detail::clone_impl<boost::exception_detail::std_exception_ptr_wrapper>;\n"
          "  using boost::call_once;")

    # M9: leaf — same gcc 16.1.0 consumer-thunk bug as thread's clone_impl
    # (M7c), for leaf::detail::exception<bad_result> (multi-base
    # exception_base/error_id → non-virtual thunks). extern template in the
    # module interface + explicit instantiation in src/boost_leaf_extras.cpp.
    patch("src/gen_exports/leaf.inc",
          "  using boost::leaf::detail::exception;\n"
          "  using boost::leaf::detail::exception_base;",
          "  using boost::leaf::detail::exception;\n"
          "  // M9: gcc 16.1.0 module consumers emit a partial vtable for\n"
          "  // exception<bad_result> (multi-base exception_base/error_id) whose\n"
          "  // non-virtual thunks stay undefined — gcc never emits them in a module\n"
          "  // consumer TU. This extern template suppresses the consumer's implicit\n"
          "  // instantiation; the complete vtable + thunks come from the explicit\n"
          "  // instantiation in src/boost_leaf_extras.cpp (same pattern as thread's\n"
          "  // clone_impl, cf. M7c).\n"
          "  extern template class boost::leaf::detail::exception<boost::leaf::bad_result>;\n"
          "  using boost::leaf::detail::exception_base;")

    # M7: url module — grammar/detail/charset.hpp defines find_if_pred /
    # find_if_not_pred only under BOOST_URL_USE_SSE2 (x86 + SSE2); the mingw
    # x86_64 snapshot carried them, but macOS arm64 (no __SSE2__) fails.
    patch("src/gen_exports/url.inc",
          "  using boost::urls::grammar::detail::find_if_not_pred;\n"
          "  using boost::urls::grammar::detail::find_if_pred;",
          "#if defined(BOOST_URL_USE_SSE2)\n"
          "  // M7 platform guard: charset.hpp defines the *_pred SSE2 helpers only under\n"
          "  // BOOST_URL_USE_SSE2 (x86 with SSE2); absent on arm64 (e.g. macOS).\n"
          "  using boost::urls::grammar::detail::find_if_not_pred;\n"
          "  using boost::urls::grammar::detail::find_if_pred;\n"
          "#endif")

    # M9: decimal — the mingw snapshot carries 128-bit / 80-bit-long-double
    # entities that the MSVC ABI never declares (BOOST_DECIMAL_HAS_INT128 is
    # off under _MSC_VER, and MSVC long double is 53-bit so the
    # LDBL_MANT_DIG==64 branch is absent). Guards mirror the upstream header
    # conditions in decimal/detail/config.hpp / bit_layouts.hpp.
    patch("src/gen_exports/decimal.inc",
          "  using boost::decimal::detail::builtin_int128_t;\n"
          "  using boost::decimal::detail::builtin_uint128_t;",
          "#if defined(BOOST_DECIMAL_HAS_INT128)\n"
          "  // M9 platform guard: config.hpp defines the __int128 typedefs only where\n"
          "  // BOOST_DECIMAL_HAS_INT128 (off under the MSVC ABI).\n"
          "  using boost::decimal::detail::builtin_int128_t;\n"
          "  using boost::decimal::detail::builtin_uint128_t;\n"
          "#endif")
    patch("src/gen_exports/decimal.inc",
          "  using boost::decimal::detail::ieee754_binary80;",
          "#if LDBL_MANT_DIG == 64 && LDBL_MAX_EXP == 16384\n"
          "  // M9 platform guard: bit_layouts.hpp defines ieee754_binary80 only for 80-bit\n"
          "  // long double (x86-64 gcc/mingw); MSVC long double is 53-bit.\n"
          "  using boost::decimal::detail::ieee754_binary80;\n"
          "#endif")
    patch("src/gen_exports/decimal.inc",
          "  using boost::decimal::detail::impl::builtin_128_pow10;",
          "#if defined(BOOST_DECIMAL_HAS_INT128)\n"
          "  // M9 platform guard: power_tables.hpp defines builtin_128_pow10 only under\n"
          "  // BOOST_DECIMAL_HAS_INT128.\n"
          "  using boost::decimal::detail::impl::builtin_128_pow10;\n"
          "#endif")

    # M9: per-lib MSVC-flavor guards — the mingw snapshot carries entities
    # that the MSVC ABI never declares (compiler-specific branches). Guards
    # mirror the upstream header conditions.
    # dll: the itanium demangling parser (dll/detail/demangling/itanium.hpp)
    # is selected only outside _MSC_VER (ctor_dtor.hpp).
    patch("src/gen_exports/dll.inc",
          "  using boost::dll::detail::parser::arg_list;\n"
          "  using boost::dll::detail::parser::const_rule;\n"
          "  using boost::dll::detail::parser::const_rule_impl;\n"
          "  using boost::dll::detail::parser::dummy;\n"
          "  using boost::dll::detail::parser::parse_type;\n"
          "  using boost::dll::detail::parser::parse_type_helper;\n"
          "  using boost::dll::detail::parser::pure_type;\n"
          "  using boost::dll::detail::parser::reference_rule;\n"
          "  using boost::dll::detail::parser::reference_rule_impl;\n"
          "  using boost::dll::detail::parser::type_name;\n"
          "  using boost::dll::detail::parser::volatile_rule;\n"
          "  using boost::dll::detail::parser::volatile_rule_impl;",
          "#if !defined(_MSC_VER)\n"
          "  // M9 platform guard: the itanium demangling parser (demangling/itanium.hpp)\n"
          "  // is selected only outside _MSC_VER (dll/detail/ctor_dtor.hpp).\n"
          "  using boost::dll::detail::parser::arg_list;\n"
          "  using boost::dll::detail::parser::const_rule;\n"
          "  using boost::dll::detail::parser::const_rule_impl;\n"
          "  using boost::dll::detail::parser::dummy;\n"
          "  using boost::dll::detail::parser::parse_type;\n"
          "  using boost::dll::detail::parser::parse_type_helper;\n"
          "  using boost::dll::detail::parser::pure_type;\n"
          "  using boost::dll::detail::parser::reference_rule;\n"
          "  using boost::dll::detail::parser::reference_rule_impl;\n"
          "  using boost::dll::detail::parser::type_name;\n"
          "  using boost::dll::detail::parser::volatile_rule;\n"
          "  using boost::dll::detail::parser::volatile_rule_impl;\n"
          "#endif")
    # functional / poly_collection: gcc-preprocessed mpl vector/map aux headers
    # (BOOST_MPL_CFG_COMPILER_DIR=gcc, set under __GNUC__ — same pattern as the
    # M3 variant.inc guards).
    patch("src/gen_exports/functional.inc",
          "  using boost::mpl::v_at_impl;\n"
          "  using boost::mpl::v_item;\n"
          "  using boost::mpl::v_iter;\n"
          "  using boost::mpl::v_mask;",
          "#if defined(__GNUC__)\n"
          "  // M9 platform guard: gcc-preprocessed mpl vector headers only.\n"
          "  using boost::mpl::v_at_impl;\n"
          "  using boost::mpl::v_item;\n"
          "#endif\n"
          "  using boost::mpl::v_iter;\n"
          "#if defined(__GNUC__)\n"
          "  using boost::mpl::v_mask;\n"
          "#endif")
    patch("src/gen_exports/poly_collection.inc",
          "  using boost::mpl::item_by_order_impl;",
          "#if defined(__GNUC__)\n"
          "  // M9 platform guard: gcc-preprocessed mpl map headers only.\n"
          "  using boost::mpl::item_by_order_impl;\n"
          "#endif")
    # intrusive: builtin_clz_dispatch — the __GNUC__ branch of the BSR
    # intrinsic chain (intrusive/detail/math.hpp).
    patch("src/gen_exports/intrusive.inc",
          "  using boost::intrusive::detail::builtin_clz_dispatch;",
          "#if defined(__GNUC__)\n"
          "  // M9 platform guard: math.hpp defines builtin_clz_dispatch only in the\n"
          "  // __GNUC__ branch of the BSR intrinsic chain.\n"
          "  using boost::intrusive::detail::builtin_clz_dispatch;\n"
          "#endif")
    # dll: demangle_symbol is part of the itanium demangling surface (only
    # outside _MSC_VER).
    patch("src/gen_exports/dll.inc",
          "  using boost::dll::experimental::demangle_symbol;",
          "#if !defined(_MSC_VER)\n"
          "  // M9 platform guard: demangle_symbol comes from demangling/itanium.hpp.\n"
          "  using boost::dll::experimental::demangle_symbol;\n"
          "#endif")
    # range: `using std::random_shuffle;` — std::random_shuffle was removed in
    # C++17; only libstdc++ still ships it (mingw gate passes), MSVC STL and
    # libc++ do not.
    patch("src/gen_exports/range.inc",
          "  using std::random_shuffle;",
          "#if defined(__GLIBCXX__)\n"
          "  // M9 platform guard: std::random_shuffle was removed in C++17; only\n"
          "  // libstdc++ (mingw/linux-gcc) still provides it.\n"
          "  using std::random_shuffle;\n"
          "#endif")
    # thread: boost::make_signed/make_unsigned reach the thread GMF only via
    # atomic/detail/type_traits/make_signed.hpp, which pulls
    # boost/type_traits/make_signed.hpp only under BOOST_HAS_INT128 (under the
    # MSVC ABI it uses std::make_signed instead).
    # M11: boost.atomic may now claim them — best-effort.
    patch("src/gen_exports/thread.inc",
          "  using boost::make_signed;\n"
          "  using boost::make_strict_lock;",
          "#if defined(BOOST_HAS_INT128)\n"
          "  // M9 platform guard: boost::make_signed is declared only where\n"
          "  // BOOST_HAS_INT128 (atomic/detail/type_traits/make_signed.hpp); under the\n"
          "  // MSVC ABI the atomic headers use std::make_signed instead.\n"
          "  using boost::make_signed;\n"
          "#endif\n"
          "  using boost::make_strict_lock;",
          required=False)
    patch("src/gen_exports/thread.inc",
          "  using boost::make_unsigned;\n"
          "  using boost::memory_order;",
          "#if defined(BOOST_HAS_INT128)\n"
          "  using boost::make_unsigned;\n"
          "#endif\n"
          "  using boost::memory_order;",
          required=False)

    # M11: math — float80_t / float_fast80_t / float_least80_t are the
    # cstdfloat long-double typedefs (cstdfloat_types.hpp), declared only for
    # 80-bit long double (same condition family as the M9 decimal guard).
    for name in ["float80_t", "float_fast80_t", "float_least80_t"]:
        patch("src/gen_exports/math.inc",
              f"  using boost::{name};",
              f"#if LDBL_MANT_DIG == 64 && LDBL_MAX_EXP == 16384\n"
              f"  // M11 platform guard: cstdfloat_types.hpp declares the 80-bit long-double\n"
              f"  // typedefs only where long double really is 80-bit; MSVC long double is 53-bit.\n"
              f"  using boost::{name};\n"
              f"#endif")
    # M11 CI fix (POSIX llvm legs): the statistics parallel impls exist only
    # under BOOST_MATH_EXEC_COMPATIBLE (tools/config.hpp: requires
    # BOOST_MATH_NO_CXX17_HDR_EXECUTION to stay undefined — libc++ provides
    # <execution> without __cpp_lib_execution, so the macro is absent there),
    # while the MSVC/libstdc++ snapshot faces define it. Guard the three
    # affected using-lines with the exact upstream condition.
    for name in ["chatterjee_correlation_par_impl",
                 "correlation_coefficient_parallel_impl",
                 "means_and_covariance_parallel_impl"]:
        patch("src/gen_exports/math.inc",
              f"  using boost::math::statistics::detail::{name};",
              f"#if defined(BOOST_MATH_EXEC_COMPATIBLE)\n"
              f"  // M11 CI platform guard: statistics {name} is defined only under\n"
              f"  // BOOST_MATH_EXEC_COMPATIBLE (chatterjee_correlation.hpp /\n"
              f"  // bivariate_statistics.hpp); libc++ lacks __cpp_lib_execution.\n"
              f"  using boost::math::statistics::detail::{name};\n"
              f"#endif")
    # M11: iostreams — codecvt_impl exists only on the libstdc++/older-dinkumware
    # workaround paths (detail/codecvt_helper.hpp); MSVC STL declares neither.
    patch("src/gen_exports/iostreams.inc",
          "  using boost::iostreams::detail::codecvt_impl;",
          "#if defined(BOOST_IOSTREAMS_NO_PRIMARY_CODECVT_DEFINITION) || \\\n"
          "    defined(BOOST_IOSTREAMS_EMPTY_PRIMARY_CODECVT_DEFINITION) || \\\n"
          "    defined(BOOST_IOSTREAMS_NO_LOCALE)\n"
          "  // M11 platform guard: detail/codecvt_helper.hpp declares codecvt_impl only\n"
          "  // on these std::codecvt workaround paths (libstdc++ mingw snapshot); the\n"
          "  // MSVC STL takes none of them.\n"
          "  using boost::iostreams::detail::codecvt_impl;\n"
          "#endif")
    # M11: process — asio selects posix_thread when BOOST_ASIO_HAS_PTHREADS
    # (asio/detail/thread.hpp checks pthreads BEFORE windows; mingw-gcc defines
    # it via boost config's BOOST_HAS_PTHREADS). The MSVC flavor uses win_thread
    # and never declares posix_thread.
    patch("src/gen_exports/process.inc",
          "  using boost::asio::detail::posix_thread;",
          "#if defined(BOOST_ASIO_HAS_PTHREADS)\n"
          "  // M11 platform guard: asio/detail/thread.hpp includes posix_thread.hpp only\n"
          "  // under BOOST_ASIO_HAS_PTHREADS (mingw snapshot); the MSVC flavor takes\n"
          "  // win_thread.\n"
          "  using boost::asio::detail::posix_thread;\n"
          "#endif")
    # M11 CI fix (POSIX legs): the process GMF includes ten windows-only headers
    # (v1/windows.hpp, v2/windows/*, windows/* launchers) — boost/winapi
    # basic_types.hpp #errors off-Windows, same reason as the M9 winapi.cppm
    # guard. The remaining GMF includes self-guard per-platform upstream.
    patch("src/process.cppm",
          "#include <boost/process/v1/extend.hpp>\n"
          "#include <boost/process/v1/windows.hpp>\n"
          "#include <boost/process/v2/windows/show_window.hpp>\n"
          "#include <boost/process/v2/windows/with_logon_launcher.hpp>\n"
          "#include <boost/process/v2/windows/with_token_launcher.hpp>\n"
          "#include <boost/process/windows/as_user_launcher.hpp>\n"
          "#include <boost/process/windows/creation_flags.hpp>\n"
          "#include <boost/process/windows/default_launcher.hpp>\n"
          "#include <boost/process/windows/show_window.hpp>\n"
          "#include <boost/process/windows/with_logon_launcher.hpp>\n"
          "#include <boost/process/windows/with_token_launcher.hpp>\n",
          "#include <boost/process/v1/extend.hpp>\n"
          "// M11 platform guard: v1/v2 windows launchers are Windows-only headers\n"
          "// (boost/winapi basic_types.hpp #errors off-Windows); M9 winapi.cppm\n"
          "// convention. POSIX face = platform-neutral + posix-self-guarded surface.\n"
          "#if defined(_WIN32) || defined(__CYGWIN__)\n"
          "#include <boost/process/v1/windows.hpp>\n"
          "#include <boost/process/v2/windows/show_window.hpp>\n"
          "#include <boost/process/v2/windows/with_logon_launcher.hpp>\n"
          "#include <boost/process/v2/windows/with_token_launcher.hpp>\n"
          "#include <boost/process/windows/as_user_launcher.hpp>\n"
          "#include <boost/process/windows/creation_flags.hpp>\n"
          "#include <boost/process/windows/default_launcher.hpp>\n"
          "#include <boost/process/windows/show_window.hpp>\n"
          "#include <boost/process/windows/with_logon_launcher.hpp>\n"
          "#include <boost/process/windows/with_token_launcher.hpp>\n"
          "#endif\n")
    # M11 CI fix (POSIX legs), second step: the mingw snapshot's GMF reached the
    # v2 core (basic_process) and the launcher detail helpers only through the
    # windows launcher chain; on POSIX include the cross-platform core and the
    # posix default launcher explicitly so the shared-surface `using` lines
    # resolve.
    patch("src/process.cppm",
          "#include <boost/process/windows/with_token_launcher.hpp>\n"
          "#endif\n\nexport module boost.process;",
          "#include <boost/process/windows/with_token_launcher.hpp>\n"
          "#endif\n"
          "// M11 platform guard (POSIX): the mingw snapshot's GMF reached the v2\n"
          "// core (basic_process) and the launcher detail helpers only through the\n"
          "// windows launcher chain; on POSIX include the cross-platform core and\n"
          "// the posix default launcher explicitly so the shared-surface `using`\n"
          "// lines resolve.\n"
          "#if !defined(_WIN32) && !defined(__CYGWIN__)\n"
          "#include <boost/process/v2/process.hpp>\n"
          "#include <boost/process/v2/posix/default_launcher.hpp>\n"
          "#endif\n\nexport module boost.process;")
    # M11 CI fix (POSIX legs): windows-only entities in process.inc — the
    # windows-flavored snapshot exports them, but their headers are only pulled
    # by the windows GMF branches above. Conditions mirror upstream:
    # asio windows services under BOOST_ASIO_WINDOWS (= _WIN32), process
    # v1/v2 windows detail under BOOST_WINDOWS_API (= _WIN32).
    patch("src/gen_exports/process.inc",
          "  using boost::asio::detail::win_object_handle_service;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: win_object_handle_service is the asio windows\n"
          "  // branch (BOOST_ASIO_WINDOWS); POSIX asio never declares it.\n"
          "  using boost::asio::detail::win_object_handle_service;\n"
          "#endif")
    patch("src/gen_exports/process.inc",
          "export namespace boost { namespace asio { namespace windows {\n"
          "  using boost::asio::windows::basic_object_handle;\n"
          "  using boost::asio::windows::basic_overlapped_handle;\n"
          "  using boost::asio::windows::basic_stream_handle;\n"
          "  using boost::asio::windows::object_handle;\n"
          "  using boost::asio::windows::stream_handle;\n"
          "}}}",
          "#if defined(_WIN32)\n"
          "export namespace boost { namespace asio { namespace windows {\n"
          "  // M11 platform guard: asio/windows/* handle types are Windows-only\n"
          "  // (BOOST_ASIO_WINDOWS); POSIX asio never declares them.\n"
          "  using boost::asio::windows::basic_object_handle;\n"
          "  using boost::asio::windows::basic_overlapped_handle;\n"
          "  using boost::asio::windows::basic_stream_handle;\n"
          "  using boost::asio::windows::object_handle;\n"
          "  using boost::asio::windows::stream_handle;\n"
          "}}}\n"
          "#endif")
    patch("src/gen_exports/process.inc",
          "export namespace boost { namespace process { namespace v1 { namespace detail { namespace windows {\n"
          "  using boost::process::v1::detail::windows::apply_out_handles;",
          "#if defined(_WIN32)\n"
          "export namespace boost { namespace process { namespace v1 { namespace detail { namespace windows {\n"
          "  // M11 platform guard: v1 detail windows impls (incl. the NT workaround\n"
          "  // block below) are declared only by the windows GMF branches.\n"
          "  using boost::process::v1::detail::windows::apply_out_handles;")
    patch("src/gen_exports/process.inc",
          "  using boost::process::v1::detail::windows::workaround::set_information_job_object;\n"
          "}}}}}}\n",
          "  using boost::process::v1::detail::windows::workaround::set_information_job_object;\n"
          "}}}}}}\n"
          "#endif\n")
    patch("src/gen_exports/process.inc",
          "  using boost::process::v2::detail::basic_process_handle_win;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: basic_process_handle_win is the windows variant\n"
          "  // (detail/process_handle_windows.hpp); POSIX takes process_handle_fd.\n"
          "  using boost::process::v2::detail::basic_process_handle_win;\n"
          "#endif")
    patch("src/gen_exports/process.inc",
          "  using boost::process::v2::detail::open_process_;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: open_process_ lives in detail/process_handle_windows.hpp.\n"
          "  using boost::process::v2::detail::open_process_;\n"
          "#endif")
    # M11 CI fix (POSIX legs): the process_handle_windows detail helpers have no
    # fd-variant counterparts (basic_process_handle_fd implements them inline);
    # is_exec_type is in detail/environment_win.hpp. All Windows-only.
    for name in ["check_handle_", "check_pid_", "check_running_", "get_exit_code_",
                 "interrupt_", "request_exit_", "resume_", "suspend_",
                 "terminate_", "terminate_if_running_"]:
        patch("src/gen_exports/process.inc",
              f"  using boost::process::v2::detail::{name};",
              f"#if defined(_WIN32)\n  // M11 platform guard: {name} lives in detail/process_handle_windows.hpp (no fd-variant counterpart).\n  using boost::process::v2::detail::{name};\n#endif")
    patch("src/gen_exports/process.inc",
          "  using boost::process::v2::environment::detail::is_exec_type;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: is_exec_type lives in detail/environment_win.hpp;\n"
          "  // POSIX environment detail does not declare it.\n"
          "  using boost::process::v2::environment::detail::is_exec_type;\n"
          "#endif")
    # M11 CI fix (POSIX legs): the generic-launcher initializer machinery
    # (probe/invoke/has_* + all_are_initializers/is_initializer + base/derived)
    # is flat in boost::process::v2::detail on Windows (windows/default_launcher.hpp)
    # but nested under v2::posix::detail with a different name set on POSIX
    # (fork-based launchers have no initializer-probe support), so these shared
    # .inc lines only resolve on Windows.
    for name in ["all_are_initializers", "base", "derived",
                 "has_on_error", "has_on_setup", "has_on_success",
                 "invoke_on_error", "invoke_on_setup", "invoke_on_success",
                 "is_initializer", "on_error", "on_setup", "on_success",
                 "probe_on_error", "probe_on_setup", "probe_on_success"]:
        patch("src/gen_exports/process.inc",
              f"  using boost::process::v2::detail::{name};",
              f"#if defined(_WIN32)\n  // M11 platform guard: {name} is the windows generic-launcher machinery (flat v2::detail); POSIX nests a different set under v2::posix::detail.\n  using boost::process::v2::detail::{name};\n#endif")
    patch("src/gen_exports/process.inc",
          "export namespace boost { namespace process { namespace v2 { namespace windows {\n"
          "  using boost::process::v2::windows::as_user_launcher;\n"
          "  using boost::process::v2::windows::default_launcher;\n"
          "  using boost::process::v2::windows::process_creation_flags;\n"
          "  using boost::process::v2::windows::process_show_window;\n"
          "  using boost::process::v2::windows::with_logon_launcher;\n"
          "  using boost::process::v2::windows::with_token_launcher;\n"
          "}}}}",
          "#if defined(_WIN32)\n"
          "export namespace boost { namespace process { namespace v2 { namespace windows {\n"
          "  // M11 platform guard: v2 windows launchers are Windows-only headers.\n"
          "  using boost::process::v2::windows::as_user_launcher;\n"
          "  using boost::process::v2::windows::default_launcher;\n"
          "  using boost::process::v2::windows::process_creation_flags;\n"
          "  using boost::process::v2::windows::process_show_window;\n"
          "  using boost::process::v2::windows::with_logon_launcher;\n"
          "  using boost::process::v2::windows::with_token_launcher;\n"
          "}}}}\n"
          "#endif")

    # M11: graph — graph's bundle transitively pulls multiprecision/proto/
    # serialization interop headers; their directive-expansion/injection
    # leaks export entities that the MSVC ABI never declares (BOOST_HAS_INT128
    # is off under the clang-msvc flavor; proto's extended-template matching is
    # gcc-specific). Guards mirror the upstream header conditions.
    for name in ["int128_type", "uint128_type"]:
        patch("src/gen_exports/graph.inc",
              f"  using boost::multiprecision::{name};",
              f"#if defined(BOOST_HAS_INT128)\n  // M11 platform guard: standalone_config.hpp declares multiprecision::{name} only under BOOST_HAS_INT128 (off under the clang-msvc flavor).\n  using boost::multiprecision::{name};\n#endif")
    for name in ["template_arity", "template_arity_helper", "template_arity_impl2"]:
        patch("src/gen_exports/graph.inc",
              f"  using boost::proto::detail::{name};",
              f"#if defined(BOOST_PROTO_EXTENDED_TEMPLATE_PARAMETERS_MATCHING)\n  // M11 platform guard: proto/detail/template_arity.hpp declares {name} only under\n  // BOOST_PROTO_EXTENDED_TEMPLATE_PARAMETERS_MATCHING (gcc extended-template matching).\n  using boost::proto::detail::{name};\n#endif")
    for name in ["divide_subtract", "divide_unsigned_helper"]:
        patch("src/gen_exports/graph.inc",
              f"  using boost::multiprecision::backends::{name};",
              f"#if defined(BOOST_HAS_INT128)\n  // M11 platform guard: the cpp_int divide helpers take double_limb_type (= __int128)\n  // and are declared only under BOOST_HAS_INT128 (off under the clang-msvc flavor).\n  using boost::multiprecision::backends::{name};\n#endif")
    for name in ["divide_subtract", "int128_type", "uint128_type"]:
        patch("src/gen_exports/graph.inc",
              f"  using boost::serialization::cpp_int_detail::{name};",
              f"#if defined(BOOST_HAS_INT128)\n  // M11 platform guard: the cpp_int interop surface exists only under BOOST_HAS_INT128\n  // (multiprecision detail; off under the clang-msvc flavor).\n  using boost::serialization::cpp_int_detail::{name};\n#endif")

    # M11: charconv — the mingw snapshot exports entities the MSVC ABI never
    # declares (mirrors the M9 decimal guards):
    # ieee754_binary80: bit_layouts.hpp defines it only for 80-bit long double
    # (MSVC long double is 53-bit); to_chars128: to_chars_integer_impl.hpp
    # declares it only under BOOST_CHARCONV_HAS_INT128.
    patch("src/gen_exports/charconv.inc",
          "  using boost::charconv::detail::ieee754_binary80;",
          "#if LDBL_MANT_DIG == 64 && LDBL_MAX_EXP == 16384\n"
          "  // M11 platform guard: bit_layouts.hpp defines ieee754_binary80 only for\n"
          "  // 80-bit long double (x86-64 gcc/mingw); MSVC long double is 53-bit.\n"
          "  using boost::charconv::detail::ieee754_binary80;\n"
          "#endif")
    patch("src/gen_exports/charconv.inc",
          "  using boost::charconv::detail::to_chars128;\n",
          "#if defined(BOOST_CHARCONV_HAS_INT128)\n"
          "  // M11 platform guard: to_chars128 exists only under BOOST_CHARCONV_HAS_INT128\n"
          "  // (to_chars_integer_impl.hpp).\n"
          "  using boost::charconv::detail::to_chars128;\n"
          "#endif\n")

    # M9: pfr — clang_wrapper_t is the clang-only NTTP wrapper
    # (core_name20_static.hpp #ifdef __clang__ branch; gcc takes the #else
    # make_clang_wrapper that returns arg directly). fields_count_dispatch_impl
    # exists only under the C++26 reflection / structured-bindings branches
    # (fields_count.hpp), which the C++23 CI compilers don't activate.
    patch("src/gen_exports/pfr.inc",
          "  using boost::pfr::detail::clang_wrapper_t;",
          "#if defined(__clang__)\n"
          "  // M9 platform guard: clang_wrapper_t is the clang-only NTTP wrapper\n"
          "  // (core_name20_static.hpp #ifdef __clang__ branch).\n"
          "  using boost::pfr::detail::clang_wrapper_t;\n"
          "#endif")
    patch("src/gen_exports/pfr.inc",
          "  using boost::pfr::detail::fields_count_dispatch_impl;",
          "#if BOOST_PFR_USE_CPP26_REFLECTION || BOOST_PFR_USE_CPP26\n"
          "  // M9 platform guard: fields_count_dispatch_impl exists only under the\n"
          "  // C++26 reflection / structured-bindings branches (fields_count.hpp).\n"
          "  using boost::pfr::detail::fields_count_dispatch_impl;\n"
          "#endif")

    # M9: uuid — the SIMD/x86 from_chars/to_chars entities live in
    # from_chars_x86.hpp / to_chars_x86.hpp / uuid_x86.ipp / simd_vector.hpp,
    # all included under BOOST_UUID_USE_SSE2 (config.hpp: __GNUC__ && __SSE2__,
    # or MSVC _M_X64). Absent on macOS arm64 (no __SSE2__).
    # M11: iostreams — boost/iostreams/filter/regex.hpp is curated out of the
    # module GMF (its boost::regex dependency trips the gcc 16.1 module
    # abi-tag streaming bug in cpp_regex_traits); drop the GMF include and the
    # regex filter exports. Best-effort: a regen from the curated libs.json
    # produces neither.
    patch("src/iostreams.cppm",
          "#include <boost/iostreams/filter/regex.hpp>\n",
          "// M11: filter/regex.hpp curated out of the GMF — the cpp_regex_traits\n"
          "// abi-tag streaming bug (gcc 16.1); consumers include it themselves.\n",
          required=False)
    patch("src/iostreams.cppm",
          "export import boost.regex;\n",
          "// M11: stale boost.regex import removed with filter/{regex,grep}.hpp\n"
          "// curation (gcc 16.1 cpp_regex_traits abi-tag streaming bug).\n",
          required=False)
    for name in ["basic_regex_filter", "regex_filter", "wregex_filter"]:
        patch("src/gen_exports/iostreams.inc",
              f"  using boost::iostreams::{name};\n",
              f"  // M11: {name} dropped — declared only via filter/regex.hpp (curated\n"
              f"  // out of the module GMF; gcc 16.1 abi-tag streaming bug).\n",
              required=False)
    # M11: test — boost/test/data/test_case.hpp is curated out of the module
    # GMF: its transitive chain (dataset → monomorphic/generators → random.hpp)
    # exposes anonymous-namespace keyword objects (TU-local) that hard-error on
    # gcc 16.1. Drop the GMF include and the data::* export blocks.
    patch("src/test.cppm",
          "#include <boost/test/data/test_case.hpp>\n",
          "// M11: data/test_case.hpp curated out of the GMF — random.hpp exposes\n"
          "// anonymous-namespace keywords (TU-local), hard-erroring on gcc 16.1.\n"
          "// Consumers include it themselves for BOOST_DATA_TEST_CASE.\n",
          required=False)
    patch("src/gen_exports/test.inc",
          "export namespace boost { namespace unit_test { namespace data {\n"
          "  using boost::unit_test::data::for_each_sample;",
          "  // M11: boost::unit_test::data::* blocks dropped — declared only via\n"
          "  // data/test_case.hpp's chain (curated out of the module GMF; gcc 16.1\n"
          "  // TU-local exposure in random.hpp).\n"
          "#if 0\n"
          "export namespace boost { namespace unit_test { namespace data {\n"
          "  using boost::unit_test::data::for_each_sample;",
          required=False)
    patch("src/gen_exports/test.inc",
          "  using boost::unit_test::data::result_of::make;\n}}}}",
          "  using boost::unit_test::data::result_of::make;\n}}}}\n#endif",
          required=False)
    # M11: io — boost/io/ostream_put.hpp is curated out of the io module GMF:
    # its function-local unnamed enum (buffer_fill) streamed from two module
    # CMIs (boost.io + boost.utility via string_view) mismatches on gcc 16.1.
    # Nothing from it appears in io.inc.
    # M11: graph — multiprecision detail unmentionable placeholders have no
    # external linkage; gcc refuses the export.
    for name in ["unmentionable", "unmentionable_type"]:
        patch("src/gen_exports/graph.inc",
              f"  using boost::multiprecision::detail::{name};\n",
              f"  // M11: {name} dropped — no external linkage (multiprecision detail\n"
              f"  // placeholder); gcc refuses the export.\n",
              required=False)
    # M11: io — boost/io/ostream_put.hpp is curated out of the io module GMF:
    # its function-local unnamed enum (buffer_fill) streamed from two module
    # CMIs (boost.io + boost.utility via string_view) mismatches on gcc 16.1.
    # Nothing from it appears in io.inc. NB: runs after the git restores below
    # in file order? No — placed after them via main() ordering: keep it here
    # only if the restore list does not include io.cppm (it does not).
    patch("src/io.cppm",
          "#include <boost/io/ostream_put.hpp>\n",
          "// M11: ostream_put.hpp curated out of the io module GMF — its\n"
          "// buffer_fill enum mismatches between the boost.io/boost.utility CMIs\n"
          "// on gcc 16.1; consumers include the header themselves.\n",
          required=False)
    for name in ["basic_grep_filter", "grep_filter", "wgrep_filter"]:
        patch("src/gen_exports/iostreams.inc",
              f"  using boost::iostreams::{name};\n",
              f"  // M11: {name} dropped — declared only via filter/grep.hpp (curated\n"
              f"  // out of the module GMF; same gcc 16.1 regex traits bug).\n",
              required=False)
    # M11: utility — boost/utility/string_ref.hpp (deprecated upstream) pulls
    # boost/io/detail/buffer_fill.hpp whose unnamed enum mismatches between the
    # boost.io and boost.utility BMIs on gcc 16.1. Curated out of the module
    # GMF; drop the include and the string_ref exports.
    patch("src/utility.cppm",
          "#include <boost/utility/string_ref.hpp>\n",
          "// M11: string_ref.hpp curated out of the GMF — its buffer_fill enum\n"
          "// mismatches between the boost.io/boost.utility BMIs on gcc 16.1;\n"
          "// consumers include the deprecated header themselves.\n",
          required=False)
    for name in ["basic_string_ref", "string_ref", "u16string_ref",
                 "u32string_ref", "wstring_ref"]:
        patch("src/gen_exports/utility.inc",
              f"  using boost::{name};\n",
              f"  // M11: {name} dropped — declared only via string_ref.hpp (curated out of\n"
              f"  // the module GMF; gcc 16.1 buffer_fill enum mismatch).\n",
              required=False)
    patch("src/gen_exports/utility.inc",
          "  using boost::detail::string_ref_traits_eq;\n",
          "  // M11: string_ref_traits_eq dropped — string_ref.hpp curated out of the GMF.\n",
          required=False)
    # M11: test — boost/test/data/monomorphic/generators/random.hpp + keywords.hpp
    # curated out of the GMF: random.hpp's templates expose keywords.hpp's
    # anonymous-namespace keyword objects (TU-local), hard-erroring on gcc 16.1.
    # M11: test — boost/test/minimal.hpp is the minimal-mode single-header
    # (it includes impl/execution_monitor.ipp + impl/debug.ipp and DEFINES
    # ::main); with it out of the libs.json entry (M11 curation), drop its
    # include from the module GMF, include the real public headers that were
    # only reachable through it, and drop the minimal_test / impl-only exports
    # from the .inc. Best-effort anchors: a future regen from the curated
    # libs.json produces neither the minimal.hpp include nor those lines.
    patch("src/test.cppm",
          "#include <boost/test/minimal.hpp>\n",
          "// M11: boost/test/minimal.hpp removed — the minimal-mode single-header defines\n"
          "// ::main via impl/execution_monitor.ipp + impl/debug.ipp, which collided with\n"
          "// every test program's main at link time. Curated out of libs.json.\n"
          "// The boost::debug / boost::detail::execution_monitor declarations were only\n"
          "// reachable through minimal.hpp; include the real public headers explicitly.\n"
          "#include <boost/test/debug.hpp>\n"
          "#include <boost/test/execution_monitor.hpp>\n",
          required=False)
    patch("src/test.cppm",
          "// every test program's main at link time. Curated out of libs.json.\n",
          "// every test program's main at link time. Curated out of libs.json.\n"
          "// The boost::debug / boost::detail::execution_monitor declarations were only\n"
          "// reachable through minimal.hpp; include the real public headers explicitly.\n"
          "#include <boost/test/debug.hpp>\n"
          "#include <boost/test/execution_monitor.hpp>\n",
          required=False)
    patch("src/gen_exports/test.inc",
          "  using boost::minimal_test::caller;\n"
          "  using boost::minimal_test::const_string;\n"
          "  using boost::minimal_test::errors_counter;\n"
          "  using boost::minimal_test::report_critical_error;\n"
          "  using boost::minimal_test::report_error;\n",
          "  // M11: boost::minimal_test::* dropped — declared only via minimal.hpp (curated\n"
          "  // out of the module GMF; it defines ::main and the minimal framework inline).\n",
          required=False)
    patch("src/gen_exports/test.inc",
          "  using boost::debug::safe_handle_helper;\n",
          "  // M11: boost::debug::safe_handle_helper dropped — declared only in\n"
          "  // impl/debug.ipp (windows impl), unreachable without minimal.hpp.\n",
          required=False)
    patch("src/test.cppm",
          "#include <boost/test/utils/timer.hpp>\n",
          "// M11: boost/test/utils/timer.hpp removed — it defines get_tick_freq without\n"
          "// inline, so the module TU collided with framework.o (framework.ipp).\n"
          "// Curated out of libs.json; nothing from it appears in test.inc.\n",
          required=False)
    patch("src/gen_exports/test.inc",
          "export namespace boost { namespace unit_test { namespace timer {\n"
          "  using boost::unit_test::timer::elapsed_time;\n"
          "  using boost::unit_test::timer::microsecond_wall_time;\n"
          "  using boost::unit_test::timer::second_wall_time;\n"
          "  using boost::unit_test::timer::timer;\n"
          "}}}\n"
          "\n"
          "export namespace boost { namespace unit_test { namespace timer { namespace details {\n"
          "  using boost::unit_test::timer::details::get_tick_freq;\n"
          "}}}}\n",
          "  // M11: boost::unit_test::timer::* dropped — declared only in utils/timer.hpp\n"
          "  // (curated out of the module GMF; its get_tick_freq definition is non-inline\n"
          "  // and collided with framework.o).\n",
          required=False)
    # boost::detail::{do_invoke,extract,forward,fpe_except_guard,
    # system_signal_exception,typeid_name} are declared in
    # impl/execution_monitor.ipp only — with minimal.hpp out of the GMF they are
    # unreachable on every platform; consumers include the public headers.
    for name in ["do_invoke", "extract", "forward", "fpe_except_guard",
                 "system_signal_exception", "typeid_name"]:
        patch("src/gen_exports/test.inc",
              f"  using boost::detail::{name};\n",
              f"  // M11: boost::detail::{name} dropped — declared only in impl/execution_monitor.ipp.\n",
              required=False)

    # M11: atomic — the mingw snapshot exports boost::is_integral/is_signed/
    # make_signed/make_unsigned (atomic/detail/type_traits/*.hpp use the
    # Boost.TypeTraits versions only under BOOST_HAS_INT128; the MSVC ABI takes
    # the std:: versions and never declares the boost:: ones) plus the
    # gcc-only backends (convert_memory_order_to_gcc, *_gcc_atomic,
    # *_gcc_x86 — same conditions as the M4/M7 thread.inc guards).
    patch("src/gen_exports/atomic.inc",
          "  using boost::is_integral;\n"
          "  using boost::is_signed;",
          "#if defined(BOOST_HAS_INT128)\n"
          "  // M11 platform guard: atomic/detail/type_traits/is_integral.hpp (and\n"
          "  // is_signed) pull the boost:: trait only under BOOST_HAS_INT128 (libstdc++\n"
          "  // __int128 workaround); the MSVC ABI takes the std:: trait instead.\n"
          "  using boost::is_integral;\n"
          "  using boost::is_signed;\n"
          "#endif")
    patch("src/gen_exports/atomic.inc",
          "  using boost::make_signed;\n"
          "  using boost::make_unsigned;\n"
          "  using boost::memory_order;\n"
          "  using boost::memory_order_acq_rel;",
          "#if defined(BOOST_HAS_INT128)\n"
          "  // M11 platform guard: atomic/detail/type_traits/make_signed.hpp — as above.\n"
          "  using boost::make_signed;\n"
          "  using boost::make_unsigned;\n"
          "#endif\n"
          "  using boost::memory_order;\n"
          "  using boost::memory_order_acq_rel;")
    for name in ["convert_memory_order_to_gcc",
                 "core_operations_gcc_atomic",
                 "fence_operations_gcc_atomic"]:
        patch("src/gen_exports/atomic.inc",
              f"  using boost::atomics::detail::{name};",
              f"#if defined(__GNUC__)\n  // M11 platform guard: gcc-only branch of boost/atomic (snapshot = mingw flavor).\n  using boost::atomics::detail::{name};\n#endif")
    for name in ["core_arch_operations_gcc_x86",
                 "core_arch_operations_gcc_x86_base",
                 "fence_arch_operations_gcc_x86"]:
        patch("src/gen_exports/atomic.inc",
              f"  using boost::atomics::detail::{name};",
              f"#if defined(__GNUC__) && (defined(__i386__) || defined(__x86_64__))\n  // M11 platform guard: gcc_x86 backend of boost/atomic (platform.hpp); x86 only.\n  using boost::atomics::detail::{name};\n#endif")
    # M11: wait_operations_windows lives in wait_ops_windows.hpp, which
    # platform.hpp includes only under BOOST_WINDOWS (wait backend = windows);
    # POSIX takes futex/darwin_ulock/generic and never declares it. Same entity
    # the M6 thread.inc guard carried before it migrated to atomic.inc.
    patch("src/gen_exports/atomic.inc",
          "  using boost::atomics::detail::wait_operations_windows;",
          "#if defined(BOOST_WINDOWS)\n"
          "  // M11 platform guard: wait_ops_windows.hpp (wait backend = windows,\n"
          "  // platform.hpp BOOST_WINDOWS); POSIX uses futex/darwin_ulock/generic.\n"
          "  using boost::atomics::detail::wait_operations_windows;\n"
          "#endif")
    # M11: container — win_critical_section lives in the non-pthread branch of
    # container/detail/thread_mutex.hpp (POSIX takes the BOOST_HAS_PTHREADS
    # pthread_mutex branch), and the whole boost::container_winapi block
    # (DWORD_/BOOL_/::SleepEx) is declared only under the
    # _WIN32/__WIN32__/WIN32 spin-lock-yield branch of container/detail/mutex.hpp.
    patch("src/gen_exports/container.inc",
          "  using boost::container::dtl::win_critical_section;\n",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: win_critical_section is the non-pthread branch\n"
          "  // of container/detail/thread_mutex.hpp; POSIX uses pthread_mutex.\n"
          "  using boost::container::dtl::win_critical_section;\n"
          "#endif\n")
    patch("src/gen_exports/container.inc",
          "export namespace boost { namespace container_winapi {\n"
          "  using ::SleepEx;\n"
          "  using boost::container_winapi::BOOL_;\n"
          "  using boost::container_winapi::DWORD_;\n"
          "}}",
          "#if defined(_WIN32)\n"
          "export namespace boost { namespace container_winapi {\n"
          "  // M11 platform guard: container_winapi DWORD_/BOOL_/SleepEx are\n"
          "  // declared only in the _WIN32 branch of container/detail/mutex.hpp.\n"
          "  using ::SleepEx;\n"
          "  using boost::container_winapi::BOOL_;\n"
          "  using boost::container_winapi::DWORD_;\n"
          "}}\n"
          "#endif")
    # M11: date_time — time_from_ftime (date_time/filetime_functions.hpp) and
    # posix_time::from_ftime (posix_time/conversion.hpp) exist only under
    # BOOST_HAS_FTIME (win32 FILETIME); same entities the M6 thread.inc guard
    # carried before them.
    guard_entity_lines("src/gen_exports/date_time.inc", "defined(_WIN32)", [
        "time_from_ftime",
        "from_ftime",
    ])
    # M11 CI fix (POSIX legs): nowide — the mingw snapshot's GMF reached
    # cstdio/stackstring/convert entities only through windows-flavored
    # transitive includes; add the cross-platform headers explicitly. The
    # console machinery and detail::stat are BOOST_WINDOWS branches upstream
    # (POSIX nowide uses std:: streams and ::stat directly) — guard those.
    patch("src/nowide.cppm",
          "#include <boost/nowide/iostream.hpp>\n#include <boost/nowide/quoted.hpp>",
          "#include <boost/nowide/iostream.hpp>\n"
          "// M11 platform guard (POSIX): cstdio/stackstring/convert were reached\n"
          "// only via windows-flavored transitive includes in the mingw snapshot;\n"
          "// include the cross-platform headers explicitly so the shared-surface\n"
          "// `using` lines resolve.\n"
          "#include <boost/nowide/cstdio.hpp>\n"
          "#include <boost/nowide/stackstring.hpp>\n"
          "#include <boost/nowide/convert.hpp>\n"
          "#include <boost/nowide/quoted.hpp>")
    for name in ["console_input_buffer", "console_output_buffer"]:
        patch("src/gen_exports/nowide.inc",
              f"  using boost::nowide::detail::{name};",
              f"#if defined(_WIN32)\n  // M11 platform guard: {name} is the windows console machinery (detail/console_buffer.hpp); POSIX nowide uses std:: streams directly.\n  using boost::nowide::detail::{name};\n#endif")
    for name in ["winconsole_istream", "winconsole_ostream"]:
        patch("src/gen_exports/nowide.inc",
              f"  using boost::nowide::detail::{name};",
              f"#if defined(_WIN32)\n  // M11 platform guard: {name} is the windows console stream branch of iostream.hpp; POSIX takes std:: streams directly.\n  using boost::nowide::detail::{name};\n#endif")
    patch("src/gen_exports/nowide.inc",
          "  using boost::nowide::detail::stat;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: detail::stat is the BOOST_WINDOWS branch of\n"
          "  // stat.hpp; POSIX exposes ::stat via a using-declaration instead.\n"
          "  using boost::nowide::detail::stat;\n"
          "#endif")
    # M11 CI fix (POSIX legs): log — the mingw snapshot bakes the Windows
    # version inline namespace (v2s_mt_nt62) into every qualified name; POSIX
    # uses v2s_mt_posix. Inline namespaces are lookup-transparent, so drop the
    # segment (see strip_log_version_namespace).
    strip_log_version_namespace("src/gen_exports/log.inc")
    # M11 CI fix (POSIX legs), follow-ups for log:
    #  - phoenix function machinery (function_eval family) was reached on the
    #    mingw snapshot only through the windows-only is_debugger_present
    #    predicate header; include the cross-platform umbrella explicitly.
    patch("src/log.cppm",
          "#include <boost/log/support/exception.hpp>\n"
          "#include <boost/log/support/regex.hpp>",
          "#include <boost/log/support/exception.hpp>\n"
          "// M11 platform guard (POSIX): phoenix function machinery was reached\n"
          "// only via the windows-only is_debugger_present predicate header in the\n"
          "// mingw snapshot; include the cross-platform umbrella explicitly so the\n"
          "// shared-surface `using` lines resolve.\n"
          "#include <boost/phoenix/function.hpp>\n"
          "#if defined(_WIN32)\n"
          "#include <boost/log/support/regex.hpp>\n"
          "#endif\n",
          required=False)
    # Bridge for the intermediate state the 2/2 fix below had first applied
    # (phoenix include without the regex-support #if guard yet).
    patch("src/log.cppm",
          "#include <boost/phoenix/function.hpp>\n#include <boost/log/support/regex.hpp>",
          "#include <boost/phoenix/function.hpp>\n"
          "#if defined(_WIN32)\n"
          "#include <boost/log/support/regex.hpp>\n"
          "#endif",
          required=False)
    # M11 CI fix (POSIX legs) 2/2: gcc modules merge the regex decls seen via
    # the imported boost.regex / boost.range CMIs (recorded with the __cxx11
    # abi tag) with the GMF's own textual re-parse of cpp_regex_traits.hpp
    # (recorded without tags) and hard-error "mismatching abi tags" on
    # cpp_regex_traits<char>::get_catalog_name_inst. Keep the boost.regex
    # support header to the Windows face only (clang/msvc merge fine) and drop
    # the one export line that needs it; POSIX consumers include
    # <boost/log/support/regex.hpp> directly (T3 rule).
    patch("src/gen_exports/log.inc",
          "  using boost::log::aux::boost_regex_expression_tag;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: needs support/regex.hpp, excluded from the\n"
          "  // POSIX GMF (gcc abi-tag merge bug, see log.cppm).\n"
          "  using boost::log::aux::boost_regex_expression_tag;\n"
          "#endif")
    # M11 CI fix (POSIX legs): cobalt — the mingw snapshot's GMF reached the
    # asio reactor / hash_map detail headers only through windows-flavored
    # chains (cobalt on POSIX selects epoll, so select_reactor.hpp et al. were
    # never included); include the cross-platform headers explicitly so the
    # shared-surface `using` lines resolve on POSIX (they are redundant but
    # harmless on Windows).
    patch("src/cobalt.cppm",
          "#include <boost/cobalt.hpp>\n#include <boost/cobalt/composition.hpp>",
          "#include <boost/cobalt.hpp>\n"
          "// M11 platform guard (POSIX): asio reactor/hash_map details were only\n"
          "// reached through windows-flavored chains in the mingw snapshot (POSIX\n"
          "// cobalt selects the epoll reactor); include them explicitly so the\n"
          "// shared-surface `using` lines resolve.\n"
          "#include <boost/asio/detail/hash_map.hpp>\n"
          "#include <boost/asio/detail/null_reactor.hpp>\n"
          "#include <boost/asio/detail/select_reactor.hpp>\n"
          "#include <boost/cobalt/composition.hpp>",
          required=False)
    # M11 CI fix (POSIX legs) 2/2: fd_set_adapter / reactor_op_queue /
    # socket_select_interrupter are per-OS-selected headers with no outer
    # platform guard; null_reactor.hpp and select_reactor.hpp self-guard empty
    # on the epoll/kqueue paths (their entities are guarded _WIN32 in the
    # .inc instead).
    patch("src/cobalt.cppm",
          "#include <boost/asio/detail/select_reactor.hpp>\n#include <boost/cobalt/composition.hpp>",
          "#include <boost/asio/detail/select_reactor.hpp>\n"
          "// fd_set_adapter / reactor_op_queue / socket_select_interrupter are\n"
          "// per-OS-selected headers with no outer platform guard; the reactor\n"
          "// headers above self-guard empty on the epoll/kqueue paths (their\n"
          "// entities are guarded _WIN32 in the .inc instead).\n"
          "#include <boost/asio/detail/fd_set_adapter.hpp>\n"
          "#include <boost/asio/detail/reactor_op_queue.hpp>\n"
          "#include <boost/asio/detail/socket_select_interrupter.hpp>\n"
          "#include <boost/cobalt/composition.hpp>",
          required=False)
    # Windows-only asio surface: IOCP/file backends, winsock init, APC, and the
    # win_* detail family (asio/detail/config.hpp BOOST_ASIO_HAS_FILE is
    # windows-random-access-handle / io_uring only; the posix signal blocker
    # replaces null_signal_blocker).
    guard_entity_lines("src/gen_exports/cobalt.inc", "defined(BOOST_ASIO_HAS_FILE)", [
        "basic_file",
        "basic_random_access_file",
        "basic_stream_file",
        "file_base",
    ])
    guard_entity_lines("src/gen_exports/cobalt.inc", "defined(_WIN32)", [
        "apc_function",
        "null_reactor",
        "select_reactor",
        "null_signal_blocker",
        "socket_select_interrupter",
        "win_event",
        "win_fd_set_adapter",
        "win_global",
        "win_global_impl",
        "win_iocp_file_service",
        "win_iocp_handle_read_op",
        "win_iocp_handle_service",
        "win_iocp_handle_write_op",
        "win_iocp_io_context",
        "win_iocp_null_buffers_op",
        "win_iocp_operation",
        "win_iocp_overlapped_ptr",
        "win_iocp_serial_port_service",
        "win_iocp_socket_accept_op",
        "win_iocp_socket_connect_op",
        "win_iocp_socket_connect_op_base",
        "win_iocp_socket_move_accept_op",
        "win_iocp_socket_recv_op",
        "win_iocp_socket_recvfrom_op",
        "win_iocp_socket_recvmsg_op",
        "win_iocp_socket_send_op",
        "win_iocp_socket_service",
        "win_iocp_socket_service_base",
        "win_iocp_thread_info",
        "win_iocp_wait_op",
        "win_mutex",
        "win_static_mutex",
        "win_thread",
        "win_thread_base",
        "win_thread_function",
        "winsock_init",
        "winsock_init_base",
        "complete_iocp_accept",
        "complete_iocp_connect",
        "complete_iocp_recv",
        "complete_iocp_recvfrom",
        "complete_iocp_recvmsg",
        "complete_iocp_send",
        "msghdr",
    ])
    #  - windows-only surface: is_debugger_present (BOOST_WINDOWS branch of
    #    expressions/predicates/is_debugger_present.hpp), the event-log /
    #    debug-output keywords and sinks (sinks/event_log_backend.hpp etc.),
    #    and spirit's decode_utf16 (wchar_t==2 branch of spirit utf8.hpp).
    guard_entity_lines("src/gen_exports/log.inc", "defined(_WIN32)", [
        "log_name",
        "log_source",
        "message_file",
        "registration",
        "basic_debug_output_backend",
        "basic_event_log_backend",
        "basic_simple_event_log_backend",
        "debug_output_backend",
        "event_log_backend",
        "simple_event_log_backend",
        "wdebug_output_backend",
        "wevent_log_backend",
        "wsimple_event_log_backend",
    ])
    patch("src/gen_exports/log.inc",
          "  using boost::log::expressions::is_debugger_present;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: is_debugger_present is the BOOST_WINDOWS branch\n"
          "  // of expressions/predicates/is_debugger_present.hpp.\n"
          "  using boost::log::expressions::is_debugger_present;\n"
          "#endif")
    patch("src/gen_exports/log.inc",
          "  using boost::log::expressions::aux::is_debugger_present;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: aux::is_debugger_present — as above.\n"
          "  using boost::log::expressions::aux::is_debugger_present;\n"
          "#endif")
    patch("src/gen_exports/log.inc",
          "export namespace boost { namespace log { namespace sinks { namespace event_log {\n"
          "  using boost::log::sinks::event_log::basic_event_composer;",
          "#if defined(_WIN32)\n"
          "export namespace boost { namespace log { namespace sinks { namespace event_log {\n"
          "  // M11 platform guard: event_log sink mapping/composer types are\n"
          "  // Windows-only (sinks/event_log_backend.hpp).\n"
          "  using boost::log::sinks::event_log::basic_event_composer;")
    patch("src/gen_exports/log.inc",
          "  using boost::log::sinks::event_log::wevent_composer;\n}}}}\n",
          "  using boost::log::sinks::event_log::wevent_composer;\n}}}}\n#endif\n")
    patch("src/gen_exports/log.inc",
          "  using boost::spirit::detail::decode_utf16;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: decode_utf16 is the wchar_t==2 branch of\n"
          "  // spirit/home/support/utf8.hpp (MSVC/mingw); POSIX wchar_t is 4 bytes.\n"
          "  using boost::spirit::detail::decode_utf16;\n"
          "#endif")
    guard_entity_lines("src/gen_exports/uuid.inc", "defined(BOOST_UUID_USE_SSE2)", [
        "compare",
        "countr_zero_nz",
        "from_chars_simd",
        "from_chars_simd_char_constants",
        "from_chars_simd_constants",
        "from_chars_simd_core",
        "from_chars_simd_load_traits",
        "simd_vector",
        "simd_vector128",
        "simd_vector256",
        "simd_vector512",
        "to_chars_simd",
        "to_chars_simd_char_constants",
        "to_chars_simd_constants",
        "to_chars_simd_core",
    ])

    # M9: signals2 — critical_section / critical_section_debug /
    # rtl_critical_section live in lwm_win32_cs.hpp, included only under
    # BOOST_HAS_WINTHREADS (mutex.hpp selector); POSIX takes lwm_pthreads.hpp.
    guard_entity_lines("src/gen_exports/signals2.inc", "defined(BOOST_HAS_WINTHREADS)", [
        "critical_section",
        "critical_section_debug",
        "rtl_critical_section",
    ])

    # M9: safe_numerics — the TU-local anonymous-class error_category singleton
    # (exception.hpp) is fixed at the vendored header (class named
    # safe_numerics_error_category_t); make_error_code is exported on all
    # platforms. No .inc guard needed.

    # M9: dll — last_error_code lives in detail/windows/path_from_handle.hpp
    # (no POSIX equivalent); the POSIX GMF never includes it.
    patch("src/gen_exports/dll.inc",
          "  using boost::dll::detail::last_error_code;",
          "#if defined(_WIN32)\n"
          "  // M9 platform guard: last_error_code is in detail/windows/\n"
          "  // path_from_handle.hpp (no POSIX counterpart).\n"
          "  using boost::dll::detail::last_error_code;\n"
          "#endif")

    # M9: bloom — m128ix2 lives in detail/fast_multiblock32_sse2.hpp, included
    # only under BOOST_BLOOM_SSE2 (detail/sse2.hpp: __SSE2__ && x86). Absent on
    # macOS arm64 (no __SSE2__; NEON branch active instead).
    patch("src/gen_exports/bloom.inc",
          "  using boost::bloom::detail::m128ix2;",
          "#if defined(BOOST_BLOOM_SSE2)\n"
          "  // M9 platform guard: m128ix2 is the SSE2 branch of fast_multiblock32\n"
          "  // (detail/sse2.hpp, __SSE2__); absent on arm64 (NEON branch).\n"
          "  using boost::bloom::detail::m128ix2;\n"
          "#endif")

    # M9: align — detail::alignment_of is config-selected by
    # boost/align/alignment_of.hpp: `using std::alignment_of;` (cxx11 branch)
    # on x86/clang-msvc, but a real `struct alignment_of` on the
    # BOOST_CLANG && !__x86_64__ branch (macOS arm64, and 32-bit unix gcc).
    # The generated snapshot (mingw → cxx11) emits `using std::alignment_of;`
    # in the module purview, which conflicts with the struct the macOS GMF
    # declares. The detail name is NOT needed by the exported surface — the
    # public boost::alignment::alignment_of inherits from it via the GMF and
    # consumers instantiate it fine (verified gcc/clang, struct and cxx11
    # paths) — so drop the export line.
    patch("src/gen_exports/align.inc",
          "  using std::add_lvalue_reference;\n  using std::alignment_of;\n  using std::false_type;\n",
          "  using std::add_lvalue_reference;\n  using std::false_type;\n")

    # M9: parser — parse_int/parse_real live in an `inline namespace
    # BOOST_PARSER_NUMERIC_NS` (std_charconv | boost_charconv | spirit_parsers,
    # selected by numeric.hpp at include time). The mingw snapshot used
    # std_charconv, so the .inc qualified the entities as
    # numeric::std_charconv::parse_int. On toolchains where a different branch
    # is active (e.g. libc++ without __cpp_lib_to_chars), the std_charconv
    # namespace doesn't exist. Use the inline-namespace-agnostic path
    # (numeric::parse_int) which resolves on every branch.
    patch("src/gen_exports/parser.inc",
          "export namespace boost { namespace parser { namespace detail { namespace numeric { namespace std_charconv {\n"
          "  using boost::parser::detail::numeric::std_charconv::parse_int;\n"
          "  using boost::parser::detail::numeric::std_charconv::parse_real;\n"
          "}}}}}",
          "export namespace boost { namespace parser { namespace detail { namespace numeric {\n"
          "  using boost::parser::detail::numeric::parse_int;\n"
          "  using boost::parser::detail::numeric::parse_real;\n"
          "}}}}")

    # M9: flyweight — the generator leaked the entire transitive surface of
    # boost.container / boost.interprocess(.winapi) / boost.intrusive /
    # boost.move_detail / boost.mpl / boost.parameter / boost.multi_index into
    # flyweight.inc (932 entities). Those namespaces are internal dependencies
    # whose availability is platform-dependent (interprocess.winapi is Windows-
    # only; container option types are macro-generated, declared only on the
    # mingw snapshot include path). The committed form is hand-trimmed to
    # flyweight's own surface (boost::flyweight + boost::flyweights::*); restore
    # it after regeneration. Mirrors the algorithm.inc convention.
    restore_from_git("src/gen_exports/flyweight.inc")

    # M6: thread module — mingw snapshot exports Windows-only entities (win32
    # thread primitives + boost.winapi) that the POSIX GMF include set never
    # declares. Guard the entirely-windows namespace blocks wholesale, and the
    # scattered Windows-only entities via guard_entity_lines.
    patch("src/gen_exports/thread.inc",
          "export namespace boost { namespace detail { namespace win32 {\n"
          "  using boost::detail::win32::create_anonymous_event;",
          "#if defined(_WIN32)\n"
          "export namespace boost { namespace detail { namespace win32 {\n"
          "  using boost::detail::win32::create_anonymous_event;")
    patch("src/gen_exports/thread.inc",
          "  using boost::detail::win32::system_info;\n"
          "  using boost::detail::win32::ticks_type;\n"
          "}}}\n\nexport namespace boost { namespace detail { namespace win32 { namespace detail {",
          "  using boost::detail::win32::system_info;\n"
          "  using boost::detail::win32::ticks_type;\n"
          "}}}\n#endif\n\nexport namespace boost { namespace detail { namespace win32 { namespace detail {")
    patch("src/gen_exports/thread.inc",
          "  using boost::detail::win32::detail::gettickcount64_t;\n"
          "}}}}\n\nexport namespace boost { namespace exception_detail {",
          "#if defined(_WIN32)\n"
          "  using boost::detail::win32::detail::gettickcount64_t;\n"
          "#endif\n"
          "}}}}\n\nexport namespace boost { namespace exception_detail {")
    guard_entity_lines("src/gen_exports/thread.inc", "defined(_WIN32)", [
        # boost block — intrusive_ptr is pulled in only via win32 thread headers
        "intrusive_ptr",
        # atomics::detail — wait_operations_windows (win32 branch of boost/atomic)
        "wait_operations_windows",
        # date_time / posix_time — FILETIME helpers (win32 only)
        "time_from_ftime",
        "from_ftime",
        # this_thread — interruptible_wait / non_interruptible_wait (win32 API wait)
        "interruptible_wait",
        "non_interruptible_wait",
        # boost::detail — win32 thread primitives (once / mutex / interlocked / tss)
        "allocate_raw_heap_memory",
        "free_raw_heap_memory",
        "basic_condition_variable",
        "basic_cv_list_entry",
        "basic_recursive_mutex",
        "basic_recursive_mutex_impl",
        "basic_recursive_timed_mutex",
        "basic_timed_mutex",
        "commit_once_region",
        "create_once_event",
        "enter_once_region",
        "rollback_once_region",
        "int_to_string",
        "interlocked_read_acquire",
        "interlocked_write_release",
        "intrusive_ptr_add_ref",
        "intrusive_ptr_release",
        "name_once_mutex",
        "once_action",
        "once_char_type",
        "once_context",
        "open_once_event",
        "underlying_mutex",
    ])
    patch("src/gen_exports/mp11.inc",
          "  using boost::mp11::detail::mpmf_unwrap;\n  using boost::mp11::detail::mpmf_wrap;",
          "#if !defined(__GNUC__)\n  // M3 hand-guard: mp_map_find.hpp (gcc bug 120161 workaround) defines mpmf_* only outside gcc.\n"
          "  using boost::mp11::detail::mpmf_unwrap;\n  using boost::mp11::detail::mpmf_wrap;\n#endif")
    patch("src/gen_exports/tuple.inc",
          "  using boost::tuples::detail::ignore_t;",
          "#if !defined(__GNUC__)\n  // M3 hand-guard: ignore_t is a member-pointer typedef; gcc treats it as internal linkage.\n  using boost::tuples::detail::ignore_t;\n#endif")
    # M4: thread.inc atomics — mingw snapshot carries gcc-only boost/atomic
    # entities (convert_memory_order_to_gcc, core_arch_operations_gcc_x86*,
    # core_operations_gcc_atomic, fence_arch_operations_gcc_x86,
    # fence_operations_gcc_atomic); absent under the MSVC ABI.
    # M11: with boost.atomic as a module these entities are claimed by it
    # (first-wins) and migrate out of thread.inc — anchors may be gone, so
    # the guards are best-effort (required=False).
    for name in ["convert_memory_order_to_gcc",
                 "core_operations_gcc_atomic",
                 "fence_operations_gcc_atomic"]:
        patch("src/gen_exports/thread.inc",
              f"  using boost::atomics::detail::{name};",
              f"#if defined(__GNUC__)\n  // M4 platform guard: gcc-only branch of boost/atomic (snapshot = mingw flavor).\n  using boost::atomics::detail::{name};\n#endif",
              required=False)
    # M7: the *_gcc_x86 backend classes need the same condition as the
    # boost/atomic gcc_x86 backend (platform.hpp: __GNUC__ && x86 arch). Plain
    # __GNUC__ broke macOS arm64 (clang defines __GNUC__, but the gcc_aarch64
    # backend applies); bare __i386__/__x86_64__ would wrongly export them
    # under the MSVC ABI (clang-cl defines no __GNUC__).
    # M11: entities may migrate to boost.atomic — best-effort.
    for name in ["core_arch_operations_gcc_x86",
                 "core_arch_operations_gcc_x86_base",
                 "fence_arch_operations_gcc_x86"]:
        patch("src/gen_exports/thread.inc",
              f"  using boost::atomics::detail::{name};",
              f"#if defined(__GNUC__) && (defined(__i386__) || defined(__x86_64__))\n  // M7 platform guard: gcc_x86 backend of boost/atomic (platform.hpp) exists only on x86; __GNUC__ is defined by clang too, so it broke macOS arm64 (gcc_aarch64 backend).\n  using boost::atomics::detail::{name};\n#endif",
              required=False)
    patch("src/gen_exports/variant.inc",
          "  using boost::mpl::aux::arity_helper;\n  using boost::mpl::aux::arity_tag;",
          "#if defined(__GNUC__)\n  // M3 hand-guard: gcc-preprocessed mpl headers only (BOOST_MPL_CFG_COMPILER_DIR=gcc).\n"
          "  using boost::mpl::aux::arity_helper;\n  using boost::mpl::aux::arity_tag;\n#endif")
    patch("src/gen_exports/variant.inc",
          "  using boost::mpl::aux::max_arity;",
          "#if defined(__GNUC__)\n  // M3 hand-guard: as above (max_arity).\n  using boost::mpl::aux::max_arity;\n#endif")
    patch("src/gen_exports/variant.inc",
          "  using boost::mpl::aux::nested_type_wknd;",
          "#if defined(__GNUC__)\n  // M3 hand-guard: as above (nested_type_wknd).\n  using boost::mpl::aux::nested_type_wknd;\n#endif")
    patch("src/gen_exports/variant.inc",
          "  using boost::mpl::aux::template_arity_impl;",
          "#if defined(__GNUC__)\n  // M3 hand-guard: as above (template_arity_impl).\n  using boost::mpl::aux::template_arity_impl;\n#endif")

    # M9: heap's container templates (d_ary_heap etc.) instantiate the intrusive
    # placement new (`::new(p, boost_move_new_t()) T`) in the consumer TU, where
    # the global operator new overload from move/detail/placement_new.hpp (a GMF
    # include) is not visible. M0 rule: re-export the global operator new
    # overloads from the module purview.
    patch("src/heap.cppm",
          '#include "gen_exports/heap.inc"',
          "// M9: heap's container templates (d_ary_heap etc.) instantiate the intrusive\n"
          "// placement new (`::new(p, boost_move_new_t()) T`) in the consumer TU, where\n"
          "// the global operator new overload from move/detail/placement_new.hpp (a GMF\n"
          "// include) is not visible. M0 rule: re-export the global operator new\n"
          "// overloads from the module purview.\n"
          "export using ::operator new;\n\n"
          '#include "gen_exports/heap.inc"',
          required=False)

    # ---- algorithm: M3 workaround (string.hpp GFM + *regex entity pruning) ----
    # algorithm.inc is regenerated with string_regex.hpp in the GFM; the M3
    # gcc abi-tag workaround keeps string.hpp instead, so the generated inc
    # (which lists the *regex entities) cannot compile in the module TU.
    # The committed M3 form is the source of truth; regenerate-free.
    restore_from_git("src/gen_exports/algorithm.inc")
    restore_from_git("src/gen_exports/algorithm.deps")
    restore_from_git("src/algorithm.cppm")  # M3 GFM (string.hpp) + no boost.regex import

    # ---- M3 libs whose .cppm are unchanged (regen only rewrites the header
    # comment): keep the M3 "final form" convention. Their .inc/.deps ARE
    # regenerated (entity ownership may shift between runs). ----
    for rel in ["any", "container_hash", "core", "endian", "io", "iterator",
                "mp11", "optional", "range", "rational", "scope", "scope_exit",
                "static_string", "tuple", "type_traits", "variant", "variant2"]:
        restore_from_git(f"src/{rel}.cppm")

    # M11: io — boost/io/ostream_put.hpp is curated out of the io module GMF:
    # its function-local unnamed enum (buffer_fill) streamed from two module
    # CMIs (boost.io + boost.utility via string_view) mismatches on gcc 16.1.
    # Nothing from it appears in io.inc. NB: io.cppm is git-restored above, so
    # this patch must run after the restores.
    patch("src/io.cppm",
          "#include <boost/io/ostream_put.hpp>\n",
          "// M11: ostream_put.hpp curated out of the io module GMF — its\n"
          "// buffer_fill enum mismatches between the boost.io/boost.utility CMIs\n"
          "// on gcc 16.1; consumers include the header themselves.\n",
          required=False)
    patch("src/gen_exports/io.inc",
          "  using boost::io::ostream_put;\n",
          "  // M11: ostream_put dropped — declared only via io/ostream_put.hpp (curated\n"
          "  // out of the module GMF; gcc 16.1 buffer_fill enum mismatch).\n",
          required=False)

    print("done.")


if __name__ == "__main__":
    main()
