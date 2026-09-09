# Changelog

> English version: [`CHANGELOG.md`](CHANGELOG.md)

本文件记录 boost-module 的版本演进。版本号格式 `b<boost版本>w<封装版本>`
（如 `b1.91.0w0.0.0-preview` = Boost v1.91.0 × 模块封装 v0.0.0 预览版）。

## b1.91.0w0.0.0-preview (2026-09-09, 预览版)

对 Boost 1.91.0 的首个 C++23 named modules 封装预览版。发布门槛按
"当前模块全量接入 + 已知限制披露" 口径执行（M13 外部依赖/asm 库持续暂缓）。

### 内容清单

- **116 个模块接口**（`src/*.cppm`）：消费者 `import boost.<lib>;` / 汇总
  `import boost;`（动态 re-export 当前激活库）。
- **118 个 feature**：116 模块 feature + `log` / `unit_test_framework`
  两个无模块 feature。
- **默认 49 库闭包**（`[features].default`），其余 opt-in
  （`features = [...]` / `default-features = false`）。
- **封装可消费总数 138 库** = 116 模块 + 2 编译库 include-only（log、
  test）+ 20 纯 include-only（宏驱动 16 + 降级 4）。
- **测试**: 默认集 141/141 smoke 通过；CI 四腿
  （windows-clang-msvc / linux-gcc / linux-llvm / macos-llvm-arm64）
  A/B 两组全量门禁。
- **`boost.version` 模块**: `boost::BOOST_VERSION` / `boost::BOOST_LIB_VERSION`
  constexpr 常量，默认集内、`import boost;` 自动可用。

### 里程碑史速览

| 里程碑 | 内容 | 结果要点 |
|---|---|---|
| M0 spike | 4 探针双编译器验证 `export namespace boost { using ...; }` 模式 | 模式成立; 导出规则确立; 消费者必须自带 std 表面 (设计使然); 链接模式成立 |
| M1 vendoring | 官方 tarball 导入, `boost/boost/` 汇总 include 根 | `deps/boost/` 布局定型 |
| M2 生成器 | gen_exports/gen_audit (libclang AST) + 27 库 4009 实体 | GMF root-only、friend 子树、clang++ gate、枚举器/特化检测 |
| M3 纯头 19 库 | 模块定稿 + 宏 re-homing + 旁路头 (C5 退役) | 生成器三修; scope 去 core 边 (gcc ICE)、algorithm 去 regex 面 (gcc abi-tag); `.inc` 平台守卫首建 |
| M4 编译 8 库 | TU 进 sources, 宏一致 | defines 补齐; stacktrace LINK+basic; filesystem v3; reapply_hand_edits 诞生 |
| M5 汇总+示例 | `import boost;` + examples | gcc B' 修复 (函数内 static 强符号 → 内部链接化 + 定义外移) |
| M6 CI 四腿 | 三平台适配 | POSIX 守卫、pthread once 伞文件、arm64/x86 守卫、mac typeinfo 兜底; depfile 纪律确立 |
| M8 features 基建 | build.mcpp 动态汇总 + gen_features | base-glob 陷阱验证; 默认闭包起点 18 |
| M9 T1a 58 库 | 纯头库批量接入 | dep_graph 传递遍历、注入 linkage 校验 |
| M10 T3 边界 | 宏面统计核实宏驱动库 include-only | 宏是预处理器 API 永不跨模块边界 |
| M11 T2 18 库 | 编译库批量 + exception 降级 | 逐库 TU 表定稿; POSIX 腿大批守卫 |
| M12 T1b 12 库 | 重型模板库 (asio/beast/geometry…) | clang 2^31 源位置上限 → CI A/B 分组; vendored 修补 5 族 |
| C1 | 五库降级 + utf 改名 | describe/openmethod/scope_exit/log/test → 编译库 include-only 新形态 |
| C2 | hof/units 重新模块化 | vendored 宏改造 (`inline constexpr`) 使对象获外链 |
| C4 (+C4.1) | bind/lambda/lambda2 重新模块化 | T3 宏面误判纠正; gcc 16 重复符号修复 (C4.1) |
| C5 | `boost.version` 模块形式化 | 删除 `macros.hpp` 旁路头; 默认闭包 48 → 49 |

（默认闭包演变: 18 (M8) → 31 (M9/M10) → 34 (M11) → 36 (M12) → 48
（dep_graph 体引用边修复）→ 49 (C5)。）

### 不支持 (M13 暂缓)

外部依赖/asm 库 11 个持续暂缓: context / fiber / coroutine (asm)、
locale (ICU)、mpi、python、parameter_python、graph_parallel、
compute (OpenCL)、mysql / redis (OpenSSL)。

### 已知限制

见 release notes（`docs/release_notes/b1.91.0w0.0.0-preview.md`）与
[架构文档 §4](docs/architecture.md#4-已知限制-消费者须知)。
