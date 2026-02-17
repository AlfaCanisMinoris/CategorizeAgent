# mini-AI-colleague (Proof of Concept)

This repository implements a small proof-of-concept of a **governed AI colleague pipeline** inspired by NorthCode's AI Colleague concept.

The goal is not raw automation, but **controlled, auditable and explainable decision-making** when triaging and planning fixes for static analysis issues (e.g. SonarQ).

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
