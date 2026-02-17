from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class AuditLogger:
    path: Path
    agent: str
    cycle_id: str

    def log(self, action: str, details: Dict[str, Any], reasoning: Optional[str] = None) -> None:
        event: Dict[str, Any] = {
            "timestamp": utc_now_iso(),
            "agent": self.agent,
            "cycle_id": self.cycle_id,
            "action": action,
            "details": details,
        }
        if reasoning:
            event["reasoning"] = reasoning

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
