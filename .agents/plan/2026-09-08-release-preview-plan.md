# 计划 — 发布预览版 (Preview Release)

> 日期: 2026-09-08 · 状态: 待实施 · 分支 `b1.91.0wdev`
> 背景: `.agents/` 旧计划/设计文档已由
> `docs/2026-09-08-consolidated-design.md` 汇总替代
> (旧文档最后存在提交 `03f616196468f71ae6bf7f22010777450356d3ec`)。
> 当前状态 (2026-09-09 C5 后复核): 116 模块 / 118 feature / 默认 49 闭包 /
> 封装 139 库 / 测试默认集 141/141 / CI 四腿 (A/B 两组门禁)。
> (计划编写时的 115/117/36 为 C5 `boost.version` 提升前旧口径。)

## 0. 用户决策 (2026-09-08)

1. **外部依赖/asm 库 (M13, 11 库) 继续暂缓**: context / fiber / coroutine /
   locale / mpi / python / parameter_python / graph_parallel / compute /
   mysql / redis —— 本期零改动, 预览版中明确标注"不支持"。
2. **下一步 = 准备发布预览版**: 发布门槛由原计划"剩余库全量接入后"调整为
   "当前 115 模块 + 已知限制披露" (见设计汇总 §10#8)。

## 1. 预览版范围定义

- **内容**: 115 模块 + 117 feature (含 log / unit_test_framework 两个无模块
  feature) + 默认 36 库闭包 + 22 纯 include-only 库 (消费者直接 include)。
- **版本/tag**: 按 README 命名规范 `b1.91.0w0.0.0` (Boost v1.91.0 × 封装
  v0.0.0); 预览性质在 release notes 中标注 (是否加 `-preview` 后缀待定, §5)。
- **平台**: CI 四腿覆盖的 win (clang-msvc) / linux (gcc 16, llvm) / macos
  (llvm, arm64); mingw 与真 MSVC 不承诺 (§4 风险披露)。

## 2. 任务分解

### T1 — 发布前置核查 (收口)

- [x] HEAD (`03f616196468f71ae6bf7f22010777450356d3ec` 之后) CI 四腿全绿确认
      (C4.1 linux-gcc 修复后的 push)。
- [x] `gen_features.py --check` 通过, 重生成零 diff; 计数复核 (2026-09-09):
      116 模块 / 118 feature / 默认闭包 49 / 测试 .cpp 141 (原目标 115/117/36
      为 C5 前旧口径, 见文件头注)。
- [x] `reapply_hand_edits.py` 幂等复跑零改动; 55 个 patch 全部反向检查通过。
      修复: 提交 `551616c4` (生成文件 ASCII-only 风格化) 将头部行 em-dash 改为
      `-` 后, cobalt/json/stacktrace/winapi/safe_numerics_src 五个 patch 的
      上下文行未同步, 反向检查失败 —— 已把 patch 头部行同步为 ASCII。
- [x] mcpp pinned 维持现状 (现为 `2026.9.6.3`, 计划编写后已由 `2026.8.29.1`
      升级, commit `450258be`; dyld 缺陷已由上游修复且 pinned 不受影响 ——
      不降级即不会再遇到, 设计汇总 §10#1 已澄清)。

### T2 — docs/architecture.md (架构文档, M14 原定产物)

消费者视角, 从设计汇总抽取:

- 项目定位与 import 用法 (三形态: 模块 / 纯 include-only / 编译库 include-only
  + test 双形态) + `default-features = false` / `features = ["all"]` 示例;
- feature 选择性构建语义 (default 36 闭包 / opt-in / implies 闭包);
- 支持矩阵 (编译器/平台/已知限制全文: clang `--features all` 2^31 上限 →
  **推荐消费者逐库 import** (用户决策 2026-09-08, 设计汇总 §10#6); gcc 消费
  三分规则; 特性宏构建期固定; filesystem v3 / thread v2 / stacktrace basic
  等裁剪; M13 11 库不支持清单)。
- [x] 编写 + CI 链接自检 (2026-09-09: `docs/architecture.md` 落地, 含消费者
      三形态 import / feature 语义 / 支持矩阵 / 已知限制 / M13 暂缓清单;
      README `辅助脚本` 章节移入 architecture.md §6, README 留短指针)。
      CI 链接自检 = 文档无 CI 引用改动, 四腿不受影响 (纯文档变更)。

### T3 — mcpp-index 薄层 boost.lua

- [ ] features 镜像进 xpkg 描述符 (117 feature + default 36, 与 mcpp.toml
      gen 区同源; 考虑由 gen_features.py 同步生成以防漂移 —— 方式待定 §5)。
- [ ] 发布流程对接 mcpp registry (index 提交方式、path-dep 与 registry 两种
      消费方式验证)。

### T4 — 发布物料

- [ ] `CHANGELOG.md` 首版: 里程碑史速览 (M0–M12, C1–C4.1) + 当前计数。
- [ ] Release notes: 内容清单、已知限制 (设计汇总 §7 全量披露)、消费者
      陷阱要点 (§8 精选)、报告问题指引 (gcc 16 缺陷家族属编译器 bug,
      需引导用户区分)。
- [ ] Tag `b1.91.0w0.0.0` + GitHub Release 流程; 干净 checkout 下
      tag 构建演练。

### T5 — 仓库文档收口

- [ ] README "相关文档" 与文内旧链接全部指向新汇总设计/计划文档
      (旧 `.agents` 文档已删除)。
- [ ] README 进度表: M11/M12/C1–C4 与发布行状态刷新 (M14 → 预览版发布)。

## 3. 验证矩阵 (发布演练收口)

| 项 | 覆盖 |
|---|---|
| `mcpp build` / `mcpp test` 默认集 (36 闭包) | llvm/msvc 本地 + CI 四腿 |
| A 组 (103 模块 + log/utf) / B 组 (T1b 12) build+test | CI 四腿 |
| examples (`import boost;`) | 本地 + CI |
| 消费者 path-dep probe: 默认 / default-features=false + 自选 / 逐库 import | 临时工程 |
| `--features unit_test_framework` 编译形态 + 默认集 included 纯头形态 | 双形态互斥 |
| `--features log` (无模块 feature + 手工 implies 链接面) | 单跑 |
| 干净 checkout + tag 构建 | 发布演练 |
| registry/index 消费 probe (T3 完成后) | path-dep 之外的正式渠道 |

## 4. 风险与披露要点 (进 release notes)

| 风险 | 披露/应对 |
|---|---|
| clang `--features all` 超 2^31 源位置上限 | 文档明示"全量请逐库 import"; gcc 侧未实测 |
| gcc 16.1 缺陷家族 (exception 不可用 / variant 自由函数 ICE / 消费三规则) | 已知限制章节 + 受害库消费方式表 |
| mingw 消费者 (thread 挂起 / url 宏冲突, 无 CI 腿) | 明示不承诺; 反馈通道 |
| macOS 精确异常 catch 落空 (Mach-O typeinfo) | 测试兜底 `std::exception` 写法披露 |
| 特性宏构建期固定 / 库内功能裁剪 (§7.1 清单) | 逐项列出, 避免预期偏差 |
| bimap 钉边等生成器债务 (.deps 漂移无系统检测) | 内部已知, 不阻塞发布; 重生成流程附核对项 (设计汇总 §10#7 待定项) |
| 真 MSVC 从未验证 | 支持矩阵如实标注 (clang-msvc 风味) |

## 5. 待定项 (实施中向用户确认)

1. tag 是否加 preview 后缀 (`b1.91.0w0.0.0` vs `b1.91.0w0.0.0-preview`)。
2. boost.lua 由 gen_features.py 自动生成还是手写同步 (防漂移 vs 简单)。
3. ~~release notes 中 `--features all` 的表述口径~~ — 已定 (2026-09-08):
   推荐逐库 import (设计汇总 §10#6)。

## 6. 预览版之后 (后续排期参考, 不在本期)

- gcc CI 腿版本升级时试探 exception 重新接入 (pendings bug)。
- mingw 支持决策 (若支持需单列里程碑: thread 挂起 / url 宏重构)。
- M13 重启评估 (外部 SDK 依赖库)。
- mcpp depfile / dep_graph 结构性缺陷的上游跟进与生成器加固。
