# 特性宏 profile (`backend-*`) 设计 (2026-09-21)

> 日期: 2026-09-21 · 状态: 实施完成 (log 系), filesystem/thread 系延期 · 分支 `b1.91.0wdev`
> 范围: 为架构文档 §4.1「特性宏一律构建期固定」给出可行的消费者自定义通道 ——
> `[features.backend-<axis>-<impl>]` + mcpp `backend = "<axis>-<impl>"` 语法糖 +
> `build.mcpp` 互斥/架构校验; 首个落地 `backend-log-ssse3` / `backend-log-avx2`。
> 关联: [`docs/zh/architecture.md`](../../docs/zh/architecture.md) §3.1 / §4.1,
> [`docs/zh/usage.md`](../../docs/zh/usage.md) §5,
> 架构汇总 [`.agents/docs/2026-09-08-consolidated-design.md`](2026-09-08-consolidated-design.md) §7.1。

## 1. 问题

`BOOST_*` 特性宏在本包里"一律构建期固定"，两条独立原因：

1. **BMI 冻结**。`src/<lib>.cppm` 以固定预处理状态编译成 CMI：声明、inline
   函数体、模板定义全部固化。宏是预处理器概念，不跨模块边界；消费者在自己 TU
   里的 `#define` 改不了已编译的 BMI。
2. **导出清单冻结**。`src/gen_exports/<lib>.inc` 是 `gen_exports.py` 在固定宏
   快照（`scripts/boost_common.py` 的 `CLANG_ARGS` + `EXTRA_DEFINES`）下跑
   libclang 生成的。改变**实体集/签名**的宏会让已提交的 `.inc` 与模块面不一致。

因此"让消费者任意 `-D` 生效"在模块形态下不可能。可行解只有两条：把宏选择提升
为**构建期可选剖面 (profile)** 由 feature 触发重编译；对未受支持的宏提供**绕过
模块的 include-only 逃生**。

## 2. 机制

mcpp 的 feature 表已经是"消费者→依赖"的合法配置通道：`[features.<f>]` 支持
`defines`（包内 `-D`）、`sources`（仅激活时编译）、`flags`（按 glob 的私有
per-TU flags）、`implies`（传递闭包），且 feature 变化改 cflags → BMI/构建缓存
自动失效重编（`docs/06-features-and-capabilities.md`）。
`backend = "<impl>"` 是通用约定糖，1:1 脱糖为请求依赖的 `backend-<impl>` feature
（`docs/05-dependencies.md`）。

据此把 profile 全部命名为 `backend-<axis>-<impl>`，消费者写：

```toml
[dependencies.boost.boost]
git = "https://github.com/ZheFeng7110/boost-module", tag = "b1.91.0w0.0.0"
backend = "log-avx2"        # == features = ["backend-log-avx2"]
```

多轴组合用 `features = ["backend-log-avx2", "..."]`（`backend =` 只表达单轴）。

### 2.1 声明 (`scripts/gen_features.py`)

新增 `PROFILE_FEATURES` 表（单一事实源），`render_toml_block()` 在库 feature 之后
渲染 `[features.backend-*]`；条目字段：

| 字段 | 含义 |
|---|---|
| `feature` | `[features]` 键，必须以 `backend-` 开头 |
| `axis` | 互斥轴；同轴 >1 个激活即报错 |
| `defines` | 包级 `-D<macro>`（必须全包一致，否则模块 ODR） |
| `sources` | 仅激活时编译的额外 TU |
| `flags` | `[{glob, defines?, cxxflags?}]` 私有 per-TU flags |
| `implies` | 拉齐基础库 feature（`default-features=false` 也能工作） |
| `arch` | 仅该 `mcpp::target_arch()` 上有效，否则拒绝 |

同时生成 `scripts/profiles.lst`（`axis<TAB>feature<TAB>arch`），供 `build.mcpp`
读取，避免在 C++ 里硬编码 profile 清单。`gen_features.py --check` 一并校验
`mcpp.toml` / `features.lst` / `profiles.lst` 三方无漂移。

### 2.2 校验 (`build.mcpp`)

prepare 阶段、模块扫描之前读取 `scripts/profiles.lst`：

- 同轴激活 >1 个 profile → 打印全部冲突 feature 名并非零退出（可加性 feature
  模型没有内建互斥；capabilities 的 `exclusive` 是包级，不适合包内 profile）。
- `arch` 不符（如 `-mavx2` 在 arm64）→ 拒绝。

### 2.3 源归属 (`PROFILE_OWNED`)

一个 profile 想*加入* base 已排除的 TU 时，不能让 base feature 的 glob 也匹配到
它——**一个 `sources` 条目（包括 target `!` 排除）会压过 profile 的重新加入**
（2026-09-21 实测，`mcpp:source` 也不行）。因此：

- 从 `[target.*.build]` 删除 `!dump_avx2.cpp` / `!dump_ssse3.cpp`（见 `mcpp.toml`
  注释）。
- `gen_features.py` 的 `PROFILE_OWNED["log"]` 命中这两个文件；`feature_sources()`
  用 `_expand_globs()` 把 log 的粗 glob 展开成显式文件列表并剔除它们。

于是 base 构建（`mcpp build` 默认 / `mcpp test`）永不编译 dump 文件（arm64 的
`<immintrin.h>` 问题照旧规避），profile 激活时才作为额外 `sources` 加入，且
`mcpp test --features backend-log-avx2` 不会与 base double-compile。

## 3. 已落地 profile

| profile | 宏 | 源/flags | 约束 |
|---|---|---|---|
| `backend-log-ssse3` | `BOOST_LOG_USE_SSSE3` | `dump_ssse3.cpp` (`-mssse3`) | x86_64 |
| `backend-log-avx2` | `BOOST_LOG_USE_SSSE3` + `BOOST_LOG_USE_AVX2` | `dump_ssse3.cpp` (`-mssse3`) + `dump_avx2.cpp` (`-mavx2`) | x86_64 |

AVX2 profile 必须同时定义 SSSE3 并编译 `dump_ssse3.cpp`：`libs/log/src/dump.cpp`
在"定义 SSse3 或 AVX2 任一"时都会引用 `dump_data_*_ssse3*`，且 AVX2 运行时探测
先检查 SSSE3（实测 `backend-log-avx2` 只带 AVX2 时 `dump.cpp` 编译失败）。

宏只作用于库 TU 的 dispatch 表：`deps/boost/boost/log/` 公共头不引用这两个宏，
因此 include-only 的消费者**无需**自定宏，profile 的 `defines` 只作用于包编译。

## 4. 验证

- `mcpp build --configure-only`：默认 481 条，无 `dump_*`；`--features
  backend-log-avx2` 483 条，`dump_ssse3.cpp` 带 `-DBOOST_LOG_USE_SSSE3 -mssse3`、
  `dump_avx2.cpp` 带 `-DBOOST_LOG_USE_SSSE3 -DBOOST_LOG_USE_AVX2 -mavx2`。
- `mcpp build --features backend-log-avx2,backend-log-ssse3` → `build.mcpp` 报
  `conflicting profile features on axis 'log-dump'` 并退出。
- 独立消费者 `default-features=false, backend="log-avx2"` 与
  `backend="log-ssse3"` 均构建链接通过（log 闭包 26 库）。
- `examples/profiles_usage`（`mcpp run -p profiles_usage`，x86_64）运行并输出
  dump 十六进制；CI examples job 对非 `macos-llvm` 腿执行。
- `uv run scripts/gen_features.py --check` 通过。

## 5. 扩展路径（未落地）

按宏对模块面的影响分三类：

1. **仅加 flags/defines（实体集无关）** — 最省，直接加 `PROFILE_FEATURES` 条目。
2. **替换既有 TU（stacktrace 后端等）** — feature 是加性的，不能"减" base 的
   `sources`；需要把 base feature 改成"模块 + 无 TU"，由 `backend-<impl>` 各自带
   实现 TU 并 `implies` 基础 feature。注意 `mcpp test` 编译 base `[build].sources`
   并集，替换型 profile 会与 base TU double-compile，需 `FEATURE_ONLY_SOURCES`
   式的隔离，改动面较大。
3. **改变导出实体集（`BOOST_FILESYSTEM_VERSION`、`BOOST_THREAD_VERSION`）** —
   需要对**全部**模块在替代宏下重新生成一遍导出树（cross-module first-wins dedup
   是有序且级联的，不能只重生成单个库），即 `src/gen_exports/<profile>/` 或
   `gen_exports.py --profile` 输出后缀。这是独立里程碑，未纳入本期。

本期对 2/3 类宏的答案仍是 include-only 逃生：消费者 `#define` 后
`#include <boost/...>`，放弃该库模块面（`deps/boost` 是传播给消费者的公共
`include_dirs`）。

CI 修复补充（2026-09-21，windows-llvm-msvc examples 腿）：include-only 消费者
自身 TU 的 ABI 宏必须与包内库 TU 一致 —— 包侧 `[build].defines`（`_MT`）只作用
于包内 TU，不传播给消费者；消费者 TU 缺 `_MT` 时 boost config 判不出
`BOOST_HAS_THREADS`，`BOOST_LOG_VERSION_NAMESPACE` 算成 `v2s_st`
（`BOOST_LOG_NO_THREADS`），而包内 log TU 是 `v2s_mt_nt62`，链接期
`/failifmismatch` 报 `boost_log_abi` mismatch。修在 vendored 层而不是要求
消费者自带宏（`_WIN32_WINNT` 无需处理：无该宏时 winapi 对 `_MSC_VER >= 1900`
默认 WIN10，与包侧 `0x0A00` 一致）：

- `scripts/patchs/config_platform.patch` — `boost/config/platform/win32.hpp`
  无条件 `#define BOOST_HAS_THREADS`：cl.exe 恒定义 `_MT`（无单线程 CRT），只有
  GNU 风味 clang++ 驱动（target `*-windows-msvc`）缺线程宏；Win32 恒有线程，
  `BOOST_DISABLE_THREADS` 的撤销通道（config/detail/suffix.hpp）不受影响。
- `scripts/patchs/config_user.patch` — `boost/config/user.hpp` 恒
  `#define BOOST_ALL_NO_LIB`：线程打开后消费者 TU 会为不存在的
  `libboost_log-clangw23-mt-s-x64-1_91.lib` 等 autolink 发 /DEFAULTLIB pragma；
  本发行版经 mcpp 构建图直连对象，无可供 autolink 的库，恒关。两个补丁经
  `reapply_hand_edits.py` 的 VENDORED_PATCHES 回放，重 vendor 不丢。

## 6. 决策与取舍

- **为什么用 feature 而不是环境变量**：feature 是声明式、可复现、进缓存键；
  环境变量注入虽能覆盖任意宏，但不可声明、不进 lock，且必然与 `.inc` 漂移。
- **为什么 `backend-` 前缀**：复用 mcpp 通用糖，消费者无需记专有语法。
- **为什么互斥在 `build.mcpp` 而不是 capabilities**：capabilities 的
  `exclusive` 是包级提供者去重，包内两个 feature 无法用它表达互斥。
- **默认值不变**：默认构建不激活任何 profile，`BOOST_*` 仍取上游默认
  （filesystem v3 / thread v2），既有消费者零影响。
