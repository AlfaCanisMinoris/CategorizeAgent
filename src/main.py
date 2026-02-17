from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .agents import CategorizeAgent, PlannerAgent
from .audit import AuditLogger
from .models import Issue, WorkPolicy


def _default_cycle_id() -> str:
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return f"cycle-{ts}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="mini-AI-colleague PoC pipeline")
    p.add_argument(
        "--issues",
        type=Path,
        default=Path("issues.json"),
        help="Path to issues.json (default: ./issues.json)",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("out"),
        help="Output directory (default: ./out)",
    )
    p.add_argument(
        "--cycle-id",
        type=str,
        default=None,
        help="Cycle identifier for traceability (default: generated timestamp-based id)",
    )
    p.add_argument("--max-groups", type=int, default=5, help="Max groups in work_set.json")
    p.add_argument("--max-issues-per-group", type=int, default=8, help="Max issues per group")
    p.add_argument(
        "--allow-file-overlap",
        action="store_true",
        help="If set, allows the same file to appear in multiple groups (default: disallow)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    root = Path(__file__).resolve().parents[1]
    issues_path: Path = (root / args.issues) if not args.issues.is_absolute() else args.issues
    out_dir: Path = (root / args.out_dir) if not args.out_dir.is_absolute() else args.out_dir

    cycle_id = args.cycle_id or _default_cycle_id()

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
    (out_dir / "work_set.json").write_text(work_set.model_dump_json(indent=2), encoding="utf-8")

    plans = PlannerAgent().run(work_set, audit_plan)
    for p in plans:
        (fix_plans_dir / f"{p.group_id}.json").write_text(p.model_dump_json(indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
