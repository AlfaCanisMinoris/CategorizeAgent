from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

Severity = Literal["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"]
IssueType = Literal["BUG", "VULNERABILITY", "CODE_SMELL"]
Priority = Literal["high", "medium", "low"]


class Issue(BaseModel):
    key: str
    rule: str
    severity: Severity
    type: IssueType
    component: str
    line: Optional[int] = None
    message: str
    status: str
    effort: Optional[int] = None
    tags: List[str] = Field(default_factory=list)


class WorkPolicy(BaseModel):
    max_groups: int = 5
    max_issues_per_group: int = 8
    avoid_file_overlap_between_groups: bool = True


class WorkGroup(BaseModel):
    group_id: str
    name: str
    priority: Priority
    rationale: str
    issue_keys: List[str]
    touched_files: List[str]


class WorkSet(BaseModel):
    cycle_id: str
    generated_at: str
    policy: WorkPolicy
    groups: List[WorkGroup]
    omitted_issue_keys: List[str] = Field(default_factory=list)


class FixStep(BaseModel):
    goal: str
    changes: List[str]
    files: List[str]


class FixPlan(BaseModel):
    group_id: str
    issue_keys: List[str]
    summary: str
    steps: List[FixStep]
