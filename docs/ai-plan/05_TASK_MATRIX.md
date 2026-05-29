# 05_TASK_MATRIX — 可执行任务矩阵

状态枚举：`PENDING` / `IN_PROGRESS` / `DONE` / `BLOCKED` / `NO-GO` / `NOT_APPLICABLE`

| ID | Priority | Task | Dependencies | Deliverable | Acceptance |
|---|---:|---|---|---|---|
| P0.A0 | P0 | Workspace bootstrap | none | active archive + manifest | archive exists; STATUS updated |
| P0.A1 | P0 | Source inventory and research refresh | P0.A0 | source-inventory files | local versions recorded; source URLs recorded |
| P0.A2 | P0 | Ops layer skeleton | P0.A0 | `/Users/cc/.hermes/ops` skeleton | `hermes-ops --help` works |
| P0.A3 | P0 | Evidence pack engine | P0.A2 | `evidence_pack.py` | phase dir/report generated |
| P0.A4 | P0 | Command ledgers | P0.A3 | `command_ledger.py` | executed and not-executed ledgers append entries |
| P0.A5 | P0 | Config integrity and redaction | P0.A3 | `config_integrity.py`, `redaction.py` | no secret value appears in output |
| P0.A6 | P0 | Phase gate and side-effect guard | P0.A3, P0.A4, P0.A5 | `phase_gate.py` | high-risk commands blocked by default |
| P0.A7 | P0 | Launchd read-only preflight | P0.A6 | `launchd_inspector.py` | plist/domain/process report generated; no side effects |
| P0.A8 | P0 | P0 validation | P0.A2-P0.A7 | P0 validation report | tests pass or blockers recorded |
| P1.B1 | P1 | Controlled launchd remediation wrapper | P0.A8 | gated `hermes-ops run` | exact command allowed only after gate |
| P1.B2 | P1 | Live validation matrix | P0.A8 | `validators.py`, validation report | provider/gateway/platform checks PASS/BLOCKED/FAIL |
| P1.B3 | P1 | Operator SOP generator | P1.B2 | `operator-sop.md` | SOP includes allowed/forbidden commands and rollback |
| P1.B4 | P1 | HMAC audit chain | P0.A4 | `audit_chain.py` | verify detects tampering |
| P1.B5 | P1 | Security baseline | P0.A5, P1.B2 | `security-baseline.md` | YOLO/allowlist/permissions checked |
| P1.B6 | P1 | P1 final GO/NO-GO | P1.B1-P1.B5 | `final-go-nogo.md` | final decision written with evidence |
| P2.C1 | P2 | Skill router compatibility layer | P0.A3 | `skill_router.py` | records repo-local/user/built-in resolution |
| P2.C2 | P2 | HermesArchive standardization | P0.A3 | archive index/latest symlink | archive manifest/index valid |
| P2.C3 | P2 | Codex/Hermes skill packaging | P2.C1 | skill skeleton | reusable workflow documented |
| P2.C4 | P2 | Kanban integration design | P1.B6 | design doc | optional mapping, no dependency on Kanban |
| P2.C5 | P2 | Web UI gateway collision detector | P0.A7 | duplicate process detector | report only, no auto patch |
| P3.D1 | P3 | Upstream PR prep | P1.B6 | upstream issue/PR notes | minimal patch proposals only |
| P3.D2 | P3 | Maintenance automation | P1.B6 | scheduled read-only check design | no automatic remediation |
| P3.D3 | P3 | Self-evaluation and regression pack | P1.B6 | regression docs/tests | update preflight can run after Hermes update |
| P3.D4 | P3 | Final documentation bundle | all previous | final docs bundle | all tasks closed or blocked with evidence |

## Execution rule

Codex must process tasks by priority order. Within a priority block, it may reorder only when required by dependencies. Any reorder must be recorded in `08_DECISIONS.md`.
