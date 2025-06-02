# Agent Repository

This project provides a small toolkit for optimising interbank transfers. It focuses on loading transaction data from CSV files, estimating the cash safety stock required at each bank, and building a linear program to minimise transfer fees. Charts and export helpers round out the workflow so that the resulting plan can be visualised or written back to disk.

## Modules

- `schemas.py` — dataclass definitions describing each CSV schema.
- `data_load.py` — utility functions to load CSV files with strict dtype enforcement and column validation.
- `fee.py` — `FeeCalculator` for looking up transaction fees from the fee table.
- `safety.py` — `calc_safety` calculates safety stock levels based on rolling net outflows.
- `optimise.py` — builds and solves the optimisation model using `pulp`.
- `export.py` — writes transfer plans to CSV.
- `charts.py` — `plot_cost_comparison` saves a simple comparison bar chart.
- `kpi_logger.py` — persists optimisation KPI metrics to `logs/kpi.jsonl`.
- `monitor.py` — timing utilities with a `Timer` context manager and `timed_run`.
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

### Timing utilities

`monitor.Timer` and `monitor.timed_run` help measure execution time and log the result at INFO level.
