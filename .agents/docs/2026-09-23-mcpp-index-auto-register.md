# 发布后自动登记 mcpp-index 并开 PR (2026-09-23)

> 日期: 2026-09-23 · 状态: 已实现 · 范围: 在 `.github/workflows/release.yml` 中追加
> `publish-index` job —— 当 `release`（GitHub 主站）与 `mirror`（GitCode 镜像站）
> 两个 job 都成功后，在 fork `ZheFeng7110/mcpp-index` 上新建分支，
> 向 `pkgs/z/ZheFeng7110.boost.lua` 前插新版本，再用 GitHub CLI 向
> 上游 `mcpplibs/mcpp-index` 开 PR。
> 关联: `.agents/docs/2026-09-23-gitcode-mirror-release.md`（镜像站流程）、
> mcpp-index 的收录流程 `.agents/skills/add-mcpp-index-package/SKILL.md`。

## 1. 背景

每次发版后，除了 GitHub 主站与 GitCode 镜像站的 Release，还需要把新版本登记进
`mcpp-index`（`mcpp add ZheFeng7110.boost@<版本>` 的解析来源）。此前这一步靠人工：
本地克隆 `~/prjs/mcpp-index`，手改 `pkgs/z/ZheFeng7110.boost.lua`，push 分支，
向上游开 PR。本改动把它自动化。

`ZheFeng7110.boost` 是 mcpp-index 中的 Form A 描述符：`xpm` 下
`linux` / `macosx` / `windows` 三个平台各列出一批
`["<xpm key>"] = { url = { GLOBAL=…, CN=… }, sha256=… }`。包是平台无关的源码
tarball，三个平台指向同一份字节、同一个 sha256。

## 2. 关键结论 / 决策

### 2.1 触发时机：`needs: [release, mirror]`

新 job `publish-index` 依赖 `release`（产生 GitHub Release 与附件）与
`mirror`（GitCode 镜像 Release）。两者都成功后才登记，保证描述符里的 GLOBAL /
CN 两个下载地址都已经可用。

### 2.2 跳过预览版

`-preview` 标签只用于发布 GitHub/GitCode Release，不登记进公共索引
（`if: ${{ !contains(github.ref_name, '-preview') }}`）。只有稳定 tag 才走
索引登记，避免公共索引出现预发布版本。

### 2.3 跨仓库写权限：专用 PAT

`GITHUB_TOKEN` 只对当前仓库（`ZheFeng7110/boost-module`）有权限，无法 push 到
fork、也无法向上游开 PR。因此引入仓库机密
`BOOST_MODULE_PR_TO_MCPP_INDEX_GH_TOKEN`（PAT，需对 fork 有 contents:write、
对上游有 pull_requests:write；公开仓库读权限亦满足 fetch upstream）。checkout
fork 与 `gh pr create` 都用它。

### 2.4 版本在前、旧版本在后；只加版本条目

按需求，新版本块插入到每个平台表的**最前面**，旧版本原样保留。描述字符串
（`description`）与文件头注释里的版本说明**不自动改写** —— 只增条目，不改文字，
避免脚本猜测并重写人工措辞。

### 2.5 描述符更新逻辑独立成脚本

`scripts/update_mcpp_index.py`（仅标准库）：

- 按行扫描，删除已存在的同 key 块（幂等：重跑只会替换，不会重复）；
- 用平台名锚定 `        linux = {` / `macosx = {` / `windows = {` 三处，把新块
  插到其后；
- 新块由 `--key/--global-url/--cn-url/--sha256` 渲染，缩进与现有文件一致
  （key 12 空格、`url` 16、`GLOBAL`/`CN` 20）。

删除逻辑按缩进识别块尾：版本块的收尾 `},` 与开头的 key 同缩进，而嵌套的
`url = {` 收尾更深，因此不会被误判。

### 2.6 分支基于 upstream/main

checkout fork 后加 `upstream` remote 并 `git fetch upstream main`，从
`upstream/main` 切出 `boost-module-<tag>` 分支。这样即使 fork 的 `main` 落后，
PR 也能干净地应用到当前上游。push 用 `--force`，便于从失败重跑修复残留分支。

### 2.7 PR

`gh pr create --repo mcpplibs/mcpp-index --base main --head ZheFeng7110:<branch>`，
标题 `Zhefeng7110.boost: Add <xpm key>`，正文给出主站/镜像站 release 链接与描述符
路径。

## 3. 流程

```
push tag (非 -preview)
  └─ release:  GitHub Release
  └─ mirror:   GitCode 镜像 Release
  └─ publish-index (needs: [release, mirror]):
       1. actions/checkout（boost-module，取脚本）
       2. gh release download <tag> -p '*.tar.xz' → target/dist/
       3. sha256sum → 新版本的 sha256
       4. actions/checkout ZheFeng7110/mcpp-index → mcpp-index/（PAT）
       5. cd mcpp-index；add upstream；fetch upstream main；
          switch -c boost-module-<tag> upstream/main
       6. python3 scripts/update_mcpp_index.py --file pkgs/z/ZheFeng7110.boost.lua ...
       7. git add / commit / push --force origin <branch>
       8. gh pr create → mcpplibs/mcpp-index
```

新版本 URL 由 tag 推导（与 `scripts/package-source.sh` 的产物名一致）：

- GLOBAL: `https://github.com/ZheFeng7110/boost-module/releases/download/<tag>/boost-module-<tag>.tar.xz`
- CN:     `https://gitcode.com/ZheFeng7/boost-module/releases/download/<tag>/boost-module-<tag>.tar.xz`

xpm key 为去掉前导 `v` 的 tag（如 `v1.91.0.0.2.0` → `1.91.0.0.2.0`）。

## 4. 验证

- `scripts/update_mcpp_index.py` 在 `ZheFeng7110.boost.lua` 副本上运行，diff 为
  三个平台各前插一个新块、旧块不动；重复运行只替换不重复。
- `mcpp xpkg parse` 解析结果 `parse OK`，且版本顺序为新版本在前。
- 用本地仓库模拟 fork/upstream 走完整 git 序列（fetch upstream main → switch →
  脚本 → commit），`git diff --stat` 仅 `pkgs/z/ZheFeng7110.boost.lua` 增加 21 行。
- 工作流 YAML 可被 PyYAML 解析；三个 `run` 块通过 `bash -n`。
- 未做：未在真实 GitHub 上跑通 PAT push / PR（需先创建机密）。

## 5. 前置条件与风险

- **前置**：需在仓库中添加机密 `BOOST_MODULE_PR_TO_MCPP_INDEX_GH_TOKEN`。本 job
  未声明 `environment`，因此它必须是**仓库机密**（若存为环境机密，需给 job 加
  `environment:`）。
- **非幂等（PR）**：同一 tag 重跑时分支可 force 修复，但 `gh pr create` 在该分支
  已有 open PR 时会失败；需先关旧 PR。
- **CI 测试仍钉旧版本**：本次改动只更新描述符，不改
  `tests/examples/boost-module/mcpp.toml` 里的 `version = "1.91.0.0.1.0"`，因此
  index CI 的选择性测试仍验证旧版本。如需让 CI 覆盖新版本，应另行 bump 该 pin。
