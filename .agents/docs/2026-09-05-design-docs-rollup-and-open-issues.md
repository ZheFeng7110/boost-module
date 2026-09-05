# 设计文档汇总与未解问题清单 (rollup)

> 日期: 2026-09-05 · 状态: 汇总快照 (基于 M0–M12 已完成时点)
> 来源: `.agents/docs/` 全部 11 篇设计文档 + `.agents/plan/` 3 篇计划/报告 + README.md
> 范围说明: **M13 (外部依赖/asm 库, 11 库) 按用户决策暂跳过不做** —— 本文仅将其
> 记录为边界 (§3.6), 不展开方案; M14 (发布) 亦未开始。
> 用途: (1) 一页看懂各里程碑设计; (2) 集中登记所有文档中"边界与已知限制"
> 小节的未解问题, 供后续里程碑 (M13/M14 及维护期) 逐项销账。

## 1. 设计文档一览 (逐篇摘要)

| 文档 | 里程碑 | 一句话摘要 |
|---|---|---|
| plan/2026-08-08-m0-spike-results.md | M0 | 4 探针双编译器验证 `export namespace boost { using ...; }` 模式成立; 产出导出规则、gcc 坑 A/B (GMF 实例化缺口、消费者 std 表面)、链接模式结论 |
| plan/boost-mcpp-module-plan.md | 主计划 | M0–M7 主线: vendoring → 生成器 → 纯头/编译库接入 → 汇总模块 → CI 四腿; 边界: 宏库不封装、特性宏构建期固定、外部依赖库排除 |
| plan/boost-mcpp-all-libs-features-plan.md | M8–M14 | 全库 155 库接入 + mcpp `[features]` 选择性构建; 默认 18 库闭包 (现 36), build.mcpp 动态汇总 `import boost;`; 用户决策与风险表 |
| docs/2026-08-09-m2-gen-exports-design.md | M2 | libclang AST 生成器: bundle TU 枚举 → 依赖闭包 → first-wins 去重 → `.inc/.deps`; clang++ gate 自动裁剪 GFM; 27 库 4009 实体 |
| docs/2026-08-10-m3-header-only-modules.md | M3 | 19 纯头库模块定稿 + 宏 re-homing (boost::BOOST_VERSION) + 旁路头; 三处手编偏离 (scope gcc ICE / algorithm regex abi-tag); .inc 平台守卫 6 处 |
| docs/2026-08-11-m4-compiled-libs.md | M4 | 8 编译库接入 (filesystem/regex/thread/chrono/program_options/stacktrace/json/url); stacktrace LINK 固定 basic; filesystem v3 决策; reapply_hand_edits.py 重放工具 |
| docs/2026-08-12-m5-aggregate-consumer.md | M5 | `import boost;` 汇总 + examples; gcc 模块管线函数内 static 强符号多重定义根因分析与 B' 修复 (内部链接化 + 定义外移); url/thread/variant 移交 M6 |
| docs/2026-08-13-m6-ci-matrix-and-platform-fixes.md | M6 | CI 四腿建立; POSIX 平台守卫、pthread once 伞文件、arm64/x86 守卫、clone_impl 显式实例化 + extern template、mac typeinfo、libc++ println 等修复 |
| docs/2026-08-15-m8-mcpp-features-infra.md | M8 | features 基建 spike 全过; build.mcpp 动态汇总模块; gen_features.py; `sources=[]` 触发 src/** 推断的陷阱 (base 保留全部 glob) |
| docs/2026-08-16-macos-ci-build-mcpp-dyld-zda-analysis.md | (分析) | macOS 腿 build.mcpp host-link dyld `__ZdaPv` abort 根因: mcpp 上游 `hostflags.cppm` macOS 分支漏 `-fuse-ld=lld` + DYLD_* 污染; 修复方向 A/B/C 记录待决策 |
| docs/2026-08-17-m9-t1a-header-only-libs.md | M9 | 58 纯头库批量接入; dep_graph 传递遍历修复、using-injection linkage 校验、归属按定义处; hof/units/predef/static_assert 降级 include-only |
| docs/2026-08-30-m10-t3-macro-driven-libs.md | M10 | T3 19 宏驱动库边界确认 (gen_audit --macros 宏面统计核实, own-family 主导); include-only 用法文档化; 旁路头确认不逐库扩展 |
| docs/2026-08-30-m11-t2-compiled-libs.md | M11 | 18 编译库批量接入 (TU 表逐库定稿); exception 降级 include-only (gcc CMI pendings bug); CI POSIX 腿大批守卫修复 + 测试消费方式调整 |
| docs/2026-09-05-m12-t1b-heavy-template-libs.md | M12 | 12 重型模板库接入 (共 115 模块); clang 2^31 源位置上限 → CI A/B 分组门禁; compute/mysql/redis 移交 M13; vendored 修补 5 族 9 文件 |

## 2. 总体进度

- 已接入模块 **115 个** (T0 27 + T1a 58 + T2 18 + T1b 12); include-only **23 库**
  (T3 19 + 降级 4); M13 边界外 11 库 (T4 原 8 + M12 移交 3)。测试 138/138 (llvm/msvc)。
- 默认集 = 36 库闭包; 其余 opt-in (`mcpp build --features <lib>`);
  CI 全量门禁按 A/B 两组 (M12 §3), `features = ["all"]` 在 clang 上不可单次构建。
- CI 四腿 (windows-llvm-msvc / linux-gcc / linux-llvm / macos-llvm) 全绿;
  mcpp pinned 2026.8.29.1。

## 3. 仍然存在的问题 (按类别, 含出处与现状)

### 3.1 GCC 16.1 模块缺陷家族 (编译器 bug, 非本项目可根治)

| # | 问题 | 现状 | 出处 |
|---|---|---|---|
| 1 | 函数内 static 在 gcc 模块消费者 TU 以强符号落普通段 → 与库 TU 多重定义 | 已知案例已修 (M5 B' 内部链接化 + 外移; M11 §7.4 同族两处); **机制未根除, 新接入库仍可能再触** | M5 §3–4, M11 §7.4 |
| 2 | `clone_impl<T>` (虚拟基) 消费者 TU 发射无 thunk 的 vtable | 库内三特化已修 (extras 显式实例化 + extern template); **消费者自定义异常类型仍缺 thunk** — extern template 无法枚举用户类型 | M6 §3.3/§3.4, M6 §5 |
| 3 | variant `apply_visitor` 自由函数重载消费者侧 ICE (has_result_type.hpp) | 测试改用成员版本 `v.apply_visitor()` 绕过; 编译器 bug 未解, 其他触发形态仍可能复现 | M6 §3.3, M3 §8 |
| 4 | exception 模块 CMI lazily-loaded pendings 递归加载失败 ("recursive lazy load") | **库降级 include-only** (唯一相对计划的删减); 任何真实消费者 TU 均失败, 模块 TU 内显式实例化无效; 等 gcc 修复后可重新接入 | M11 §1, §6.1 |
| 5 | CMI/GMF 合并冲突 (`std::__byte_operand` 等, `<cstddef>` 双路进入) | 测试侧改纯 include 绕过 (T3 consumer rule); 机制仍在 | M11 §7.4 |
| 6 | `__synth3way_t operator<=>` mangle 冲突 (wave CMI 与依赖 CMI 各记一份) | 测试改纯 include; `-fabi-version=0` 对合成运算符无效 | M11 §7.4 |
| 7 | Boost.Test nfp 关键字匿名命名空间 TU-local 暴露 | vendored 修复 (命名命名空间 + inline 变量), 已解 — 列作匿名命名空间撞名族的工作范式 | M11 §6.5/§7.4 |

> 汇总观察: gcc 侧的消费方式已事实上分化为三条规则 —— 正常 import /
> import + 补标准头 (<new>/<typeinfo>) / 纯 include (T3 consumer rule)。
> 每接入新库都需按此重新核实 gcc 消费面, 无通用预防手段。

### 3.2 工具链硬上限

| # | 问题 | 现状 | 出处 |
|---|---|---|---|
| 1 | clang 源位置 2^31 上限: `--features all` (117 CMI 聚合 ~2.98GB) 报 "ran out of source locations", 无 flag 可调 | CI 门禁改 A/B 两组; **全量消费者须逐库 import**; gcc 侧同限未测 | M12 §3, §7.4 |
| 2 | libclang 不暴露变量模板 cursor → 变量模板一律缺失 (pfr::tuple_size_v、hana `int_c`/`_c` 等) | 类模板替代拼写 + curated 兜底 (仅必要时); 生成器层面无解 | M9 §6, M12 §7.1 |
| 3 | libclang 不遍历 requires 子句/约束表达式 → 实体闭包可能缺失 | 编译期 smoke 兜底 | M2 §9 |
| 4 | 显式特化跨库不可达 (`template<> ...` 无法 using 导出) | 审计旗标 + curated; 未系统消除 | M2 §9, M2 §11.3 |
| 5 | boost 命名空间别名到 std 的实体 (type_info 等) 闭包 canonical 消解不可达 | curated 兜底 | M3 §4.7 |

### 3.3 标准/模块语义硬限制 (不可导出面)

| # | 问题 | 消费者替代拼写 | 出处 |
|---|---|---|---|
| 1 | 内部链接 constexpr 对象不可导出: hof/units 整库降级 include-only | include 上游头 | M9 §1, §6 |
| 2 | 同型: accumulators `extract::count/mean/...`、mqtt5 `prop::*` 命名常量、hana 字面量变量模板 | `extract_result<>` 函数模板 / `integral_constant` / 类模板 | M12 §7.1 |
| 3 | 匿名命名空间 forwarder 不导出: range pipe 语法 (`vec | reversed` 不可用)、multi_array `boost::extents` | 函数形式 reverse/filter/transform; 容器式构造 | M3 §8, M9 §6 |
| 4 | `numeric::interval<double>` 模块面不可实例化 (默认 policies 依赖 CMI 无法携带的显式特化) | include `<boost/numeric/interval/interval.hpp>` | M12 §7.2 |
| 5 | 宏永远不跨模块边界: T3 19 库 + test 的 BOOST_TEST_* + 包级版本宏 | include 上游头 / macros.hpp 旁路头 (仅 BOOST_VERSION) | M10 §4, M11 §6.7 |
| 6 | 同一 TU 内宏面与 re-homed 拼写互斥 (`boost::BOOST_VERSION` vs 宏展开) | 二选一 | M3 §6 |

### 3.4 构建期固定 / 库内功能裁剪 (设计决策, 消费者不可调整)

| # | 问题 | 出处 |
|---|---|---|
| 1 | 消费者无法自定义任何 BOOST_* 特性宏 (模块/库 TU 宏随构建期固定) — 总边界 | 主计划 边界, M4 §9, M11 §6.8 |
| 2 | filesystem 模块面固定 v3 API (上游 CMake 默认 v4) | M4 §5 |
| 3 | thread 模块面固定 v2 API (`boost::unique_future`, 无 `boost::future`) | M4 §9 |
| 4 | stacktrace 实现固定 basic (无 windbg/addr2line 符号名面) | M4 §3 |
| 5 | algorithm 模块无 regex 面 (gcc 模块 TU abi-tag 冲突, string_regex→string 裁剪) | M3 §3.3, M4 §9 |
| 6 | iostreams 外部后端 (zlib/gzip/bzip2/lzma/zstd) 与 cobalt ssl 不入包 (OpenSSL) | M11 §6.2 |
| 7 | math tr1 组件、container dlmalloc/alloc_lib、process 聚合头 boost/process.hpp 不入包 | M11 §6.3 |
| 8 | log event_log 靠手写 mc.exe 桩; dump_avx2/ssse3 不入包 | M11 §6.4 |
| 9 | atomic sse41 走"探测失败"回退路径 (未走上游 per-TU -msse4.1) | M11 §2 |
| 10 | type_erasure `any<>` 动态分发路径在 clang-msvc 模块消费者侧不能实例化 (vtable_storage 与模块 ODR 不兼容) — 模块面/概念模板可用 | M11 §6.6 |

### 3.5 平台与 CI 覆盖缺口

| # | 问题 | 现状 | 出处 |
|---|---|---|---|
| 1 | **mingw 无 CI 腿**, 两个本地基线失败长期挂账: (a) thread `sleep_for` win32 实现运行挂起; (b) url `BOOST_URL_RETURN_EC` 宏函数内 static 冲突 (需宏重构, 超出 B') | 未解; CI 不阻塞 | M6 §5, M5 §5 |
| 2 | macOS Mach-O typeinfo 跨模块边界分裂 → 精确异常 catch 落空 | 测试以 `std::exception` 兜底; 根治 (Mach-O typeinfo 合并) 超出范围 | M6 §5 |
| 3 | gcc 消费者自定义异常 clone_impl thunk (§3.1#2) 在 CI 覆盖路径之外 | 记录在案, 未解 | M6 §5 |
| 4 | linux-gnu (glibc) 腿未本地验证 (以 musl 交叉代表 POSIX 面); macOS arm64 的 epoll→select_reactor 守卫为条件推定 | 依赖 CI 原生腿 | M11 §7.3 |
| 5 | 真 MSVC (cl) 从未验证 — CI windows 腿是 clang-msvc 风味 | M0 起一直如此, 双编译器 CI 兜底 | M0 风险, M2 §2 |
| 6 | mcpp macOS build.mcpp host-link dyld `__ZdaPv` 缺陷 (上游 hostflags.cppm macOS 分支漏 lld) | **已解 (2026-09-05 用户确认): mcpp 上游已修复, 修复版本号未记录, 但大于 CI 当前 pinned 的 2026.8.29.1** —— 即 pinned 版本只要 ≥ 修复版即不受影响; 2026-08-16 分析文档保留作根因存档 | 2026-08-16 分析文档 §7 |

### 3.6 范围边界 (按决策排除, 非缺陷)

| # | 内容 | 出处 |
|---|---|---|
| 1 | **M13 暂跳过 (用户决策 2026-09-05)**: T4 11 库不接入 —— context/fiber/coroutine (asm)、locale (ICU)、mpi、python、graph_parallel、parameter_python + M12 移交的 compute (OpenCL) / mysql / redis (OpenSSL) | M12 §1, all-libs-plan §4 |
| 2 | T3 19 宏驱动库 + 4 降级库保持 include-only (宏是预处理器 API, 原理上不可模块化) | M10 §1 |
| 3 | conversion (无头 stub)、coroutine2 (依赖 context)、property_map_parallel (无汇总根头) 等非库/依赖边界外 | M9 §1 |

### 3.7 工程流程风险 (本项目可改进项)

| # | 问题 | 现状 | 建议 | 出处 |
|---|---|---|---|---|
| 1 | **vendored 头修补无自动回放**: M5 B' (regex 2 文件 + system extras)、M11 §6.9 (6 处)、M11 §7.4 (+2 处)、M12 §6 (5 族 9 文件) 直接改 `deps/boost/boost/**`; 重跑 `import_boost.py` 会全部还原上游原貌, 而 `reapply_hand_edits.py` **只覆盖 .inc/.cppm, 不回放 vendored 修补** (已核实脚本无此逻辑) | 仅 git 历史保护 | 把 vendored 修补纳入 reapply (或 import_boost 后置钩子), 并在 README 重生成流程中显式标注 | M5 §6, M11 §6.9, M12 §6 |
| 2 | .inc 平台守卫 / .cppm 手编在重生成后丢失 | reapply_hand_edits.py 已可一键重放 (幂等), 但每轮接入都新增锚点, required 锚点漂移需人工维护 (M12 已出现 required→best-effort 降级) | 保持现状 + 每次重生成后 `gen_features.py --check` | M3 §8, M4 §10, M12 §4 |
| 3 | mcpp 工具链不发 GNU depfile: 编辑 .inc 等 purview 内 include 文件后不重建 | 必须 `mcpp clean --bmi-cache` (纪律性约束, 忘记则静默用陈旧 BMI) | 上游修 depfile 前无解, 持续遵守 | M6 §3.1/§5 |
| 4 | `[build].sources` 不可清空 (mcpp `src/**` 推断使 test 模式分组失效) | base 保留全部 per-lib glob, feature 声明 gating | 遵守现状约定 (mcpp.toml 注释已标) | M8 §1.1/§6 |
| 5 | libclang 资源目录依赖: pip wheel 的 libclang 无资源目录 → 声明静默丢失 (mp11 事件先例) | README 已有 LIBCLANG_PATH 指引; uv 路径已配 PEP 723 | 保持 | M3 §4.1 |
| 6 | M14 未开始: mcpp-index boost.lua、docs/architecture.md、发布流程均缺 (用户指定等全量接入后) | M13 跳过后 M14 前置状态需用户重新确认 | — | 主计划 M7/M14 |

### 3.8 消费者侧已记录的写法陷阱 (测试期沉淀, 文档化即可)

- MSVC `assert` 宏 `(!!(x)) || ...` 不短路: 用户定义 `operator||`/`operator!`
  (tribool、hana bool 表达式) 会被无条件求值 → 先 `bool(...)` 显式转换 (M9 §4, M12 §7.3)。
- `import std;` 与拉入 `<type_traits>` 等的 include 同 TU → std 变量模板重定义
  (MSVC 风味); 宏测试改纯头包含 (M9 §4)。
- `lexical_cast<bool>` 在 clang+MSVC STL 下连纯 include 也崩溃 — 上游问题, 测试不覆盖 (M9 §4)。
- dll `program_location` MSVC 风味崩溃 → 测试只验默认构造 (M9 §4)。
- 模块不能导出 `std::tuple_size` 特化 (GMF 声明消费者不可见) (M9 §4)。
- 消费者必须自带 std 表面 (`import std;` 或 include) — boost 实体签名引用 std
  类型的运算符在纯 import TU 不可见 (M0 §3, 设计使然)。
- POSIX timer 粒度 `_SC_CLK_TCK` (10ms) — 忙等不足一个 tick 得 wall==0, 测试需 sleep (M11 §7.4)。

## 4. 复核建议 (销账优先级)

1. **高**: §3.7#1 vendored 修补回放脚本化 —— 这是唯一会因一条常规命令
   (`import_boost.py`) 静默丢失正确性修复的项。
2. ~~§3.5#6 补记 macOS build.mcpp 缺陷的解除方式~~ — 已补记 (2026-09-05): 上游
   mcpp 已修复, 修复版本 > CI pinned 2026.8.29.1。后续仅当考虑把 pinned 版本
   **降级**时需先确认修复版号; 维持现状无动作。
3. **中**: §3.1#4 exception 重新接入 —— 每逢 gcc 版本升级 (CI linux-gcc 腿) 时
   用 tests/exception.cpp 试探 pendings bug 是否已修。
4. **中**: §3.2#1 gcc 侧 `--features all` 聚合实测 (M12 记录"未测"), 若 gcc 无
   源位置上限则可让 linux 腿保留全量门禁。
5. **低**: §3.5#1 mingw 腿与两个本地基线失败 (thread 挂起 / url 宏冲突) —— 若
   决定支持 mingw 消费者则需单列里程碑; 否则维持"CI 无 mingw 腿"现状并保持记录。
