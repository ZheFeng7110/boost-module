# boost-module

> English documentation: [`README.md`](README.md)

使用 [mcpp](https://github.com/mcpp-community/mcpp) 构建工具对 [Boost 库](https://www.boost.org/)进行模块化封装
（C++23 named modules），思路参考 [opencv-m](https://github.com/Sunrisepeak/opencv-m)：
把 Boost 的头文件 API 以模块接口（`.cppm` + `export using`）的形式导出，让消费者可以
`import boost.filesystem;`（或汇总 `import boost;`），API 拼写与上游一致，无需
`#include` 头文件。

- 目标上游: **Boost 1.91.0** (`BOOST_VERSION 109100`)
- 编译器: clang 22 / gcc 16 (MinGW-w64), 与 opencv-m 一致的双编译器 CI 路线
- 仓库结构: `deps/boost/` (vendored 源码) + `src/*.cppm` + `src/gen_exports/*.inc` (生成器产物) + `scripts/` (辅助脚本) + `tests/`、`examples/`

## 使用方式

```toml
# 默认: 49 库闭包
[dependencies]
boost.boost = { git = "https://github.com/ZheFeng7110/boost-module", tag = "b1.91.0w0.0.0-preview" }

# 只选若干库 (default-features = false 关闭默认集)
[dependencies.boost.boost]
git = "https://github.com/ZheFeng7110/boost-module"
tag = "b1.91.0w0.0.0-preview"
default-features = false
features = ["optional", "json"]

# 全量
boost.boost = { git = "https://github.com/ZheFeng7110/boost-module", tag = "b1.91.0w0.0.0-preview", features = ["all"] }
```

后续正式版发布后会上架 mcpp package，现阶段先使用 git 依赖。

详细使用说明见用户使用文档: [`docs/usage.md`](docs/zh/usage.md)

供开发者参考的项目架构文档: [`docs/architecture.md`](docs/zh/architecture.md)

## 分支与 Tag 命名

分支名格式为 `bx.x.xwdev`：

- `b` = **boost**
- `x.x.x` = Boost 版本（如 `1.91.0`）
- `w` = **wrapper**（模块封装）
- `dev` = **develop** 的缩写

例如当前开发分支 `b1.91.0wdev` 对应 Boost v1.91.0 的模块封装开发。

Tag 命名同样带两段版本号，格式为 `b<boost版本>w<封装版本>`，例如 **`b1.91.0w0.0.0`**
表示 Boost v1.91.0、模块封装版本 0.0.0。

修订记录: [`CHANGELOG_zh.md`](CHANGELOG_zh.md) | 详细发布记录: [`docs/zh/release_notes/`](docs/zh/release_notes)

## 许可证

模块封装部分采用 [BSL (Boost Software License)](./LICENSE)。

仓库内其他第三方库保留各自的原始许可：
- Boost - [BSL (Boost Software License)](deps/boost/LICENSE_1_0.txt)
- libclang - [Apache License v2.0 with LLVM Exceptions](https://llvm.org/docs/DeveloperPolicy.html#new-llvm-project-license-framework)
