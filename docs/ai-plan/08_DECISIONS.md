# 08_DECISIONS — Architecture Decision Record

## ADR-0001 — 使用非侵入式本地 Ops Layer

- Decision: 先在 `/Users/cc/.hermes/ops` 实现 Ops 层，不修改 Hermes core。
- Reason: 官方 Hermes 已有基础功能；本计划补生产控制层。
- Consequence: 可回滚、可审计、不会把本机运维补丁和 upstream 混在一起。

## ADR-0002 — Python stdlib first

- Decision: 核心实现优先使用 Python 标准库。
- Reason: 降低安装依赖、网络审批、供应链风险。
- Consequence: `jq`、`yq`、`gitleaks`、`pytest` 等作为 optional/recommended 工具，不作为核心阻塞依赖。

## ADR-0003 — 不使用 YOLO / approval bypass

- Decision: 禁止 `--yolo`、`HERMES_YOLO_MODE=1`、danger full access。
- Reason: 本计划目标是生产化安全，而不是绕过安全。
- Consequence: 有副作用操作必须通过 gate；Codex 可以连续执行安全任务，但不能绕过硬停。

## ADR-0004 — 不从旧 Hermes 恢复功能代码

- Decision: 旧系统只作为需求来源。
- Reason: 用户明确要求重新设计全新 Hermes，不从旧系统恢复功能。
- Consequence: 不复制旧 scripts/plist/config/env。

## ADR-0005 — STATUS.md 是长任务防漂移账本

- Decision: Codex 每个 milestone 必须更新 `07_STATUS.md`。
- Reason: 长任务会发生上下文压缩或线程中断；状态文件保证可接续。
- Consequence: 不允许只在对话中报告进度。

## Future ADRs

Codex 如作出任何新架构选择，必须追加如下格式：

```md
## ADR-XXXX — Title

- Decision:
- Reason:
- Alternatives considered:
- Consequence:
- Evidence:
```

## ADR-0006 — pytest broken 时降级到 stdlib smoke

- Decision: 当现有 `pytest` 运行时因缺少 `pygments` 无法启动时，不安装新依赖，改为运行 `/Users/cc/.hermes/ops/tests/run_smoke.py` 作为核心回归烟测，并把 `pytest` 记为 `BLOCKED_TOOL_MISSING`。
- Reason: 计划明确禁止全局安装和未知 installer；核心实现已尽量使用 stdlib，可接受工具链缺失时的窄验证降级。
- Alternatives considered: 本地安装/修复 `pytest` 依赖；放弃任何回归执行。
- Consequence: P0.A8 可以继续完成核心验证，但需要在最终报告里明确 `pytest` 工具链未恢复。
- Evidence: `/Users/cc/HermesArchive/hermes-new-20260527_211109/phases/P0.A8-p0-validation/pytest.txt`

## ADR-0007 — D4 launchd remediation 只通过 exact hermes-ops allowlist

- Decision: D4 只允许 `/bin/launchctl enable gui/501/ai.hermes.gateway`、`/bin/launchctl bootstrap gui/501 /Users/cc/Library/LaunchAgents/ai.hermes.gateway.plist`、`/bin/launchctl kickstart -k gui/501/ai.hermes.gateway` 这类 exact command 通过 `hermes-ops` gate；本轮实际只执行了 `enable` 和 `bootstrap`。
- Reason: D4.A 证据显示 service disabled 且未加载；用户明确允许在 phase gate GO 后通过 `hermes-ops` 做最小 remediation。
- Alternatives considered: 直接运行 raw `launchctl`；继续保持 NO-GO 不修复 launchd。
- Consequence: gateway blocker 已移除；所有副作用命令都有 command ledger 和 not-executed dry-run 证据。
- Evidence: `/Users/cc/HermesArchive/hermes-new-20260527_211109/reports/D4-launchd-remediation-report.md`

## ADR-0008 — pytest blocker 使用本地隔离依赖而不修 user-site

- Decision: 将缺失的 `pygments` 安装到 `/Users/cc/.hermes/ops/.pytest-deps`，通过 `PYTHONPATH` 运行 pytest；不修改 user-site pytest 依赖。
- Reason: D4.D 要求优先使用本地隔离测试环境，且不改变 production Hermes 行为。
- Alternatives considered: `python3 -m pip install --user pygments`；继续只跑 smoke。
- Consequence: 隔离 pytest PASS；裸 `python3 -m pytest /Users/cc/.hermes/ops/tests` 仍作为 blocker 保留。
- Evidence: `/Users/cc/HermesArchive/hermes-new-20260527_211109/reports/D4-validation-matrix.md`

## ADR-0009 — D5 生产 GO 以授权外部 live validation 为准

- Decision: 在 D5 中只通过 `hermes-ops` 执行已授权的最小外部 live validation；DeepSeek provider 与 Telegram DM 均 PASS 后，将最终生产结论从 D4 narrow NO-GO 更新为 `PRODUCTION_GO for post-upgrade production use`。
- Reason: D4 的生产阻塞只剩外部 provider/Telegram 验证缺授权；D5 用户授权已明确允许最小外部检查，同时禁止 config/env、allowed users、launchd/gateway lifecycle 直接变更。
- Alternatives considered: 继续保持 D4 NO-GO；直接用 raw provider/Telegram 脚本绕过 `hermes-ops`。
- Consequence: 未配置的 Telegram group、jobs/cron/home delivery、Feishu/Lark 记录为 `NOT_APPLICABLE`，不阻塞生产 GO；裸 user-site pytest 继续作为工具链问题记录，隔离 pytest PASS 后不阻塞生产 GO。
- Evidence: `/Users/cc/HermesArchive/hermes-new-20260527_211109/reports/D5-final-go-nogo.md`

## ADR-0010 — D6 只确认当前自启动基线，不提前声明 POST_REBOOT_GO

- Decision: D6 新增 `hermes-ops autostart status|verify|report|remediate`，默认只读验证官方 `ai.hermes.gateway` LaunchAgent；当前机器状态满足 `D6_CURRENT_BASELINE_GO`，但 `POST_REBOOT_GO` 保持 `PENDING_OPERATOR_REBOOT`。
- Reason: 用户目标是确认 Mac 重启并由 `cc` 登录后 launchd 守护 Hermes；该事实必须由真实 reboot/login 后的验证证明，不能用当前运行状态替代。
- Alternatives considered: 直接声明 post-reboot GO；创建自定义 root LaunchDaemon；直接运行 raw `launchctl` 或 `hermes gateway start`。
- Consequence: D6 不改 `config.yaml`、不改 `.env`、不执行外部 provider/Telegram live validation、不创建 root daemon；如重启后失败，只能走 D6.C gated hermes-ops remediation。
- Evidence: `/Users/cc/HermesArchive/hermes-new-20260527_211109/reports/D6-autostart-final.md`

## ADR-0011 — 语言层先落 B0 与禁用态插件，不越过 config hard-stop

- Decision: 本轮只让 `SOUL.md` 的 B0 中文 UX policy 生效；B1/A1 代码作为默认禁用的 user plugin 和 offline ops lib 落地，不执行 `hermes plugins enable`、不改 `config.yaml`、不重启 gateway。
- Reason: 本地 Hermes `pre_llm_call` 和 `transform_llm_output` hook contract 支持目标设计，但 user plugin live activation 需要 `plugins.enabled` config change 和 gateway reload，均属于本仓库 hard-stop 保护范围。
- Alternatives considered: 直接编辑 `config.yaml` 启用插件；修改 Hermes core；继续只做 probe-only milestone。
- Consequence: B0 已可影响后续提示风格；B1/A1 离线验证通过但 live runtime activation 标记为 `BLOCKED`，需后续 gated activation。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/reports/final-go-nogo.md`

## ADR-0012 — LANG-M6 只受控启用 B-layer，不启用 A-layer

- Decision: 在 `LANG-M6` 中通过 `hermes-ops` exact allowlist 执行 `hermes plugins enable hermes-language-layer` 和 `hermes gateway restart`，并用 `/Users/cc/.hermes/lang-layer/config.json` 明确设置 `b_enabled: true`、`a_enabled: false`、`local_model_enabled: false`。
- Reason: 上一轮已证明 hook contract 可用，但 runtime activation 需要 config/plugin enablement 和 gateway reload；本轮用户目标正是执行 gated B-layer live activation，同时要求 A-layer 等待 B-layer live behavior 验证后再考虑。
- Alternatives considered: 直接编辑 `/Users/cc/.hermes/config.yaml`；启用 A/B 两层；修改 Hermes core；只保留 staged plugin 不启用。
- Consequence: B-layer 当前对后续 Hermes 输出生效；A-layer 不注入 task card；rollback 必须同样通过 `hermes-ops` gate 执行 `hermes plugins disable hermes-language-layer` 和 gateway restart。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/reports/LANG-M6-gated-b-layer-live-activation.md`

## ADR-0013 — LANG-M7 仅做观察计划和只读预检查，等待人工 Telegram 摘要

- Decision: 将 `LANG-M7-b-layer-observation-and-polish` 标记为 `BLOCKED`，直到操作员提供手动 Telegram 观察摘要；本轮不启用 A-layer、不调用 Ollama、不发送 Telegram、不改 provider/model、credentials、launchd、Hermes core 或 site-packages。
- Reason: M7 的有效验收依赖操作员手动 Telegram 测试结果；Codex 不能代发测试消息，也不能把未发生的 live observation 记为 PASS。
- Alternatives considered: Codex 主动发送 Telegram 测试；直接给出 GO；先做 B-layer wording patch。
- Consequence: B-layer 保持已启用，A-layer 保持禁用，gateway 只读检查稳定；最终 M7 决策保持 `BLOCKED`，可在收到摘要后更新为 `GO`、`GO_WITH_POLISH` 或 `NO-GO`。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/reports/M7-final-status.md`

## ADR-0014 — LANG-M7 完成人工观察后给出 GO_WITH_POLISH

- Decision: 将 `LANG-M7-b-layer-observation-and-polish` 从 `BLOCKED` 更新为 `GO_WITH_POLISH`；B-layer 保持启用，A-layer 保持禁用，不应用 wording patch。
- Reason: 操作员提供了 M7-01 到 M7-06 的完整 Telegram 人工观察摘要；未观察到 protected-token corruption、gateway issue、A-layer activation、Ollama/local-model call、provider/model change、credential change 或 unsafe behavior，但英文普通回复和代码块呈现仍需润色。
- Alternatives considered: 因 M7-02/M7-05 存在 polish 问题而给出 `NO-GO`；在本轮直接修改 B-layer wording；继续保持 `BLOCKED`。
- Consequence: M7 观察阶段关闭，后续 polish 必须作为单独显式任务执行，并继续保护 commands、paths、URLs、code blocks、JSON/YAML keys、model/provider names。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/reports/M7-final-status.md`

## ADR-0015 — LANG-M8 只做 B-layer 最小 polish，live 生效等待 gated reload

- Decision: 对 B-layer deterministic fallback 做最小 polish：覆盖安全普通英文运维句的中文化，移除 `Hermes 返回了英文说明：` 混合前缀，并继续原样保护 fenced code blocks；M8 决策为 `GO_PENDING_RELOAD`。
- Reason: M7 只暴露两个 polish 问题；当前任务明确禁止 gateway reload/restart，运行中的 gateway PID `11127` 已加载旧 Python 模块，不能声称 live Telegram 已生效。
- Alternatives considered: 调用 Ollama 做泛化翻译；直接 reload gateway；扩大 B-layer 翻译器；修改 Hermes core。
- Consequence: 本地源码和测试通过，但 live gateway 输出需后续单独 gated reload/revalidation；未知任意英文回复不再加混合 prefix，而是保持原文，避免不安全的伪翻译。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M8-b-layer-polish/reports/M8-final-status.md`

## ADR-0016 — LANG-M8R 复用现有 LANG-M6 gateway restart 门禁

- Decision: 在 `LANG-M8R-gated-reload-revalidation` 中通过现有 `hermes-ops` exact allowlist 执行 `/Users/cc/.hermes/ops/bin/hermes-ops run --phase LANG-M6 --risk service-change -- hermes gateway restart`，并将 M8R pre-state、reload、post-state、canary、validation 证据记录到独立 M8R phase 目录。
- Reason: 当前 `hermes-ops` 仅在 `LANG-M6` allowlist 中允许 exact `hermes gateway restart`；用户要求执行最小 reload/restart 且禁止 raw hard-stop 操作、launchctl enable/bootstrap/bootout、A-layer、Ollama、Telegram 外发和 provider/model/credential 变更。
- Alternatives considered: 直接运行 raw `hermes gateway restart`；新增 M8R allowlist 代码；使用 `launchctl kickstart`；跳过 reload 保持 `GO_PENDING_RELOAD`。
- Consequence: M8 polish patch 已加载到 live gateway；gateway PID `11127` -> `67527`，runs `3` -> `4`；B-layer 保持启用，A-layer 保持禁用，local model 保持禁用；M8R canary、full pytest、diff check 和 secret scan 均 PASS。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M8R-gated-reload-revalidation/reports/M8R-reload-revalidation.md`

## ADR-0017 — LANG-M9 真实观察后给出 NO-GO_CODE_BLOCK_PROTECTION

- Decision: 将 `LANG-M9-post-polish-live-observation` 从缺观察 `BLOCKED` 更新为 `NO-GO_CODE_BLOCK_PROTECTION`，在 schema-limited ledger 中记录为 `NO-GO`。
- Reason: 操作员提供了真实 Telegram 截图观察：T1 English ordinary reply PASS，T3 path/URL PASS，T4 YAML keys PASS；但 T2 fenced code block FAIL，虽然 `print("hello hermes")` 未被语义改写，代码块围栏形状没有保留，且回复在用户明确要求 "do not execute it" 时推断了执行输出。
- Alternatives considered: 因 T1/T3/T4 通过而给出 `GO_WITH_POLISH`；自动 rollback M8 polish；由 Codex 发送 Telegram 补测；启用 A-layer 或调用 Ollama 修复。
- Consequence: 不自动 rollback，因为 gateway 稳定且 T1/T3/T4 的 B-layer 修复有效；B-layer 保持启用，A-layer 保持禁用，gateway 保持 PID `67527`、runs `4`；后续应开 `LANG-M10` 聚焦修复 fenced code block preservation 和 forbidden execution inference。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M9-post-polish-live-observation/reports/M9-final-status.md`

## ADR-0018 — LANG-M10 fenced code blocks bypass B-layer rewrites before reload

- Decision: 在 `LANG-M10` 中将 B-layer fenced code block 处理前置到 fixed-map、deterministic English rendering 和 optional local-model rendering 之前；含 triple-backtick 的响应默认整段保留，仅当响应自身包含 no-run/no-execute 语义且追加 `Output:`/`Result:` 类执行结果时，删除该推断结果段。
- Reason: M9 证明 fenced code block 是 protected-token 类高优先级对象；原实现先执行 fixed English rewrite，导致带代码块的响应仍可能被 B-layer 改写。B-layer 没有可靠用户原始意图上下文，因此最小安全策略是代码块优先保护。
- Alternatives considered: 启用 A-layer 注入更强 prompt；调用 Ollama 重写；回滚 M8；修改 Telegram/provider/Hermes core；自动 reload gateway。
- Consequence: 非代码英文回复渲染保持不变；带 fenced code block 的英文说明不再被 B-layer 翻译，优先保证代码块形状、语言 tag 和内容原样；源码验证通过但 live gateway PID `67527` 需要后续 gated reload/revalidation 才能生效。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M10-code-block-preservation-fix/reports/M10-final-status.md`

## ADR-0019 — LANG-M10R 复用 LANG-M6 gateway restart 门禁加载 M10

- Decision: 在 `LANG-M10R-gated-reload-revalidation` 中通过现有 `hermes-ops` exact allowlist 执行 `/Users/cc/.hermes/ops/bin/hermes-ops run --phase LANG-M6 --risk service-change -- hermes gateway restart`，并将 M10R pre-state、rollback snapshot、reload、post-state、canary、validation 证据记录到独立 M10R phase 目录。
- Reason: 当前 `hermes-ops` 仅在 `LANG-M6` allowlist 中允许 exact `hermes gateway restart`；用户目标要求把已验证 M10 fix 加载到 live gateway，同时禁止 raw hard-stop 操作、launchctl enable/bootstrap/bootout、A-layer、Ollama、Telegram 外发和 provider/model/credential 变更。
- Alternatives considered: 直接运行 raw `hermes gateway restart`；新增 M10R allowlist 代码；使用 `launchctl kickstart`；跳过 reload 保持 `GO_PENDING_RELOAD`。
- Consequence: M10 patch 已加载到 live gateway；gateway PID `67527` -> `13263`，runs `4` -> `5`；B-layer 保持启用，A-layer 保持禁用，local model 保持禁用；M10R canary、full pytest、diff check 和 secret scan 均 PASS。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M10R-gated-reload-revalidation/reports/M10R-reload-revalidation.md`

## ADR-0020 — LANG-M11 用 B-layer volatile caller context 修复 live 输入保护

- Decision: 在 `LANG-M11-live-b-layer-regression-fix` 中只修改 `ops/lib/language_layer.py` 与测试，通过 `render_b_layer(source_text=...)` 和 bounded caller-context lookup 获取当前 turn 的 `user_message`，用于 B-layer fenced code 保护；不修改 plugin wrapper，不启用 A-layer，不注入 LLM context，不持久化用户原文。
- Reason: M11 live 失败证明输出侧可能已经丢失原始 fenced block；仅看 `response_text` 无法可靠恢复代码块形状和 no-execute 意图。当前任务允许编辑范围不包含 `plugins/hermes-language-layer/__init__.py`，但 plugin wrapper 的 `kwargs` 中仍有当前调用的 `user_message`，可在库内做限定深度的 volatile lookup。
- Alternatives considered: 修改 plugin wrapper 显式传入 `user_message`；启用 A-layer 注入更强 prompt；调用 Ollama；修改 Hermes core transform hook；对 `print("hello hermes")` 做硬编码推断。
- Consequence: M11 patch 已通过 gated reload 加载；gateway PID `13263` -> `94212`，runs `5` -> `6`；B-layer 保持启用，A-layer 保持禁用，local model 保持禁用；本地 plugin canary 覆盖 T1/T2，最终决策为 `GO_PENDING_MANUAL_TELEGRAM`。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M11-live-b-layer-regression-fix/reports/M11-final-status.md`

## ADR-0021 — LANG-M11 人工 Telegram 摘要缺失时不提交

- Decision: 将 `LANG-M11-manual-telegram-finalization` 记为 `BLOCKED_PENDING_OPERATOR_SUMMARY`，不执行 `git commit` 或 `git push`。
- Reason: 本轮收到的 operator retest summary 是字面占位符 `PASTE_SUMMARY_HERE`，无法证明 T1-T4 Telegram live 输出 PASS、NEEDS_POLISH 或 FAIL。根据 M11 gate，缺人工 Telegram 证据不能接受 live 修复。
- Alternatives considered: 仅凭本地 plugin canary 继续 commit/push；由 Codex 主动发送 Telegram 测试；将占位符解释为 PASS。
- Consequence: B-layer 继续启用，A-layer 继续禁用，gateway 保持 PID `94212`；repo 四个文件仍为未提交修改，等待真实 T1-T4 人工摘要后再判定 GO/GO_WITH_POLISH/NO-GO。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M11-live-b-layer-regression-fix/reports/M11-final-status.md`

## ADR-0022 — LANG-M11 重复占位符摘要继续阻塞提交

- Decision: 第二次收到的 operator retest summary 仍为字面占位符 `PASTE_SUMMARY_HERE`，因此维持 `BLOCKED_PENDING_OPERATOR_SUMMARY`，不执行 `git commit` 或 `git push`。
- Reason: 该输入没有包含 T1-T4 Telegram 输出事实，无法验证自然中文、fenced code block、path/URL、YAML key/value 和 `/sethome` token。
- Alternatives considered: 复用上一次本地 canary 作为人工 Telegram 验收；将重复占位符视作无变化 PASS。
- Consequence: B-layer 继续启用，A-layer 继续禁用，gateway 保持 PID `94212`；等待真实人工摘要。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M11-live-b-layer-regression-fix/reports/M11-final-status.md`

## ADR-0023 — LANG-M11 第三次占位符摘要触发 goal blocked

- Decision: 第三次收到的 operator retest summary 仍为字面占位符 `PASTE_SUMMARY_HERE`，继续维持 `BLOCKED_PENDING_OPERATOR_SUMMARY`，不执行 `git commit` 或 `git push`，并将线程 goal 标记为 blocked。
- Reason: 同一 blocking condition 已连续三次出现；缺少 T1-T4 Telegram 输出事实，无法完成 acceptance gate。
- Alternatives considered: 继续保持 goal active 并重复报告阻塞；仅凭本地 canary 接受并提交。
- Consequence: B-layer 继续启用，A-layer 继续禁用，gateway 保持 PID `94212`；repo 四个文件仍为未提交修改，等待真实人工摘要后可恢复。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M11-live-b-layer-regression-fix/reports/M11-final-status.md`

## ADR-0024 — LANG-M11 真实 Telegram retest 后接受为 GO_WITH_POLISH

- Decision: 将 `LANG-M11-manual-telegram-finalization` 从 `BLOCKED_PENDING_OPERATOR_SUMMARY` 更新为 `GO_WITH_POLISH`，并按用户授权继续执行四个白名单 repo 文件的 stage、staged checks、commit 和 `origin main` push。
- Reason: 操作员提供了真实 Telegram retest 观察：T1 English status reply PASS；T2 fenced code block PASS；T3 path/URL PASS_WITH_CAUTION；T4 YAML and `/sethome` PASS_WITH_CAUTION。未观察到 gateway issue 或 protected-token corruption，B-layer 保持启用，A-layer 保持禁用。
- Alternatives considered: 将 T3/T4 caution 降级为 blocking `NO-GO`；把 schema 外的 `PASS_WITH_CAUTION` 改写为 `PASS`；等待 Codex 主动 Telegram 补测；启用 A-layer 或调用 Ollama。
- Consequence: M11 fix 可接受并发布；T3 的 "check" prompt tool-trigger 行为和 T4 的 English interrupt/tool status message 作为后续 gateway/system-message polish 跟踪，不阻塞本次 B-layer regression fix。
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M11-live-b-layer-regression-fix/reports/M11-final-status.md`
