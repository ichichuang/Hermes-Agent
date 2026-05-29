# 00_INDEX — Hermes 升级计划体系索引

## 读取顺序

1. `01_SPEC.md` — 目标、非目标、边界。
2. `02_RESEARCH_BRIEF.md` — 研究依据。
3. `03_ARCHITECTURE.md` — 目标架构。
4. `04_PRIORITY_PLAN.md` — 按优先级排列的执行计划。
5. `05_TASK_MATRIX.md` — 可执行任务矩阵。
6. `06_VALIDATION.md` — 验收命令和通过标准。
7. `11_HARD_STOP_POLICY.md` — 硬停规则。
8. `12_LAUNCHD_REMEDIATION.md` — launchd 专项处理。
9. `13_LIVE_VALIDATION.md` — live validation 矩阵。
10. `15_FINAL_ACCEPTANCE.md` — 最终完成标准。

## Codex 必须持续写入的文件

- `07_STATUS.md`
- `08_DECISIONS.md`
- active evidence pack under `/Users/cc/HermesArchive/hermes-new-<timestamp>/`

## 最终交付物

- `/Users/cc/.hermes/ops/bin/hermes-ops`
- `/Users/cc/.hermes/ops/lib/*.py`
- `/Users/cc/.hermes/ops/tests/*`
- `/Users/cc/HermesArchive/hermes-new-<timestamp>/reports/final-go-nogo.md`
- `/Users/cc/HermesArchive/hermes-new-<timestamp>/reports/final-validation-matrix.md`
- `/Users/cc/HermesArchive/hermes-new-<timestamp>/reports/operator-sop.md`
- `/Users/cc/HermesArchive/hermes-new-<timestamp>/reports/next-actions.md`

## 关键判断

不要把 Telegram、Feishu/Lark、Weixin、cron、DeepSeek、launchd service 本身当成“老系统独有功能”重造。新版 Hermes 官网已经有这些基础能力。本计划要补的是生产化控制层：证据、硬停、验收、审计、SOP、归档。
