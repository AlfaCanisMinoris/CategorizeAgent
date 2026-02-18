# mini-AI-colleague (Proof of Concept)

Solution to the NorthCode pre-assignment “mini-AI-colleague”.
Repository name on GitHub: **CategorizeAgent**.
---

## Purpose

This PoC demonstrates:

- Deterministic triage and grouping of issues
- Policy-driven decision making
- Separation of responsibilities between agents
- Full audit trail in JSONL format
- Safe planning without automatic code changes
- End-to-end test coverage

The system does **not** modify source code. It only generates structured work sets and fix plans.

---

## High-Level Architecture

```mermaid
flowchart TD
    A[Load issues.json] --> B[CategorizeAgent]
    B --> C[write: out/work_set.json]
    B --> G[write: out/audit_logs/audit_log_categorize_agent.jsonl]
    C --> D[PlannerAgent]
    D --> E[write: out/fix_plans/*.json]
    D --> P[write: out/audit_logs/audit_log_planner_agent.jsonl]

----

## Setup

Option A (recommended):
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

Option B (simple):

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt


----

## Demo (bash)

Copy/paste:

```bash
python -m src.main --help | head -n 25

rm -rf /tmp/demo_out
python -m src.main --issues data/issues.json --out-dir /tmp/demo_out --cycle-id demo
ls -R /tmp/demo_out

cat /tmp/demo_out/work_set.json | head -n 40
tail -n 3 /tmp/demo_out/audit_logs/audit_log_categorize_agent.jsonl
cat /tmp/demo_out/fix_plans/group-1.json

pytest -q

rm -rf /tmp/out1 /tmp/out2
python -m src.main --issues data/issues.json --out-dir /tmp/out1 --cycle-id proof --generated-at 2026-02-17T00:00:00Z
python -m src.main --issues data/issues.json --out-dir /tmp/out2 --cycle-id proof --generated-at 2026-02-17T00:00:00Z
diff -u /tmp/out1/work_set.json /tmp/out2/work_set.json && echo "OK: deterministic"
