# C4 — bind / lambda / lambda2 重新模块化与 bimap 依赖边钉定

> 日期: 2026-09-07 · 状态: 实施完成 · 分支 b1.91.0wdev
> 前序: C1–C3 (2026-09-07-c1-c3-usage-reclassification-and-hof-units-reentry.md)
> 背景: M10 T3 名单对 bind/lambda/lambda2 的"宏驱动"归因经复核为误判。

## 1. 归因纠正 (为什么 T3 判定错了)

T3 "~19 库" 来自 all-libs 计划 §2 粗筛,M10 用 `gen_audit.py --macros` 的
own-family 宏占比"核实"。该标准只能证明"宏面大",不能证明"API 是宏":

| 库 | own 宏数 | 宏的真实身份 | 真实 API |
|---|---|---|---|
| bind | 9 (9/10 own) | include guard、BOOST_BIND_CC/ST/NOEXCEPT 调用约定配置、BOOST_BIND_OPERATOR X-macro、BOOST_BIND_NO_PLACEHOLDERS 开关 —— 全部实现细节,无一出现在用户代码里 | `boost::bind` 函数模板 + `boost::arg<I>` + `boost::placeholders::_1.._9` (`BOOST_INLINE_CONSTEXPR`, C++17 起外链) |
| lambda2 | 9 (9/9 own) | 除 VERSION 外全是 X-macro 助手,用完即 `#undef` | `_1.._9`/`first`/`second` (`inline constexpr`) + 运算符函数模板 —— 零补丁可模块化 |
| lambda | 17 (17/17 own) | 全部实现宏 | `_1.._3`/`_e` 占位符 + functor/运算符模板 |

lambda 的 include-only 结论碰巧正确但归因错误:其占位符定义在**匿名命名空间**
(`lambda/core.hpp` 的 `free1..3/_1.._3`、`lambda/exceptions.hpp` 的
`freeE/_e`)——TU-local 实体不可 `export using`,与 M9 hof/units 同型
(内部链接对象),不是宏原因。

唯一模块面给不了的 bind 行为:弃用的 `<boost/bind.hpp>` 在全局命名空间做
`using namespace boost::placeholders;` —— using-directive 无法被 named
module 注入消费者 TU。这正是上游已弃用行为,推荐写法本就是消费者自持 using。

## 2. vendored 补丁 (仅 lambda,三处)

仿 C2 hof/units 改法(改内部链接本身),`reapply_vendored_patches()` C4 块:

1. `lambda/detail/lambda_functors.hpp`: `lambda_functor() {}` →
   `constexpr lambda_functor() {}` —— 占位符对象字面类型化的前提。
   `placeholder<>` 特化全空类,隐式构造即 constexpr;拷贝构造不需要
   (C++17 保证省略拷贝)。
2. `lambda/core.hpp`: 匿名命名空间块 →
   `inline constexpr placeholderN_type freeN = ...;` +
   `inline constexpr placeholderN_type& _N = freeN;` (外链 + 跨 TU 去重)。
   `placeholder1..3_type` 本就是 const typedef,引用类型无需调整。
3. `lambda/exceptions.hpp`: 同法处理 `freeE/_e`;注意 `placeholderE_type`
   不带 const,`_e` 须写 `inline constexpr const placeholderE_type&`。
   上游源在 `_e = freeE;` 后有 8 个尾随空格,补丁锚点按 pristine 文本精确
   匹配。

`detail::constant_null_type` 保持内部:仅被导出类的成员体引用,从不导出。

## 3. 名单迁移

- `boost_common.py`: bind/lambda/lambda2 移出 `LIBS_T3` (19 → 16),
  进 `LIBS_T1A` (58 → 61, 字母序插入);TARGET_LIBS 112 → 115。
- features.lst / mcpp.toml [features] 块由 gen_features 重生成:
  114 → 117 feature,默认闭包 36 不变。
- 纯 include-only 25 → 22。

## 4. bimap 的 boost.iterator 边丢失与定点修复

### 4.1 缺陷

bimap 测试在 C4 后失败 (`operator!=` 消失)。链条: bimap 的 GMF 含
`boost/bimap/support/lambda.hpp`;C4 前 lambda 非目标库,其 detail 头是
"shared" 候选,bimap 经它们 BFS 到 `boost::iterators` 家族实体并记
`boost.iterator` 边;C4 后这些头归属 lambda,claim 顺序变化使该路径消失,
`bimap.deps` 丢失 `boost.iterator` → 模块不再 re-export `operator!=`
(消费者比较 view 迭代器需要它,boost.iterator 导出
`using boost::operator!=;`)。property_tree/wave 各有一条
`boost.tuple` 边以同机制消失 (经 lambda detail 头中介的 BFS 路径),
其 GMF 面较窄未构成可观察破坏。

### 4.2 全局修法两次否决记录

**own-subtree 递归 (已否决)**: 让 `dep_graph` 在同库根 (`dep == lib`)
继续下钻 (仅 extra_deps 计算启用, topo 图不动)。能恢复 bimap 边,但
语义过宽: 它把**仅模块 TU 内部使用、消费者永不可见**的包含也记为边
(实测 geometry 子树的 overlay/debug 头 include boost/graph →
geometry↔graph 假循环, mcpp 校验拒绝; 72 库虚增 259 条边)。
**全局递归 (已否决)**: 同时作用于 topo 图会洗牌拓扑顺序,first-wins
归属随之漂移,把 gcc 风味独有的 mpl aux 实体 (`arity_helper` 族) 冲进
functional/graph 的 .inc (MSVC/llvm-msvc 风味 TU 无此实体,编译失败),
M3/M9 平台守卫爆炸。实测复现后两案均放弃。

### 4.3 实施修法: 定点钉边 (C1 手工 implies 先例)

`reapply_hand_edits.py` C4 块:
- `src/gen_exports/bimap.deps`: +`boost.iterator` (带注释行);
- `src/bimap.cppm`: +`export import boost.iterator;` (带注释)。

随重生成管线每轮回放, 幂等。gen_features 的 implies 自动获得 iterator。

### 4.4 连带守卫调整

- `scope.cppm` gcc-ICE 守卫锚点从 "module 行后紧跟 core 边" 放宽为裸
  `export import boost.core;` 行, 并 `required=False` (scope.cppm 在
  M3 final-form git 还原清单内, 还原后的 HEAD 形态不含裸 core 行 ——
  该补丁仅为未来脱管场景兜底)。
- `poly_collection.inc` 的 `item_by_order_impl` 守卫改 `required=False`,
  新增 `type_erasure.inc` 同实体守卫 (`required=False`): 实体落点随
  claim 顺序漂移时两处守卫按需命中 (本机稳态下 poly_collection 命中、
  type_erasure 跳过)。

## 5. 消费面注记

- bind: 模块消费者自持 `using namespace boost::placeholders;` 或限定
  `boost::placeholders::_N`;弃用头 `<boost/bind.hpp>` 的全局 using 仅
  include 面有效。
- lambda: `_e` 由非 const 引用改为 const 引用 (constexpr 对象隐含 const);
  上游模板形参均按 const& 接收,无破坏面。上游既有怪癖不变: 同 TU 混入
  `<boost/bind.hpp>` 弃用全局 using 时 `_1` 歧义 (全局 using-directive
  撞名,与模块无关)。
- bind/lambda 的 `std::bind`/`boost::bind` ADL 歧义为上游既有行为
  (boost::arg 与 std::plus 各自拉入同名自由模板),文档一贯要求限定调用。

## 6. 测试

| 文件 | 面 | 内容 |
|---|---|---|
| tests/bind.cpp (新) | import | bind 模板/arg/placeholders/ref 绑定、mem_fn |
| tests/lambda.cpp (新) | import | `_1 += 10`、if_[_1 = 0]、lambda::bind、try_catch + `_e` |
| tests/lambda2.cpp (新) | import | `_1 + 1`、`_1 < _2`、`_1[_2]` map 下标、first/second |
| tests/functional.cpp (改) | import | +`import boost.bind;` (mem_fn 归属漂移, §4.2) |

## 7. 验证矩阵

| 项 | 结果 |
|---|---|
| `gen_exports` 全量重生成 (115 库, --emit-cppm) | ✅ |
| `reapply_hand_edits.py` 回放 + 幂等复跑 | ✅ |
| `gen_features.py` 重生成 + `--check` | ✅ |
| `mcpp build --features bind,lambda,lambda2` | ✅ llvm-msvc 本地 |
| `mcpp test` 默认集 141/141 (含 wave/property_tree/xpressive 等受害面) | ✅ |
| 定点复测 bind / lambda / lambda2 / bimap / functional / units (+units_include) / property_tree | ✅ 逐库单跑全绿 |
| CI 四腿 (push 后) | 待确认 |

注: `mcpp test --list` (141) 不含 opt-in-only 库测试 (bind/lambda/lambda2/
hof/units), opt-in 面由定点单跑覆盖。

## 8. 计数收口

- 模块 **115** (T0 26 + T1a 61 + T2 16 + T1b 12);feature **117**
  (+log/unit_test_framework 两个无模块);纯 include-only **22**
  (T3 16 + predef/static_assert + exception + describe/openmethod/
  scope_exit);编译库 include-only **2**;封装总数 **139** 不变;
  默认闭包 **36**;本地测试默认集 141/141 + opt-in 定点全绿。

## 9. 遗留与销账

- rollup 未解问题清单新增: M10 宏面统计验证标准的系统性盲点 ——
  "own-family 宏占比" 只能证明宏面大,不能证明 API 是宏;对
  "少量实现宏 + 对象/模板 API" 的库 (bind 9、lambda2 9、lambda 17) 会
  误判。`gen_audit.py --macros` 结论今后须与实体面审计 (linkage/导出面)
  交叉验证。
- bimap 的 boost.iterator re-export 边为手工钉定 (§4.3),其丢失根因
  (聚合式 GMF 下 .deps 走查对"同库根"停步 + first-wins BFS 巧合路径)
  是 gen 生成器的结构性缺陷,记录于 C4 §4.2;全局修复两案均因副作用
  过大否决,若未来 .deps 再次漂移,同法补钉。
- first-wins 错位实体 (reference_wrapper 家族在 bind 而非 core) 属
  既有现象,C4 顺带如实记录,不另行重排。
