# boost-module

> 中文文档: [`README_zh.md`](README_zh.md)

C++23 named modules wrapper for the [Boost libraries](https://www.boost.org/), built with the
[mcpp](https://github.com/mcpp-community/mcpp) build tool, following the approach of
[opencv-m](https://github.com/Sunrisepeak/opencv-m): Boost's header-based API is exported as
module interfaces (`.cppm` + `export using`), so consumers can simply write
`import boost.filesystem;` (or the umbrella `import boost;`). The API spelling is identical to
upstream — no `#include` needed.

- Target upstream: **Boost 1.91.0** (`BOOST_VERSION 109100`)
- Compilers: clang 22 / gcc 16 (MinGW-w64), the same dual-compiler CI approach as opencv-m
- Repository layout: `deps/boost/` (vendored sources) + `src/*.cppm` + `src/gen_exports/*.inc`
  (generator output) + `scripts/` (helper scripts) + `tests/`, `examples/`

## Usage

The package is published on the mcpp package index (namespace `ZheFeng7110`):

```toml
# Default: 49-library closure
[dependencies.ZheFeng7110]
boost = { version = "1.91.0.0.1.0" }

# Pick a few libraries only (default-features = false disables the default set)
[dependencies.ZheFeng7110]
boost = { version = "1.91.0.0.1.0", default-features = false, features = ["optional", "type_traits", "json", "version"] }

# Everything
[dependencies.ZheFeng7110]
boost = { version = "1.91.0.0.1.0", features = ["all"] }
```

Alternatively, depend on the git repository directly:

```toml
[dependencies.ZheFeng7110.boost]
# Mainland China mirror: https://gitcode.com/ZheFeng7/boost-module
git = "https://github.com/ZheFeng7110/boost-module"
tag = "v1.91.0.0.1.0"
```

Both channels carry the same package; the mcpp package index is the recommended one.

See the user guide for details: [`docs/usage.md`](docs/usage.md)

Project architecture documentation for developers: [`docs/architecture.md`](docs/architecture.md)

## Branch and Tag Naming

Branches are named `bx.x.xwdev`:

- `b` = **boost**
- `x.x.x` = Boost version (e.g. `1.91.0`)
- `w` = **wrapper** (the modules wrapper)
- `dev` = short for **develop**

For example, the current development branch `b1.91.0wdev` corresponds to the modules wrapper
for Boost v1.91.0.

Tags carry both version numbers as a six-segment numeric version, `v<boost version>.<wrapper version>`
(each three segments), e.g. **`v1.91.0.0.1.0`** means Boost v1.91.0 with wrapper version 0.1.0.

The version must be pure digits and dots: mcpp's version grammar requires a digit first (no `b`/`v`
prefix) and rejects letters in the numeric core. The leading `v` belongs to the git tag only — the
`[package].version` field and a consumer's `version = "..."` declaration must omit it. mcpp's publish
convention already prepends `v` when it derives the tag/tarball URL.

Revision history: [`CHANGELOG.md`](CHANGELOG.md) | Detailed release notes:
[`docs/release_notes/`](docs/release_notes)

## License

The modules wrapper itself is licensed under the [BSL (Boost Software License)](./LICENSE).

Other third-party libraries in this repository keep their original licenses:
- Boost - [BSL (Boost Software License)](deps/boost/LICENSE_1_0.txt)
- libclang - [Apache License v2.0 with LLVM Exceptions](https://llvm.org/docs/DeveloperPolicy.html#new-llvm-project-license-framework)
