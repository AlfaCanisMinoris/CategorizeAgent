from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_end_to_end_run_creates_outputs():
    root = Path(__file__).resolve().parents[1]

    # Run pipeline
    result = subprocess.run(
        [sys.executable, "-m", "src.main"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    out_dir = root / "out"
    assert (out_dir / "work_set.json").exists()
    assert (out_dir / "audit_logs" / "audit_log_categorize_agent.jsonl").exists()
    assert (out_dir / "audit_logs" / "audit_log_planner_agent.jsonl").exists()
    assert (out_dir / "fix_plans").exists()

    work_set = json.loads((out_dir / "work_set.json").read_text(encoding="utf-8"))
    groups = work_set["groups"]
    plan_files = sorted((out_dir / "fix_plans").glob("group-*.json"))

    # 1 plan per group
    assert len(plan_files) == len(groups)

    # No file overlap between groups (policy intent)
    all_files = []
    for g in groups:
        all_files.extend(g["touched_files"])
    assert len(all_files) == len(set(all_files)), "Same file appears in multiple groups"
