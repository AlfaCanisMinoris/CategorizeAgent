from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .agents import CategorizeAgent, PlannerAgent
from .audit import AuditLogger
from .models import Issue, WorkPolicy

ROOT = Path(__file__).resolve().parents[1]
ISSUES_PATH = ROOT / "issues.json"

OUT_DIR = ROOT / "out"
FIX_PLANS_DIR = OUT_DIR / "fix_plans"
AUDIT_DIR = OUT_DIR / "audit_logs"


def _cycle_id() -> str:
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return f"cycle-{ts}"


def main() -> None:
    cycle_id = _cycle_id()

    raw = json.loads(ISSUES_PATH.read_text(encoding="utf-8"))
    issues = [Issue(**x) for x in raw]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIX_PLANS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    audit_cat = AuditLogger(AUDIT_DIR / "audit_log_categorize_agent.jsonl", "CategorizeAgent", cycle_id)
    audit_plan = AuditLogger(AUDIT_DIR / "audit_log_planner_agent.jsonl", "PlannerAgent", cycle_id)

    policy = WorkPolicy(max_groups=5, max_issues_per_group=8, avoid_file_overlap_between_groups=True)

    work_set = CategorizeAgent(policy).run(issues, audit_cat, cycle_id)
    (OUT_DIR / "work_set.json").write_text(work_set.model_dump_json(indent=2), encoding="utf-8")

    plans = PlannerAgent().run(work_set, audit_plan)
    for p in plans:
        (FIX_PLANS_DIR / f"{p.group_id}.json").write_text(p.model_dump_json(indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
