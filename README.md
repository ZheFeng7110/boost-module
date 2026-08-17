# boost-module

使用 [mcpp](https://github.com/mcpp-community/mcpp) 构建工具对 [Boost 库](https://www.boost.org/)进行模块化封装
（C++23 named modules），思路参考 [opencv-m](https://github.com/Sunrisepeak/opencv-m)：
把 Boost 的头文件 API 以模块接口（`.cppm` + `export using`）的形式导出，让消费者可以
`import boost.filesystem;`（或汇总 `import boost;`），API 拼写与上游一致，无需
`#include` 头文件。

- 目标上游: **Boost 1.91.0** (`BOOST_VERSION 109100`)
- 编译器: clang 22 / gcc 16 (MinGW-w64), 与 opencv-m 一致的双编译器 CI 路线
- 仓库结构: `deps/boost/` (vendored 源码) + `src/*.cppm` + `src/gen_exports/*.inc` (生成器产物) + `scripts/` (辅助脚本) + `tests/`、`examples/`

## 进度

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M0 | Spike 验证 (opencv 式 `export namespace boost { using ...; }` 成立) | ✅ |
| M1 | 官方 tarball vendoring 重做 (`scripts/import_boost.py`) | ✅ |
| M2 | 生成器 `scripts/gen_exports.py` + `scripts/gen_audit.py` | ✅ |
| M3 | 纯头库模块层 (19 库) + 每库 smoke 测试 | ✅ |
| M4 | 编译库接入 (8 库) + 28/28 测试 | ✅ |
| M5 | 汇总模块 `import boost;` 与消费者验证 (含 gcc/mingw 多重定义 B' 修复) | ✅ |
| M6 | CI 矩阵与三平台适配 (win/linux/mac) 全绿 | ✅ |
| M7 | 剩余库接入与发布 (被 M8–M14 计划拆分) | ⏳ |
| M8 | mcpp features 基建 (build.mcpp 动态汇总 + 生成器全库化) | ✅ |
| M9 | 纯头库批量接入 (T1a, 58 库) + 88/88 测试 | ✅ |
| M10 | 宏驱动库边界确认 (include-only) | ⏳ |
| M11 | 编译库批量接入 (T2, 19 库) | ⏳ |
| M12 | 重型模板库接入 (T1b, ~15 库 opt-in) | ⏳ |
| M13 | 外部依赖/asm 库 (T4: context/fiber/coroutine/locale 等) | ⏳ |
| M14 | 发布 (mcpp-index 薄层 + 架构文档 + 发布流程) | ⏳ |

> 里程碑 M7 之后见 [`boost-mcpp-all-libs-features-plan.md`](.agents/plan/boost-mcpp-all-libs-features-plan.md):
> 全库 (155 库) 接入 + mcpp `[features]` 按库选择性构建 (`default-features = false` 自选,
> `features = ["all"]` 全量); 汇总模块 `import boost;` 由 build.mcpp 动态生成, 恰好
> re-export 激活的库。

## 按库选择性构建 (M8 mcpp features + M9 全量接入)

每个库对应一个 feature（`scripts/gen_features.py` 生成，勿手改）：
当前共 **85 个模块**（T0 27 + M9 T1a 58），hof/units/static_assert/predef 等
宏/constexpr-对象 API 库保持 include-only（详见 M9 设计文档）。

- **默认集** = 31 库闭包（`[features].default`，随模块 import 边自动增长）：
  `mcpp build` / `mcpp test` 覆盖核心面（18 个原核心库 + config/assert/
  utility/move 等基建库）。
- **opt-in 库**：其余 54 库需显式激活：`mcpp build --features <库,...>`。
- **全量**：`mcpp build --features all`（85 模块全部编译）。

消费者侧（path dep 用法）：

```toml
# 默认: 核心 18 库
[dependencies]
boost.boost = { path = ".." }

# 只选若干库 (default-features = false 关闭默认集)
boost.boost = { path = "..", default-features = false, features = ["optional", "json"] }

# 全量
boost.boost = { path = "..", features = ["all"] }
```

`import boost;`（build.mcpp 动态生成的汇总模块）恰好 re-export 当前激活的库；
零激活时是合法空壳。详见
[`.agents/docs/2026-08-15-m8-mcpp-features-infra.md`](.agents/docs/2026-08-15-m8-mcpp-features-infra.md)。

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
uv run scripts/gen_exports.py                        # 生成全部 85 库的导出列表
uv run scripts/gen_exports.py --libs optional system --emit-cppm
uv run scripts/reapply_hand_edits.py                 # 重生成后重放 M3/M4/M9 手编 (.cppm 偏离 + .inc 平台守卫)
uv run scripts/gen_features.py                       # 重新生成 mcpp.toml 的 [features] 块 + scripts/features.lst
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
- `scripts/gen_features.py` — 由 `libs.json` + `src/gen_exports/*.deps` 生成
  `mcpp.toml` 的 `[features]` 块（每库一个 feature，`sources` = 该库 `.cppm` + 编译库
  TU globs，`implies` = 模块 import 边）与 `scripts/features.lst`（build.mcpp 消费）。
  默认集 = 18 库闭包，其余 9 库 opt-in（`--features <库>` 显式激活）。
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
- 全库导入 + mcpp features 计划: [`.agents/plan/boost-mcpp-all-libs-features-plan.md`](.agents/plan/boost-mcpp-all-libs-features-plan.md)
- 设计文档: [`.agents/docs/`](.agents/docs/)
