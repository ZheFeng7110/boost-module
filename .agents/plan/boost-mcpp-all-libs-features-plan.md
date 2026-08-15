# Boost 1.91.0 全库导入 + mcpp features 计划

> 日期: 2026-08-13 · 状态: 草稿 · 上游: Boost 1.91.0 (BOOST_VERSION 109100)
> 前置: [boost-mcpp-module-plan.md](boost-mcpp-module-plan.md) (M0–M6 已完成, 27 库接入, CI 四腿全绿)
> 本次范围: 全部 155 个库的接入方案 + mcpp features 选择性构建; 用户决策记录于 §5
> 进度: **M8 done (2026-08-15)** — features 基建落地, 27 库全部迁入 feature, build.mcpp 动态汇总

## 0. 目标

- 除宏驱动库与外部依赖库外, **全部 Boost 库**接入 C++23 模块层 (当前 27 → ~124 个模块)
- 通过 mcpp `[features]` (Cargo 风格, 加性) 让消费者**按库选择**构建内容:
  - 默认只构建"精简核心集" (闭包后 18 库), 其余 opt-in
  - `features = ["asio", "log"]` 精确选择; `default-features = false` 完全自选; `features = ["all"]` 全量
- `import boost;` 汇总模块**动态生成**: 恰好 re-export 当前激活的库 (build.mcpp 方案, 用户确认)
- 宏驱动库保持 include-only (import+include 混用, 标准允许); 外部依赖库单列里程碑

## 1. mcpp features 机制调研结论 (已验证源码)

对 mcpp v2026.8.11.3 (docs/05-mcpp-toml.md §2.8 + src/build/prepare.cppm 实证):

1. `[features]` 表形式可携带 `sources` (feature-gated 源文件 glob, **同时作用于 `bc.sources` 与 `modules.sources`, 即 .cppm 可被 gating**)、`implies` (传递闭包激活)、`defines` (**传播到消费者**的 interface 宏)、`flags` (per-glob 私有编译标志)
2. 激活集 = `[features].default` ∪ 显式请求, 经 implies 闭包; 消费者侧 `features = [...]` / `default-features = false` (Cargo 对等, #242)
3. feature-gated 机制: 出现在任一 feature `sources` 里的 glob 默认从构建剔除 (DROP), 激活时加回 (ADD); `!` 前缀 glob 为排除项。目标条件合并 (`[target.'cfg']`) 在 feature pass **之前** (prepare.cppm L1535/L2984 → L4341), 故 target 级 sources 同样受 DROP 管
4. `MCPP_FEATURE_<NAME>` 宏仅本包编译期可见 (私有), 消费者拿不到 → 消费者只能靠 import 区分
5. **条件 import 不可行**: 默认扫描器拒绝条件预处理块内的 import; scan_overrides 声明的 import 集合会被 P1689 编译后校验精确比对 (`verify_unit_expectations`), 多声明即报错
6. feature 变化一定改变 cflags (MCPP_FEATURE_*) → BMI/构建缓存键随 features 自动失效; build.mcpp 的 ctxHash 含 feature 集, 换 features 自动重跑 (build_program.cppm L396)
7. build.mcpp (Cargo build.rs 模型): 在 feature 激活后、modgraph 扫描前运行 (prepare.cppm L4882), `mcpp::has_feature()` 可编程注入 feature-gated 源 (opencv-m 先例)
8. `mcpp test` (includeDevDeps) 模式: DROP 跳过但 ADD 保留 → 非激活 feature 的源不编译, 测试须带对应 `--features`

## 2. 库分类 (155 目录, 157 - 2 个 .txt)

| Tier | 含义 | 数量 | 说明 |
|---|---|---|---|
| T0 | 已接入 | 27 | M0–M6 完成 |
| T1 | 纯头模块库 (新增) | ~78 | 非宏 header-only; 细分为 T1a 常规 (~63) / T1b 重型模板 opt-in (~15: asio/beast/hana/gil/geometry/compute/mysql/mqtt5/multiprecision/numeric/interprocess/accumulators/polygon/redis/qvm 等) |
| T2 | 编译模块库 (新增) | 19 | atomic/charconv/cobalt/container/contract/date_time/exception/graph/iostreams/log/math/nowide/process/random/serialization/test/timer/type_erasure/wave |
| T3 | 宏驱动 include-only | ~19 | preprocessor/mpl/fusion/proto/spirit/xpressive/lambda/lambda2/bind/typeof/vmd/phoenix/parameter/metaparse/function_types/tti/local_function/msm/foreach (用户确认不建模块) |
| T4 | 外部依赖/asm | 8 | mpi/python/parameter_python/graph_parallel/locale/context/fiber/coroutine (M13 单列里程碑) |
| T5 | 非库 | 4 | detail/headers 目录 + 2 个 .txt (不接入) |

> 最终名单以生成器结果为准: T3 判定标准 = 公共 API 宏注入面 (BOOST_PP_/BOOST_FUSION_/BOOST_SPIRIT_ 等族), 由 gen_audit.py 新增宏面统计核对, 不硬承诺。

## 3. 设计方案

### 3.1 mcpp.toml 结构

```toml
[package]        # 不变
[build]
sources = []     # 全部 per-lib 源移入 feature; 仅留共享 TU (初始为空)
include_dirs = ["include", "deps/boost"]
defines  = ["BOOST_ALL_NO_LIB", "_MT", "_WIN32_WINNT=0x0A00"]
cxxflags = ["-w"]

# ── <gen-features> 由 scripts/gen_features.py 生成, 勿手改 ──
[features]
default = [18 库核心闭包集]                    # 见 §3.2
all     = { implies = [全部 T1+T2 库] }        # CI 全量构建用
[features.optional]
sources = ["src/optional.cppm"]
implies = ["core", "type_traits"]
[features.filesystem]
sources = ["src/filesystem.cppm", "deps/boost/libs/filesystem/src/*.cpp"]
implies = ["system", "variant2"]
[features.thread]
sources = ["src/thread.cppm",
           "deps/boost/libs/thread/src/future.cpp",
           "deps/boost/libs/thread/src/win32/*.cpp",
           "deps/boost/libs/thread/src/pthread/once.cpp",
           "deps/boost/libs/thread/src/pthread/thread.cpp"]
flags    = [{ glob = "deps/boost/libs/thread/src/**", defines = ["BOOST_THREAD_BUILD_LIB"] }]
implies  = ["chrono", "core", "io", "optional", "system", "type_traits"]

# ── 每库 per-OS TU 互斥: feature 内列全平台 glob, target 表用 ! 排除 ──
[target.windows.build]
sources = ["!deps/boost/libs/thread/src/pthread/**"]
[target.unix.build]
sources = ["!deps/boost/libs/thread/src/win32/**"]
ldflags = ["-pthread"]
```

要点:
- 每库 feature 的 `sources` = 该库 `.cppm` + 该库编译 TU glob (T2); `implies` = 该库 `.deps` 的模块 import 边 (依赖闭包保证被 import 的模块必被编译)
- per-OS TU (thread 模式推广): 全平台 glob 进 feature, 异平台排除进 `[target.'cfg'.build]` (DROP 对 target 合并源同样生效, §1.3); 各 `.cpp` 内部平台自守卫的库无需 target 表
- `boost_system_extras.cpp` → feature `system`; `boost_thread_extras.cpp` → feature `thread` (不再无条件编译)
- 原 `[build].flags` thread 条目移入 feature `thread.flags` (私有 per-TU, 不传播消费者; 不能用 feature `defines` — 那会传播给消费者)

### 3.2 默认核心集 (18 库, implies 闭包)

候选 15 库 {any, algorithm, chrono, core, filesystem, io, json, mp11, optional, regex, system, thread, tuple, type_traits, variant} + 闭包 {variant2, iterator, range} = **18 库**:
any / algorithm / chrono / core / filesystem / io / iterator / json / mp11 / optional / range / regex / system / thread / tuple / type_traits / variant / variant2

- 闭包由生成器计算 (模块 import 边), 保证 `import boost;` 恒可编译
- 现 27 库中其余 9 库 (container_hash/endian/rational/scope/scope_exit/stacktrace/static_string/program_options/url) 移入 opt-in — 对应测试改由 `mcpp test --features <组>` 跑
- 集合可调 (用户偏好记录: 精简核心集)

### 3.3 动态汇总模块 (build.mcpp)

新增 `build.mcpp` (Cargo build.rs 模型, opencv-m 先例):

```cpp
import mcpp;   // + <cstdio> 等 (build.mcpp 编译环境无 import std;, 文本 include 先行)
int main() {
    // 读 scripts/features.lst (gen_features.py 生成的库清单, rerun_if_changed)
    // 对每个模块库: if (mcpp::has_feature(lib)) 收集 "export import boost.<lib>;"
    // spew(out_dir/boost.cppm, "export module boost;\n" + imports)  — mtime 稳定写
    // mcpp::source(out_dir/boost.cppm)   — 在 modgraph 扫描前可见 (prepare G2)
}
```

- 语义: `import boost;` 恰好 re-export 激活库 — 与任意 features 组合一致, 替代 M5 静态 `src/boost.cppm` (删除)
- 生成文件依赖 feature 集 (ctxHash 失效) + features.lst (rerun_if_changed)
- 零激活时生成 `export module boost;` 空壳 (合法)
- **M8 首日 spike 验证**: 生成模块被扫描/编译/打包进 lib target/消费者可 import (openai 未踩过此路, 见 §6 风险)

### 3.4 消费者用法

```toml
# 默认: 核心 18 库, import boost; / import boost.filesystem;
[dependencies]
boost.boost = { path = ".." }

# 只选若干库
boost.boost = { path = "..", default-features = false, features = ["optional", "json"] }

# 全量
boost.boost = { path = "..", features = ["all"] }
```

### 3.5 生成器管线扩展 (scripts/)

- `boost_common.py`: `TARGET_LIBS` → 从 libs.json 派生全库名单 + tier 表
- `libs.json`: 全量重生成 (27 → ~124 库, 938 → ~15000 头), standalone-compile filter + 人工 curation
- `gen_exports.py`: 全库模式 (`.cppm` + `.inc` + `.deps` + clang++ gate 自动裁剪 GFM, 沿用 M2 §10/§11)
- `gen_audit.py`: 全库 static-inline/内部链接审计 + 宏面统计 (T3 判定输入)
- **新 `gen_features.py`**: 由 libs.json + `.deps` 生成 `mcpp.toml` 的 `[features]` 块 (marker splice, 提交)、`features.lst`、default 闭包; 幂等
- `reapply_hand_edits.py`: 扩展新库手编
- `import_boost.py` / vendoring: 无变化 (M1 已全量导入)

## 4. 里程碑

### M8 — Features 基建 + 生成器全库化 (done)
- ✅ build.mcpp 生成汇总模块 spike (扫描/打包/消费者 import 三连验证) — 见设计文档 2026-08-15 §1
- ✅ gen_features.py + mcpp.toml 重构 (27 库全部迁入 feature) — 每库 feature = sources (`.cppm` + 编译 TU globs) + implies (模块 import 边); base `[build].sources` 保留全部 per-lib glob (实测 `sources=[]` 触发 src/** 推断会破坏 test 模式分组, 见设计文档 §1.1)
- ✅ 默认集改为 18 库闭包 (any/algorithm/chrono/core/filesystem/io/iterator/json/mp11/optional/range/regex/system/thread/tuple/type_traits/variant/variant2); 其余 9 库 opt-in (container_hash/endian/rational/scope/scope_exit/stacktrace/static_string/program_options/url)
- ✅ 静态 src/boost.cppm 删除, 由 build.mcpp 按激活 feature 动态生成 (import boost; 恰好 re-export 激活库)
- ✅ 验证: 默认 `mcpp build/test` + examples 全绿 (thread/url 为 M6 §5 已知 mingw 本地问题, 与改造前基线一致); `--features all` 27 库全绿; 消费者 `default-features=false` probe 绿 (仅 optional/json + implies 编译)
- 设计文档: `.agents/docs/2026-08-15-m8-mcpp-features-infra.md`

### M9 — 纯头库批量接入 (T1a, ~63 库)
- 每库: 生成 `.cppm/.inc/.deps` → clang++ gate → 裁剪/curated → 审计手编 → smoke 测试 (每库 1 文件, import + 2~3 代表性实体)
- 平台守卫实体按 M6 模式进 `.inc` #if 守卫; 跨库 first-wins 归属变动 → 全量重生成 + 门禁 + reapply 重放
- 验证: 分组 `mcpp test --features <批>` 全绿 + `--features all` 冒烟

### M10 — 宏驱动库边界确认 (T3, ~19 库)
- gen_audit 宏面统计核对名单; 文档记录 include-only 用法 (macros.hpp 旁路头不扩展)
- 无模块/无 feature/无构建工作; 验证: 代表性 include 冒烟 (import+include 混用)

### M11 — 编译库批量接入 (T2, 19 库)
- 每库: `.cppm` + `libs/*/src/**` 进 feature; per-OS TU 用 thread 模式 (`!` 排除); per-库私有 flags (thread 的 BOOST_THREAD_BUILD_LIB 模式推广, 如 math 的 quadmath 等)
- 验证: 每库 smoke + 链接正确性 (模块声明 ↔ 库 TU 定义, M4 §5 模式)

### M12 — 重型模板库 (T1b, ~15 库, opt-in)
- 巨型 GFM (asio/hana/geometry/gil 等) 编译时/内存门禁; 裁剪与拆分策略 (M2 §11 自动裁剪可能不够 → curated GFM 拆分)
- 验证: 单库 gate 通过 + smoke; 若某库模块化不可行 (编译 10 分钟级/内存爆炸), 降级为 include-only 并记录

### M13 — 外部依赖/asm 库 (T4, 8 库)
- context/fiber/coroutine: 评估 per-platform `.S` + build.mcpp os-gated 注入 (M8 的 build.mcpp 基建复用)
- locale: 无 ICU 降级接入评估 (facets 子集)
- mpi/python/graph_parallel/parameter_python: 无外部依赖不可构建 → 明确排除, 文档记录 (与用户确认的边界一致)
- 验证: 每库 smoke (能力范围内)

### M14 — 发布 (用户指定等全量接入后再做)
- mcpp-index 薄层 boost.lua (features 镜像进 xpkg 描述符) + docs/architecture.md + 发布流程

## 5. 用户决策记录 (2026-08-13)

1. 汇总模块: **build.mcpp 动态生成** (非静态 27 库)
2. 默认集: **精简核心集** (18 库闭包)
3. 宏驱动库: **保持 include-only**
4. 外部依赖库: **列入计划但单独里程碑** (M13)
5. 测试规模: **每库最小 smoke**

## 6. 风险与未知

| 风险 | 应对 |
|---|---|
| build.mcpp 生成模块未被扫描/打包/消费者 import (新路径) | M8 首日 spike, 三连验证; 失败则回退静态 27 库汇总 + 文档 |
| 巨型库模块编译时间/内存 (asio/hana/geometry/gil) | T1b 单列; 门禁 + GFM 拆分; 不可行降级 include-only |
| 27→124 库 first-wins 实体归属剧变 | 全量重生成 + clang++ gate + reapply 重放 (M3/M4 已有管线) |
| 跨模块 import 边与 feature implies 不一致 | .deps 自动生成 implies; `--features all` 全量门禁兜底 |
| 老库 static-inline/内部链接实体 | gen_audit 每库审计 + 手编 (M2 先例: 27 库仅 6 处) |
| `mcpp test` 对非默认库需 --features | CI 分组跑; 测试文件 import 缺失模块时编译失败即信号 |
| 消费者侧 feature 名拼写错误 | mcpp strict validation (警告/--strict 报错) |

## 7. 工作量预估

M8 基建 1–2 天 (含 spike) → M9 纯头库 2–3 天 → M10 宏库 0.5 天 → M11 编译库 2–3 天 → M12 重型库 1–2 天 → M13 外部库 1–2 天 → M14 发布 0.5–1 天。合计约 **8–13 天**。
