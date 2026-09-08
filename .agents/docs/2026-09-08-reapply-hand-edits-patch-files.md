# reapply_hand_edits.py 补丁文件化重构（2026-09-08）

## 背景

`scripts/reapply_hand_edits.py` 此前用 Python `patch(rel, old, new)` 函数承载
全部字符串补丁（226 处调用，脚本 3100+ 行），锚点文本内嵌在 Python 源码里，
可维护性差。本次重构把补丁内容与脚本逻辑分离。

## 新结构

- `scripts/patchs/<module>.patch` — 一个模块一个统一 diff 文件（52 个文件，
  覆盖 75 个目标文件）。deps/boost 的 vendored 头按所属 Boost 库命名
  （`archive/` → `serialization.patch`，`numeric/ublas/` → `ublas.patch`）；
  src 侧按模块名命名（`core.patch` 含 `core.cppm` + `core.inc` 的 hunk）。
  多目标模块的 hunk 合入同一文件，`git apply` 原生支持多文件 diff。
- `scripts/reapply_hand_edits.py` — 瘦身至 ~490 行：
  - `apply_patch_file(name)`：`git apply` 应用 `scripts/patchs/<name>.patch`；
    已应用检测用 `git apply --check --reverse`（反向可应用 ⇒ 内容已包含），
    幂等。`json/core/io` 为宽容项（旧 `required=False` 语义：json.cppm 的
    注释从未入库；core/io 的 .cppm 随后即被 git restore 覆盖）。
  - `guard_entity_lines` / `ensure_file` / `restore_from_git` 保持原样：
    前者的包裹行集依赖重生成后的 .inc 内容（非固定锚点），后两者语义不变。
  - 仅保留一个 `patch()` 兜底：`type_erasure.inc` 的 C4 实体归属锚点
    （锚点是否存在取决于重生成后的 first-wins 归属，无法表达为静态 diff）。

## 重生成 patch 文件的方法

对 freshly 重生成的文件施加手编后，`git diff -- <file>`（以重生成态为基准）
保存为 `scripts/patchs/<module>.patch`。hunk 内保留解释性注释的惯例不变。

## 验证

1. 反向检查：52 个 patch 全部 `git apply --check --reverse` 通过（当前提交态
   = 已应用；json/core/io 容忍例外）。
2. 正向回放：转换脚本从当前提交态逆向重建"重生成原貌"，在干净临时目录
   逐个 `git apply` 全部 patch，75 个文件与预期态逐字节一致。
3. 幂等复跑：新脚本对当前树全量跑一遍，除脚本本身外 `git status` 零改动。

## 已知取舍

- 死锚点（`required=False` 且重生成后永不重现：iostreams/utility 的策展删除、
  `io.inc` 的 ostream_put）不再保留；git-restore 覆盖的 scope.cppm 锚点同弃。
- 补丁以 hunk 上下文匹配（默认 3 行上下文），对重生成输出的敏感性等同旧
  锚点机制；`gen_exports.py` 输出格式变化时需同步再生成对应 .patch。
