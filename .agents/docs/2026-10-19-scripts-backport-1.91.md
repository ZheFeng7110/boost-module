# 1.91 分支生成脚本工程化与幂等性 CI 回迁

## 范围

将 `b1.92.0wdev` 的 `0ffca374` 至 `77c6b48f`（含端点，共 15 个提交）
整体回迁到 `b1.91.0wdev`，包括 uv 项目与锁文件、`meta_datas/` 元数据目录、
`scripts/ci/`、生成校验器、LLVM 发现逻辑和跨平台 LF 回归测试。

## 分支适配

- 新工作流的 push / pull_request 目标均改为 `b1.91.0wdev`。
- 保留 Boost 1.91.0 的下载 URL、SHA-256、库元数据、生成快照、补丁和
  `gen_features.py` 中的 1.91 专用源文件清单，不引入 Boost 1.92 升级。
- 生成工具链沿用源提交最终固定的完整 LLVM 23.1.3（驱动、libclang、
  builtin headers 必须一致），不改变现有编译测试矩阵的 LLVM 22.1.8。
- mcpp-index 更新脚本移至 `scripts/ci/`，同步发布工作流调用路径；
  不修改任何已发布的 release notes 或 changelog。
- 架构文档中的 uv 调用明确选择 `scripts` 项目，并使用迁移后的元数据路径。
- 1.91 的已提交 `simple_event_log.h` 不含前导空行；同步修正补丁回放中的
  文件模板并测试首次创建与重复回放，避免重新导入后产生单行漂移。

## 验证

通过 `uv sync --project scripts --locked` 安装锁定依赖，运行
`scripts/tests/` 的 unittest 回归测试。从干净提交运行
`scripts/ci/verify_generated.py --import-boost-if-changed`，验证 Boost 导入与
补丁回放、MinGW sysroot、导出生成与补丁回放、feature 元数据和两类审计。
每个闭环必须保持 `git diff HEAD` 与非 ignored untracked 文件为空。
Windows / macOS 的真实运行由新增 CI 矩阵验证。

### 本地结果

- 锁定依赖安装、22 项 unittest、全部工作流的 GitHub Actions schema 与
  Bash 语法校验均通过。
- 使用完整 LLVM 23.1.3 运行带 `--import-boost-if-changed` 的验证器通过，
  包含 Boost 1.91 重新导入；所有闭环均保持干净，无需修改生成快照。
- LLVM 22.1.8 成功编译并运行 `build.mcpp`，依赖追踪指向迁移后的两个
  `.lst` 文件；单独启用 version 的 smoke test 正确输出 `boost.version`。
- 本机 mcpp 为 2026.10.17.1，其带哈希的输出目录与清单原有
  `[lib].path = "target/.build-mcpp/out/boost.cppm"` 不一致，导致
  `--configure-only` 在后续清单验证阶段失败。CI 固定为 2026.9.21.3；
  本次不扩展修改 mcpp 版本兼容性，也未执行完整 C++ 编译测试矩阵。
