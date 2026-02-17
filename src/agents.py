from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .audit import AuditLogger, utc_now_iso
from .models import FixPlan, FixStep, Issue, WorkGroup, WorkPolicy, WorkSet

_SEV_ORDER = {"BLOCKER": 0, "CRITICAL": 1, "MAJOR": 2, "MINOR": 3, "INFO": 4}


def _priority_from_severity(sev: str) -> str:
    if sev in ("BLOCKER", "CRITICAL"):
        return "high"
    if sev == "MAJOR":
        return "medium"
    return "low"


def _worst_severity(severities: List[str]) -> str:
    # Smaller order value = worse severity
    return sorted(severities, key=lambda s: _SEV_ORDER.get(s, 99))[0]


@dataclass
class CategorizeAgent:
    policy: WorkPolicy

    def run(self, issues: List[Issue], audit: AuditLogger, cycle_id: str) -> WorkSet:
        audit.log("run_started", {"issue_count": len(issues)}, "Start triage and grouping.")

        open_issues = [i for i in issues if i.status in ("OPEN", "REOPENED")]
        audit.log(
            "filtered",
            {"kept": len(open_issues), "dropped": len(issues) - len(open_issues)},
            "Keep only OPEN/REOPENED issues for this cycle.",
        )

        # Sort by severity (worse first) then effort (higher first)
        open_issues.sort(key=lambda i: (_SEV_ORDER.get(i.severity, 99), -(i.effort or 0)))

        groups: List[WorkGroup] = []
        omitted: List[str] = []

        file_to_group: Dict[str, int] = {}  # file -> group index
        group_issue_counts: List[int] = []
        group_severities: List[List[str]] = []  # per group list of severities (for priority)

        def can_add(gidx: int) -> bool:
            return group_issue_counts[gidx] < self.policy.max_issues_per_group

        def refresh_group_metadata(gidx: int) -> None:
            # Update priority + name based on worst severity in group
            worst = _worst_severity(group_severities[gidx])
            prio = _priority_from_severity(worst)
            f = groups[gidx].touched_files[0]
            groups[gidx].priority = prio  # type: ignore
            groups[gidx].name = f"{prio.capitalize()} issues in {f}"
            groups[gidx].rationale = (
                f"Grouped by file path to reduce merge-conflict risk; "
                f"worst severity in group: {worst}."
            )

        for issue in open_issues:
            f = issue.component

            # If file already in a group, add there (avoid cross-group conflicts)
            if f in file_to_group:
                gidx = file_to_group[f]
                if can_add(gidx):
                    groups[gidx].issue_keys.append(issue.key)
                    group_issue_counts[gidx] += 1
                    group_severities[gidx].append(issue.severity)
                    refresh_group_metadata(gidx)

                    audit.log(
                        "issue_assigned",
                        {"issue_key": issue.key, "group_id": groups[gidx].group_id, "file": f, "severity": issue.severity},
                        "Same file as existing group; assign to avoid cross-group conflicts.",
                    )
                else:
                    omitted.append(issue.key)
                    audit.log(
                        "issue_omitted",
                        {"issue_key": issue.key, "reason": "max_issues_per_group", "file": f, "severity": issue.severity},
                        "Group for this file is full per policy.",
                    )
                continue

            # New file needs a new group
            if len(groups) >= self.policy.max_groups:
                omitted.append(issue.key)
                audit.log(
                    "issue_omitted",
                    {"issue_key": issue.key, "reason": "max_groups", "file": f, "severity": issue.severity},
                    "Reached max_groups limit.",
                )
                continue

            group_id = f"group-{len(groups) + 1}"
            prio = _priority_from_severity(issue.severity)
            name = f"{prio.capitalize()} issues in {f}"
            rationale = (
                "Grouped by file path to reduce merge-conflict risk; "
                f"worst severity in group: {issue.severity}."
            )

            wg = WorkGroup(
                group_id=group_id,
                name=name,
                priority=prio,  # type: ignore
                rationale=rationale,
                issue_keys=[issue.key],
                touched_files=[f],
            )
            groups.append(wg)
            group_issue_counts.append(1)
            group_severities.append([issue.severity])
            file_to_group[f] = len(groups) - 1

            audit.log(
                "group_created",
                {"group_id": group_id, "issue_keys": [issue.key], "touched_files": [f], "worst_severity": issue.severity},
                rationale,
            )

        ws = WorkSet(
            cycle_id=cycle_id,
            generated_at=utc_now_iso(),
            policy=self.policy,
            groups=groups,
            omitted_issue_keys=omitted,
        )

        audit.log(
            "run_completed",
            {"groups": len(groups), "omitted": len(omitted)},
            "Completed grouping run.",
        )
        return ws


@dataclass
class PlannerAgent:
    def run(self, work_set: WorkSet, audit: AuditLogger) -> List[FixPlan]:
        plans: List[FixPlan] = []
        audit.log("run_started", {"group_count": len(work_set.groups)}, "Start planning for groups.")

        for g in work_set.groups:
            audit.log("plan_started", {"group_id": g.group_id, "issue_keys": g.issue_keys}, "Create fix plan.")

            steps: List[FixStep] = []
            for f in g.touched_files:
                steps.append(
                    FixStep(
                        goal=f"Address issues in {f}",
                        changes=[
                            "Identify the exact rule violations at the referenced line(s).",
                            "Apply minimal, low-risk refactor/fix to satisfy the Sonar rule.",
                            "Run unit tests and update/add tests if behavior changes.",
                        ],
                        files=[f],
                    )
                )

            plan = FixPlan(
                group_id=g.group_id,
                issue_keys=g.issue_keys,
                summary=f"Plan to address {g.priority} priority issues in '{g.name}'.",
                steps=steps,
            )
            plans.append(plan)

            audit.log(
                "plan_created",
                {"group_id": g.group_id, "steps": len(steps), "files": g.touched_files, "priority": g.priority},
                "Generated per-file steps to keep changes reviewable and reduce conflicts.",
            )

        audit.log("run_completed", {"plan_count": len(plans)}, "Completed planning run.")
        return plans
