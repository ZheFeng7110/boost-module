# M10 — 宏驱动库边界确认 (T3, 19 库)

> 日期: 2026-08-30 · 里程碑: M10 (`boost-mcpp-all-libs-features-plan.md` §4)
> 前置: M8 (features 基建) · M9 (T1a 58 库) · 本文记录实现与验证过程

## 1. 范围与结论

计划 §2 的 T3 "~19 库" 名单以宏面统计核实后**全部成立** (无增删):

> preprocessor / mpl / fusion / proto / spirit / xpressive / lambda / lambda2 /
> bind / typeof / vmd / phoenix / parameter / metaparse / function_types / tti /
> local_function / msm / foreach

加上 M9 已降级的 4 个 include-only 库 (predef / static_assert / hof / units),
include-only 集合共 **23 库**。边界判定标准 (计划 §2 注): **公共 API 宏注入面**
——宏是预处理器层面的 API,C++23 named modules 永远无法导出宏;这些库的使用方式
(BOOST_PP_CAT、BOOST_FOREACH、BOOST_TTI_HAS_MEMBER_DATA...) 本身就是宏调用,
建模块在原理上不可行,不是工作量问题 (用户决策 §5.3: 保持 include-only)。

**M10 无模块/无 feature/无构建工作**: T3 库不出现在 `[features]`、
`features.lst`、`[build].sources`、`src/*.cppm` 中,对 mcpp.toml 零改动。

## 2. gen_audit.py --macros (宏面统计)

新增 `--macros` 模式 (文本级扫描,不依赖 libclang bundle,秒级完成):

- 逐库统计其**自有公共头集**内 `#define` 的唯一宏名 (扣除同集内 `#undef`),
  区分 function-like / object-like;头集来源: 模块库用 libs.json (即 GMF
  实际 include 面),非模块库用非 detail 启发式 (predef 这类纯 `.h` 库补 `.h` 解析)
- 按规范宏族分桶 (BOOST_PP_/BOOST_MPL_/BOOST_FUSION_/BOOST_SPIRIT_ 等族 +
  predef 的 BOOST_OS_/BOOST_COMP_/BOOST_ARCH_ 检测族),报告 own-family 占比与 top-3 族
- 模块库附带 `src/gen_exports/<lib>.inc` 的 entities 数作对比 (导出实体面)
- 输出 `target/gen/audit/macro_surface.txt` + stdout 表

## 3. 宏面统计核对结果 (关键数据)

T3 候选库全部由自身宏族主导 (`own` = own-family 宏数,`macros` = 唯一宏总数):

| lib | headers | macros | own | 备注 |
|---|---:|---:|---:|---|
| preprocessor | 266 | 22919 | 22919 | BOOST_PP_ 族 22653,全库即宏 |
| metaparse | 317 | 2398 | 2396 | BOOST_METAPARSE_ |
| parameter | 103 | 1116 | 1114 | BOOST_PARAMETER_ (1001 个 function-like) |
| spirit | 892 | 1036 | 1019 | BOOST_SPIRIT_ |
| mpl | 1045 | 739 | 727 | BOOST_MPL_ |
| fusion | 471 | 524 | 190 | 另有 332 个 "other" = 经 include 传递的 mpl/config 宏 |
| local_function | 33 | 227 | 223 | BOOST_LOCAL_FUNCTION_ |
| phoenix | 95 | 209 | 198 | BOOST_PHOENIX_ |
| vmd | 64 | 157 | 156 | BOOST_VMD_ |
| proto | 55 | 148 | 147 | BOOST_PROTO_ |
| msm | 63 | 141 | 103 | BOOST_MSM_ |
| function_types | 21 | 42 | 39 | BOOST_FT_ |
| tti | 32 | 78 | 78 | BOOST_TTI_ |
| typeof | 27 | 38 | 35 | BOOST_TYPEOF_ |
| foreach | 1 | 29 | 28 | BOOST_FOREACH |
| xpressive | 20 | 31 | 25 | BOOST_XPRESSIVE_ |
| lambda | 13 | 17 | 17 | BOOST_LAMBDA_ |
| bind | 9 | 10 | 9 | BOOST_BIND_ |
| lambda2 | 2 | 9 | 9 | BOOST_LAMBDA2_ |
| predef (M9) | 136 | 518 | 509 | BOOST_OS_/COMP_/ARCH_ 检测族 |
| static_assert (M9) | 1 | 6 | 4 | 且模块名含关键字非法 |
| hof / units (M9) | 52/305 | 137/329 | 137/283 | API 为内部链接对象,宏面次要 |

对比: 85 个模块库的宏面全部 ≤ 200 量级 (最大 outcome 193 / winapi 157 /
type_traits 201),且都封在各自 GMF 内部、**永不外泄给消费者**;唯一例外
utility 的 588 来自上游 `boost/utility/binary.hpp` 的 BOOST_BINARY 字面量宏表
(561 个),同为 GMF 内部。模块库宏面高不是缺陷 (宏不跨模块边界),而 T3 库的宏面
**就是 API 本身**,每消费者 TU 直接受注入 —— 这就是边界的本质差异。

## 4. include-only 消费者用法 (文档记录)

T3 库没有模块,消费者**直接 include 上游头**,与模块 import 同 TU 混用
(标准允许, gm 内 header attachment 互不干扰):

```cpp
// 宏 API: 直接 include (预处理器层面, 模块永远给不了)
#include <boost/preprocessor/cat.hpp>
#include <boost/foreach.hpp>

// 类型/函数 API: 可以选 include 或 import (例如 mpl / fusion / bind 的类型面)
#include <boost/mpl/vector.hpp>
import boost.core;          // 模块拼写与 include 拼写共存于同一 TU

// 使用: 宏拼写与模块拼写各司其职
static_assert(BOOST_PP_CAT(1, 2) == 12);
BOOST_FOREACH (int x, vec) { ... }
```

要点:

- **宏拼写只能来自 include**: 宏不跨模块边界,`import boost.*;` 永远不提供
  BOOST_PP_* / BOOST_FOREACH / BOOST_TTI_* 等宏
- **类型/函数拼写二选一**: `boost::mpl::vector` 可以 include 后直接用,也可以
  (对已模块化的库) import 后用 re-export 拼写;T3 库只有 include 一条路
- **`include/boost-module/macros.hpp` 旁路头不逐库扩展** (M0 §5 约束,本期确认):
  它只承载包级版本宏 (BOOST_VERSION/BOOST_LIB_VERSION,来自 boost/version.hpp),
  与各模块 GMF include 集不相交、零 ODR 风险。若逐库复制 T3 宏面进旁路头,
  会把宏面 GMF-外部化、与上游头相互 #include-guard 撞车 —— 明确不做;T3 宏 API
  一律以 include 上游头获取
- mcpp.toml / features.lst 对 T3 库零声明: 无 feature 意味着消费者侧
  `--features all` 也不会引入它们 (无源可编),纯头随用随含

## 5. 冒烟测试 (import + include 混用)

19 个新测试 (每库 1 文件,`tests/<lib>.cpp`,与现有测试同名规范),统一模式:

```cpp
#include "test_assert.hpp"
import boost.config;        // 最小默认集模块 (GMF 仅 boost/config.hpp)
#include <boost/mpl/vector.hpp>
...
```

- 每测试含代表性 API 用法 + 断言: 宏 (BOOST_PP_CAT/BOOST_FOREACH/BOOST_VMD_...),
  类型面 (mpl::vector/fusion::vector/function_types/TTI 元函数),以及经典
  端到端 (spirit::qi::parse、xpressive regex_search、msm 两状态机、phoenix
  惰性求值、proto 表达式树、parameter 命名参数、local_function 局部函数)
- **gcc 16 无需守卫**: 与 describe/statechart 的先例 (同库 include + import
  触发 ODR 重定义,gcc 须回退纯头) 不同,混用伙伴选 `boost.config` 后模块侧
  附着面极小,mpl 又刻意不 include boost/config.hpp,llvm/gcc/msvc 三风味
  全部干净通过,无一处需要 gcc 纯头回退
- 测试写法核对 (对齐上游 vendored 测试): parameter 的 `BOOST_PARAMETER_NAME(index)`
  生成关键字 **`_index`** (下划线前缀) 且参数表须写 `(required (index,*))`;
  tti 成员函数用组合形式 `has_member_function_scaled<int (Point::*)(int)>`;
  vmd 的 `(a)(b)` 是 sequence 不是 tuple (IS_TUPLE=0)
- mpl/fusion/spirit/xpressive 等在 test 模式 (全量源) 与默认集下均可编译,
  无需 `--features`(import 的只有默认集内的 boost.config)

## 6. 验证矩阵 (本地 llvm 22 / gcc 16.1 mingw)

| 项 | 结果 |
|---|---|
| `mcpp test` (llvm-msvc, 88 旧 + 19 新 = 107) | ✅ 107/107 |
| `mcpp build` (默认 31 库闭包, llvm) | ✅ |
| `mcpp build --features all` (85 模块, llvm) | ✅ |
| `mcpp test <name>` 19 个 T3 单跑 (gcc 16.1.0) | ✅ 19/19 |
| `mcpp test` 全量 (gcc 16.1.0 mingw) | 105/107 (仅 thread 超时 + url 编译失败 = M6 §5 已知 mingw 本地基线, 与 M10 无关) |
| examples (`import boost;` 消费者) | ✅ |
| `gen_audit.py --macros` 全 108 库 | ✅ 报告入档 |

> CI 四腿 (llvm-msvc / linux-gcc / linux-llvm / macos-llvm) 由 push 后的 CI
> 覆盖;本地图形验证了 llvm-msvc 与 mingw gcc 两个代表风味。

## 7. 已知限制与后续

- fusion 的 "other" 332 个宏为传递注入 (mpl/config 家族),佐证 include-only
  决策: 模块化也无法切断传递宏面
- msm 测试用 on_entry 计数器观察状态迁移 (最小可观测断言),不覆盖 msm 全部
  front-end 形态 —— 按计划只做最小冒烟
- T1b/T2/T4 移交 M12–M13;T3 集合从此冻结,后续新库按宏面统计 (gen_audit
  --macros) 进 include-only 名单时同步记录
