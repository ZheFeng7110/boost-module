#!/usr/bin/env python3
"""Re-apply hand edits that scripts/gen_exports.py --emit-cppm overwrites.

Run after ANY full regeneration:

    uv run scripts/gen_exports.py --emit-cppm
    uv run scripts/reapply_hand_edits.py

The string-replacement patches live as unified diffs under scripts/patchs/
(one <module>.patch per module); they are applied with `git apply` and are
idempotent: when a patch is already contained in the target files, the
reverse-apply check succeeds and the patch is skipped. The .inc platform
guards (guard_entity_lines), the vendored file addition (ensure_file) and
the "M3 final form" git restores stay programmatic below.

Also replays the vendored header patches under deps/boost/ (M5/M11/M12),
which scripts/import_boost.py wipes on re-vendoring (rollup doc §3.7#1).

Regenerating a patch file: apply the hand edit to the freshly regenerated
file, then `git diff -- <file>` (against the regenerated state) and save it
as scripts/patchs/<module>.patch. Hunks for several files of one module go
into the same .patch (git apply handles multi-file diffs).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATCH_DIR = ROOT / "scripts" / "patchs"

# One entry per scripts/patchs/<name>.patch. Files are independent, so the
# order is irrelevant except for readability (vendored deps/boost patches
# first). json/core/io are "tolerant": their anchors may legitimately be
# absent in the committed state (json's explanatory comment never got
# committed; core.cppm/io.cppm are git-restored right after patching).
# The former bimap entry (C4 boost.iterator pin) is gone: gen_exports pass 2
# (body-reference .deps completion) emits the edge naturally since 2026-09-08.
TOLERANT = {"json", "core", "io"}

VENDORED_PATCHES = [
    "asio", "beast", "hof", "io", "lambda", "mqtt5", "parameter", "regex",
    "safe_numerics", "serialization", "system", "test", "ublas", "units",
]

SRC_PATCHES = [
    "align", "atomic", "bloom", "charconv", "cobalt", "config",
    "container", "core", "decimal", "dll", "functional", "graph", "hana",
    "heap", "hof", "hof_src", "interprocess", "intrusive", "iostreams",
    "json", "lambda", "lambda_src", "leaf", "math", "mp11", "multiprecision",
    "nowide", "parameter", "parser", "pfr", "poly_collection", "process",
    "program_options", "qvm", "range", "safe_numerics", "safe_numerics_src",
    "stacktrace", "system_src", "thread", "tuple", "url", "utility",
    "variant", "winapi",
]
# note: the vendored/src split — hof/io/lambda/safe_numerics/system spanned
# deps/boost/ AND regenerated src/ files in one diff, which cannot replay
# after a regen (deps part already applied ⇒ forward fails; src part freshly
# regenerated ⇒ reverse fails). The deps hunks stay in VENDORED_PATCHES, the
# src hunks moved to <name>_src.patch (io_src dropped: src/io.cppm is
# git-restored right after, its hunk was a transitional no-op; core.patch's
# core.cppm hunk dropped for the same reason). hana was orphaned (never
# listed) — the ::boost:: ext-tag spelling regressed on every regen.


def apply_patch_file(name):
    """git-apply scripts/patchs/<name>.patch; skip when already applied."""
    rel = f"scripts/patchs/{name}.patch"
    r = subprocess.run(["git", "apply", "--whitespace=nowarn", rel], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if r.returncode == 0:
        print(f"  patched {rel}")
        return
    c = subprocess.run(["git", "apply", "--check", "--reverse", rel], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if c.returncode == 0:
        print(f"  skip   {rel} (already applied)")
        return
    if name in TOLERANT:
        print(f"  skip   {rel} (anchor not present, tolerated)")
        return
    raise SystemExit(f"{rel}: failed to apply\n"
                     f"  stdout: {r.stdout[:300]}\n  stderr: {r.stderr[:300]}")


def patch(rel, old, new, *, required=True):
    """Fallback for patches that cannot be expressed as a static diff:
    the type_erasure.inc anchor only exists when the C4 mpl-entity ownership
    flips back to poly_collection after a regeneration."""
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    if new in s:
        print(f"  skip   {rel} (already applied)")
        return
    n = s.count(old)
    if n == 1:
        p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")
        print(f"  patched {rel}")
        return
    if n == 0 and not required:
        print(f"  skip   {rel} (anchor not present, not required)")
        return
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


def ensure_file(rel, content):
    """Create a vendored file that is an addition, not an upstream patch
    (no-op when already present)."""
    p = ROOT / rel
    if p.exists():
        print(f"  skip   {rel} (already present)")
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8", newline="\n")
    print(f"  created {rel}")


def main():
    print("reapplying hand edits...")

    # ---- vendored header patches under deps/boost/ (rollup doc §3.7#1):
    # import_boost.py re-vendoring wipes them; replay before the .inc/.cppm
    # pass below. scripts/patchs/<module>.patch, applied with git apply. ----
    print("applying vendored patches (scripts/patchs, deps/boost)...")
    for name in VENDORED_PATCHES:
        apply_patch_file(name)

    print("applying src patches (scripts/patchs, src/)...")
    for name in SRC_PATCHES:
        apply_patch_file(name)

    # ---- conditional C4 ownership anchor: cannot be a static diff ----
    patch("src/gen_exports/type_erasure.inc",
          "  using boost::mpl::item_by_order_impl;",
          "#if defined(__GNUC__)\n"
          "  // M9 platform guard (C4 moved the claim here from\n"
          "  // poly_collection): gcc-preprocessed mpl map headers only —\n"
          "  // absent from the msvc-flavor TU, keep the export gcc-only.\n"
          "  using boost::mpl::item_by_order_impl;\n"
          "#endif",
          required=False)  # C4: the entity may be claimed by type_erasure

    # M11 (M11 §6.4): new vendored file (mc.exe stub), not an upstream patch.
    ensure_file("deps/boost/libs/log/src/windows/simple_event_log.h", """
/*
 *          Copyright Andrey Semashev 2007 - 2015.
 * Distributed under the Boost Software License, Version 1.0.
 *    (See accompanying file LICENSE_1_0.txt or copy at
 *          http://www.boost.org/LICENSE_1_0.txt)
 */

/*
 * M11: hand-written replacement for the mc.exe-generated header. Upstream
 * builds it from simple_event_log.mc at configure/build time (see
 * libs/log/CMakeLists.txt); the vendored tree has no build-time code
 * generation, so the constants (which only need to be self-consistent event
 * IDs passed to ReportEvent) are defined here directly, mirroring the .mc
 * MessageId/Severity layout.
 */

#pragma once

#define BOOST_LOG_SEVERITY_DEBUG   0x00000000L
#define BOOST_LOG_SEVERITY_INFO    0x00000001L
#define BOOST_LOG_SEVERITY_WARNING 0x00000002L
#define BOOST_LOG_SEVERITY_ERROR   0x00000003L

#define BOOST_LOG_MSG_DEBUG   ((DWORD)0x01000100L)
#define BOOST_LOG_MSG_INFO    ((DWORD)0x01000101L)
#define BOOST_LOG_MSG_WARNING ((DWORD)0x01000102L)
#define BOOST_LOG_MSG_ERROR   ((DWORD)0x01000103L)
""")
    # ---- .inc platform guards (M3 §5, M6/M9/M11/M12 platform flavors):
    # the committed .inc files are a mingw-flavor snapshot; wrap Windows-only
    # / compiler-specific entities in the upstream header conditions. These
    # stay programmatic (the wrapped line set depends on the regenerated
    # .inc content, not on fixed anchors). ----
    guard_entity_lines("src/gen_exports/date_time.inc", "defined(_WIN32)", [
        "time_from_ftime",
        "from_ftime",
    ])
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
        "win_iocp_overlapped_op",
        "win_object_handle_service",
        "basic_object_handle",
        "basic_overlapped_handle",
        "basic_random_access_handle",
        "basic_stream_handle",
        "object_handle",
        "overlapped_handle",
        "overlapped_ptr",
        "random_access_handle",
        "stream_handle",
        "complete_iocp_accept",
        "complete_iocp_connect",
        "complete_iocp_recv",
        "complete_iocp_recvfrom",
        "complete_iocp_recvmsg",
        "complete_iocp_send",
        "msghdr",
    ])
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
    guard_entity_lines("src/gen_exports/signals2.inc", "defined(BOOST_HAS_WINTHREADS)", [
        "critical_section",
        "critical_section_debug",
        "rtl_critical_section",
    ])
    guard_entity_lines("src/gen_exports/interprocess.inc", "defined(_WIN32)", [
        "basic_managed_windows_shared_memory",
        "managed_windows_shared_memory",
        "windows_shared_memory",
        "wmanaged_windows_shared_memory",
        "do_winapi_wait",
        "winapi_mutex_functions",
        "winapi_mutex_wrapper",
        "winapi_semaphore_functions",
        "winapi_semaphore_wrapper",
        "winapi_wrapper_timed_wait_for_single_object",
        "winapi_wrapper_try_wait_for_single_object",
        "winapi_wrapper_wait_for_single_object",
        "windows_bootstamp",
        "windows_intermodule_singleton",
        "windows_semaphore_based_map",
        "file_time_to_microseconds",
        "get_bootstamp",
        "get_temporary_wpath",
        "intermodule_singleton_common",
        "intermodule_singleton_impl",
        "mapping_handle_from_shm_handle",
        "os_file_traits",
        "ref_count_ptr",
        "shm_named_mutex",
        "shm_named_semaphore",
        "spin_condition",
        "spin_mutex",
        "spin_recursive_mutex",
        "spin_semaphore",
        "unrestricted_permissions_holder",
        "wshmem_open_or_create",
        "get_map_base_name",
        "get_map_name",
        "get_map_size",
        "get_pid_creation_time_str",
        "thread_safe_global_map_dependant",
        "mutex_traits",
    ])
    guard_entity_lines("src/gen_exports/process.inc", "defined(_WIN32)", [
        "stream_handle",
    ])
    guard_entity_lines("src/gen_exports/asio.inc", "defined(BOOST_ASIO_HAS_FILE)", [
        "basic_file",
        "basic_random_access_file",
        "basic_stream_file",
        "file_base",
        "random_access_file",
        "stream_file",
    ])
    guard_entity_lines("src/gen_exports/asio.inc", "defined(_WIN32)", [
        "apc_function",
        "calculate_hash_value",
        "random_access_handle",
        "stream_handle",
        "fd_set_adapter",
        "hash_map",
        "null_reactor",
        "select_reactor",
        "null_signal_blocker",
        "socket_select_interrupter",
        "reactor_op_queue",
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
        "win_iocp_overlapped_op",
        "win_object_handle_service",
        "win_mutex",
        "win_static_mutex",
        "win_thread",
        "win_thread_base",
        "win_thread_function",
        "winsock_init",
        "winsock_init_base",
        "basic_object_handle",
        "basic_overlapped_handle",
        "basic_random_access_handle",
        "basic_stream_handle",
        "object_handle",
        "overlapped_handle",
        "overlapped_ptr",
        "complete_iocp_accept",
        "complete_iocp_connect",
        "complete_iocp_recv",
        "complete_iocp_recvfrom",
        "complete_iocp_recvmsg",
        "complete_iocp_send",
        "msghdr",
    ])
    guard_entity_lines("src/gen_exports/beast.inc", "defined(_WIN32)", [
        "file_win32",
        "set_file_pointer_ex",
        "win32_unicode_path",
        "highPart",
        "lowPart",
        "make_win32_error",
        "null_lambda",
        "run_write_some_win32_op",
        "write_some_win32_op",
        "basic_dstream",
        "dstream_buf",
    ])
    # ---- M3/M9 "final form" restores: these files are hand-maintained in
    # git (regeneration would clobber them), so pin them back from HEAD ----
    # M9: flyweight — restore the hand-trimmed committed form (the
    # generator leaks the transitive container/interprocess surface).
    restore_from_git("src/gen_exports/flyweight.inc")
    guard_entity_lines("src/gen_exports/thread.inc", "defined(_WIN32)", [
        "intrusive_ptr",
        "wait_operations_windows",
        "time_from_ftime",
        "from_ftime",
        "interruptible_wait",
        "non_interruptible_wait",
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
    # ---- algorithm: M3 workaround (string.hpp GFM + *regex pruning) ----
    # The committed M3 form is the source of truth; regenerate-free.
    restore_from_git("src/gen_exports/algorithm.inc")
    restore_from_git("src/gen_exports/algorithm.deps")
    # ---- M3 libs whose .cppm are unchanged (regen only rewrites the
    # header comment): keep the M3 "final form" convention. scope_exit
    # left the list in C1: boost.scope_exit is include-only now. ----
    restore_from_git("src/algorithm.cppm")
    restore_from_git("src/any.cppm")
    restore_from_git("src/container_hash.cppm")
    restore_from_git("src/core.cppm")
    restore_from_git("src/endian.cppm")
    restore_from_git("src/io.cppm")
    restore_from_git("src/iterator.cppm")
    restore_from_git("src/mp11.cppm")
    restore_from_git("src/optional.cppm")
    restore_from_git("src/range.cppm")
    restore_from_git("src/rational.cppm")
    restore_from_git("src/scope.cppm")
    restore_from_git("src/static_string.cppm")
    restore_from_git("src/tuple.cppm")
    restore_from_git("src/type_traits.cppm")
    restore_from_git("src/variant.cppm")
    restore_from_git("src/variant2.cppm")
    print("done.")


if __name__ == "__main__":
    main()
