# AGENTS.md

## 计划与设计文档

- 当用户明确写计划，或者智能体处于 Plan Mode 的时候，需要把对应的计划写入 `./.agents/plan/` 下
- 当添加新功能的时候，需要编写设计文档在 `./.agents/docs/` 下，文档的命名需要以日期开头

## 发布文档

- `docs/release_notes/`（含 `docs/zh/release_notes/`）与 changelog 只在发布版本时编写
- 一经写好即视为不可变，不得再修改或回填；后续变更只体现在新的发布版本中

## Git 提交规范

由智能体产生的 git 提交的最后一行要标注 AI 辅助信息，格式为
`Generated-by: AGENT_NAME:MODEL_VERSION[, AGENT_NAME2:MODEL_VERSION2, ...]`:
  - AGENT_NAME：你使用的 AI 智能体的名称（例如 Claude, Copilot, Codex 等）。
  - MODEL_VERSION：具体调用的模型版本（例如 claude-opus-5-5, gpt-6-astra, deepseek-flash 等）。
  - 若包含多个 AGENT_NAME:MODEL_VERSION，则用逗号分隔。
  - 示例：
    - `Generated-by: Codex:gpt-6.1-sol`
    - `Generated-by: OpenCode:deepseek-flash`
    - `Generated-by: Claude:claude-opus-5-5`
    - `Generated-by: Kimi Code:"kimi-k3", OpenCode:glm-5.3`
