# Changelog

> 中文版: [`CHANGELOG_zh.md`](CHANGELOG_zh.md)

This file tracks the version history of boost-module. Version numbers follow the
`b<boost version>w<wrapper version>` format
(e.g. `b1.91.0w0.0.0-preview` = Boost v1.91.0 × modules wrapper v0.0.0 preview).

## b1.91.0w0.0.0-preview (2026-09-09, preview)

First C++23 named modules wrapper preview for Boost 1.91.0. The release bar was applied as
"all currently supported modules included + known limitations fully disclosed"
(M13 external-dependency/asm libraries remain deferred).

### Contents

- **116 module interfaces** (`src/*.cppm`): consumers `import boost.<lib>;` or the umbrella
  `import boost;` (dynamically re-exports the currently active libraries).
- **118 features**: 116 module features + two module-less features, `log` and
  `unit_test_framework`.
- **Default 49-library closure** (`[features].default`); everything else is opt-in
  (`features = [...]` / `default-features = false`).
- **138 libraries consumable in total** = 116 modules + 2 compiled libraries consumed
  include-only (log, test) + 20 pure include-only (16 macro-driven + 4 downgraded).
- **Testing**: 141/141 smoke tests pass on the default set; four CI legs
  (windows-clang-msvc / linux-gcc / linux-llvm / macos-llvm-arm64) with full A/B gating.
- **`boost.version` module**: `boost::BOOST_VERSION` / `boost::BOOST_LIB_VERSION`
  constexpr constants, part of the default set, automatically available via `import boost;`.

### Milestone History at a Glance

| Milestone | Scope | Key outcomes |
|---|---|---|
| M0 spike | 4 probes, dual-compiler validation of the `export namespace boost { using ...; }` pattern | Pattern viable; export rules established; consumers must provide their own std surface (by design); linkage model viable |
| M1 vendoring | Official tarball import, `boost/boost/` aggregate include root | `deps/boost/` layout finalized |
| M2 generator | gen_exports/gen_audit (libclang AST) + 27 libraries, 4009 entities | GMF root-only, friend subtrees, clang++ gate, enumerator/specialization detection |
| M3 header-only 19 libs | Module finalization + macro re-homing + bypass headers (C5 retired) | Three generator fixes; scope de-cored (gcc ICE), algorithm de-regexed (gcc abi-tag); `.inc` platform guards introduced |
| M4 compiled 8 libs | TUs into sources, macro consistency | defines completed; stacktrace LINK+basic; filesystem v3; reapply_hand_edits born |
| M5 umbrella + examples | `import boost;` + examples | gcc B' fix (function-local static strong symbols → internal linkage + definitions moved out) |
| M6 CI four legs | Three-platform adaptation | POSIX guards, pthread once umbrella header, arm64/x86 guards, mac typeinfo fallback; depfile discipline established |
| M8 features infrastructure | build.mcpp dynamic umbrella + gen_features | base-glob pitfall validated; default closure starts at 18 |
| M9 T1a 58 libs | Header-only batch onboarding | dep_graph transitive traversal, injected linkage validation |
| M10 T3 boundary | Macro-surface statistics confirm macro-driven libraries are include-only | Macros are preprocessor-level API and never cross module boundaries |
| M11 T2 18 libs | Compiled-library batch + exception downgrade | Per-library TU tables finalized; large batch of POSIX-leg guards |
| M12 T1b 12 libs | Heavy template libraries (asio/beast/geometry…) | clang 2^31 source-location cap → CI A/B split; 5 families of vendored patches |
| C1 | Five libraries downgraded + utf renamed | describe/openmethod/scope_exit/log/test → compiled libraries consumed include-only |
| C2 | hof/units re-modularized | Vendored macro rework (`inline constexpr`) gives objects external linkage |
| C4 (+C4.1) | bind/lambda/lambda2 re-modularized | T3 macro-surface misjudgment corrected; gcc 16 duplicate symbol fix (C4.1) |
| C5 | `boost.version` module formalized | `macros.hpp` bypass header removed; default closure 48 → 49 |

(Default closure evolution: 18 (M8) → 31 (M9/M10) → 34 (M11) → 36 (M12) → 48
(dep_graph body-reference edge fix) → 49 (C5).)

### Not Supported (M13 deferred)

11 external-dependency/asm libraries remain deferred: context / fiber / coroutine (asm),
locale (ICU), mpi, python, parameter_python, graph_parallel, compute (OpenCL),
mysql / redis (OpenSSL).

### Known Limitations

See the release notes (`docs/release_notes/b1.91.0w0.0.0-preview.md`) and
[architecture doc §4](docs/architecture.md#4-known-limitations-consumer-notes).
