# GitCode 镜像同步与 Release 发布 (2026-09-23)

> 日期: 2026-09-23 · 状态: 已实现 · 分支 `b1.91.0wdev`
> 范围: 在 `.github/workflows/release.yml` 的 tag 发布流程后追加 `mirror` job ——
> 强制同步全部分支/tag 到中国大陆镜像 `gitcode.com/ZheFeng7/boost-module`，
> 并用 GitCode CLI 在镜像站发布与 GitHub 主站内容一致的 Release（Release Note 用中文版）。
> 关联: `README_zh.md` / `docs/zh/*` 中给出的镜像地址；
> GitCode CLI 文档 https://gitcode.com/atomgit-cli/cli 。

## 1. 背景

主站托管在 GitHub (`ZheFeng7110/boost-module`)，另有一个面向中国大陆的 GitCode
镜像 `ZheFeng7/boost-module`。此前镜像靠人工推送，容易落后于主站（实测镜像
`b1.91.0wdev` 落后于主站）。需要在每次发版后自动：

1. 把**所有分支与 tag** 强制同步到镜像（镜像始终等于主站的 ref 视图）；
2. 在镜像站发布 Release，**标题 / 预发布状态 / 附件与 GitHub 完全一致**，
   仅 Release Note 使用中文版 `docs/zh/release_notes/<tag>.md`。

触发沿用现有 Release workflow 的 `push: tags: ["*"]`，用一个独立的 `mirror`
job 承接，`needs: [release]`，保证 GitHub Release 已生成后再同步。

## 2. 关键结论 / 决策

### 2.1 同步：不使用 `git push --mirror`，改用显式镜像 refspec

GitCode CLI **没有**镜像/强制推送命令（`gc repo sync` 是「同步目录并开 PR」，
不是镜像）。同步必须走 `git`。

`actions/checkout`（`fetch-depth: 0`）的 ref 布局是：分支落在
`refs/remotes/origin/*`，tag 落在 `refs/tags/*`。若直接 `git push --mirror`：

- 会把 `refs/remotes/origin/*` **原样**推到镜像的 `refs/remotes/origin/*`；
- `refs/remotes/origin/HEAD`（symref）会被推成镜像上的 `refs/heads/HEAD`。

因此改为显式 refspec + `--prune`：

```bash
git fetch --prune --force origin \
  "+refs/heads/*:refs/remotes/origin/*" \
  "+refs/tags/*:refs/tags/*"
git update-ref -d refs/remotes/origin/HEAD || true
git push --force --prune "$MIRROR_URL" \
  "+refs/remotes/origin/*:refs/heads/*" \
  "+refs/tags/*:refs/tags/*"
```

- 分支：`refs/remotes/origin/*` → `refs/heads/*`，强制覆盖；
- tag：`refs/tags/*` → `refs/tags/*`，强制覆盖；
- `--prune`：删除镜像上已被主站删除的分支与 tag（已本地验证 `--prune` 对
  tag refspec 同样生效）；
- 先删 `origin/HEAD`：否则通配 refspec 会把它当普通 ref 推成 `refs/heads/HEAD`。

先做一次显式 `git fetch` 是为了不依赖 checkout 的 fetch 行为，确保拿到全部分支。

### 2.2 git 认证：overt HTTPS 用 Basic `oauth2:<PAT>`

GitCode 的 REST API 认 `Authorization: Bearer`，但 **git-over-HTTPS 端点拒绝
Bearer**，只接受 HTTP Basic，用户名固定 `oauth2`、密码为 PAT（与 GitLab/TGit
同类约定）。因此用一次性（仅本条命令）的 URL 级 extraHeader：

```bash
AUTH="$(printf 'oauth2:%s' "$GITCODE_TOKEN" | base64 -w0)"
git -c "http.https://gitcode.com/.extraHeader=Authorization: Basic ${AUTH}" push ...
```

相对把 token 写进 remote URL，extraHeader 不会持久化到 `.git/config`，也不会
进入 git 的错误输出；credential 只存在于该进程内存。

### 2.3 发布：用 GitCode CLI（固定版本 + npm）

`mirror` job 通过 npm 安装 CLI，固定 `atomgit-cli@0.14.0`：

```bash
npm install --no-save --ignore-scripts atomgit-cli@0.14.0
```

- npm 包内置全平台二进制（Linux/macOS/Windows），`--ignore-scripts` 关闭
  lifecycle 脚本，不做隐式下载；
- 装到 `$RUNNER_TEMP/gc-cli`，把 `node_modules/.bin` 加入 `$GITHUB_PATH`，
  避免全局安装的权限问题；
- 命令加 `--no-interactive`，声明 CI 非交互；`GC_NO_UPDATE_CHECK=1` 关闭后台
  更新检查。

发布两步：

```bash
gitcode --no-interactive release create "$TAG" [--prerelease] \
  -R ZheFeng7/boost-module --title "$TAG" --notes-file /tmp/release_notes_zh.md
gitcode --no-interactive release upload "$TAG" target/dist/* -R ZheFeng7/boost-module
```

### 2.4 附件取自主站 Release，而非重新打包

`package-source.sh` 产物含时间戳，重跑不会逐字节复现。为满足「内容与主站相同」，
`mirror` job 用 `gh release download "$TAG"` 把主站 Release 的附件下到
`target/dist/` 再上传，保证与主站**同一份字节**。

### 2.5 环境机密

`GITCODE_TOKEN` 保存在 GitHub Environment 机密中，job 必须声明
`environment: GITCODE_TOKEN` 才能读到该机密（环境名与机密名相同）。

## 3. 流程

```
push tag
  └─ release:  git notes(英) → package-source.sh → gh release create (GitHub)
  └─ mirror (needs: release, environment: GITCODE_TOKEN):
       1. checkout(fetch-depth: 0)
       2. 拷 docs/zh/release_notes/<tag>.md → /tmp/release_notes_zh.md
       3. 装 gitcode CLI (npm, 0.14.0)
       4. gh release download <tag> → target/dist/
       5. git push --force --prune 全分支/tag → gitcode 镜像
       6. gitcode release create（中文 note + 预发布标志）
       7. gitcode release upload 附件
```

## 4. 验证

- `actionlint .github/workflows/release.yml` 通过；
- 同步 refspec 与 `--prune`（含对 tag 的删除、`origin/HEAD` 处理）已用本地
  bare 仓对手工复现实验验证；
- `gitcode` 0.14.0 的 `release create/upload` 参数以 `--help` 核对，
  `-R/--notes-file/--title/--prerelease/--no-interactive` 均存在。

## 5. 风险与边界

- **非幂等**：GitHub 侧 `gh release create` 与镜像侧 `release create` 在 tag
  已有 Release 时都会失败（GitCode 官方 API 无删除 Release 接口），与本改动
  之前的行为一致；重跑需先手动删 Release。
- **分支保护**：镜像若对目标分支启用保护，`--force --prune` 会被拒绝；镜像
  作为只读镜像应保持无保护。
- 未处理镜像仓库尚未创建的情况（视为已存在）。
