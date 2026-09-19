# 变量模板初始化器跨模块 `.deps` 边补全 (A1) + 消费者 smoke (D)

> 日期: 2026-09-19 · 状态: 已实现 · 分支 `b1.91.0wdev`
> 决策来源: 架构文档 §4.1 残余限制; `.agents/docs/2026-09-17-variable-template-export.md`
> §5; 用户 2026-09-19 选择 A1 + D。

## 1. 问题 (根因复述)

变量模板已由 `gen_exports.py` 以合成 kind `VAR_TEMPLATE_DECL` 导出
(`_classify_var_template`, 2026-09-17)。但 libclang 把 `VarTemplateDecl`
暴露为 **无子节点的 `UNEXPOSED_DECL`**，且：

- `cursor.get_children()` 为空 → pass-2 `collect_body_edges.walk()` 无子树可走；
- `cursor.type` 为 `INVALID` → pass-1 `referenced_types()` 取不到类型；
- `cursor.extent` **在变量名之后即截断**（实测 `pfr::tuple_size_v` extent
  结束于名字末 offset，初始化器从下一 token 开始）。

因此初始化器里引用的跨模块实体既不进签名闭包、也不进体引用补全；include 图
`dep_graph()` 又在 target 库根停步，无法兜底。后果：导出模块 `A` 的变量模板若
初始化器引用家库 `B`，`A.deps` 缺 `boost.B`，纯 import 消费者实例化时可能缺声明。

## 2. A1 设计：越过 extent 的 token 级扫描

在 `collect_body_edges` 内新增变量模板分支（新增 `tu` 形参）：

1. 仅处理 `records` 中 `kind == VAR_TEMPLATE_KIND` 且属于本文出集的记录
   （与既有 body 遍历同一 claimed 快照）。
2. `_var_template_initializer_qnames(tu, cursor)`：从 `cursor.extent.end` 起
   分块 tokenize（每块 25 行，最多 4 块），切到顶层 `;`；从 token 流抽取
   **全限定 `boost::` 名字链**（`boost (:: ident)+`，遇 `<` 停止）。
3. `_qname_cursor_index(usr_index)` 建 `qname -> [cursor]`，按最长前缀解析；
   命中实体复用与 body 遍历**同一套过滤**（promote / boost 前缀 / 已在本文出
   面 / shared / TARGET_LIBS / seen），产出 `{home: set(usr)}`。
4. 交给既有 `merge_body_edges` 做直连/传递/成环过滤后并入 `.deps`。

**取舍（A1 刻意保守）**：只跟随字面全限定 `boost::...`，因此宏展开名、相对名
（`mp11::x`）、`using` 别名、ADL/依赖名仍会漏（残余限制保留）；不会误扫 std
面。过近似仅表现为多余 `export import`，仍被 merge 过滤。

缓存：结果随 `body_deps` 进入 `summary`；未命中重算，命中时沿用既有 `.deps`。
（注：现行 cache-hit 路径不回填 `body_all`，仅依赖 `.deps` 已含旧边；A1 沿用
该语义，不额外改动缓存协议。）

## 3. D 设计：消费者 smoke 实例化覆盖

为初始化器可能跨模块的导出变量模板补**实例化**断言（不只是 `using`），使缺边
在 CI 暴露。首选 `mqtt5`（`has_at_resolve = boost::is_detected<...>`，家库
`type_traits`）；若 A1 因传递可达被 merge 抑制，则断言仍验证初始化器实例化
可用（回退路径由 CI 覆盖）。

## 4. 验证（结果）

本机无 mingw sysroot，未重生成已提交的 mingw 风味 `.deps`/`.inc`；改为
host 目标（`x86_64-linux-gnu` + 系统 libstdc++）在 `/tmp` 隔离 out 目录做
端到端与单元验证：

- `_var_template_initializer_qnames` 正确恢复字面全限定引用：`pfr`（未
  clobber 前的 bundle）无（`tuple_size` 非限定）、`mqtt5::has_at_resolve`/
  `has_tls_handshake` → `boost::is_detected`、`math::is_void_v` →
  `boost::math::is_void`、`geometry::tag_keyword_arg` → `boost::mp11::mp_at_c`。
- `collect_body_edges('geometry', …)` 对该记录产出 `{'mp11': 1}`（经 qname
  最长前缀/命名空间回退 + 家库过滤）。
- host 目标 `gen_exports.py --libs mqtt5 pfr --out /tmp/…` 全流程无异常、
  pass 2 新增 0 边。
- 全量候选扫描（21 个受影响库）：候选边均落在同库 / 已是直连 / shared /
  非 target 库，**A1 对当前快照零新增 `.deps` 边**（merge 过滤后），因此本次
  提交无需改动生成物。
- `tests/mqtt5.cpp` 新增的实例化断言经头文件 `-fsyntax-only` 校验，并经
  `mcpp test mqtt5 --features mqtt5` 构建运行通过（gcc@16.1.0）。
- `reapply_hand_edits.py` 退出 0，工作区仅含预期改动。
- 文档措辞已更新：`docs/architecture.md` §4.1、`docs/zh/architecture.md`、
  `.agents/docs/2026-09-08-consolidated-design.md` §7.2#2、
  `.agents/docs/2026-09-17-variable-template-export.md` §5。

## 5. 涉及文件

- `scripts/gen_exports.py`（A1）
- `tests/mqtt5.cpp`（D，视实际边而定）
- `src/gen_exports/*.deps`、随动的 `src/*.cppm` / `scripts/features.lst` /
  `mcpp.toml`（若默认闭包变化）
- `docs/architecture.md`、`docs/zh/architecture.md`、
  `.agents/docs/2026-09-17-variable-template-export.md`
