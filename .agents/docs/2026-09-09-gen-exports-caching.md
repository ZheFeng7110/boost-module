# gen_exports.py 增量缓存设计（方案 A + C）

日期：2026-09-09
关联：`gen_exports.py` 全量运行约 1.5 小时的性能优化（第一阶段）。

## 背景与目标

`python scripts/gen_exports.py` 全量运行约 1.5 小时。每个库的处理流程是
`_parse_bundle`（最多 6 轮 `clang++ -fsyntax-only` gate + 一次 libclang 完整
parse）加 Python AST 分析，全程串行。而 `.inc`/`.deps` 输出是输入的确定性
函数（文件头注释承诺 bit-identical），输入不变时重复生成纯属浪费。

本阶段目标：**输入未变的库完全跳过**（方案 A），**gate 结果缓存**（方案 C）。
并行化（B）、parse 选项调整（D）、Python 热路径微优化（E）明确排除在外。

## 缓存布局

```
scripts/_gen_exports-cache/     # .gitignore 已加入
  <lib>.skip.json               # 方案 A：增量跳过判据 + 声明快照
  <lib>.gate.json               # 方案 C：clang++ gate 结果
  bundles/<lib>.cpp             # bundle TU（原 target/gen/bundles/）
```

`gen_audit.py` 的 bundle 读取路径改为优先缓存目录，回退旧位置。

## 方案 A：按库增量跳过

### 缓存键（`_skip_key`）

一个 sha256，覆盖输出确定性地依赖的全部输入：

| 输入 | 说明 |
|---|---|
| `code` | `gen_exports.py` + `boost_common.py` 的内容哈希（生成逻辑变更即失效） |
| `bundle` | 初始 GFM include 列表文本（含 `GMF_OVERRIDE` 应用后的结果） |
| `closure` | bundle 传递闭包内**所有 boost 头文件的内容哈希**（任一 detail 头被改都能失效） |
| `extra` | `EXTRA_DEFINES[lib]` |
| `clang_args` | `bc.CLANG_ARGS` |
| `curated` | `scripts/curated/<lib>.txt` 内容 |
| `full_closure` / `no_body_deps` | 输出语义开关 |
| `libs` | `--libs` 子集（claiming first-wins 依赖处理集合） |
| `up:<u>:<key>` | 每个上游 target 库（`dep_graph` 闭包）的键，上游重生成即失效下游 |

上游键按 `topo_order` 依赖方向递归计算；处于 include 环中的库（上游键不可得）
永远不缓存（保守正确，最坏退化为不命中）。

### 命中条件与命中动作

命中条件：`<lib>.skip.json` 的 `key` 与当前重算键一致，且输出工件存在
（`<lib>.inc` 必须存在；`<lib>.deps` 存在性须与缓存记录的 `deps_present` 一致）。

命中动作：

1. 重放声明快照，使下游 miss 库看到与全量运行完全相同的 first-wins 状态：
   - `claims`（USR → 处理库）→ `claimed`（setdefault）
   - `inject_claims`（qname → 处理库）→ `claimed_inject`（setdefault）
   拓扑顺序保证上游先重放，与原执行的 setdefault 序列语义一致。
2. 复用缓存的 gate 剪枝后 GFM 列表（供 `--emit-cppm` 使用）。
3. 复用缓存的 summary 条目写入 `gen_report.json`。
4. 不重跑 gate、libclang parse 与任何分析。

### pass-2 交互

`merge_body_edges` 可能向既有 `.deps` 追加边，使所有已缓存键过时。策略
（保守）：**本次运行存在 pass-2 新增边 → 删除全部 `*.skip.json`，本运行不写
缓存**，下次运行全量重算后重建。gate 缓存不受影响（键与 .deps 无关）。

## 方案 C：gate 结果缓存

`<lib>.gate.json`，键为初始 bundle 文本 + gate 命令行 + `EXTRA_DEFINES` +
clang++ 版本 + **闭包内容哈希**（头文件内容变化可能改变 gate 结果）。

- 命中 `ok: true` → 跳过整个剪枝循环（最多 6 轮 clang++），直接重放剪枝后的
  GFM 集并进入 libclang parse。
- 命中 `ok: false` → 直接重放失败（含缓存的 stderr 头部），不再重跑。
- 未命中 → 原有循环，结束后写缓存。

libclang parse 本身不缓存（AST 缓存属于方案 B/D 范畴）。

## 实现注意（性能）

闭包哈希最初直接实现时暴露出两个 Windows 文件系统调用热点，均已 memoize
（`_hdr_info`/`_norm`/`_file_hash`/`_boost_includes`）：`Path.resolve()` 与
`Path.is_file()` 在闭包遍历的量级（数千头文件 × 每库）下耗时以分钟计。
memoize 后每文件的哈希/include 解析/存在性在全进程只做一次。

当前残余固定开销：即便全部命中，键预计算（`dep_graph` + 97 个库的
`gfm_headers_of` 全文读取 + 闭包哈希）约 3 分钟——相对原 1.5 小时可忽略，
进一步压低归入方案 E。

## 开关

- `--no-cache`：禁用两种缓存的读与写（完全旧行为），调试用。
- `--scan` 不经过任何缓存。

## 验收结果

1. `--libs crc` 两连跑：第二跑 `skipped crc (cache hit, exported=44)`，
   `.inc` 与 `gen_report.json` 和首跑 byte-identical（`diff` 通过）。
2. 头文件内容加一行注释 → miss 并重算；还原 → 重算一次后恢复命中。
3. `--no-cache` 正常走全量路径。
4. `git status` 仅缓存目录（已忽略）与预期源码变更。
5. 全量运行（1.5h）的 bit-identical 验收留待用户下次全量生成时确认
   （`git diff src/gen_exports` 应为空）。

## 预期收益

- 稳态 rerun（无输入变化）：1.5h → 约 3 分钟（键预计算），后续可再优化。
- 单库/少库迭代：仅该库及其下游重算（约 40s~数分钟/库的 parse+分析），
  gate 缓存另省每库最多 6 轮 clang++ 语法检查。
- 全量冷缓存运行不变（与原耗时相当，略增键计算 ~3 分钟）。
