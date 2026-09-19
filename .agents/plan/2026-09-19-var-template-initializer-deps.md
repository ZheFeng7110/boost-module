# 变量模板初始化器跨模块 `.deps` 边补全 (A1+A2) + 消费者 smoke (D)

> 日期: 2026-09-19 · 状态: 已实现 (A1 提交 6f9ec29c; A2 见下) · 分支 `b1.91.0wdev`
> 决策来源: 架构文档 §4.1 残余限制; `.agents/docs/2026-09-17-variable-template-export.md`
> §5; 用户 2026-09-19 选择 A1 + D, 随后追加 A2。

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

## 2b. A2 设计：相对限定名解析

A1 之外，把 token 流里的 `ident (:: ident)+` 链全部收集（不再只认 `boost`），
并在 `_initializer_lookup_qnames(chain, ns_chain)` 里做文本名字解析：

1. `boost::...` 链按原样（A1）；
2. 相对链按变量模板所在命名空间链**由内向外**逐级前缀，再到 `boost::` 根、
   最后全局（模拟 C++ 非限定名查找）；
3. 每个候选再按最长前缀回退（沿用 A1，覆盖未入 USR 索引的别名模板）；
4. **命名空间级回退护栏** `_namespace_matches_home`：只有候选命名空间段与解析
   出的家库名对应 (归一化后相等或互为前缀) 才接受该命名空间游标，避免
   `boost::detail` 这类共享命名空间被首个声明文件误归到某库而产生伪边
   （实测该伪边为 `parser/math/outcome -> boost.throw_exception`）。
5. `add_edge` 返回是否真正加边；调用方按候选顺序取**第一个有效**匹配，从而
   跳过被护栏/家库过滤的中间命名空间，继续尝试更外层前缀。

D 侧不变。

## 3. D 设计：消费者 smoke 实例化覆盖

为初始化器可能跨模块的导出变量模板补**实例化**断言（不只是 `using`），使缺边
在 CI 暴露。首选 `mqtt5`（`has_at_resolve = boost::is_detected<...>`，家库
`type_traits`）；若 A1 因传递可达被 merge 抑制，则断言仍验证初始化器实例化
可用（回退路径由 CI 覆盖）。

## 4. 验证（结果）

A1 阶段本机无 mingw sysroot，先在 host 目标（`x86_64-linux-gnu`）上做单元与
端到端验证；A2 阶段已安装 `scripts/_deps/mingw64`（fetch_mingw_sysroot.py），
用完整 LLVM libclang 复现 mingw 风味全量生成。

A1 (host 目标):

- `_var_template_initializer_qnames` 正确恢复字面全限定引用：`mqtt5::
  has_at_resolve`/`has_tls_handshake` → `boost::is_detected`、`math::is_void_v`
  → `boost::math::is_void`、`geometry::tag_keyword_arg` → `boost::mp11::mp_at_c`。
- `collect_body_edges('geometry', …)` 对该记录产出 `{'mp11': 1}`。
- 全量候选扫描（21 个受影响库）：候选边均落在同库 / 已是直连 / shared /
  非 target 库，A1 对当前快照零新增 `.deps` 边。

A2 (mingw sysroot, llvm23 libclang):

- 全量 `gen_exports.py --no-cache` (A2) 与等价的 A1 基线（monkeypatch 只保留
  `boost::` 链）各跑一次，**pre-merge `body_deps` 完全一致**（逐库逐 home 集合
  相等），最终 `.deps` 亦逐文件一致 → A2 对当前 Boost 1.91 快照零新增边。
- A2 未加护栏时曾多出 3 条 `parser/math/outcome -> boost.throw_exception` 伪边
  （相对 `detail::...` 链回退到共享 `boost::detail` 命名空间）；护栏
  `_namespace_matches_home` 消除之，且不影响 body walk 的 NAMESPACE_REF 真边。
- `_initializer_lookup_qnames` 相对链候选顺序与命名空间护栏单测通过
  （`mp11::mp_at_c` → `boost::geometry::detail::...`/`boost::geometry`/...；
  `boost::mp11`↔mp11 通过，`boost::detail`↔throw_exception 拒绝）。

其他:

- `tests/mqtt5.cpp` 的实例化断言经头文件 `-fsyntax-only` 校验，并经
  `mcpp test mqtt5 --features mqtt5` 构建运行通过（gcc@16.1.0）。
- `reapply_hand_edits.py` 退出 0，`gen_features.py --check` 退出 0。
- 文档措辞已更新：`docs/architecture.md` §4.1、`docs/zh/architecture.md`、
  `.agents/docs/2026-09-08-consolidated-design.md` §7.2#2、
  `.agents/docs/2026-09-17-variable-template-export.md` §5。

> 注：用当前已安装的 mingw sysroot + llvm23 直接全量重生成会带来一批与 A2
> 无关的历史漂移（如 `align/container_hash/endian/tuple/winapi/atomic/thread`
> 的旧 `.deps` 边在当前生成器下不再产生，疑似 2026-09-17 之前的降级解析快照）。
> 因此本次仅提交 A2 代码/测试/文档，未刷新生成物；历史漂移需另行专项核对。

## 5. 涉及文件

- `scripts/gen_exports.py`（A1 + A2）
- `tests/mqtt5.cpp`（D）
- `docs/architecture.md`、`docs/zh/architecture.md`、
  `.agents/docs/2026-09-17-variable-template-export.md`、
  `.agents/docs/2026-09-08-consolidated-design.md`
- 生成物（`src/gen_exports/*.deps` / `src/*.cppm` / `scripts/features.lst` /
  `mcpp.toml`）本阶段未变（A1+A2 零新增边）
