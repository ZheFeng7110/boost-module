# AGENTS.md

## 计划与设计文档

- 当用户明确写计划，或者智能体处于 Plan Mode 的时候，需要把对应的计划写入 `./.agents/plan/` 下
- 当添加新功能的时候，需要编写设计文档在 `./.agents/docs/` 下，文档的命名需要以日期开头

## Git 提交规范

由智能体产生的 git 提交的最后一行要标注 AI 辅助信息，格式为
`Assisted-by: AGENT_NAME:MODEL_VERSION[, AGENT_NAME2:MODEL_VERSION2, ...] [TOOL1] [TOOL2]...`:
  - AGENT_NAME：你使用的 AI 工具、框架或智能体的名称（例如 Claude, Copilot, Codex 等）。
  - MODEL_VERSION：具体调用的模型版本（例如 claude-3-opus, gpt-4 等）。
  - `[TOOL1]` `[TOOL2]`（可选）：搭配使用的专业代码分析工具（例如 coccinelle, sparse, smatch, clang-tidy 等）。
  - 若 MODEL_VERSION 包含空格，需用英文双引号将其包裹，例如 "K2.7 Code"。
  - 若包含多个 AGENT_NAME:MODEL_VERSION，则用逗号分隔。
  - 示例：
    - `Assisted-by: Codex:ChatGPT-4.5`
    - `Assisted-by: OpenCode:deepseek-v4-pro clang-tidy`
    - `Assisted-by: Claude:claude-3-opus coccinelle sparse`
    - `Assisted-by: Kimi Code:"K2.7 Code", OpenCode:GLM-5.1 clang-tidy`
