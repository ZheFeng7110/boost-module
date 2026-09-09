# GitHub Release 发布流程 (runbook)

> 日期: 2026-09-09 · 适用: 预览版及后续所有版本 · 版本命名 `b<boost版本>w<封装版本>`
> 首个适用版本: `b1.91.0w0.0.0-preview` (T4 收口, 见
> [发布预览版计划](../.agents/plan/2026-09-08-release-preview-plan.md))

## 0. 前置条件 (发布门槛)

- [ ] CI 四腿 (windows-clang-msvc / linux-gcc / linux-llvm / macos-llvm-arm64)
      对待发布 commit 全绿, A/B 两组门禁均通过。
- [ ] `uv run scripts/gen_features.py --check` 通过 (features 块与
      features.lst 零漂移)。
- [ ] `uv run scripts/reapply_hand_edits.py` 幂等复跑零改动
      (vendored 修补全部可回放)。
- [ ] 计数复核: `src/*.cppm` = 模块数、`scripts/features.lst` = feature 数、
      `[features].default` = 默认闭包, 与 CHANGELOG / release notes 中
      数字一致。
- [ ] `docs/release_notes/<version>.md` 已就绪 (内容清单 / 已知限制 /
      报告问题指引), `CHANGELOG.md` 已有对应版本条目。
- [ ] 用户确认可以打 tag (预览版流程曾约定"先不打 tag")。

## 1. 干净 checkout 下 tag 构建演练 (打 tag 前必须)

tag 一旦打上就指向不可变快照, 先在临时目录模拟"消费者 clone 后构建":

```bash
git clone <repo-url> "$TEMP/boost-module-release-drill"
cd "$TEMP/boost-module-release-drill"
git checkout <待发布 commit>

# 本地腿 (llvm/msvc 默认) 全量验证
mcpp build
mcpp test                 # 默认集 smoke 全绿 (当前口径 141)
mcpp run -p default_usage # examples
```

任一步失败 → 回到开发分支修复后重跑演练, **不得带病打 tag**。

## 2. 打 tag

```bash
# 在开发分支上 (b1.91.0wdev), 待发布 commit 处
git tag -a b1.91.0w0.0.0-preview -m "Preview release: Boost 1.91.0 C++23 named modules wrapper v0.0.0"
git push origin b1.91.0w0.0.0-preview
```

- 一律用 **annotated tag** (携带 tagger / 日期 / message)。
- tag 名与 release notes 文件名、CHANGELOG 条目严格一致。
- 误打未推送的 tag: `git tag -d <tag>`; 已推送的 tag 原则上**不删除不改写**,
  需撤回时发新版本并在 release notes 中标注废弃。

## 3. 创建 GitHub Release

```bash
gh release create b1.91.0w0.0.0-preview \
  --title "b1.91.0w0.0.0-preview" \
  --notes-file docs/release_notes/b1.91.0w0.0.0-preview.md \
  --prerelease          # 预览版必须; 正式版去掉本项
```

- 正文直接复用 `docs/release_notes/<version>.md` (预览版发布后可在
  GitHub 界面微调措辞, 但仓库内文件仍是权威版本)。
- **不上传二进制附件**: 本项目是源码包, 消费者经 git dep / (未来)
  mcpp package index 获取; Source code (zip/tar.gz) 由 GitHub 自动生成。
- Release 页面 Topics 标签 (如可用): `cpp` `cpp23` `boost` `modules`。

## 4. 发布后收口

- [ ] Release 页面可见, notes 渲染正常, 指向的 tag commit 正确。
- [ ] 消费者 probe: 临时工程以 `git = ... tag = <tag>` 依赖声明走一遍
      build+run (architecture.md §2.1 的三种配置中至少默认集一种)。
- [ ] `CHANGELOG.md` 与 `docs/release_notes/` 与实际发布一致
      (如 GitHub 界面改过措辞, 回同步到仓库内文件)。
- [ ] 开发分支 README / architecture.md 中的示例 tag 更新为新 tag
      (仅当下一次版本仍是预览口径; 正式版发布时另走 T3 registry 对接)。
- [ ] 计划文档勾选对应任务项。

## 5. 正式版差异 (相对预览版流程)

| 项 | 预览版 | 正式版 |
|---|---|---|
| `--prerelease` | 加 | 不加 |
| tag 后缀 | `-preview` | 无 (`b1.91.0w0.0.0`) |
| mcpp package index (T3) | 不上架 | boost.lua 对接 + registry 消费 probe 必做 |
| 已知限制披露 | 全量 | 缩减为仍有效的条目 |
