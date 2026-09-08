# boost-module 总体设计汇总 (2026-09-08 重写版)

> 日期: 2026-09-08 · 状态: 汇总快照 · 分支 `b1.91.0wdev`
> 目标上游: **Boost 1.91.0** (`BOOST_VERSION 109100`)
> 本文档**替代** `.agents/` 下全部旧设计/计划/分析文档 (清单见 §11)。
> **旧文档最后存在提交: `03f616196468f71ae6bf7f22010777450356d3ec`**
> (refactor(scripts): reapply_hand_edits — string patches as git .patch files)。
> 矛盾与不明确之处集中列于 §10, 在后续对话中逐项修正。

## 1. 项目定位与目标

使用 [mcpp](https://github.com/mcpp-community/mcpp) 构建工具对 Boost 库做
C++23 named modules 封装, 思路参考 opencv-m: 把 Boost 头文件 API 以模块接口
(`.cppm` + `export namespace boost { using ...; }`) 形式导出, 消费者
`import boost.filesystem;`(或汇总 `import boost;`), API 拼写与上游一致,
无需 `#include`。单仓库 = mcpp 包仓库: vendored 源码 + 模块层 + 完整构建
(`[package] name="boost"` + `[build]` + `[targets.boost] kind="lib"`)。

- 编译器: clang 22 / gcc 16.1.0 (MinGW-w64 本地; CI 双编译器四腿)。
- mcpp pinned `2026.8.29.1` (CI)。
- 许可: 封装层 BSL; Boost 上游 BSL; libclang Apache-2.0-LLVM。

## 2. 总体架构与当前状态

### 2.1 仓库布局

```
boost-module/
├── mcpp.toml                 # [package] + [build] + [features] (gen 区勿手改) + [target.*]
├── build.mcpp                # 动态生成汇总模块 generated/boost.cppm (gitignored)
├── src/*.cppm                # 每模块一个接口 (115 个)
├── src/gen_exports/*.inc     # 生成器产物: export using 列表 (committed)
├── src/gen_exports/*.deps    # export import 提示 (committed)
├── src/boost_system_extras.cpp / boost_thread_extras.cpp   # B' 外移定义库 TU
├── include/boost-module/macros.hpp   # 旁路头: 仅包级版本宏 (BOOST_VERSION)
├── deps/boost/               # vendored 1.91.0 (import_boost.py 导入; boost/boost/ 为唯一 include 根)
├── scripts/                  # import_boost / gen_exports / gen_audit / gen_features /
│                             # reapply_hand_edits + patchs/*.patch (52 个) + curated/*.txt + libs.json
├── tests/  examples/         # 每库 smoke (141 个默认集) + import boost; 消费者示例
└── .github/workflows/tests.yml   # CI 四腿
```

关键布局事实 (M1 教训): 官方 tarball 把所有库头统一收在顶层 `boost/boost/`
汇总 include 根, `libs/<lib>/` 下**没有** `include/`; `deps/boost` 是唯一
include 根, 库↔头映射经 `libs/<lib>/meta/libraries.json` 或同名目录推断
(`scripts/libs.json` 固化)。

### 2.2 库分类与计数收口 (155 库, C4 后)

| 分类 | 数量 | 内容 |
|---|---|---|
| 模块 (feature 有模块) | **115** | T0 26 (M0–M6, C1 除 scope_exit) + T1a 61 (M9 58 + C2 hof/units + C4 三库) + T2 16 (M11 18 − C1 log/test) + T1b 12 (M12) |
| 纯 include-only | **22** | T3 宏驱动 16 (preprocessor/mpl/fusion/proto/spirit/xpressive/typeof/vmd/phoenix/parameter/metaparse/function_types/tti/local_function/msm/foreach) + predef/static_assert (M9) + exception (M11) + describe/openmethod/scope_exit (C1) |
| 编译库 include-only (有 feature 无模块) | **2** | log / unit_test_framework (C1; test 双形态消费) |
| 封装总数 | **139** | 115 模块 + 24 include-only |
| M13 暂缓 (用户决策) | 11 | context/fiber/coroutine (asm)、locale (ICU)、mpi、python、parameter_python、graph_parallel、compute (OpenCL)、mysql/redis (OpenSSL) |
| 非库/边界外 | 若干 | conversion (无头 stub)、coroutine2 (依赖 context)、property_map_parallel (无汇总根头)、detail/headers 目录 |

- feature **117** = 115 模块 feature + log / unit_test_framework 两个无模块 feature
  (`gen_features.py` 生成, 勿手改)。
- **默认集 = 36 库闭包** (`[features].default`, 随模块 import 边自动增长);
  其余 opt-in (`mcpp build --features <库,...>`); 全量 `--features all`。
- 测试: 默认集 **141/141** (llvm/msvc 本地) + opt-in 定点全绿; CI 全量门禁
  按 **A/B 两组** (A = default + T1a + T2 共 103 模块 + log/unit_test_framework;
  B = T1b 12), 因 clang 聚合源位置上限不可单次 `--features all` (§7.2#1)。
- CI 四腿全绿: windows-llvm-msvc / linux-gcc / linux-llvm / macos-llvm。

### 2.3 mcpp features 机制 (实测结论)

1. `[features.X]` 可带 `sources` (feature-gated 源, 同时作用 build/test 模式)、
   `implies` (传递闭包)、`defines` (**传播消费者**)、`flags` (per-glob 私有)。
2. 激活集 = `default` ∪ 显式请求; 消费者 `features=[...]` / `default-features=false`。
3. feature-gated: 任一 feature `sources` 里的 glob 默认 DROP, 激活时 ADD;
   target 条件表在 feature pass 之前合并, 同受 DROP 管。
4. `MCPP_FEATURE_<NAME>` 宏仅本包编译期可见 (test TU 亦可达, C1 门控实证)。
5. 条件 import 不可行 (扫描器拒绝条件块内 import; P1689 校验精确比对)。
6. feature 变化改变 cflags → BMI/构建缓存自动失效。
7. build.mcpp (Cargo build.rs 模型) 在 feature 激活后、modgraph 扫描前运行,
   `mcpp::has_feature()` 编程注入源。
8. **陷阱**: `[build].sources = []` 触发 mcpp `src/**` 推断 → test 模式
   DROP 跳过失效; 实测采用 base 保留全部 per-lib glob, feature `sources`
   用**同一字符串**声明 gating (build 模式 DROP 剔除, test 模式全量编译)。
9. per-OS TU 互斥 (thread 模式推广): feature 列全平台 glob,
   `[target.windows/unix.build].sources` 用 `!` 排除异平台。

mcpp.toml 关键项: `[build].defines = [BOOST_ALL_NO_LIB, _MT,
WIN32_LEAN_AND_MEAN, SECURITY_WIN32]` (POSIX 无害); `_WIN32_WINNT=0x0A00`
仅在 target.windows (POSIX 上触发 asio Windows-App 探测硬错);
`include_dirs += deps/boost/libs/log/src、deps/boost/libs/atomic/src`
(私有头引号 include / BOOST_PP_ITERATE 裸文件名);
target.windows.ldflags += ws2_32/ntdll/shell32/advapi32/secur32/user32/synchronization。

### 2.4 动态汇总模块 (build.mcpp)

- 读 `scripts/features.lst` (gen_features.py 产物), 对每个模块库
  `if (mcpp::has_feature(lib))` 收集 `export import boost.<lib>;`, mtime 稳定写
  `generated/boost.cppm` 并 `mcpp::source()` 注入; 无模块 feature
  (log/unit_test_framework) 跳过。
- `import boost;` 恰好 re-export 当前激活库; 零激活为合法空壳。
- 生成位置为项目根 `generated/` (`[lib].path` 显式声明, 消除 validate 警告;
  MCPP_MANIFEST_DIR 绝对路径, root/path-dep 两身份通用)。

## 3. 生成器管线 (scripts/)

### 3.1 import_boost.py (M1)

下载固定 SHA-256 的官方 `boost_1_91_0.tar.gz`, 裁剪 (doc/example/Jamfile/html
等不导入) 后导入 `deps/boost/`。每次重导会**抹掉全部 vendored 修补**,
必须重跑 `reapply_hand_edits.py` 回放。

### 3.2 gen_exports.py (M2, M3/M4/M9/M11 历轮增强)

libclang AST 生成器, 核心规则:

- **输入**: `libs.json` 固化头集 (启发式 scan + 人工 curation; config 只留
  boost/config.hpp、multi_index 补聚合根、serialization 补 boost/archive/** 等);
  `scripts/curated/<lib>.txt` 兜底生成器看不见的实体 (宏生成、std 别名、
  friend 运算符再导出等), 并做注入 linkage 校验。
- **AST 枚举**: 每库一个 bundle TU (GMF = root 头 include-DAG 源点聚合, detail
  头不自足不直接 include); 收集语义父链全 `boost::*`、外部链接、声明位置在库头集
  的类/函数/变量/枚举/typedef/concept; friend-in-class 运算符跳过 (ADL 可达),
  自由运算符以 `using boost::operator==;` 显式导出; 类内枚举 enumerator 不导出
  (随类); 显式特化 (token 流检测 `template<>`) 不可导出; 变量模板 libclang
  不暴露 (类模板替代 + curated 兜底)。
- **依赖闭包**: 签名引用 BFS (只走声明), file→lib 归属; 非目标库文件入
  "shared" 桶由首个需求库认领 → **first-wins** 跨模块去重 (拓扑序处理,
  环按清单顺序打破); 被认领实体记 `<lib>.deps` → `export import boost.<home>;`。
- **clang++ gate**: libclang 缺失头报告不可靠, bundle 需 clang++ 驱动子进程
  权威校验, 失败迭代裁剪 GFM (thread 平台头、regex ICU 头由此自动剪除);
  词法上下文检查排除函数体幻影。
- **EXTRA_DEFINES / GMF_OVERRIDE**: stacktrace 用 BOOST_STACKTRACE_LINK 生成;
  json GMF 覆盖为 json.hpp (去 src.hpp)。
- M9 增强: dep_graph 沿非目标库头传递遍历 (单头聚合识别, 否则 tokenizer 等
  实体被抢); using-declaration 目标形态五类 (相对/全限/全局::/全局非 boost/
  std 别名 — 后两类直接导出目标本身); 归属按定义处而非首声明。

### 3.3 gen_audit.py

static-inline / 内部链接实体审计 (目标库实测: M2 27 库仅 6 处, M3 19 库 0);
`--macros` 宏面统计 (own-family 分桶, T3 判定输入)。**C4 纠正**: own-family
宏占比只证明"宏面大"不证明"API 是宏" (bind 9 / lambda2 9 / lambda 17 全是
实现细节宏), 今后 `--macros` 结论须与实体面审计交叉验证。

### 3.4 gen_features.py

由 `libs.json` + `*.deps` 生成 mcpp.toml `[features]` 块 (marker splice, 幂等)
+ `scripts/features.lst`; `--check` 校验一致性。特例表:
`FEATURE_NAME_OVERRIDE = {"test": "unit_test_framework"}`、
`FEATURE_ONLY_SOURCES = ["unit_test_framework"]` (框架 TU 不进 base sources,
保证与 included 纯头形态不可同链接)、无模块 feature 支持、log/utf 的
implies 手工钉定 (原 .deps 边, 保证 `--features log` 拉齐链接依赖)、
`EXTRA_IMPLIES = {"parser": ["charconv"]}`。

### 3.5 reapply_hand_edits.py (M4 引入, 2026-09-08 补丁文件化)

重生成后一键重放全部手编, 幂等; main() 首步 `reapply_vendored_patches()`
回放 `deps/boost/` 全部 vendored 修补 (M5 B' / M9 / M11 / M12 / C2 / C4/C4.1,
约 27 个修补文件 + 1 个新增文件 = log 的 mc.exe 桩 simple_event_log.h),
从 pristine 上游文本锚定。2026-09-08 重构: 字符串补丁迁出 Python 内嵌
(原 226 处 `patch()` 调用), 以统一 diff 存 `scripts/patchs/<module>.patch`
(52 个文件覆盖 75 个目标文件), `git apply` 应用 + `git apply --check
--reverse` 反向检测实现幂等; 仅 `type_erasure.inc` 的 C4 归属锚点保留
`patch()` 兜底 (锚点依赖重生成后 first-wins 结果, 无法静态化)。
`guard_entity_lines` / `ensure_file` / `restore_from_git` ("M3 final form")
保持脚本内逻辑。

### 3.6 使用纪律

- `uv run scripts/gen_exports.py --scan|...` (PEP 723 内联元数据, 自动建
  libclang 环境); pip libclang wheel 无资源目录 → 声明静默丢失
  (mp11 事件先例), 需 LIBCLANG_PATH 指向完整 LLVM。
- 重生成循环: `gen_exports.py --emit-cppm` → `reapply_hand_edits.py` →
  `gen_features.py` (+`--check`)。
- mcpp 工具链不发 GNU depfile: 编辑 .inc 等 purview 内 include 后必须
  `mcpp clean --bmi-cache` (纪律约束, 忘记则静默用陈旧 BMI)。

## 4. 消费形态与消费者用法

### 4.1 三种形态

1. **模块 import** (115 库): `import boost.<lib>;` / `import boost;`
   (恰好 re-export 激活库)。API 拼写与上游一致; 自由运算符已显式导出;
   friend 运算符经 ADL。
2. **纯 include-only** (22 库): 无 feature 无模块, 直接 `#include` 上游头;
   可与模块 import 同 TU 混用 (标准允许)。宏 API (BOOST_PP_/BOOST_FOREACH/
   BOOST_DESCRIBE_*/BOOST_OPENMETHOD*/BOOST_SCOPE_EXIT_*/BOOST_TEST_* 等)
   永远只能来自 include —— 宏是预处理器层面 API, 不跨模块边界 (M10 边界)。
3. **编译库 include-only** (2 库, C1 新形态): feature 保留库 TU 编译链接,
   无模块接口。
   - **log**: `--features log` + `#include <boost/log/...>` + 链接库 TU。
   - **test** (`unit_test_framework`): 双形态互斥 (框架 TU 与 included 聚合
     实现符号冲突, 不可同链接) —— feature 开 = 编译框架 (`<boost/test/
     unit_test.hpp>` + `BOOST_TEST_NO_MAIN` + `impl/unit_test_main.ipp` +
     自持 main); feature 关 = 纯头聚合 `<boost/test/included/unit_test.hpp>`
     (自带 main)。

### 4.2 消费者示例

```toml
[dependencies]
boost.boost = { path = ".." }                                              # 默认 36 库闭包
boost.boost = { path = "..", default-features = false, features = ["optional", "json"] }  # 自选
boost.boost = { path = "..", features = ["all"] }                          # 全量 (clang 下超单 TU 上限, 应逐库 import)
```

### 4.3 宏 re-homing 与旁路头

- core.cppm 导出 `boost::BOOST_VERSION` / `boost::BOOST_LIB_VERSION` constexpr
  (拼写保持); `include/boost-module/macros.hpp` 仅承载包级版本宏。
- **同一 TU 内宏定义与 re-homed 拼写互斥** (宏吞拼写), 二选一。
- 旁路头**不逐库扩展** (与各模块 GMF include 集不相交约束, M0 §5); T3 宏
  API 一律 include 上游头。

## 5. 里程碑史与关键决策 (速览)

| 里程碑 | 内容 | 结果要点 |
|---|---|---|
| M0 spike | 4 探针双编译器验证 `export namespace boost { using ...; }` | 模式成立; 导出规则确立; gcc 坑 A (GMF 全局辅助实体需 `export using ::operator new;`) / 坑 B (消费者 include 与 GMF 同头冲突 → `import std;`); 消费者必须自带 std 表面 (设计使然); 链接模式成立 |
| M1 vendoring | 官方 tarball 导入, `boost/boost/` 汇总根 | deps/boost 布局定型 (§2.1) |
| M2 生成器 | gen_exports/gen_audit + 27 库 4009 实体 | GMF root-only、friend 子树、clang++ gate、枚举器/特化检测; `--fmodules` clang 禁用 (`--precompile` + `-fmodule-output`); 无 `module :private` (gcc 未实现) |
| M3 纯头 19 库 | 模块定稿 + 宏 re-homing + 旁路头 | 生成器三修 (资源目录/using-injection/CLASS_TEMPLATE/typedef); scope 去 core 边 (gcc ICE)、algorithm 去 regex 面 (gcc abi-tag); .inc 平台守卫 6 处首建 |
| M4 编译 8 库 | TU 进 sources, 宏一致 | defines 补 `_MT`/`_WIN32_WINNT`; stacktrace LINK+basic; filesystem v3; json GMF 去 src.hpp; reapply_hand_edits 诞生 |
| M5 汇总+示例 | `import boost;` + examples | **gcc B' 修复**: gcc 16 模块管线把 inline 函数内 static 以强符号落普通段 → 内部链接化 + 定义外移 (boost_system_extras.cpp); M4 "gcc 28/28" 记录勘误 (实 5 败) |
| M6 CI 四腿 | 三平台适配 | POSIX 守卫、pthread once 伞文件、arm64/x86 守卫、clone_impl 显式实例化 + extern template、mac typeinfo 兜底、libc++ printf; depfile 纪律确立 |
| M8 features 基建 | build.mcpp 动态汇总 + gen_features + 全库化 | spike 三连验证; base-glob 陷阱 (§2.3#8); 默认 18 库闭包 |
| M9 T1a 58 库 | 纯头批量接入 | dep_graph 传递遍历、注入 linkage 校验; hof/units/predef/static_assert 当时降级 (hof/units 后由 C2 翻案); 测试陷阱沉淀 (MSVC assert 不短路等) |
| M10 T3 边界 | 宏面统计核实 19 库 include-only | 宏是预处理器 API 永不跨边界; 旁路头不扩展; (C4 后 T3=16, 三库翻案) |
| M11 T2 18 库 | 编译库批量 + exception 降级 | 逐库 TU 表定稿 (atomic sse41 排除、date_time 仅 greg_month、test 18 TU 排 main、wave 两层子目录…); gfm 死循环修复; POSIX 腿大批守卫 + gcc Test 六连败修复 (§6.3) |
| M12 T1b 12 库 | 重型模板库 | clang 2^31 源位置上限 → A/B 分组; asio/multiprecision first-wins 自立; 默认闭包 36; vendored 修补 5 族 (匿名命名空间→inline constexpr) |
| C1 | 五库降级 + utf 改名 | describe/openmethod/scope_exit (宏主体 + gcc ODR)、log (gcc 消费面)、test (宏主体, 双形态) → 编译库 include-only 新形态; 默认闭包 36 (functional 移出) |
| C2 | hof/units 重新模块化 | vendored 宏改造 (`BOOST_HOF_STATIC_*`/`BOOST_UNITS_STATIC_CONSTANT` → `inline constexpr`) 使对象获外链; units 1355 / hof 353 实体; gcc 无需混用守卫 |
| C3 | 文档/计数同步 | rollup/README/M9/M10/M11 补记 |
| C4 (+C4.1) | bind/lambda/lambda2 重新模块化 | T3 宏面误判纠正; lambda 占位符 TU-local → inline constexpr (vendored 3 处); bimap 的 boost.iterator 边丢失 → 定点钉定 (全局修法两案否决); C4.1: gcc 16 重复符号 (constant_null_type CMI 重复发射) → inline constexpr |
| M13 | 外部依赖/asm 11 库 | **用户决策暂缓 (2026-09-05), 持续暂缓 (2026-09-08)** |
| M14 | 发布 | **下一步: 发布预览版 (2026-09-08 决策, 见 plan/2026-09-08-release-preview-plan.md)** |

用户历史决策 (2026-08-13): 动态汇总模块 / 精简核心默认集 / 宏驱动库
include-only / 外部依赖库单列里程碑 / 每库最小 smoke。

## 6. 编译器与平台问题及修复模式

### 6.1 GCC 16.1.0 模块缺陷家族 (非本项目可根治)

| # | 问题 | 现状 |
|---|---|---|
| 1 | 函数内 static 在消费者 TU 强符号落普通段 → 多重定义 | 已知案例已修 (B': 内部链接化 + 外移); 机制未根除, 新库仍可能再触 |
| 2 | `clone_impl<T>` (虚基) 消费者 TU 发射无 thunk vtable | 库内三特化已修 (显式实例化 + extern template); 消费者自定义异常类型仍缺 thunk (extern template 无法枚举用户类型) |
| 3 | variant `apply_visitor` 自由函数重载消费者 ICE | 测试用成员版本绕过; 编译器 bug 未解 |
| 4 | exception CMI pendings "recursive lazy load" | 库降级 include-only; gcc 修复后可重接入 (CI gcc 升级时试探) |
| 5 | CMI/GMF 合并冲突 (`std::__byte_operand` 等) | 机制仍在, 受害库按需纯 include; log 降级后该面统一 |
| 6 | `__synth3way_t operator<=>` mangle 冲突 (wave) | 测试纯 include; `-fabi-version=0` 对合成运算符无效 |
| 7 | Boost.Test nfp 匿名命名空间 TU-local 暴露 | vendored 修复 (命名命名空间 + inline 变量), 已解 |

**gcc 消费方式三分规则**: 正常 import / import + 补标准头 (`<new>`/`<typeinfo>`,
cobalt 先例) / 纯 include (T3 consumer rule)。每接入新库需重新核实 gcc 消费面。

### 6.2 修复模式 (vendored 修补族)

同一根因族反复出现, 形成标准修法 (reapply 幂等回放):

- **TU-local/匿名命名空间实体** (CMI + GMF 两路同 mangle 撞名, 或 gcc
  "exposes TU-local") → 命名命名空间 + `inline constexpr` 变量
  (M11 serialization/io/test ×4、M12 ublas/asio×4/beast/mqtt5/parameter、
  C2 hof/units 宏定义、C4 lambda、C4.1 constant_null_type)。
- **闭包类型恒 TU-local** → 命名 struct 空函数对象 (mqtt5 async_traits)。
- **函数内 static 强符号** (B' 族) → 命名空间级 static 内部链接化 + 定义外移。
- 平台实体 (win32/pthread/INT128/SSE 等) → .inc `#if` 守卫, 条件镜像上游头
  (M3 6 处 → M9 26 处 → M11/M12 大批; 坑: 裸架构条件在 x86_64-windows-msvc
  误导出, 须 `__GNUC__ && (__i386__||__x86_64__)` 完整条件)。

### 6.3 平台专项 (M6/M11)

- pthread `once.cpp` 是伞文件 (include once_atomic.cpp), glob 会双编 →
  target.unix sources 明确列表。
- macOS Mach-O typeinfo 跨模块边界不合并 → 精确 catch 落空, 测试以
  `std::exception` 兜底; 根治超范围。
- libc++ 22.1.8 `std::println` 格式串问题 → examples 改 `std::printf`。
- POSIX timer 粒度 `_SC_CLK_TCK` (10ms) → 测试忙等前需 sleep。
- clone_impl: 消费者 TU 隐式实例化发射无 thunk 的弱 vtable, ELF COMDAT group
  先到先留 → `extern template class clone_impl<...>;` 放模块接口抑制实例化。

### 6.4 mcpp 工具链已知问题

- 不发 GNU depfile → `mcpp clean --bmi-cache` 纪律 (§3.6)。
- `sources=[]` 触发 src/** 推断陷阱 (§2.3#8)。
- macOS build.mcpp host-link dyld `__ZdaPv` abort (上游 hostflags.cppm macOS
  分支漏 `-fuse-ld=lld`): **上游已修复** (2026-09-05 用户确认; 2026-09-08
  进一步确认 pinned 2026.8.29.1 不受影响, 不降级即不会再遇到, 修复版本号
  无需追查, 见 §10#1); 2026-08-16 根因分析存档于旧文档 (已随旧档删除, 结论
  保留于此)。

## 7. 边界与已知限制

### 7.1 设计决策固定 (消费者不可调整)

特性宏一律构建期固定 (消费者无法自定义任何 BOOST_* 特性宏 — 总边界);
filesystem v3 API; thread v2 API (`unique_future`); stacktrace basic;
algorithm 无 regex 面 (gcc abi-tag); iostreams 外部后端 (zlib/gzip/bzip2/
lzma/zstd) 与 cobalt ssl 不入包 (OpenSSL); math tr1、container
dlmalloc/alloc_lib、process 聚合头不入包; log event_log 手写 mc.exe 桩、
dump_avx2/ssse3 不入包; atomic sse41 走探测失败回退; type_erasure `any<>`
动态分发路径 clang-msvc 模块消费者不可实例化 (模块面/概念模板可用)。

### 7.2 工具链/标准硬限制

1. **clang 源位置 2^31 上限**: `--features all` (117 CMI ~2.98GB) 报
   "ran out of source locations", 无 flag 可调 → CI A/B 分组; 全量消费者
   应逐库 import; gcc 侧同限未测。
2. libclang 不暴露变量模板 → pfr::tuple_size_v、hana int_c 等缺失 (类模板
   替代拼写); requires 子句不遍历 → 编译期 smoke 兜底。
3. 显式特化跨库不可导出; boost 命名空间别名到 std 的实体 canonical 不可达
   (curated 兜底)。
4. 内部链接 constexpr 对象不可导出 — 残余面: accumulators `extract::*`
   (用 `extract_result<>` 函数模板)、mqtt5 `prop::*` 常量 (用
   `integral_constant`)、hana 字面量变量模板; hof/units 已由 C2 改造解决。
5. 匿名命名空间 forwarder 不导出: range pipe 语法 (`vec | reversed`)、
   multi_array `boost::extents` — 用函数形式/容器式构造。
6. `numeric::interval<double>` 模块面不可实例化 (默认 policies 显式特化
   CMI 无法携带) → include 头文件。
7. 宏永不跨模块边界 (§4.1); 同 TU 宏面与 re-homed 拼写互斥 (§4.3)。
8. 消费者必须自带 std 表面 (`import std;` 或 include) — boost 实体签名引用
   std 类型的运算符在纯 import TU 不可见 (M0 §3, 设计使然)。

### 7.3 平台与 CI 覆盖缺口

- **mingw 无 CI 腿**, 两个本地基线失败长期挂账: (a) thread `sleep_for` win32
  实现运行挂起; (b) url `BOOST_URL_RETURN_EC` 宏函数内 static 冲突 (需宏重构)。
- macOS 精确异常 catch (§6.3); gcc 消费者自定义异常 clone_impl thunk 在 CI
  覆盖路径之外。
- linux-gnu (glibc) 腿未本地验证 (musl 交叉代表 POSIX 面); macOS arm64 的
  epoll→select_reactor 守卫为条件推定。
- 真 MSVC (cl) 从未验证 (CI windows 腿是 clang-msvc 风味)。

### 7.4 工程流程风险

- 新增 vendored 修补需手工向 `reapply_vendored_patches()` 登记 (锚点漂移需
  人工维护, M12 出现 required→best-effort 降级先例; patch 文件化后 hunk 上下文
  对 gen_exports 输出格式敏感, 格式变化需同步再生成 .patch)。
- bimap 的 `boost.iterator` re-export 边为手工钉定 (C4 §4.3), 根因是
  dep_graph 对"同库根"停步 + first-wins BFS 巧合路径的结构性缺陷; 全局修复
  两案 (own-subtree 递归 / 全局递归) 均因副作用否决; .deps 再漂移时同法补钉。
- `gen_audit.py --macros` 判定盲点 (C4): 宏面统计须与实体面审计交叉验证。

## 8. 消费者/测试写法陷阱沉淀

- MSVC `assert` 宏 `(!!(x)) || ...` 不短路: 用户定义 `operator||`/`operator!`
  (tribool、hana bool) 被无条件求值 → 先 `bool(...)` 显式转换。
- `import std;` 与拉入 `<type_traits>` 的 include 同 TU → std 变量模板重定义
  (MSVC 风味); 宏测试改纯头包含。
- `lexical_cast<bool>` clang+MSVC STL 连纯 include 也崩 (上游问题, 不覆盖);
  dll `program_location` MSVC 风味崩 (测试只验默认构造)。
- 模块不能导出 `std::tuple_size` 特化 (GMF 声明消费者不可见)。
- program_options: 多值/无效值在 store() 阶段抛异常 (非 notify); macOS
  测试 catch 需 `std::exception` 兜底。
- parameter 的 `BOOST_PARAMETER_NAME(index)` 生成关键字 `_index` (下划线前缀);
  tti 用组合形式成员函数探测; vmd 的 `(a)(b)` 是 sequence 非 tuple。
- hof `reverse_fold` 按右到左折叠 (与 `fold` 方向相反)。
- url: `query()` 返回 std::string; params 迭代器 `operator->` delete;
  字符集对象是 grammar::all_chars / lut_chars。
- lambda: 同 TU 混入弃用 `<boost/bind.hpp>` 全局 using 时 `_1` 歧义 (上游
  既有); bind/lambda 的 `std::bind`/`boost::bind` ADL 歧义为上游既有, 限定调用。

## 9. 验证体系

- 本地: llvm/msvc (默认) 全量 `mcpp build`/`mcpp test` (141) + examples
  `mcpp run`; mingw gcc 16.1 复现 gcc 平台问题; musl 交叉 (`--target
  x86_64-linux-musl`) 验 POSIX 编译面 + nm 符号级核验。
- CI 四腿: 每腿 checkout → pinned mcpp (sha256 校验) → xlings 工具链
  (per-job cache) → `mcpp build` → `mcpp test` → examples; A/B 两组全量门禁;
  test 双形态由组 A (utf 开) 与默认集 (included 形态) 分别覆盖。
- 每轮重生成收口: `gen_features.py --check` + `.deps` 无悬空边核对。

## 10. 矛盾与不明确之处 (待后续对话修正)

1. ~~**mcpp macOS dyld 修复版本自相矛盾**~~ — **已澄清 (用户确认 2026-09-08)**:
   确为 mcpp 上游已修复, CI pinned 2026.8.29.1 不受影响; 只要不**降级** pinned
   就不会再遇到该缺陷, 修复进入的具体版本号无需追查 (rollup §3.5#6 原文
   "修复版本大于 pinned"系表述错误, rollup 已删)。行动: 无。
2. ~~**rollup §3.6#2 计数陈旧**~~ — **处理中 (用户决策 2026-09-08)**: 将重新
   全量计数 (模块/feature/include-only/闭包/测试), 稍后执行; 重计结果出来前
   仍以 C4 §8 / 本文 §2.2 计数为准。
3. **历史勘误 (已记录, 无需行动)**: M4 文档 "gcc/mingw 28/28 全绿" 与 M5
   修订 (实为 5 项失败) 矛盾; M10 文档 include-only "23 库" 漏数 exception
   (实 24, C1 前) —— 均为过程文档记录不实, 已由后继文档勘误。
4. **默认闭包数字演变散落**: 18 (M8) → 31 (M9/M10) → 34 (M11) → 36 (M12)
   → C1 计划预估 35 实际 36 (functional 移出)。最终值 **36** 多处确认;
   今后以 `gen_features.py` 输出为唯一权威。
5. **hof/units gcc 混用守卫**: C1 计划预设需要 gcc 侧 ODR 守卫, CI 实测
   不需要并已移除 —— 已解, 但说明"宏面大 ⇒ 会撞 ODR"的推断不可靠
   (与 §10#3/T3 误判同族教训)。
6. ~~**`--features all` 的发布表述**~~ — **已定 (用户决策 2026-09-08)**:
   **推荐消费者逐库 import**; 预览版 release notes / architecture.md 按此
   口径表述 (不承诺 `--features all` 单次可用, gcc 侧亦不再补测)。
7. ~~**bimap 钉边与生成器债务**~~ — **已定 (用户决策 2026-09-08)**: 决定
   **尝试修复 dep_graph 结构性缺陷** (同库根停步 + first-wins BFS 巧合路径
   导致聚合式 GMF 的 re-export 边丢失, 见 C4 §4.2; 前提是不得复现两案否决
   记录中的副作用 —— topo 洗牌/实体归属漂移/平台守卫爆炸)。修复落地前
   bimap 钉边与守卫保持现状; 修复方案设计另行展开 (未实施, 仅记录决策)。
8. **M13/M14 前置关系**: 原计划 M14 发布以"剩余库全量接入"为前置; 2026-09-05
   M13 被用户决策暂缓, 2026-09-08 进一步决策**直接发布预览版** —— 发布门槛
   由"全量接入"改为"当前 115 模块 + 已知限制披露", 本决策以此为准。
9. **T3 名单冻结 vs 判定标准**: M10 宣布 T3 名单冻结, C4 即除名三库;
   "冻结"应以实体面复核为准而非时间点 —— 新库进入 include-only 的判定流程
   (宏面 + 实体面双验) 建议固化为标准操作, 待确认。

## 11. 被本文替代的旧文档 (最后存在提交 `03f616196468f71ae6bf7f22010777450356d3ec`)

plan/: boost-mcpp-module-plan.md (M0–M7 主线)、boost-mcpp-all-libs-features-plan.md
(M8–M14 全库计划)、2026-08-08-m0-spike-results.md、
2026-09-06-usage-reclassification-and-include-only-adjustment-plan.md。
docs/: 2026-08-09-m2-gen-exports-design.md、2026-08-10-m3-header-only-modules.md、
2026-08-11-m4-compiled-libs.md、2026-08-12-m5-aggregate-consumer.md、
2026-08-13-m6-ci-matrix-and-platform-fixes.md、2026-08-15-m8-mcpp-features-infra.md、
2026-08-16-macos-ci-build-mcpp-dyld-zda-analysis.md (根因结论已并入 §6.4)、
2026-08-17-m9-t1a-header-only-libs.md、2026-08-30-m10-t3-macro-driven-libs.md、
2026-08-30-m11-t2-compiled-libs.md、2026-09-05-m12-t1b-heavy-template-libs.md、
2026-09-05-design-docs-rollup-and-open-issues.md、
2026-09-07-c1-c3-usage-reclassification-and-hof-units-reentry.md、
2026-09-07-c4-bind-lambda-lambda2-modularization.md、
2026-09-08-reapply-hand-edits-patch-files.md。
各里程碑的逐项实施细节 (逐库 TU 表、逐守卫条件、逐 vendored 补丁锚点) 以
git 历史为准 (该提交之前可追溯)。
