from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import List

__all__ = ["KPIRecord", "append_kpi", "load_recent"]


@dataclass
class KPIRecord:
    timestamp: datetime
    total_fee: int
    total_shortfall: int
    runtime_sec: float


LOG_PATH = Path("logs/kpi.jsonl")


def append_kpi(record: KPIRecord, path: Path = LOG_PATH) -> None:
    """Append a KPI record as a JSON line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(record)
    data["timestamp"] = record.timestamp.isoformat()
    with path.open("a", encoding="utf-8") as f:
        json.dump(data, f)
        f.write("\n")


def load_recent(days: int = 30, path: Path = LOG_PATH) -> List[KPIRecord]:
    """Load records newer than ``days`` from ``path``."""
    if not path.exists():
        return []
    threshold = datetime.now() - timedelta(days=days)
    records: List[KPIRecord] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            ts = datetime.fromisoformat(data["timestamp"])
            if ts >= threshold:
                records.append(
                    KPIRecord(
                        timestamp=ts,
                        total_fee=int(data["total_fee"]),
                        total_shortfall=int(data["total_shortfall"]),
                        runtime_sec=float(data["runtime_sec"]),
                    )
                )
    return records
