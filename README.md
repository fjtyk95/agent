# Agent Repository

This project provides helper utilities for handling bank transaction CSV files. It defines CSV schemas using Python dataclasses and provides utilities for loading data, calculating required safety stock, and generating charts.
This project provides a small toolkit for optimising interbank transfers. It focuses on loading transaction data from CSV files, estimating the cash safety stock required at each bank, and building a linear program to minimise transfer fees. Charts and export helpers round out the workflow so that the resulting plan can be visualised or written back to disk.

## Modules

- `schemas.py` — dataclass definitions for each CSV file.
- `data_load.py` — functions to load CSV files with strict dtype enforcement and column validation.
- `safety.py` — `calc_safety` computes safety stock levels based on rolling net outflows.
- `charts.py` — `plot_cost_comparison` creates a stacked bar chart comparing baseline and optimised costs, saved to `/output/cost_comparison.png`.
- `interactive_notebook.ipynb` — Jupyter notebook with sliders to run an optimisation example.
- `schemas.py` — dataclass definitions describing each CSV schema.
- `data_load.py` — utility functions to load CSV files with strict dtype enforcement and column validation.
- `fee.py` — `FeeCalculator` for looking up transaction fees from the fee table.
- `safety.py` — `calc_safety` calculates safety stock levels based on rolling net outflows.
- `optimise.py` — builds and solves the optimisation model using `pulp`.
- `export.py` — writes transfer plans to CSV.
- `charts.py` — `plot_cost_comparison` saves a simple comparison bar chart.
- `kpi_logger.py` — persists optimisation KPI metrics to `logs/kpi.jsonl`.
- `interactive_notebook.ipynb` — Jupyter notebook illustrating an optimisation run.

## Dataclass schema

Each CSV row type is represented as a small dataclass. For example:

```python
@dataclass
class BankMaster:
    bank_id: str
    branch_id: str
    service_id: str
    cut_off_time: str  # HH:MM
```

These classes provide a lightweight schema so that loaded data can be type checked and validated easily.

## Utilities

### Data loading

The functions in `data_load.py` such as `load_bank_master` and `load_cashflow` ensure that columns and types match the expected schema when reading CSV files with pandas.

### Fee calculation

`FeeCalculator` parses a fee table and exposes `get_fee()` to look up the cost of a transfer for a given service and amount range.

### Safety stock estimation

`safety.py` offers `calc_safety` which computes the required minimum balance by taking a rolling sum of net outflows and selecting a quantile.

### Optimisation model

`optimise.py` builds a linear program to plan transfers while minimising fees and penalties for violating safety stock. The solved transfers and balances can then be exported and visualised.

### KPI logging

Use `kpi_logger.append_kpi` to save run metrics such as fees and runtime to `logs/kpi.jsonl`. Recent history can be loaded with `kpi_logger.load_recent()`.

```python
from datetime import datetime
from kpi_logger import KPIRecord, append_kpi

append_kpi(
    KPIRecord(
        timestamp=datetime.now(),
        total_fee=1000,
        total_shortfall=0,
        runtime_sec=2.3,
    )
)
```
kpi_logger.py
新規
+54
-0

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