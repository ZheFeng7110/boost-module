# GitHub Release 发布流程 (runbook)

> 适用于任意版本的发布, 与具体版本无关。
> 版本命名: 六段纯数字 `v<boost版本>.<封装版本>`, 下文以 `<tag>` 指代待发布版本的 tag 名
> (如 `v1.92.0.0.0.0`), release notes 文件名为 `docs/release_notes/<tag>.md`
> (带 `v` 前缀, 如 `v1.92.0.0.0.0.md`)。
> `<version>` 指去掉开头 `v` 后的同一字符串 (如 `1.92.0.0.0.0`), 用于 CHANGELOG 条目 ——
> 也是 `[package].version` / 下游 `version = "..."` 必须填写的值。

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
- [ ] `docs/release_notes/<tag>.md` 已就绪 (内容清单 / 已知限制 /
      报告问题指引), `CHANGELOG.md` 已有对应版本条目。
- [ ] 用户确认可以打 tag。

## 1. 干净 checkout 下 tag 构建演练 (打 tag 前必须)

tag 一旦打上就指向不可变快照, 先在临时目录模拟"消费者 clone 后构建":

```bash
git clone <repo-url> "$TEMP/boost-module-release-drill"
cd "$TEMP/boost-module-release-drill"
git checkout <待发布 commit>

# 本地腿 (llvm/msvc 默认) 全量验证
mcpp build
mcpp test                 # 默认集 smoke 全绿
mcpp run -p default_usage # examples
```

任一步失败 → 回到开发分支修复后重跑演练, **不得带病打 tag**。

## 2. 打 tag

```bash
# 在开发分支上, 待发布 commit 处
git tag -a <tag> -m "<版本说明一句话, 如 Boost X.Y.Z C++23 named modules wrapper vX.Y.Z>"
git push origin <tag>
```

- 一律用 **annotated tag** (携带 tagger / 日期 / message)。
- tag 名与 release notes 文件名 (均带 `v` 前缀) 严格一致; CHANGELOG 条目用去掉
  `v` 的同一版本号。
- **推送 tag 即自动触发 release workflow** (见 §3); 推送前必须确保
  `docs/release_notes/<tag>.md` 存在 —— 缺失时 workflow 直接失败。
- 误打未推送的 tag: `git tag -d <tag>`; 已推送的 tag 原则上**不删除不改写**,
  需撤回时发新版本并在 release notes 中标注废弃。

## 3. 创建 GitHub Release

[`.github/workflows/release.yml`](.github/workflows/release.yml) 在 tag 推送后
**自动创建**: workflow 提取 `docs/release_notes/<tag>.md` 作为 release 正文
(**文件缺失则直接报错失败**), 运行 `scripts/package-source.sh` 打出源码包
(`.zip` / `.tar.gz` / `.tar.xz` / `.7z` + `.sha256` 校验文件) 并作为附件上传,
release 标题为 `Release <tag>`; 以 `-preview` 结尾的 tag 自动加 prerelease 标记。

在 Actions 页的 `Release` workflow 中观察运行结果。仅当修复前置条件后自动化
仍失败时, 才手动兜底:

```bash
bash scripts/package-source.sh
gh release create <tag> \
  --title "Release <tag>" \
  --notes-file docs/release_notes/<tag>.md \
  target/dist/* \
  --prerelease          # 预览版必须; 正式版去掉本项
```

- 正文直接复用 `docs/release_notes/<tag>.md` (发布后可在
  GitHub 界面微调措辞, 但仓库内文件仍是权威版本)。
- **不上传二进制附件**: 附件仅限 `scripts/package-source.sh` 产出的源码包
  (zip / tar.gz / tar.xz / 7z 及 sha256 校验文件); 消费者正常经 git dep /
  (未来) mcpp package index 获取源码。GitHub 自动生成的
  "Source code (zip/tar.gz)" 链接仍与归档并存。
- Release 页面 Topics 标签 (如可用): `cpp` `cpp23` `boost` `modules`。

## 4. 发布后收口

- [ ] Release 页面可见, notes 渲染正常, 指向的 tag commit 正确; `Release`
      workflow 运行成功, 源码包 (zip / tar.gz / tar.xz / 7z + sha256) 已挂到 release 附件。
- [ ] 消费者 probe: 临时工程以 `git = ... tag = <tag>` 依赖声明走一遍
      build+run (architecture.md §2.1 的三种配置中至少默认集一种)。
- [ ] `CHANGELOG.md` 与 `docs/release_notes/` 与实际发布一致
      (如 GitHub 界面改过措辞, 回同步到仓库内文件)。
- [ ] 开发分支 README / architecture.md 中的示例 tag 更新为新 tag
      (仅当下一次版本仍是预览口径; 正式版发布时另走 T3 registry 对接)。
- [ ] 相关计划文档勾选对应任务项 (如有)。

## 5. 预览版与正式版差异

| 项 | 预览版 | 正式版 |
|---|---|---|
| `--prerelease` | 加 (workflow 对 `-preview` tag 自动设置) | 不加 |
| tag 后缀 | `-preview` | 无 (如 `v1.92.0.0.0.0`) |
| mcpp package index (T3) | 不上架 | boost.lua 对接 + registry 消费 probe 必做 |
| 已知限制披露 | 全量 | 缩减为仍有效的条目 |
