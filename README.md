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

```toml
# Default: 49-library closure
[dependencies]
boost.boost = { git = "https://github.com/ZheFeng7110/boost-module", tag = "b1.91.0w0.0.0-preview" }

# Pick a few libraries only (default-features = false disables the default set)
[dependencies.boost.boost]
git = "https://github.com/ZheFeng7110/boost-module"
tag = "b1.91.0w0.0.0-preview"
default-features = false
features = ["optional", "json"]

# Everything
boost.boost = { git = "https://github.com/ZheFeng7110/boost-module", tag = "b1.91.0w0.0.0-preview", features = ["all"] }
```

Once the first stable release is out, the package will be published on the mcpp package index;
for now, use git dependencies.

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

Tags carry both version numbers in the form `b<boost version>w<wrapper version>`, e.g.
**`b1.91.0w0.0.0`** means Boost v1.91.0 with wrapper version 0.0.0.

Revision history: [`CHANGELOG.md`](CHANGELOG.md) | Detailed release notes:
[`docs/release_notes/`](docs/release_notes)

## License

The modules wrapper itself is licensed under the [BSL (Boost Software License)](./LICENSE).

Other third-party libraries in this repository keep their original licenses:
- Boost - [BSL (Boost Software License)](deps/boost/LICENSE_1_0.txt)
- libclang - [Apache License v2.0 with LLVM Exceptions](https://llvm.org/docs/DeveloperPolicy.html#new-llvm-project-license-framework)
