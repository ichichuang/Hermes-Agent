# Kanban Integration Design

## Goal

Map `docs/ai-plan/05_TASK_MATRIX.md` into Hermes Kanban without replacing `07_STATUS.md` as the source of truth.

## Design

- Keep `07_STATUS.md` authoritative for task state.
- Derive Kanban cards from the task matrix IDs and current status table.
- Sync only metadata:
  - task id
  - title
  - priority
  - dependency note
  - evidence path
  - validation summary
- Never drive launchd or gateway actions from Kanban automation.

## Proposed mapping

| Ledger field | Kanban field |
|---|---|
| Task ID | Card title prefix |
| Status | Lane |
| Evidence path | Card body |
| Validation | Checklist item |
| Notes | Card notes |

## Safety

- Kanban remains read-mostly.
- Status transitions still happen in `07_STATUS.md`.
- Any automation created later must call read-only `hermes-ops` commands only.
