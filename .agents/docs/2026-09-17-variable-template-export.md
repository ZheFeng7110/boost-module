# 变量模板导出 (libclang UNEXPOSED_DECL 分类)

> Date: 2026-09-17 · Audience: 维护者 · 状态: 已实现
> 相关: `docs/architecture.md` §4.1, `.agents/docs/2026-09-08-consolidated-design.md` §7.2#2

## 1. 背景

此前 `boost.pfr::tuple_size_v`、`boost.hana::int_c`/`integral_c` 等**变量模板**
不在模块导出面内，消费者只能用类模板替代拼写（`tuple_size<T>::value`、
`integral_constant<int, i>{}`）。架构文档将其登记为 "libclang generation blind
spot"。

## 2. 根因

libclang 没有变量模板专属 cursor kind：`VarTemplateDecl` 及其偏特化/显式特化
一律回落到 `CXCursor_UnexposedDecl`，且**不暴露**内部的 `VarDecl` 子节点。证据
（合成 TU）：

```
UNEXPOSED_DECL 'tuple_size_v'  def=True linkage=EXTERNAL qname=boost::pfr::tuple_size_v
UNEXPOSED_DECL 'is_ok'         # 偏特化
UNEXPOSED_DECL 'is_ok'         # 显式特化 template<>
```

而 `scripts/gen_exports.py` 的导出白名单 `EXPORT_KINDS` 只含 `VAR_DECL`，不含
`UNEXPOSED_DECL`，因此：

- `build_usr_index`（基于 `DECL_KINDS`）不索引；
- `collect_candidates` 的第一道门 `is_export_kind` 直接丢弃；
- `collect_injections` / `collect_curated` 复用同一判定，连 curated 兜底清单也
  无法登记变量模板（会打印 `curated skip (not in TU)`）。

实测 `export using boost::pfr::tuple_size_v;` / `boost::hana::int_c` 在 clang 与
g++ 下均合法，问题纯在生成器识别层。

## 3. 设计

### 3.1 分类器

新增合成 kind `VAR_TEMPLATE_DECL` 与 `_var_template_class(cursor, tu)`：

- 仅处理 `UNEXPOSED_DECL` 且 `spelling` 非空；
- token 流须以 `template` `<` 开头；
- `template <> ...` → `explicit`；模板形参表闭合后声明名紧跟 `<` → `partial`；
  其余 → `primary`；
- 按 USR memo（`_VT_CLASS`，每个 TU 开始时清空）。

`is_export_kind(cursor, tu=None)` = 命中 `EXPORT_KINDS` **或** `primary`。只放行
主模板：偏特化/显式特化随主模板名一起可达，不单独 `using`。

### 3.2 廉价预过滤

`std` 头里充满变量模板（`std::is_void_v`、`std::conjunction_v` …），同样是
`UNEXPOSED_DECL`。`_is_boost_var_template` 先要求 `bc.namespace_chain()[0] ==
"boost"` 再 tokenize，避免索引/分词 std 面。

### 3.3 接入点

`tu` 贯穿 `build_usr_index`、`collect_candidates`、`collect_injections`、
`collect_curated`（新增 `tu` 形参）；`collect_candidates` 命中的记录 kind 归一为
`VAR_TEMPLATE_KIND`；`gen_report.json` 增加 `var_templates` 列表。

### 3.4 生成环境可配置

`boost_common.py` 新增 `BOOST_MODULE_GEN_TARGET` / `BOOST_MODULE_GEN_SYSROOT`
（默认 mingw triple，不改变已提交 mingw 风味快照）；`_append_resource_dir`
同时识别 `libclang.so`/`.dylib`（原先只找 `libclang.dll`，导致 Linux/WSL 下
libclang 找不到自带 `stddef.h`，解析降级、声明丢失）。

`gen_exports.py` 跳过 `LIBS_SPECIAL`（`boost.version` 为手写模块），避免
`--emit-cppm` 覆盖 `src/version.cppm` 并生成无用的 `version.inc`。

### 3.5 已知取舍

错误恢复下（缺 std 头）函数模板也可能被报成 `UNEXPOSED_DECL` 且 extent 截断，
从而被当作变量模板。最坏结果是重复 `using`（`emit_inc` 按限定名去重，无害），
内部链接目标仍被 `bc.linkage_ok` 拦截。**已确认可接受**。

## 4. 影响面

- 363 条变量模板 `using` 进入 21 个模块的 `.inc`（geometry/hana/math/decimal/
  parser/asio/mqtt5/pfr/…）。
- `graph`/`outcome`/`wave` 的 `.deps` 因 `boost.version` 成为目标库而新增
  include-graph 边（version 模块启用后的自然追平，非变量模板引入）。
- 手工 patch `decimal.patch`、`parser.patch` 因新行进入 hunk 上下文而重新生成。

## 5. 残余限制

变量模板初始化器不遍历（`UNEXPOSED_DECL` 无子节点，`referenced_types` 与 pass-2
body walk 都看不到），因此初始化器内引用的跨模块类型不会生成 `.deps` 边；
需要时消费者显式 `import` 被引用模块。相邻的 "requires 子句不遍历" 不在本次范围。

## 6. 验证

- 分类器合成 TU 单测（primary/partial/explicit/asm/std）。
- clang 端到端：`--precompile src/pfr.cppm` + 消费者
  `import boost.pfr; static_assert(boost::pfr::tuple_size_v<S> == 2);` 通过；
  hana 同法验证 `int_c`/`integral_c`。
- 全量重生成（mingw + 本地解包 sysroot）后 `reapply_hand_edits.py` 退出 0；
  `.inc` 差异经脚本核对仅为变量模板新增 + parser 命名空间搬移 + 头注释计数。
- 全量测试覆盖：21 个受影响库的 `tests/*.cpp` 各补一条变量模板断言
  （align/any/asio/callable_traits/cobalt/compat/container/decimal/geometry/
  hof/math/mqtt5/multiprecision/outcome/parser/poly_collection/type_traits/
  unordered/variant2，pfr/hana 已于首轮覆盖）。每条断言先用对应 Boost 头
  做 `-fsyntax-only` 校验语义，再用 clang `--precompile` 构建模块闭包 + 消费者
  做端到端验证；asio/cobalt/container/outcome/parser/poly_collection 等含编译
  TU 的库消费者仅做 `-fsyntax-only`（链接由 CI 覆盖），hof 的 `if_c` 断言额外
  编译运行通过。

## 7. 涉及文件

- `scripts/gen_exports.py`、`scripts/boost_common.py`
- `scripts/patchs/decimal.patch`、`scripts/patchs/parser.patch`
- `src/gen_exports/*.inc`、`src/gen_exports/{graph,outcome,wave}.deps`
- `src/{graph,outcome,wave}.cppm`
- `tests/pfr.cpp`、`tests/hana.cpp`
- `docs/architecture.md`、`docs/zh/architecture.md`、release notes、consolidated design
