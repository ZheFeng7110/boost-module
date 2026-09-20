# 内部链接对象导出补全 — range / multi_array / accumulators / mqtt5

> 日期: 2026-09-20 · 状态: 已实施
> 关联: `docs/zh/architecture.md` §4.1 已知限制 (原第 2、3 条)、
> `.agents/docs/2026-09-08-consolidated-design.md` §6.2 / §7.2#4-#5。

## 1. 背景

`architecture.md` §4.1 曾披露两条消费者须知限制:

1. **匿名命名空间 forwarder 不导出** — range pipe 语法 (`vec | reversed`)、
   multi_array `boost::extents` / `boost::indices`。
2. **内部链接 constexpr 对象不可导出** — 残余面 accumulators `extract::*`
   (需用 `extract_result<>`)、mqtt5 `prop::*` 常量 (需用
   `std::integral_constant`)。

两者同一根因: C++ 命名空间作用域的 `const` / `constexpr` 对象默认**内部
链接**; 位于匿名命名空间时还额外失去限定名 (`bc.namespace_chain` 返回
`[]`, `bc.qualified_name` 返回 `""`)。生成器 `gen_exports.py` 的
`collect_candidates` 同时以 `bc.linkage_ok` 与限定名过滤, 于是这些实体被
静默丢弃, 模块面自然缺名。

## 2. 方案

沿用既有 vendored 修补族 (§6.2「命名命名空间 + inline 变量」), 本任务四库
全部是**用户 API**, 因此保留其公开命名空间, 仅补 `inline` 取得外部链接:

| 库 | 修改 | 公开拼写 |
|---|---|---|
| range | 12 个 `adaptor/*.hpp` 的匿名命名空间 forwarder 对象 → `inline const ...` | `boost::adaptors::reversed` / `filtered` / `transformed` / `indirected` / `map_keys` / `map_values` / `replaced` / `replaced_if` / `strided` / `tokenized` / `uniqued` / `adjacent_filtered` / `adjacent_filtered_excl` / `ref_unwrapped` |
| multi_array | `base.hpp`: 去掉匿名命名空间, `extents` / `indices` 改 `inline` 变量 | `boost::extents` / `boost::indices` |
| accumulators | 43 个头文件、66 个命名空间级 `extractor<...> const X = {};` → `inline extractor<...> const X = {};` | `boost::accumulators::extract::*` (并连带使 `using extract::X;` 注入的 `boost::accumulators::X` 可导出) |
| mqtt5 | `property_types.hpp` 的 `DEF_PROPERTY_TRAIT` 宏末行 `constexpr` → `inline constexpr` | `boost::mqtt5::prop::*` (27 个) |

非公开 detail 实体无消费者需求, 未纳入。

`inline` 同时解决跨 TU 定义合并, 替代原先匿名命名空间「每 TU 一份」的
作用; 语义与拼写与上游一致 (ADL/运算符查找不受对象所在命名空间影响)。

## 3. 生成器与产物

生成器**无需改动**: 实体具备外部链接与合法限定名后, 既有
`collect_candidates` / `collect_injections` 自动收集, `emit_inc` 按
`boost::` 限定名排序产出。

受影响导出清单 (`src/gen_exports/*.inc`, 实体数变化; `.deps` 四库均不变):

| 库 | `.inc` entities |
|---|---|
| range | 468 → **482** (+14) |
| multi_array | 51 → **53** (+2) |
| accumulators | 585 → **717** (+132 = 66 `extract::*` + 66 `boost::accumulators::*` using 注入) |
| mqtt5 | 308 → **335** (+27) |

其余库产物零变化。

### 3.1 复现 (重生成 → 重放手编)

```bash
LIBCLANG_PATH=<llvm lib dir> uv run scripts/gen_exports.py --emit-cppm
uv run scripts/reapply_hand_edits.py
```

vendored 修补文件:

- `scripts/patchs/range_adaptors.patch` (新增, 12 文件)
- `scripts/patchs/multi_array.patch` (新增, 1 文件)
- `scripts/patchs/accumulators.patch` (新增, 43 文件)
- `scripts/patchs/mqtt5.patch` (追加 `property_types.hpp` hunk, 原
  `async_traits.hpp` hunk 保持)

`reapply_hand_edits.py` 的 `VENDORED_PATCHES` 已登记三个新名字; 全部幂等
(应用后反向 apply 检测跳过)。

> 说明: 生成器 `_parse_bundle` 的 clang++ gate 未传 `_WIN32_WINNT` /
> `WIN32_LEAN_AND_MEAN` (仅 `BC.CLANG_ARGS` 传), 在 pinned MinGW sysroot
> 下会把 `boost/atomic.hpp` 等误判 prune。该缺陷早于本任务 (sysroot
> bootstrap 引入), 与本任务四库无关 (四库在既有 gate 下逐字节复现
> HEAD), 故本次不改; 完整重生成若在 atomic 等库处 reapply 失败, 属该
> 既有缺陷, 不在本任务范围。

## 4. 测试

`tests/{range,multi_array,accumulators,mqtt5}.cpp` 改用新拼写:

- range: `v | boost::adaptors::reversed`、`v | boost::adaptors::filtered(...)`
- multi_array: `boost::multi_array<double,2> e(boost::extents[2][3])`,
  `decltype(boost::indices)` 断言
- accumulators: `ba::extract::count(acc)` 等 + `ba::mean(acc)` (注入拼写)
- mqtt5: `props[m5::prop::session_expiry_interval]` (不再用
  `std::integral_constant`)

## 5. 残留

- consolidated design §7.2#4 另列 hana 字面量变量模板; 变量模板导出已由
  2026-09-17/A1+A2 处理, hana 变量模板 (`int_c` 等) 已在模块面。本任务
  仅收口 accumulators/mqtt5 两个对象面残余。
- 「内部链接对象不可导出」作为 C++ 语言事实仍然成立; 凡上游未加 `inline`
  的 `const`/`constexpr` 公开对象, 仍需逐个 vendored 改造或提供替代拼写。
- 生成器 gate 的 `_WIN32_WINNT` 缺陷见 §3.1 注。
