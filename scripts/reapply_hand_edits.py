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

    # ---- .inc platform guards (M3 §5) ----
    patch("src/gen_exports/core.inc",
          "  using boost::int128_type;",
          "#if defined(BOOST_HAS_INT128)\n  // M3 hand-guard: suffix.hpp defines int128_type only where BOOST_HAS_INT128.\n  using boost::int128_type;\n#endif")
    patch("src/gen_exports/core.inc",
          "  using boost::uint128_type;",
          "#if defined(BOOST_HAS_INT128)\n  // M3 hand-guard: suffix.hpp defines uint128_type only where BOOST_HAS_INT128.\n  using boost::uint128_type;\n#endif")
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
    patch("src/gen_exports/system.inc",
          "export namespace boost { namespace winapi {\n  using boost::winapi::BOOLEAN_;",
          "#if defined(_WIN32)\nexport namespace boost { namespace winapi {\n  using boost::winapi::BOOLEAN_;")
    patch("src/gen_exports/system.inc",
          "  using boost::winapi::_LARGE_INTEGER;\n  using boost::winapi::_SECURITY_ATTRIBUTES;\n  using boost::winapi::format_message;\n}}",
          "  using boost::winapi::_LARGE_INTEGER;\n  using boost::winapi::_SECURITY_ATTRIBUTES;\n  using boost::winapi::format_message;\n}}\n#endif")

    # M6: program_options winmain splitter — <boost/program_options/winmain.hpp>
    # is pulled into the GMF only on Windows.
    patch("src/gen_exports/program_options.inc",
          "  using boost::program_options::split_winmain;",
          "#if defined(_WIN32)\n  // M6 platform guard: winmain.hpp (split_winmain) is Windows-only.\n  using boost::program_options::split_winmain;\n#endif")

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
    patch("src/gen_exports/thread.inc",
          "export namespace boost { namespace winapi {\n  using boost::winapi::ACCESS_MASK_;",
          "#if defined(_WIN32)\nexport namespace boost { namespace winapi {\n  using boost::winapi::ACCESS_MASK_;")
    patch("src/gen_exports/thread.inc",
          "  using boost::winapi::open_event;\n  using boost::winapi::open_semaphore;\n}}",
          "  using boost::winapi::open_event;\n  using boost::winapi::open_semaphore;\n}}\n#endif")
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
    for name in ["convert_memory_order_to_gcc",
                 "core_arch_operations_gcc_x86",
                 "core_arch_operations_gcc_x86_base",
                 "core_operations_gcc_atomic",
                 "fence_arch_operations_gcc_x86",
                 "fence_operations_gcc_atomic"]:
        patch("src/gen_exports/thread.inc",
              f"  using boost::atomics::detail::{name};",
              f"#if defined(__GNUC__)\n  // M4 platform guard: gcc-only branch of boost/atomic (snapshot = mingw flavor).\n  using boost::atomics::detail::{name};\n#endif")
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

    print("done.")


if __name__ == "__main__":
    main()
