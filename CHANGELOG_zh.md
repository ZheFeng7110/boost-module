# Changelog

> English version: [`CHANGELOG.md`](CHANGELOG.md)

本文件记录 boost-module 的版本演进。版本号采用六段纯数字
`v<boost版本>.<封装版本>` 格式（如 `v1.91.0.0.0.1` = Boost v1.91.0 × 模块封装
v0.0.1）。2026-09-22 之前发布的条目使用历史的 `b<boost版本>w<封装版本>` 拼写,
原样保留。

## 1.91.0.0.0.1 (2026-09-22, 正式版补丁)

模块封装补丁 `1.91.0.0.0.1`（git tag `v1.91.0.0.0.1`）。模块/feature 计数与可消费面
与 `1.91.0.0.0.0`（tag `b1.91.0w0.0.0`）完全一致; 变更仅为版本/tag 命名迁移与一处
Windows 构建修复。

### 自 b1.91.0w0.0.0 以来的变更

- **版本/tag 命名迁移**: 由 `b<boost>w<封装>` 切换为六段纯数字
  `v<boost版本>.<封装版本>` 方案（`[package].version = "1.91.0.0.0.1"`,
  tag `v1.91.0.0.0.1`）—— 因 mcpp 版本语法要求首字符为数字、数值核心不接受字母。
  消费者需将 `tag = ...` / `rev = ...` 更新为 `v1.91.0.0.0.1`。
- **Windows 构建修复**: 将 `BOOST_THREAD_BUILD_LIB` 从 `[features.thread].flags`
  移回基础 `[build].flags`（按 glob 作用于 `deps/boost/libs/thread/src/**`）,
  使 thread 未激活时 `mcpp test` 不再因 `tss_cleanup_implemented()` 链接失败;
  同步更新 `scripts/gen_features.py`。
- 无模块、feature、计数或 API 变更; 支持的库集合不变。

### 已知限制

与 `1.91.0.0.0.0` 一致; 因 T3 package index 集成仍待做, 在该版中保持全量披露。
见 [`docs/zh/release_notes/v1.91.0.0.0.1.md`](docs/zh/release_notes/v1.91.0.0.0.1.md)。

## b1.91.0w0.0.0 (2026-09-21, 正式版)

Boost 1.91.0 的首个正式版。模块/feature 计数与预览版一致; 本周期收口了若干导出
盲区, 并新增了消费者选择特性宏的受支持通道。mcpp package index 上架 (T3) 有意
安排在本次 tag 之后, 故现阶段仍以 git 依赖为支持渠道。

### 内容清单

- **116 个模块接口**（`src/*.cppm`）：消费者 `import boost.<lib>;` / 汇总
  `import boost;`（动态 re-export 当前激活库）。
- **118 个库 feature**：116 模块 feature + `log` / `unit_test_framework`
  两个无模块 feature; 另有 **2 个 profile feature**（`backend-log-ssse3` /
  `backend-log-avx2`, x86_64 Boost.Log dump 后端）。
- **默认 49 库闭包**（`[features].default`），其余 opt-in
  （`features = [...]` / `default-features = false`）。
- **封装可消费总数 138 库** = 116 模块 + 2 编译库 include-only（log、
  test）+ 20 纯 include-only（宏驱动 16 + 降级 4）。
- **测试**: 默认集 141/141 smoke 通过；CI 四腿
  （windows-clang-msvc / linux-gcc / linux-llvm / macos-llvm-arm64）
  A/B 两组全量门禁。
- **`boost.version` 模块**: `boost::BOOST_VERSION` / `boost::BOOST_LIB_VERSION`
  constexpr 常量，默认集内、`import boost;` 自动可用。

### 预览版以来的变更

- **特性宏 profile (`backend-*`)**: 消费者可选 `BOOST_*` 特性宏, 首批
  `backend-log-ssse3` / `backend-log-avx2`; `build.mcpp` 校验同轴互斥与目标架构。
- **变量模板导出**: `boost::pfr::tuple_size_v`、`boost::hana::int_c` /
  `integral_c` 等 21 个模块的 363 条变量模板; 生成器可分类不透明的
  `UNEXPOSED_DECL` 变量模板并恢复跨模块初始化器依赖。
- **内部链接对象导出**: range adaptor 管道语法、`boost::extents` /
  `boost::indices`、accumulators `extract::*`、mqtt5 `prop::*`, 经 vendored
  `inline` 修补导出。
- **include-only 消费者 Win32 ABI 对齐**（`config` 修补）: 修复 clang-msvc 的
  `boost_log_abi` mismatch。
- **导出生成器加固**: 固定 MinGW sysroot bootstrap、统一 `clang++` gate、重建
  `process.inc`; **构建修复**: `boost.cppm` 生成到 `MCPP_OUT_DIR`。
- **CI**: group A/B 改为并行 job, examples 对两者同时门禁; 升级 toolchain/缓存;
  补齐完整英文文档。

### 不支持 (M13 暂缓)

外部依赖/asm 库 11 个持续暂缓: context / fiber / coroutine (asm)、
locale (ICU)、mpi、python、parameter_python、graph_parallel、
compute (OpenCL)、mysql / redis (OpenSSL)。

### 已知限制

见 release notes（`docs/release_notes/b1.91.0w0.0.0.md`）与
[架构文档 §4](docs/architecture.md#4-已知限制-消费者须知)。因 T3 package index
集成仍待做, 已知限制保持全量披露, 未做正式版的精简。

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
