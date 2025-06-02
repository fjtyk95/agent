from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

__all__ = ["KPIRecord", "append_kpi", "load_recent"]


@dataclass
class KPIRecord:
    timestamp: datetime
    total_fee: int
    total_shortfall: int
    runtime_sec: float


def append_kpi(record: KPIRecord, path: Path = Path("logs/kpi.jsonl")) -> None:
    """Append a KPI record to ``path`` in JSON-lines format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(record)
    data["timestamp"] = record.timestamp.isoformat()
    with path.open("a", encoding="utf-8") as f:
        json.dump(data, f)
        f.write("\n")


def load_recent(days: int = 30, path: Path = Path("logs/kpi.jsonl")) -> List[KPIRecord]:
    """Return records newer than ``days`` days from ``path``."""
    if not path.exists():
        return []
    cutoff = datetime.now() - timedelta(days=days)
    records: List[KPIRecord] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            ts = datetime.fromisoformat(d["timestamp"])
            if ts >= cutoff:
                records.append(
                    KPIRecord(
                        timestamp=ts,
                        total_fee=int(d["total_fee"]),
                        total_shortfall=int(d["total_shortfall"]),
                        runtime_sec=float(d["runtime_sec"]),
                    )
                )
    return records
