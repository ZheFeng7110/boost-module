# 生成脚本幂等性 CI

## 目标

为仓库中会产生已提交产物的脚本增加跨平台门禁，确保从干净 checkout
运行生成流程后，工作树不会出现 tracked diff。生成脚本可以继续使用
`target/` 和 `scripts/_deps/` 下的 gitignored 缓存。

## 校验流程

`scripts/ci/verify_generated.py` 按以下顺序运行，并在每个可以独立收口的步骤后执行
`git diff --exit-code HEAD --`：

1. `fetch_mingw_sysroot.py`
2. `gen_exports.py --emit-cppm`（中间产物允许变化）
3. `reapply_hand_edits.py`（与上一步组成收口边界）
4. `gen_features.py`
5. `gen_features.py --check`
6. `gen_audit.py` 及 `gen_audit.py --macros`

开始和结束时还检查非 ignored 的 untracked 文件。`import_boost.py` 是特例：
它重新导入 pristine Boost 时会刻意移除 `deps/boost/` 下的项目补丁，因此只在
后续 `reapply_hand_edits.py` 收口后检查工作树是否干净。

`gen_exports.py --scan` 不纳入门禁，因为 `scripts/meta_datas/libs.json` 包含需要
人工维护的 curated 选择；`update_mcpp_index.py` 需要 checkout 外部的 mcpp-index
descriptor，`package-source.sh` 是发布打包动作，也不属于本 CI 的生成闭环。

## import_boost 的触发策略

工作流使用完整 Git 历史，由校验器比较 Pull Request 的 base 或 push 的 before
提交。只有 `scripts/import_boost.py` 在该范围内发生变化时才运行它；该检查由
`ubuntu-latest` 单独负责，Windows 和 macOS leg 跳过，避免一次变更重复下载三次
相同 tarball。

## 平台矩阵

`.github/workflows/scripts.yml` 使用 `ubuntu-latest`、`windows-latest` 和
`macos-latest` 各运行一条 leg，不增加 Linux ARM、Windows ARM 或 macOS Intel
专用 leg。`fetch_mingw_sysroot.py` 的 `scripts/_deps/_archives/` 由
`actions/cache` 按操作系统缓存；缓存 key 包含脚本哈希，且脚本仍会在复用前校验
固定 SHA-256。uv 项目环境由 `scripts/pyproject.toml` 和锁文件提供 `libclang`
依赖。
