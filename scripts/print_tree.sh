#!/usr/bin/env bash
set -euo pipefail

cat <<'TREE'
.hermes/
  README.md
  INSTALL.md
  FILE_INDEX.md
  TREE.txt
  MANIFEST.json
  AGENTS.md
  CODEX_DESKTOP_GOAL_PROMPT.md
  .codex/
    config.toml
  docs/
    ai-plan/
      00_INDEX.md
      01_SPEC.md
      02_RESEARCH_BRIEF.md
      03_ARCHITECTURE.md
      04_PRIORITY_PLAN.md
      05_TASK_MATRIX.md
      06_VALIDATION.md
      07_STATUS.md
      08_DECISIONS.md
      09_RISK_REGISTER.md
      10_OPEN_SOURCE_TOOLS.md
      11_HARD_STOP_POLICY.md
      12_LAUNCHD_REMEDIATION.md
      13_LIVE_VALIDATION.md
      14_CODEX_EXECUTION.md
      15_FINAL_ACCEPTANCE.md
  templates/
    evidence-pack/
      manifest.template.json
      phase-report.template.md
      command-ledger.template.jsonl
      not-executed-ledger.template.jsonl
    reports/
      operator-sop.template.md
      final-go-nogo.template.md
      final-validation-matrix.template.md
      next-actions.template.md
  scripts/
    check_plan_tree.sh
    install_to_hermes_home.sh
    print_tree.sh
  ops/                    # Codex will create/implement this
TREE
