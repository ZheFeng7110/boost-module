# boost-module

使用 [mcpp](https://github.com/mcpp-community/mcpp) 构建工具对 [Boost 库](https://www.boost.org/)进行模块化封装
（C++23 named modules），思路参考 [opencv-m](https://github.com/Sunrisepeak/opencv-m)：
把 Boost 的头文件 API 以模块接口（`.cppm` + `export using`）的形式导出，让消费者可以
`import boost.filesystem;`（或汇总 `import boost;`），API 拼写与上游一致，无需
`#include` 头文件。

- 目标上游: **Boost 1.91.0** (`BOOST_VERSION 109100`)
- 编译器: clang 22 / gcc 16 (MinGW-w64), 与 opencv-m 一致的双编译器 CI 路线
- 仓库结构: `deps/boost/` (vendored 源码) + `src/*.cppm` + `src/gen_exports/*.inc` (生成器产物) + `scripts/` (辅助脚本) + `tests/`、`examples/` (计划中)

## 进度

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M0 | Spike 验证 (opencv 式 `export namespace boost { using ...; }` 成立) | ✅ |
| M1 | 官方 tarball vendoring 重做 (`scripts/import_boost.py`) | ✅ |
| M2 | 生成器 `scripts/gen_exports.py` + `scripts/gen_audit.py` | ✅ |
| M3 | 纯头库模块层 (19 库) + 每库 smoke 测试 | ✅ |
| M4 | 编译库接入 (8 库) + 双风味 28/28 测试 | ✅ |
| M5 | 汇总模块 `import boost;` 与消费者验证 | ⏳ |
| M6 | CI 与发布 | ⏳ |

## 辅助脚本

脚本依赖 **libclang**（`scripts/gen_exports.py` / `scripts/gen_audit.py` 用它解析
Boost 头文件的 AST）。未安装 libclang 时需先安装：

```bash
pip install libclang        # 或设置 LIBCLANG_PATH 指向本地 LLVM 的 libclang.dll
```

安装了 [uv](https://docs.astral.sh/uv/) 的用户无需手动安装 —— 脚本带 PEP 723 内联元数据，
`uv run` 会自动创建带 libclang 的临时环境：

```bash
uv run scripts/gen_exports.py --scan                 # 重新生成 scripts/libs.json
uv run scripts/gen_exports.py                        # 生成全部 27 库的导出列表
uv run scripts/gen_exports.py --libs optional system --emit-cppm
uv run scripts/reapply_hand_edits.py                 # 重生成后重放 M3/M4 手编 (.cppm 偏离 + .inc 平台守卫)
uv run scripts/gen_audit.py                          # static-inline / 内部链接审计
uv run scripts/import_boost.py                       # 重新导入官方 boost tarball
```

> 不用 uv 时照常 `python scripts/xxx.py` 运行即可（shebang 保持普通 `#!/usr/bin/env python3`，
> 内联元数据只是注释）。

各脚本职责：

- `scripts/import_boost.py` — 下载固定 SHA-256 的官方 `boost_1_91_0.tar.gz`，裁剪后导入
  `deps/boost/`（`boost/boost/` 汇总 include 根 + `libs/` 等）。
- `scripts/gen_exports.py` — libclang AST 枚举库的公共头 → 收集 `boost::` 外部链接实体 →
  依赖闭包（如 filesystem 连带 system::error_code）→ 跨模块去重（first wins）→ 产出
  `src/gen_exports/<lib>.inc`（`export namespace boost { using ...; }` 列表）、`*.deps`
  （`export import` 提示）、`src/<lib>.cppm` 草稿。
- `scripts/gen_audit.py` — 输出需手工替代的 static-inline / 内部链接实体清单。
- `scripts/reapply_hand_edits.py` — 重生成 `.inc`/`.cppm` 后一键重放全部手编
  （core/scope/algorithm 的 gcc 变通、`.inc` 平台守卫、算法头注释约定），幂等。

## 分支与 Tag 命名

分支名格式为 `bx.x.xwdev`：

- `b` = **boost**
- `x.x.x` = Boost 版本（如 `1.91.0`）
- `w` = **wrapper**（模块封装）
- `dev` = **develop** 的缩写

例如当前开发分支 `b1.91.0wdev` 对应 Boost v1.91.0 的模块封装开发。

Tag 命名同样带两段版本号，格式为 `b<boost版本>w<封装版本>`，例如 **`b1.91.0w0.0.0`**
表示 Boost v1.91.0、模块封装版本 0.0.0。

## 许可证

模块封装部分采用 [BSL (Boost Software License)](./LICENSE)。

仓库内其他第三方库保留各自的原始许可：
- Boost - [BSL (Boost Software License)](deps/boost/LICENSE_1_0.txt)
- libclang - [Apache License v2.0 with LLVM Exceptions](https://llvm.org/docs/DeveloperPolicy.html#new-llvm-project-license-framework)

## 相关文档

- 计划与里程碑: [`.agents/plan/boost-mcpp-module-plan.md`](.agents/plan/boost-mcpp-module-plan.md)
- 设计文档: [`.agents/docs/`](.agents/docs/)
