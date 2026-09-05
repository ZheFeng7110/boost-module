# 计划 — 消费者使用方式重分类与 include-only 边界调整

> 日期: 2026-09-06 · 状态: 待实施 (v2, 按用户 2026-09-06 二次决策修订)
> 修订记录:
> - v1 曾将 test 排除在降级名单外 (当时理解为"保留模块、仅改 feature 名");
> - **v2 按用户澄清**: test 同样**不做模块封装** (宏为主体 API),采用双形态消费
>   —— 启用 `unit_test_framework` feature 时视为编译库 (feature 只编译库 TU),
>   不启用时作为纯头文件库直接 include。v1 的"解释说明"段落作废。
> 上游目标: Boost 1.91.0 · 分支 b1.91.0wdev · 当前 115 模块
> (T0 27 + T1a 58 + T2 18 + T1b 12),include-only 24 库,共 139 库。

## 0. 决策清单 (用户 2026-09-06,含二次澄清)

1. **降级 include-only (不做模块封装,直接 include 上游头)**:
   describe / openmethod / scope_exit / log / **test** (五库)。
   - describe / openmethod / scope_exit / test: 公共 API 以 BOOST_DESCRIBE_* /
     BOOST_OPENMETHOD* / BOOST_SCOPE_EXIT* / BOOST_TEST_* 宏为主体
     (M10 边界: 宏永不跨模块边界),模块面与宏面割裂,统一 include;
   - log: gcc 消费面早已不可用 (M11 §7.4,测试已纯 include;CMI/GMF 撞名族
     rollup §3.1#5 未根除),降级消除三编译器消费方式不一致;
   - **test 双形态** (§2): 官方推荐编译库形态 → `unit_test_framework` feature
     启用时视为编译库;官方可选纯头配置 → 不启用 feature,直接 include 纯头
     聚合头。
2. **test 的 mcpp feature 名称改为 `unit_test_framework`** (与上游 CMake 目标
   boost_unit_test_framework 对齐);该 feature **无模块接口**,仅编译库 TU;
   不存在 `import boost.test`。
3. **内部链接导致降级/受限的库尝试重新模块化**: hof / units —— vendored 头改造,
   static / 匿名命名空间 → 常规命名空间 (**内部实现移入 detail 命名空间**)
   + inline,使公共 API 对象获得外链,再走生成器管线重新接入。
4. **M13 的 11 个未封装库继续推迟** (context / fiber / coroutine / locale / mpi /
   python / parameter_python / graph_parallel / compute / mysql / redis),
   本期零改动。

## 1. 阶段 1 — describe / openmethod / scope_exit / log / test 降级

### 1.1 理由与影响

- describe / openmethod / scope_exit: 纯头库,宏为主 API;同库 include+import
  混用在 gcc 16.1 触发 ODR 重定义 (M9 §4 / describe.cpp 先例),消费者事实上
  被迫二选一。降级后统一纯 include,与 T3 宏驱动库同规则,并消除 gcc ODR 陷阱。
- log: 编译库,降级后**保留 feature、只删模块接口** (§1.2 新形态)。
- test: 编译库 + 宏主体 API。降级后无模块,进入 §1.2 新形态,feature 改名
  unit_test_framework 并双形态消费 (§2)。

### 1.2 编译库 include-only (新形态: 有 feature 无模块)

log 与 test (unit_test_framework) 共用同一形态: `[features]` 条目保留
`sources` (全部库 TU),**无 `.cppm` 模块源**:

- gen_features.py 需支持无模块 feature: build.mcpp 动态汇总模块跳过对应
  `export import` (无 CMI 可导出);
- 消费者: `features = ["log"]` / `features = ["unit_test_framework"]` +
  `#include` 上游头 + 链接包产物 (库 TU 随 feature 编译进包);
- 实施时先 spike 验证 mcpp 对无模块 feature 的支持 (预计仅 build.mcpp 汇总
  模块生成处需要适配);若不支持则回退: 完全移除该 feature 并在 README 记录
  "编译库暂不提供,待 gcc 缺陷族修复后回归" (默认不采用)。

**test 双形态消费矩阵**:

| 形态 | feature | include | 链接 |
|---|---|---|---|
| 编译框架 (官方推荐形态) | `--features unit_test_framework` | `<boost/test/unit_test.hpp>` (+ `BOOST_TEST_NO_MAIN` + `<boost/test/impl/unit_test_main.ipp>` 取 runner,或自持 main) | 包内框架 TU |
| 纯头文件库 (官方可选形态) | **不启用** | `<boost/test/included/unit_test.hpp>` (聚合头,自带 main) | 无 |

> 上游 header-only 聚合头 `boost/test/included/**` 此前在 M11 §3 从模块 GMF
> include 面剔除,原因是与库 TU 双重定义 —— 该约束在无模块后依然成立:
> **两形态不得同链接混用** (框架 TU 与 included 聚合实现符号冲突)。
> 消费者二选一;仓库测试侧按 §1.3 门控拆分。

### 1.3 实施步骤 (与 §2 的 feature 改名合并为一轮重生成,避免双倍 churn)

1. `boost_common.py`:
   - LIBS_M3 移出 scope_exit;LIBS_T1A 移出 describe、openmethod;
     LIBS_T2 移出 log、test (余 16 编译库模块);
   - 新增 `LIBS_COMPILED_INCLUDE_ONLY = ["log", "test"]` (含原因注释: log=gcc
     缺陷族、test=宏主体 API 双形态,镜像 LIBS_INCLUDE_ONLY_M9/M11 惯例);
   - TARGET_LIBS 103 → 98;
2. 删除 `src/{describe,openmethod,scope_exit,log,test}.cppm` 与
   `src/gen_exports/{describe,openmethod,scope_exit,log,test}.{inc,deps}`
   (log/test 无模块,无 .inc);
3. `reapply_hand_edits.py`: 清理失效锚点 (describe/openmethod/scope_exit 的
   .inc 守卫、log 的 strip_log_version_namespace() 与 log.cppm GMF 补头、
   test.cppm 相关锚点);**deps/boost 下 test 头的 vendored 修补保留**
   (print_helper/basic_cstring/modifier/token_iterator 四处对两种 include
   形态同样受益,与模块无关);
4. `gen_exports.py` / `gen_features.py` 全量重生成 → `reapply_hand_edits.py`
   幂等回放 → `gen_features.py --check`;
   - first-wins 归属复核: 重生成后核对 `.deps` 无悬空 `export import` 边
     (statechart 等库的测试曾 include mpl,但 mpl 本就是 include-only 库,
     不受影响);
5. 测试改写 (5 个 + 1 新增):
   - tests/{describe,openmethod,scope_exit,log}.cpp → 纯 include smoke
     (镜像 tests/exception.cpp 的 T3 规则;scope_exit.cpp 保留
     `import boost.core;` 部分);
   - tests/test_utf.cpp → 去掉 `import boost.test;`,改编译形态纯 include
     (BOOST_TEST_NO_MAIN + unit_test_main.ipp + 自持 main,链接面不变),
     仅在 `--features unit_test_framework` 下运行;
   - 新增 tests/test_included.cpp → 纯头形态
     (`#define BOOST_TEST_MODULE` + `<boost/test/included/unit_test.hpp>`,
     自带 main),仅在**未启用** unit_test_framework 的默认 test 集运行;
   - **门控拆分**: 两形态不可同时链接 (§1.2),实施时核对 `mcpp test` 的
     feature 门控行为 —— test_utf 与 test_included 互斥排布 (feature 开/关
     各跑其一),CI 矩阵按此覆盖两种形态;
6. 默认集闭包重算 (gen_features 自动): scope_exit 在默认闭包内,默认集
   36 → 35 (以重生成输出为准);
7. CI: tests.yml 的 BOOST_GROUP_A (default + T1a + T2) 103 → 98 模块;
   test 形态门控在 CI 腿上各自覆盖;
8. README + M10/M11 设计文档补记 (§4)。

## 2. 阶段 1 同轮 — test feature 改名 unit_test_framework (无模块 feature)

1. `gen_features.py`:
   - 新增 feature 名覆盖表 `FEATURE_NAME_OVERRIDE = {"test":
     "unit_test_framework"}`,内部库键保持 `test` (LIBS_T2 移出后为
     LIBS_COMPILED_INCLUDE_ONLY 键、COMPILED_TU_GLOBS 键、tests/test_utf.cpp
     文件名均不改),仅 `[features]` 键与 features.lst 输出改名;
   - unit_test_framework feature 声明: `sources` = COMPILED_TU_GLOBS["test"]
     的 18 个 TU,**无模块源** (§1.2);
2. mcpp.toml `[features]` 块 + scripts/features.lst 由 gen_features.py 重生成;
   `all` feature 的 implies 列表同步 (含 unit_test_framework、log,重生成自动);
3. 文档同步: README 消费者示例 (`--features unit_test_framework` 编译形态 /
   不启用 + included 聚合头纯头形态)、rollup feature 计数;
4. 原 `import boost.test;` 拼写作废 —— 全仓 (tests/examples/文档) 清扫。

## 3. 阶段 2 — hof / units 内部链接改造与重新模块化

### 3.1 现状与目标

M9 降级原因 (LIBS_INCLUDE_ONLY_M9): 公共 API 为**内部链接 constexpr 对象**
(hof: boost::hof::compose / _1... 由 BOOST_HOF_STATIC_FUNCTION /
BOOST_HOF_STATIC_CONSTEXPR 等宏在命名空间作用域生成 `static` 对象;
units: boost::units::si::meter 等由 BOOST_UNITS_STATIC_CONSTANT 类机制生成
`static const`)。`using` 声明无法导出内部链接实体,故整库 include-only。

目标: 改造 vendored 头使对象获得**外部链接**,重新走生成器管线接入
boost.hof / boost.units 模块。

### 3.2 改造原则 (用户决策)

- `static` / 匿名命名空间作用域对象 → **常规命名空间 + inline**;
  - 公共 API 对象 (compose/_1/meter/si 前缀常量等): 外层命名空间 +
    `inline constexpr` (C++23,inline 变量外链,跨 TU 去重;M12 已有大量先例:
    asio prefer/query/require 单件、beast static_const 宏、parameter keyword);
  - 内部实现对象: 移入 `detail` 命名空间 + inline;
- 优先改**宏定义本身** (boost/hof/detail/*.hpp 的 BOOST_HOF_STATIC_* 族、
  boost/units/ 的 BOOST_UNITS_STATIC_CONSTANT / detail 宏),一次修改全局生效,
  与 M12 对 BOOST_BEAST_INLINE_VARIABLE / BOOST_PARAMETER_NAME_KEYWORD 的
  修法同型;
- 逐头扫描匿名命名空间 (gen_audit 或文本扫描),同规则处理。

### 3.3 实施步骤

1. vendored 头改造: `deps/boost/boost/hof/**`、`deps/boost/boost/units/**`
   (先 gen_audit --macros / 文本扫描确定改动文件清单,逐文件登记);
2. **`reapply_hand_edits.py::reapply_vendored_patches()` 登记锚点** (M12 §6 惯例:
   import_boost 重导会抹掉修补,锚点必须可幂等回放);
3. `boost_common.py`: hof、units 移出 LIBS_INCLUDE_ONLY_M9,加入 LIBS_T1A
   (TARGET_LIBS 98 → 100);
4. `uv run scripts/gen_exports.py --libs hof units` → 生成 .cppm/.inc/.deps →
   `reapply_hand_edits.py` → `gen_features.py` → `--check`;
5. 新增 smoke: tests/hof.cpp (compose/pipeline/reverse_fold)、tests/units.cpp
   (si::meter 量纲运算、conversion) —— **宏用法与 import 用法分开测**;
6. 三编译器验证: llvm-msvc 本地 + gcc 16.1 musl 交叉 (CI POSIX 腿);
   重点验证 **include+import 混用的 ODR 面**: units 宏面大 (M10 统计 own 283),
   消费者很可能宏与类型面同 TU 混用 —— 若 gcc 撞 ODR,测试/文档按
   describe.cpp 先例守卫 (gcc 侧纯 include),库落在「混合」类而非纯 import。

### 3.4 风险与回退

- 若宏改造后实体面仍不可导出 (对象经模板静态成员 / const 数组等形态),
  按实体逐个 curated 兜底;仍不可行的库**回退 include-only** 并在 M9 文档
  补记原因 (保留"尝试过"的记录,不强行接入);
- units 的 BOOST_UNITS_* 宏 API 无法进模块 → 接入后天然是「宏 include +
  类型/常量面 import」混合库,文档按混合类归类 (非纯 import);
- static_assert / predef 不在本次范围 (纯宏库,与内部链接无关,维持 include-only)。

## 4. 阶段 3 — 文档与计数同步 (收尾)

1. **rollup (2026-09-05) 计数修正**:
   - 已知错误: §2 include-only "23 库 (T3 19 + 降级 4)" 漏数 M11 降级的
     exception;
   - 本计划后 (以 hof/units 成功接入为准): 模块 115 → 110,加 hof/units
     回归 = **112**;feature 115 → 112 (describe/openmethod/scope_exit 除名;
     log/unit_test_framework 无模块),加 hof/units = **114**;
     include-only 24 → 29 (T3 19 + predef/static_assert/exception +
     describe/openmethod/scope_exit/test/log),hof/units 成功后回落 **27**;
     封装总数 139 不变;
   - 三类使用方式表更新: 「整库混合」成员清空 (仅余 io / numeric 局部混合;
     units 若接入落混合类);新增「编译库 include-only (有 feature 无模块)」
     档: log / unit_test_framework (test 双形态);
2. README: 三类用法小节、feature/模块计数、默认闭包数、
   `--features unit_test_framework` 编译形态与不启用时 included 纯头形态
   的双形态示例、include-only 名单增补;
3. M10 文档补记: T3 名单冻结,新增"宏主体 API 降级"档
   (describe/openmethod/scope_exit/test,原因 + 日期),与 T3 分列;
4. M11 文档补记: log 降级、test 去模块 + feature 改名双形态、§2 TU 表变化;
   M9 文档补 hof/units 重接入结果或回退原因。

## 5. 验证矩阵 (每阶段收口)

| 项 | 覆盖 |
|---|---|
| `mcpp build` (默认闭包) | llvm/msvc 本地 + gcc 16.1 musl 交叉 |
| `mcpp build --features all` | A 组 (98 模块) + B 组 (T1b) 分组门禁不变 |
| `mcpp test` 默认集 | 全量 (改写后的 include-only smoke + test_included 纯头形态) |
| `--features unit_test_framework` 单跑 | test_utf 编译形态构建/链接/运行 |
| `--features log` 单跑 | log include-only + 库 TU 链接 |
| tests/{describe,openmethod,scope_exit}.cpp | 纯 include 编译+运行 |
| tests/{hof,units}.cpp (阶段 2) | import 面 (三编译器) + 宏 include 面 |
| 无模块 feature 的汇总模块 | build.mcpp 生成 `import boost;` 跳过 log/unit_test_framework,examples 编译 |
| `gen_features.py --check` | 重生成一致性 |
| CI 四腿 | push 后全绿 (A/B 组) |

## 6. 实施顺序与提交切分

1. **C1 (阶段 1+2)**: 五库降级 (含 test 去模块) + unit_test_framework 改名 +
   无模块 feature 形态 (一轮重生成),含 mcpp.toml/features.lst/tests/CI/README;
2. **C2 (阶段 2)**: hof/units vendored 改造 + 锚点登记 + 重新接入
   (独立提交,便于回退);
3. **C3 (阶段 3)**: 文档/计数同步 (rollup、README、M9/M10/M11 补记)。
