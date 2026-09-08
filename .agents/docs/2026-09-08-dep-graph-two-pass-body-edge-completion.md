# dep_graph 结构性缺陷修复 — 两遍扫描体引用边补全 (pass 2)

> 日期: 2026-09-08 · 状态: 实施完成 · 分支 `b1.91.0wdev`
> 决策来源: 汇总文档 §10#7 (用户决策: 尝试修复, 前提是不得复现 C4 §4.2
> 两案否决记录中的副作用 —— topo 洗牌 / 实体归属漂移 / 平台守卫爆炸)。

## 1. 缺陷与丢失机制 (C4 §4.1 复述)

`.deps` re-export 边有两条独立来源, 各自欠完备:

1. **AST 签名闭包** (`closure_from`): 只走声明 (`referenced_types`), 不走
   函数体/模板体 —— 经体引用才可达的家库实体 (如 view 迭代器的
   `iterator_core_access` 家族) 永远不产生边。
2. **include 图 extra_deps** (`bc.dep_graph`): 在 target 库根处停步
   (`dep != lib → add; continue`), 经其他 target 库头传递可达的包含不可见。

C4 时 bimap 的 `boost.iterator` 边恰好处在两者的盲区: 路径经
`boost/bimap/support/lambda.hpp` → (C4 后已属目标库的) lambda detail 头 →
iterator 家族, 签名闭包不到、include 图停步, 只能靠 `patchs/bimap.patch`
手工钉边 (同机制还悄悄丢失过 property_tree/wave 的 `boost.tuple` 边)。

## 2. 修法: claim 与 edge 分离的两遍扫描

**pass 1 (完全不动)**: candidates / injections / curated / 闭包 /
first-wins 认领 / `emit_inc` 导出表 —— 归属冻结, `.inc` 输出与修前逐字节
一致 (唯一例外见 §6 C4.1 后续)。

**pass 2 (新增)**:
- `collect_body_edges`: 对**恰好 emit_inc 导出集** (own + 未认领 pulls,
  与 `emit_inc` 同一 `claimed` 快照) 的每个实体, 遍历其声明与定义子树,
  收集引用类游标 (`DECL_REF_EXPR / MEMBER_REF_EXPR / TYPE_REF /
  TEMPLATE_REF / UNRESOLVED_LOOKUP_EXPR` 等) 经
  `clang_getSpecializedCursorTemplate` 解析隐式实例化到模板 (实例化游标的
  location 可能是实例化点, 不可用于归属), promote 后取定义文件家库。
- 引用目标若**已在本文出集** (own 或 pulled), 该实体随本文出, 不产冗余边
  (保护手工维护的 final-form `.cppm` 不引入杂边)。
- `merge_body_edges`: 过滤 (按 topo 序) —— 已直连 / 已传递可达 → 跳过;
  成环 → 跳过并告警 (mcpp 拒绝 import 环); 其余并入 `<lib>.deps`。
  `.cppm` 草稿在合并**之后**统一 emit (否则 import 块是 pass-1 旧值)。
- 边的充分性: 家库永远导出自己的实体 (`own` 无 claimed 过滤), 指向定义
  家库的 import 边总是自足的, 与实体被谁 first-wins 认领无关。

副作用核对: 归属零漂移 (pass 1 未动)、topo 顺序不变 (`topo_order` 用
include 图)、平台守卫零变化 (`.inc` 逐字节一致)、新增边全部经环检测
(仅 geometry→graph 被拒 —— 与 C4 §4.2 实测的假循环一致)。

## 3. 全量结果 (115 库, 三次重生成逐次确定)

- **46 个 `.deps` 新增 71 条边 / 45 库** (最终 `functional→function` 经
  精化过滤消失、`algorithm` 组被其 restore 机制抑制, 见 §5): 头条为
  **bimap → boost.iterator (6 refs) —— C4 手工钉边由生成器自然再生**,
  另恢复 C4 同机制丢失的 property_tree → any/bind/range、
  wave → format/multi_index。
- **3 个手工 final-form `.deps`/`.cppm` 脱同步被独立复现**: optional/
  static_string 的 `→boost.core`、variant 的 `→container_hash/integer/
  type_index` 本来就写在 restore 型 `.cppm` 里而 `.deps` 缺失 —— pass 2
  自动补齐 `.deps`, 全部 17 个 restore 型 `.cppm` 与 `.deps` 现已零失配
  (校验脚本核对通过)。
- **默认闭包 36 → 48** (用户决策 2026-09-08: 接受扩张): 新成员
  compat(system) / dynamic_bitset(random) / endian(json) /
  integer(chrono/random/serialization/variant) / lambda(units) /
  lexical_cast(math/numeric) / math(numeric/units) / multi_array(numeric) /
  random(math) / serialization(numeric) / tokenizer(date_time) /
  units(numeric) —— 全部 ∈ M3/T1a/T2, **CI A 组 105 feature 不变**,
  B 组 12 不变, 测试总数 141 不变 (默认 smoke 36→48, opt-in 80→68)。
- `lambda.inc` +1 实体: `detail::constant_null_type` (C4.1 vendored 补丁
  改外链 `inline constexpr` 后首次重生成被收集; 导出安全性与 C2/C4.1
  同型, comdat 去重)。

## 4. 连带修复: patch 文件化方案的潜伏缺陷

03f61619 的 patch 文件化以"整文件非前即后"为幂等前提, 但重生成循环
(`gen_exports --emit-cppm → reapply`) 会制造**混合态**: 跨 `deps/boost/`
(持续已应用) 与重生成 `src/` (回到前态) 的多文件 patch, 正向/反向检查
双双失败。首次真实重生成触发, 修法:

- hof/io/lambda/safe_numerics/system **按生命周期拆分**: deps hunks 留
  `VENDORED_PATCHES`, src hunks 移入 `<name>_src.patch` 进 `SRC_PATCHES`
  (io_src 整个删除: `src/io.cppm` 随后即被 git restore 覆盖, hunk 本为
  过渡件; 同理删除 core.patch 的 `core.cppm` hunk)。
- **hana.patch 孤儿修复**: 该补丁 (ext-tag `::boost::` 全局限定拼写)
  从未列入 SRC_PATCHES, 任何重生成都会丢拼写 —— 已列入。

## 5. 已知限制

- `algorithm.deps`/`algorithm.inc`/`algorithm.cppm` 是 restore 型手工
  final form —— pass 2 为 algorithm 找到的体引用边 (array/function/
  bind/regex/smart_ptr 等 14 refs 级) 被还原机制抑制, 候选记录保留在
  `target/gen/gen_report.json` (`body_deps` 字段); 若未来 hand form
  重新同步, 同批边可自然再生。
- geometry→graph 体引用边因成环被跳过 (该消费需求无法用 import 边表达)。
- 默认 48 中 12 个新成员的体引用边使默认构建面增大 (CI A 组不变)。
- gcc 腿未本地重验 (本地 llvm/msvc 基线 141/141 + bimap 定点全绿;
  gcc 侧由 CI 四腿覆盖, M13 暂缓库不受影响)。

## 6. 验证矩阵

| 项 | 结果 |
|---|---|
| 全量重生成 ×3 (115 库, --emit-cppm), 边集逐次一致 | ✅ (确定性) |
| `.inc` 与修前逐字节一致 (除 lambda +1 C4.1 后续) | ✅ |
| reapply 回放 + 幂等复跑 (混合态修复后) | ✅ |
| `gen_features.py` 重生成 + `--check` | ✅ |
| restore 型 `.cppm` ↔ `.deps` 零失配 (17 文件) | ✅ |
| `mcpp clean --bmi-cache` + `mcpp build` (默认 48) | ✅ llvm-msvc 本地 |
| `mcpp test` 默认集 | ✅ 141/141 |
| bimap 定点 (`mcpp test --features bimap`, 无钉边) | ✅ |
| CI 四腿 (push 后) | 待确认 |

## 7. 销账

- 汇总文档 §10#7 (dep_graph 结构性缺陷) 已实施关闭;
  §7.4 "bimap 钉边 + `.deps` 再漂移时同法补钉" 作废 (生成器自然再生);
  §2.2 / §10#4 默认闭包 36 → 48 (以 `gen_features.py` 输出为权威)。
- `patchs/bimap.patch` 删除, `reapply_hand_edits.py` SRC_PATCHES 移除
  bimap 条目。
