# C1–C3 — 消费者使用方式重分类与 hof/units 重新模块化

> 日期: 2026-09-07 · 状态: 已完成 (C1 提交 33914203, C2 提交 749d4f88, C3 本文)
> 计划: `.agents/plan/2026-09-06-usage-reclassification-and-include-only-adjustment-plan.md`
> (v2) · 分支 b1.91.0wdev · 本文记录实施结果与验证过程,并收录计划期后
> 用户确认的偏差 (§5)。

## 1. C1 — 五库降级 (describe / openmethod / scope_exit / log / test)

### 1.1 决策与形态

| 库 | 降级后形态 | 原因 |
|---|---|---|
| describe / openmethod / scope_exit | 纯 include-only (无 feature 无模块) | 公共 API 以 BOOST_DESCRIBE_* / BOOST_OPENMETHOD* / BOOST_SCOPE_EXIT_* 宏为主体 (M10 边界: 宏永不跨模块边界); gcc 16.1 对同库 include+import 混用 ODR 重定义,消费者被迫二选一,宏面赢 |
| log | **编译库 include-only** (feature 保留库 TU,无模块) | gcc 消费面早已不可用 (M11 §7.4),模块面消失后三编译器消费方式统一 |
| test | 编译库 include-only + **feature 改名 `unit_test_framework`** + **双形态消费** | 宏主体 API (BOOST_TEST_*);官方推荐编译框架形态 + 官方可选纯头形态并存 |

「编译库 include-only」为 C1 新形态: `[features.<f>]` 保留 `sources` (库 TU
globs) 与 `flags`,无 `.cppm` (无 CMI 可导出)。`build.mcpp` 生成 `import
boost;` 汇总时跳过无模块 feature (`kModuleLessFeatures` 表)。

### 1.2 test 双形态互斥 (核心设计点)

两形态不可同链接 (框架 TU 与 `<boost/test/included/**>` 聚合实现符号冲突,
M11 §3):

- `gen_features.py` 新增 `FEATURE_ONLY_SOURCES = ["unit_test_framework"]`:
  框架 TU globs **不进** base `[build].sources`。M8 §1.1 实测 test 模式
  (includeDevDeps) DROP 跳过但 ADD 保留 → base 内 TU 会无条件编进每个测试
  程序;feature-only sources 仅在 feature 激活时编译 (build/test 皆然),
  从源集层面保证互斥。
- 测试文件用 `MCPP_FEATURE_UNIT_TEST_FRAMEWORK` 宏门控 (spike 验证该宏到达
  测试 TU): `tests/test_utf.cpp` (feature 开,BOOST_TEST_NO_MAIN +
  `impl/unit_test_main.ipp` + 自持 main) 与新增 `tests/test_included.cpp`
  (feature 关,聚合头自带 main),各自在对方形态下编译为直通 stub。

### 1.3 实施与管线

- `boost_common.py`: LIBS_M3 移出 scope_exit、LIBS_T1A 移出
  describe/openmethod、LIBS_T2 移出 log/test;新增
  `LIBS_COMPILED_INCLUDE_ONLY = ["log", "test"]`;TARGET_LIBS 115 → 110。
- 删除 5 个 `.cppm` 与对应 `.inc/.deps`;`reapply_hand_edits.py` 清理失效
  锚点 (strip_log_version_namespace、log/test 模块守卫、scope_exit 移出
  M3 restore 列表);test 头 vendored 修补 (print_helper/basic_cstring/
  runtime modifier/token_iterator) 与 log simple_event_log.h 桩保留 ——
  对两种消费形态同样受益。
- `gen_features.py`: 无模块 feature 支持、`FEATURE_NAME_OVERRIDE`、log/
  unit_test_framework 的 implies 手工钉定 (原 .deps 边,`--features log`
  需在 build 模式拉齐 filesystem/thread/chrono 等链接依赖)。
- 全量重生成 (110 库) → reapply → gen_features → `--check` 绿;`.deps`
  无悬空边。first-wins 归属漂移: describe::* 实体改由实际 include 其头的
  模块导出 (container_hash/json),共享头 mem_fn/function_equal 族由
  boost.functional 接管 (scope_exit 时代经其 re-export 链) —— `functional`
  移出默认闭包 (36)。
- CI: A 组 103 → 98 模块 + 追加 `log,unit_test_framework` (feature 名) ——
  组 A 腿跑 test_utf 编译形态,默认集跑 test_included 纯头形态。

## 2. C2 — hof / units 内部链接改造与重新模块化

### 2.1 改造方式 (计划 §3.2: 改宏定义本身)

M9 降级原因唯一且集中: 公共 API 对象经宏生成内部链接。扫描确认两个宏头
文件即覆盖全部面 (hof 无其他宏消费者、units 无 boost/units 外消费者,
展开点全为命名空间作用域):

- `boost/hof/detail/static_const_var.hpp`:
  `BOOST_HOF_STATIC_CONSTEXPR` `const constexpr` → `inline constexpr`
  (覆盖 arg_c/if_c 变量模板);
  `BOOST_HOF_STATIC_AUTO_REF` / `BOOST_HOF_STATIC_CONST_VAR(name)`
  `static constexpr auto&` → `inline constexpr auto&` (覆盖
  BOOST_HOF_DECLARE_STATIC_VAR 全部 ~40 个公共单件: compose/flow/_1.._9/_/
  capture/pack/...);gcc-4.6 weak 分支未动。
- `boost/units/static_constant.hpp`: C++11 分支
  `BOOST_STATIC_CONSTEXPR type name` → `inline constexpr type name`
  (185 处展开,si::meter 等全部单位常量;C++11 前分支不被激活)。

语义: `inline constexpr` 对默认构造的类类型常量与原 `static constexpr`
等价 (值语义/常量初始化),获得外链 + 跨 TU 去重 —— 与 M12
BOOST_BEAST_INLINE_VARIABLE / BOOST_PARAMETER_NAME_KEYWORD 修法同型。

### 2.2 结果

- `boost_common.py`: hof/units 移出 LIBS_INCLUDE_ONLY_M9 (回
  predef/static_assert) 加入 LIBS_T1A,TARGET_LIBS 110 → 112;
  全量重生成 (112 库,--emit-cppm) → reapply → gen_features → `--check`
  绿。units 导出 1355 实体 (implies: assert/config/iterator/math/tuple/
  type_traits/utility),hof 导出 353 实体 (自含,无 .deps)。
- vendored 补丁锚点登记 `reapply_vendored_patches()` (4 处 patch,从
  pristine 上游文本锚定,回放/幂等均验证)。
- hof.inc MSVC 风味守卫 7 实体 (M9 §3 惯例,镜像上游条件):
  `detail::bool_seq` (!`_MSC_VER`,and.hpp)、`detail::called_val`/
  `callable_args`/`can_be_called_impl` (!`BOOST_HOF_NO_EXPRESSION_SFINAE`,
  can_be_called.hpp)、`detail::eval_helper`
  (!`BOOST_HOF_NO_ORDERED_BRACE_INIT`,apply_eval.hpp)、
  `operators::increment`/`decrement` (!`_MSC_VER`,placeholders.hpp)。
- 归属漂移: 共享头实体 (bimap/numeric 此前认领部分) 改由 boost.units
  first-wins 导出。
- CI: A 组 += hof,units (98 → 100 模块)。

### 2.3 测试 (宏面与 import 面分开测,计划 §3.3.5)

| 文件 | 面 | 内容 |
|---|---|---|
| tests/hof.cpp | import (模块面) | compose/`_1 + _2`/always/pipable |
| tests/units.cpp | import (模块面) | si::meter/second/hertz 量纲运算、quantity_cast |
| tests/hof_include.cpp (新) | include/宏面 | 用户侧 BOOST_HOF_STATIC_FUNCTION + reverse_fold |
| tests/units_include.cpp (新) | include/宏面 | si 常量 + quantity_cast (force/area/pressure) |

**写法陷阱沉淀**: `boost::hof::reverse_fold` 按右到左折叠
(`(1,2,3)` → 132,`fold` → 123),初版断言 123 被运行期 assert 捕获。

## 3. C3 — 文档与计数同步 (本文 + rollup/README/M9/M10/M11 补记)

- rollup (2026-09-05): §2 计数修正 (含勘误: 原 "include-only 23 库" 漏数
  exception,实为 24) + §3.1#5/§3.3#1/§3.3#5/§3.6#2 现状更新。
- README: feature/模块/闭包/include-only 计数、双形态示例、名单增补。
- M9 §7 补记 (hof/units 重接入)、M10 §8 补记 (宏主体 API 降级档,与 T3
  分列)、M11 §8 补记 (log/test 变化)。

## 4. 验证矩阵

| 项 | 结果 |
|---|---|
| `mcpp build` (默认 36 库闭包) | ✅ llvm/msvc 本地 |
| `mcpp build --features hof,units` (C2) | ✅ |
| `mcpp build --features log` (手工 implies 链接面) | ✅ |
| `mcpp test` 默认集 (C1 139/139 → C2 141/141) | ✅ test_included 实跑 / test_utf stub |
| `mcpp test --features unit_test_framework` | ✅ 139/139,test_utf 编译形态实跑,无符号冲突 |
| examples (`import boost;` 汇总,build.mcpp 跳过无模块 feature) | ✅ |
| `gen_features.py --check` | ✅ |
| **CI 四腿** (push 后) | ✅ C1、C2 均全绿 (linux-gcc 腿验证 hof/units import 无混用 ODR) |

## 5. 计划期后的偏差记录 (用户确认, 2026-09)

1. **默认闭包 37 → 36** (计划 §1.3.6 预估 35): 以重生成输出为准 ——
   `functional` 移出闭包 (boost.functional 现自行导出 boost::function 类,
   不再经 scope_exit 时代的 re-export 链)。
2. **hof/units 的 gcc 混用守卫取消**: 计划 §3.3.6 曾按 describe.cpp 先例
   预设 gcc 侧 ODR 守卫 (tests/hof.cpp / tests/units.cpp 初版带
   `__GNUC__` 条件)。CI linux-gcc 腿实测 `import boost.hof;` /
   `import boost.units;` 在 gcc 16.1 直接可用 —— 两库 GMF 不含
   describe.cpp 撞车实体族,宏面大不等于撞名。用户注释掉条件编译宏并经
   CI 确认后,C3 将守卫彻底移除 (本条为记录)。describe/openmethod/
   scope_exit 的纯 include 消费规则不受影响 (仍无模块,不存在混用面)。

## 6. 最终计数 (C3 收口)

- 模块 **112** (T0 26 + T1a 58 + T2 16 + T1b 12);feature **114** (+log/
  unit_test_framework 两个无模块);纯 include-only **25** (T3 19 + predef/
  static_assert + exception + describe/openmethod/scope_exit);编译库
  include-only **2** (log / unit_test_framework,test 双形态);封装总数
  **139** 不变。默认闭包 **36**。测试 141/141 (llvm/msvc 本地)。
