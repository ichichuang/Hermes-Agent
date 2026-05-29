#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
required=(
  "README.md"
  "INSTALL.md"
  "FILE_INDEX.md"
  "TREE.txt"
  "MANIFEST.json"
  "AGENTS.md"
  "CODEX_DESKTOP_GOAL_PROMPT.md"
  ".codex/config.toml"
  "docs/ai-plan/00_INDEX.md"
  "docs/ai-plan/01_SPEC.md"
  "docs/ai-plan/02_RESEARCH_BRIEF.md"
  "docs/ai-plan/03_ARCHITECTURE.md"
  "docs/ai-plan/04_PRIORITY_PLAN.md"
  "docs/ai-plan/05_TASK_MATRIX.md"
  "docs/ai-plan/06_VALIDATION.md"
  "docs/ai-plan/07_STATUS.md"
  "docs/ai-plan/08_DECISIONS.md"
  "docs/ai-plan/09_RISK_REGISTER.md"
  "docs/ai-plan/10_OPEN_SOURCE_TOOLS.md"
  "docs/ai-plan/11_HARD_STOP_POLICY.md"
  "docs/ai-plan/12_LAUNCHD_REMEDIATION.md"
  "docs/ai-plan/13_LIVE_VALIDATION.md"
  "docs/ai-plan/14_CODEX_EXECUTION.md"
  "docs/ai-plan/15_FINAL_ACCEPTANCE.md"
  "templates/evidence-pack/manifest.template.json"
  "templates/evidence-pack/phase-report.template.md"
  "templates/evidence-pack/command-ledger.template.jsonl"
  "templates/evidence-pack/not-executed-ledger.template.jsonl"
  "templates/reports/operator-sop.template.md"
  "templates/reports/final-go-nogo.template.md"
  "templates/reports/final-validation-matrix.template.md"
  "templates/reports/next-actions.template.md"
)

missing=0
for f in "${required[@]}"; do
  if [[ -f "$ROOT/$f" ]]; then
    printf 'OK      %s\n' "$f"
  else
    printf 'MISSING %s\n' "$f" >&2
    missing=1
  fi
done

exit "$missing"
