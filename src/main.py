from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .agents import CategorizeAgent, PlannerAgent
from .audit import AuditLogger
from .models import Issue, WorkPolicy


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_cycle_id() -> str:
    return f"cycle-{_utc_now_iso()}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="mini-AI-colleague PoC pipeline")

    p.add_argument("--issues", type=Path, default=Path("issues.json"),
                   help="Path to issues.json (default: ./issues.json)")
    p.add_argument("--out-dir", type=Path, default=Path("out"),
                   help="Output directory (default: ./out)")

    p.add_argument("--cycle-id", type=str, default=None,
                   help="Cycle identifier (default: generated timestamp-based id)")

    p.add_argument("--generated-at", type=str, default=None,
                   help="Override generated_at timestamp in work_set.json (for fully reproducible runs)")

    p.add_argument("--max-groups", type=int, default=5, help="Maximum number of groups")
    p.add_argument("--max-issues-per-group", type=int, default=8, help="Maximum issues per group")
    p.add_argument("--allow-file-overlap", action="store_true",
                   help="Allow same file to appear in multiple groups (default: disallow)")

    return p.parse_args()


def main() -> None:
    args = parse_args()

    root = Path(__file__).resolve().parents[1]
    issues_path = args.issues if args.issues.is_absolute() else (root / args.issues)
    out_dir = args.out_dir if args.out_dir.is_absolute() else (root / args.out_dir)

    cycle_id = args.cycle_id or _default_cycle_id()
    generated_at = args.generated_at or _utc_now_iso()

    raw = json.loads(issues_path.read_text(encoding="utf-8"))
    issues = [Issue(**x) for x in raw]

    fix_plans_dir = out_dir / "fix_plans"
    audit_dir = out_dir / "audit_logs"

    out_dir.mkdir(parents=True, exist_ok=True)
    fix_plans_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    audit_cat = AuditLogger(audit_dir / "audit_log_categorize_agent.jsonl", "CategorizeAgent", cycle_id)
    audit_plan = AuditLogger(audit_dir / "audit_log_planner_agent.jsonl", "PlannerAgent", cycle_id)

    policy = WorkPolicy(
        max_groups=args.max_groups,
        max_issues_per_group=args.max_issues_per_group,
        avoid_file_overlap_between_groups=not args.allow_file_overlap,
    )

    work_set = CategorizeAgent(policy).run(issues, audit_cat, cycle_id)

    # Force deterministic generated_at when provided (or use current time)
    ws_dict = work_set.model_dump()
    ws_dict["generated_at"] = generated_at
    (out_dir / "work_set.json").write_text(json.dumps(ws_dict, indent=2), encoding="utf-8")

    plans = PlannerAgent().run(work_set, audit_plan)
    for plan in plans:
        (fix_plans_dir / f"{plan.group_id}.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
