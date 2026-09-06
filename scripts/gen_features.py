#!/usr/bin/env python3
"""gen_features.py — generate the [features] block of mcpp.toml (M8).

One feature per Boost library. Each feature's `sources` = that library's
`.cppm` plus (for compiled libraries) its `libs/*/src/**` TU globs; `implies` =
the library's module import edges (read from src/gen_exports/<lib>.deps). The
generator also keeps `[build].sources` (the union of every feature's globs) in
sync — both are spliced between markers, so they cannot drift.

C1 (2026-09-06, usage-reclassification plan §1.2/§2): compiled include-only
libraries (boost_common.LIBS_COMPILED_INCLUDE_ONLY — log, test) keep a feature
with their library TU globs but have NO `.cppm` (no module interface, no CMI
to export). test's feature is renamed `unit_test_framework` (FEATURE_NAME_
OVERRIDE, aligned with the upstream CMake target boost_unit_test_framework);
the internal lib keys stay `log` / `test`. build.mcpp skips those features
when generating the `import boost;` aggregate (no `export import` edge exists
for a module-less feature).

Why base keeps every per-lib glob: `mcpp test` (includeDevDeps) skips the DROP
(only ADD runs), so the base `[build].sources` is what test mode compiles. If
per-lib globs lived ONLY in features, the default `mcpp test` would not build
the opt-in libraries and their tests would fail (plan §1.8 describes exactly
this feature-only shape; M8 keeps the base globs so the full test suite is
green by default, and `--features all` / per-group runs remain additive).
`mcpp build` (build mode) runs the DROP, so only active features' globs compile
— that is where the default-features selection actually takes effect. See
.agents/docs/2026-08-15-m8-mcpp-features-infra.md §1.1/§2.

Exception — FEATURE_ONLY_SOURCES: the unit_test_framework TU globs are
deliberately NOT put into the base set. In test mode the base compiles
unconditionally and every TU links into every test program (no archive
pull-on-demand), so the framework TUs and the official header-only aggregate
(<boost/test/included/**>, tests/test_included.cpp) would double-define the
framework symbols in one program (M11 §3 constraint: the two consumption
forms must never link together). Feature-only sources compile only when the
feature is active — in build AND test mode (M8 §1.1) — which makes the two
test forms mutually exclusive exactly as the plan requires: default `mcpp
test` runs the header-only form, `mcpp test --features unit_test_framework`
runs the compiled form.

Usage:
    uv run scripts/gen_features.py          # splice mcpp.toml + features.lst
    uv run scripts/gen_features.py --check  # verify committed output is current
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MCPP_TOML = ROOT / "mcpp.toml"
LIBS_JSON = ROOT / "scripts" / "libs.json"
DEPS_DIR = ROOT / "src" / "gen_exports"
FEATURES_LST = ROOT / "scripts" / "features.lst"

# The full module-library list — derived from boost_common.TARGET_LIBS (which
# knows the tier tables). boost_common has no hard dependency on libclang at
# import time, so plain `uv run scripts/gen_features.py` works. The compiled
# include-only libs (log, test — C1) are re-inserted at their former T2 slots
# so the generated feature block stays diff-stable.
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import boost_common as bc
    _T2_REINSERT = {"iostreams": "log", "serialization": "test"}
    LIBS = []
    for _lib in bc.TARGET_LIBS:
        LIBS.append(_lib)
        if _lib in _T2_REINSERT:
            LIBS.append(_T2_REINSERT[_lib])
    COMPILED_INCLUDE_ONLY = list(bc.LIBS_COMPILED_INCLUDE_ONLY)
except Exception:
    LIBS = [
        "optional", "variant", "variant2", "any", "core", "container_hash",
        "mp11", "static_string", "scope", "type_traits",
        "algorithm", "iterator", "range", "io", "rational", "endian",
        "tuple", "system",
        "filesystem", "regex", "thread", "chrono", "program_options",
        "stacktrace", "json", "url",
    ]
    COMPILED_INCLUDE_ONLY = []

# C1: feature-name overrides — the [features] table key (and features.lst
# line) differs from the internal lib key. Internal keys (COMPILED_TU_GLOBS,
# tests/test_utf.cpp naming) are unchanged; only the feature spelling follows
# the upstream CMake target boost_unit_test_framework. There is no
# `import boost.test` — the module is gone (compiled include-only).
FEATURE_NAME_OVERRIDE = {"test": "unit_test_framework"}


def feature_name(lib):
    return FEATURE_NAME_OVERRIDE.get(lib, lib)

# Default feature set = 18-lib closure (plan §3.2). The closure is computed from
# .deps below and asserted to be closed before writing; this is the candidate list.
DEFAULT_CANDIDATES = [
    "any", "algorithm", "chrono", "core", "filesystem", "io", "iterator",
    "json", "mp11", "optional", "range", "regex", "system", "thread",
    "tuple", "type_traits", "variant", "variant2",
]

# Compiled libraries: feature sources = .cppm + these TU globs.
COMPILED_TU_GLOBS = {
    "filesystem":       ["deps/boost/libs/filesystem/src/*.cpp"],
    "regex":            ["deps/boost/libs/regex/src/*.cpp"],
    "chrono":           ["deps/boost/libs/chrono/src/*.cpp"],
    "program_options":  ["deps/boost/libs/program_options/src/*.cpp"],
    "stacktrace":       ["deps/boost/libs/stacktrace/src/basic.cpp"],
    "json":             ["deps/boost/libs/json/src/*.cpp"],
    "url":              ["deps/boost/libs/url/src/**/*.cpp"],
    # thread: all-platform globs live in the feature; the target tables below
    # `!`-exclude the cross-platform ones (plan §3.1 "per-OS TU 互斥").
    "thread":           ["deps/boost/libs/thread/src/future.cpp",
                         "deps/boost/libs/thread/src/win32/*.cpp",
                         "deps/boost/libs/thread/src/pthread/once.cpp",
                         "deps/boost/libs/thread/src/pthread/thread.cpp"],
    # M9: parser pulls boost/charconv when std::from_chars is unavailable
    # (detail/numeric.hpp picks boost_charconv branch; seen on the linux-llvm
    # CI leg). boost.charconv is a module since M11 — parser now *implies* it
    # (EXTRA_IMPLIES below) instead of shipping its TUs, so the TU glob is not
    # duplicated across two features (double ADD when both are active).
    # M11 T2 compiled libs (design doc §2 — per-lib TU table with exclusions):
    # atomic: find_address_sse41.cpp excluded — upstream compiles it with
    # per-TU -msse4.1 flags only after a compiler probe; without its
    # BOOST_ATOMIC_USE_SSE41 the lock_pool takes the SSE2 path (this is the
    # upstream "probe failed" fallback, which we mirror).
    "atomic":           ["deps/boost/libs/atomic/src/lock_pool.cpp",
                         "deps/boost/libs/atomic/src/find_address_sse2.cpp"],
    "charconv":         ["deps/boost/libs/charconv/src/*.cpp"],
    # cobalt: io/*.cpp enumerated to exclude ssl.cpp (OpenSSL — external, M13);
    # main.cpp defines main_promise::run_main only, not ::main.
    "cobalt":           ["deps/boost/libs/cobalt/src/*.cpp",
                         "deps/boost/libs/cobalt/src/detail/*.cpp",
                         "deps/boost/libs/cobalt/src/io/steady_timer.cpp",
                         "deps/boost/libs/cobalt/src/io/system_timer.cpp",
                         "deps/boost/libs/cobalt/src/io/signal_set.cpp",
                         "deps/boost/libs/cobalt/src/io/sleep.cpp",
                         "deps/boost/libs/cobalt/src/io/read.cpp",
                         "deps/boost/libs/cobalt/src/io/write.cpp",
                         "deps/boost/libs/cobalt/src/io/serial_port.cpp",
                         "deps/boost/libs/cobalt/src/io/pipe.cpp",
                         "deps/boost/libs/cobalt/src/io/file.cpp",
                         "deps/boost/libs/cobalt/src/io/random_access_file.cpp",
                         "deps/boost/libs/cobalt/src/io/stream_file.cpp",
                         "deps/boost/libs/cobalt/src/io/endpoint.cpp",
                         "deps/boost/libs/cobalt/src/io/socket.cpp",
                         "deps/boost/libs/cobalt/src/io/datagram_socket.cpp",
                         "deps/boost/libs/cobalt/src/io/seq_packet_socket.cpp",
                         "deps/boost/libs/cobalt/src/io/stream_socket.cpp",
                         "deps/boost/libs/cobalt/src/io/resolver.cpp",
                         "deps/boost/libs/cobalt/src/io/acceptor.cpp"],
    # container: alloc_lib.c excluded (C TU) AND dlmalloc.cpp excluded — its
    # dlmalloc_* wrappers call the boost_cont_* C API defined in alloc_lib.c,
    # so shipping either alone leaves undefined symbols. This mirrors the
    # upstream "BOOST_CONTAINER_HEADER_ONLY" degradation (no extended
    # allocators); the pmr resource TUs are self-contained.
    "container":        ["deps/boost/libs/container/src/global_resource.cpp",
                         "deps/boost/libs/container/src/monotonic_buffer_resource.cpp",
                         "deps/boost/libs/container/src/pool_resource.cpp",
                         "deps/boost/libs/container/src/synchronized_pool_resource.cpp",
                         "deps/boost/libs/container/src/unsynchronized_pool_resource.cpp"],
    "contract":         ["deps/boost/libs/contract/src/contract.cpp"],
    # date_time: upstream CMake compiles only greg_month.cpp — the other
    # b2-era gregorian/posix_time TUs conflict with the 1.91 headers
    # (greg_weekday.hpp defines the as_*_string methods inline unconditionally).
    "date_time":        ["deps/boost/libs/date_time/src/gregorian/greg_month.cpp"],
    # exception is include-only on gcc 16.1 (see boost_common.py
    # LIBS_INCLUDE_ONLY_M11) — its clone TU ships no feature.
    "graph":            ["deps/boost/libs/graph/src/*.cpp"],
    # iostreams: external-library backends (zlib/gzip/bzip2/lzma/zstd, M13
    # boundary) excluded — only the system-library-free device TUs ship.
    "iostreams":        ["deps/boost/libs/iostreams/src/file_descriptor.cpp",
                         "deps/boost/libs/iostreams/src/mapped_file.cpp"],
    # log: windows/posix dirs are per-OS exclusive via the target tables'
    # `!` rules (same basename symbols in ipc_reliable_message_queue.cpp /
    # object_name.cpp). dump_avx2/dump_ssse3 are `!`-excluded on BOTH targets
    # (unconditional <immintrin.h> breaks arm64; their symbols are only
    # referenced under consumer-set BOOST_LOG_USE_AVX2/SSSE3, which the fixed
    # module interface cannot honor — M4 §9 pattern). event_log_backend.cpp
    # ships: its generated windows/simple_event_log.h is vendored as a
    # hand-written stub (see that file; the .mc constants only need to be
    # self-consistent event IDs).
    "log":              ["deps/boost/libs/log/src/*.cpp",
                         "deps/boost/libs/log/src/setup/*.cpp",
                         "deps/boost/libs/log/src/windows/*.cpp",
                         "deps/boost/libs/log/src/posix/*.cpp"],
    # math: no TU — libs/math/src has only the deprecated std::tr1 wrappers
    # (upstream CMake: add_library(boost_math INTERFACE)). Header-only module.
    "nowide":           ["deps/boost/libs/nowide/src/*.cpp"],
    # process: flat glob — every platform TU is internally guarded with
    # `#if defined(BOOST_PROCESS_V2_POSIX/WINDOWS)` (verified); all src TUs
    # are the v2 API.
    "process":          ["deps/boost/libs/process/src/**/*.cpp"],
    "random":           ["deps/boost/libs/random/src/random_device.cpp"],
    "serialization":    ["deps/boost/libs/serialization/src/*.cpp"],
    # test: unit_test_main.cpp / cpp_main.cpp / test_main.cpp are EXCLUDED —
    # they are upstream's prg_exec_monitor / test_exec_monitor entry points
    # that define ::main or reference the user's test_main(); `mcpp test`
    # links every TU into each test program, so they collide there (no archive
    # pull-on-demand in that mode). Consumers own main + the unit_test_main
    # runner (the runner comes from #including impl/unit_test_main.ipp with
    # BOOST_TEST_NO_MAIN, cf. tests/test_utf.cpp); all framework services are
    # linked from the remaining TUs. C1: these TUs ship under the module-less
    # unit_test_framework feature (FEATURE_ONLY_SOURCES — kept out of the
    # base set so the included/* aggregate test can link without them).
    "test":             ["deps/boost/libs/test/src/compiler_log_formatter.cpp",
                         "deps/boost/libs/test/src/debug.cpp",
                         "deps/boost/libs/test/src/decorator.cpp",
                         "deps/boost/libs/test/src/execution_monitor.cpp",
                         "deps/boost/libs/test/src/framework.cpp",
                         "deps/boost/libs/test/src/junit_log_formatter.cpp",
                         "deps/boost/libs/test/src/plain_report_formatter.cpp",
                         "deps/boost/libs/test/src/progress_monitor.cpp",
                         "deps/boost/libs/test/src/results_collector.cpp",
                         "deps/boost/libs/test/src/results_reporter.cpp",
                         "deps/boost/libs/test/src/test_framework_init_observer.cpp",
                         "deps/boost/libs/test/src/test_tools.cpp",
                         "deps/boost/libs/test/src/test_tree.cpp",
                         "deps/boost/libs/test/src/unit_test_log.cpp",
                         "deps/boost/libs/test/src/unit_test_monitor.cpp",
                         "deps/boost/libs/test/src/unit_test_parameters.cpp",
                         "deps/boost/libs/test/src/xml_log_formatter.cpp",
                         "deps/boost/libs/test/src/xml_report_formatter.cpp"],
    "timer":            ["deps/boost/libs/timer/src/*.cpp"],
    "type_erasure":     ["deps/boost/libs/type_erasure/src/dynamic_binding.cpp"],
    "wave":             ["deps/boost/libs/wave/src/*.cpp",
                         "deps/boost/libs/wave/src/cpplexer/**/*.cpp"],
}

# Hand-maintained implies additions (union with the generated .deps edges).
# parser: its GMF includes boost/charconv.hpp only where std::from_chars is
# unavailable (linux-llvm CI leg) — the mingw-generated .deps lacks the edge,
# but the consumer-side link dependency is unconditional on that branch.
# C1: log / test have no module, hence no .deps file — their implies are
# hand-pinned to the module import edges their module TUs carried before the
# downgrade (src/gen_exports/{log,test}.deps, deleted). The library TUs still
# need these features' TU globs at link time (e.g. log → filesystem/thread/
# chrono), so `--features log` / `--features unit_test_framework` must pull
# them in build mode.
EXTRA_IMPLIES = {
    "parser": ["charconv"],
    "log": ["assert", "atomic", "config", "core", "date_time", "filesystem",
            "integer", "intrusive", "io", "iterator", "move", "mp11",
            "numeric", "optional", "property_tree", "range", "regex",
            "smart_ptr", "system", "thread", "throw_exception", "type_index",
            "type_traits", "utility", "variant", "winapi"],
    "test": ["algorithm", "assert", "config", "core", "function", "iterator",
             "smart_ptr", "type_traits", "utility"],
}

# C1: features whose TU globs are feature-ONLY — deliberately excluded from
# the base [build].sources union. In test mode the base compiles
# unconditionally and every TU links into every test program, so the
# unit_test_framework TUs and the official header-only aggregate
# (<boost/test/included/**>, consumed by tests/test_included.cpp) would
# double-define the framework symbols when both land in one program (M11 §3).
# Feature-only sources compile only when the feature is active (M8 §1.1),
# making the two test consumption forms mutually exclusive. log's TUs stay in
# the base: its consumers only #include headers, no aggregate conflict.
FEATURE_ONLY_SOURCES = ["unit_test_framework"]

# Per-lib private compile flags (feature `flags` = private per-TU, never
# propagated to consumers — plan §3.1; was [build].flags in M4).
FEATURE_FLAGS = {
    "thread": [{"glob": "deps/boost/libs/thread/src/**",
                "defines": ["BOOST_THREAD_BUILD_LIB"]}],
    # log: the windows/ TUs include <security.h>, whose sspi.h chain requires
    # one of SECURITY_WIN32/KERNEL/MAC — upstream CMake defines SECURITY_WIN32
    # for exactly these TUs (CMakeLists.txt:324).
    "log":    [{"glob": "deps/boost/libs/log/src/windows/**",
                "defines": ["SECURITY_WIN32"]}],
}

# Library-owned extras (non-module TU needed by the module, M5/M7).
EXTRAS = {
    "system": ["src/boost_system_extras.cpp"],
    "thread": ["src/boost_thread_extras.cpp"],
    # M9: gcc 16.1.0 module consumers emit a partial vtable for
    # leaf::detail::exception<bad_result> whose non-virtual thunks stay
    # undefined (same pipeline bug as thread's clone_impl, cf. M7c). The
    # extern template in leaf.inc suppresses the consumer's instantiation;
    # this TU's explicit instantiation provides the complete vtable + thunks.
    "leaf": ["src/boost_leaf_extras.cpp"],
}

# Base `[build].flags` / ldflags that no longer live in features.
BASE_LDFLAGS_UNIX = ["-pthread"]

GEN_START = "# ── <gen-features> generated by scripts/gen_features.py — do not edit ──"
GEN_END = "# ── </gen-features> ──"


def load_libs_json():
    if LIBS_JSON.exists():
        return json.loads(LIBS_JSON.read_text(encoding="utf-8"))
    return None


def deps_of(lib):
    """Module import edges for a lib: {home lib} from src/gen_exports/<lib>.deps."""
    p = DEPS_DIR / (lib + ".deps")
    if not p.exists():
        return set()
    return {line.strip()[len("boost."):]
            for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("boost.")}


def feature_sources(lib):
    """Feature sources for a lib. Compiled include-only libs (log, test — C1)
    ship their library TU globs but no `.cppm`: the module interface (and the
    CMI it would produce) is gone."""
    srcs = []
    if lib not in COMPILED_INCLUDE_ONLY:
        srcs.append("src/{}.cppm".format(lib))
    srcs.extend(COMPILED_TU_GLOBS.get(lib, ()))
    srcs.extend(EXTRAS.get(lib, ()))
    return srcs


def all_sources():
    """Union of every feature's sources = [build].sources, minus the
    FEATURE_ONLY_SOURCES exclusions (C1: unit_test_framework's framework TUs
    must not compile unconditionally in test mode — see the docstring)."""
    skip = {feature_name(lib) for lib in FEATURE_ONLY_SOURCES}
    seen, out = set(), []
    for lib in LIBS:
        if feature_name(lib) in skip:
            continue
        for g in feature_sources(lib):
            if g not in seen:
                seen.add(g)
                out.append(g)
    return out


def dep_edges():
    """{lib: set(lib)} — .deps import edges + hand-maintained EXTRA_IMPLIES."""
    graph = {lib: deps_of(lib) for lib in LIBS}
    for lib, extra in EXTRA_IMPLIES.items():
        graph.setdefault(lib, set()).update(extra)
    return graph


def default_closure(candidates):
    """Candidates + their implies closure (within the full lib set)."""
    graph = dep_edges()
    active = set(candidates)
    changed = True
    while changed:
        changed = False
        for lib in list(active):
            for dep in graph[lib]:
                if dep not in active:
                    active.add(dep)
                    changed = True
    return [lib for lib in LIBS if lib in active]


def assert_closed(closure):
    graph = dep_edges()
    missing = sorted({d for lib in closure for d in graph[lib]} - set(closure))
    if missing:
        raise SystemExit(
            "default closure not closed; missing implies: {}".format(missing))


def _flags_toml(flags):
    return "[{}]".format(", ".join(
        '{{ glob = "{}", defines = [{}] }}'.format(
            f["glob"], ", ".join('"{}"'.format(d) for d in f["defines"]))
        for f in flags))


def render_toml_block():
    closure = default_closure(DEFAULT_CANDIDATES)
    assert_closed(closure)
    optin = [lib for lib in LIBS if lib not in closure]

    lines = [GEN_START]
    lines.append("[features]")
    lines.append("default = [{}]".format(
        ", ".join('"{}"'.format(feature_name(l)) for l in closure)))
    lines.append("all = {{ implies = [{}] }}".format(
        ", ".join('"{}"'.format(feature_name(l)) for l in LIBS)))
    for lib in LIBS:
        lines.append("[features.{}]".format(feature_name(lib)))
        lines.append("  sources = [{}]".format(
            ", ".join('"{}"'.format(s) for s in feature_sources(lib))))
        if lib in FEATURE_FLAGS:
            lines.append("  flags = {}".format(_flags_toml(FEATURE_FLAGS[lib])))
        deps = sorted(deps_of(lib) | set(EXTRA_IMPLIES.get(lib, ())))
        if deps:
            lines.append("  implies = [{}]".format(
                ", ".join('"{}"'.format(d) for d in deps)))
    lines.append(GEN_END)
    return "\n".join(lines) + "\n"


def render_sources_block():
    srcs = all_sources()
    return ("# ── <gen-sources> generated by scripts/gen_features.py — do not edit ──\n"
            "sources = [\n"
            + "\n".join('    "{}",'.format(s) for s in srcs)
            + "\n]\n"
            + "# ── </gen-sources> ──\n")


def splice(text, start_marker, end_marker, replacement):
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1 or end <= start:
        raise SystemExit("markers not found in mcpp.toml: {} / {}".format(
            start_marker, end_marker))
    end = text.find("\n", end) + 1
    return text[:start] + replacement + text[end:]


def write_committed():
    text = MCPP_TOML.read_text(encoding="utf-8")
    text = splice(text, "# ── <gen-sources>", "# ── </gen-sources>",
                  render_sources_block())
    text = splice(text, GEN_START, GEN_END, render_toml_block())
    MCPP_TOML.write_text(text, encoding="utf-8", newline="\n")
    # features.lst lists FEATURE names (build.mcpp consumes it; the module-less
    # entries log/unit_test_framework are skipped there — no CMI to export).
    feature_names = [feature_name(l) for l in LIBS]
    FEATURES_LST.write_text("\n".join(feature_names) + "\n",
                            encoding="utf-8", newline="\n")
    closure = default_closure(DEFAULT_CANDIDATES)
    print("wrote {}{} with {} features; default={} opt-in={}".format(
        MCPP_TOML, "" , len(LIBS), ",".join(closure),
        ",".join(l for l in LIBS if l not in closure)))
    print("wrote {} ({} libs)".format(FEATURES_LST, len(LIBS)))
    print("default closure: {}".format(" ".join(closure)))
    print("opt-in: {}".format(" ".join(l for l in LIBS if l not in closure)))


def check_committed():
    text = MCPP_TOML.read_text(encoding="utf-8")
    ok = True
    for name, marker_start, marker_end, expected in (
            ("sources", "# ── <gen-sources>", "# ── </gen-sources>",
             render_sources_block()),
            ("features", GEN_START, GEN_END, render_toml_block())):
        s = text.find(marker_start)
        e = text.find(marker_end)
        if s == -1 or e == -1:
            print("MISSING {} markers".format(name))
            ok = False
            continue
        e = text.find("\n", e) + 1
        actual = text[s:e]
        if actual != expected:
            print("DRIFT in {} block: run scripts/gen_features.py".format(name))
            ok = False
    lst = FEATURES_LST.read_text(encoding="utf-8").splitlines() if FEATURES_LST.exists() else []
    if lst != [feature_name(l) for l in LIBS]:
        print("DRIFT in features.lst")
        ok = False
    return ok


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        sys.exit(0 if check_committed() else 1)
    write_committed()
    return 0


if __name__ == "__main__":
    main()
