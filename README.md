# Agent Repository

This repository offers a toolkit for optimising interbank transfers. It contains dataclasses defining each CSV schema, functions for loading data with pandas, utilities to calculate safety stock, an optimisation model built with pulp, and exporters for charts and CSV results.


## Setup

The recommended way to install dependencies is via [Poetry](https://python-poetry.org/):

```bash
poetry install

This will create a virtual environment and install all required packages.

## Day-to-day usage

1. **Prepare CSV files** using the schema definitions in `schemas.py`.
2. **Load data** with the loader functions in `data_load.py`:
   ```python
   from data_load import load_bank_master, load_fee_table, load_balance, load_cashflow
   df_master = load_bank_master("bank_master.csv")
   df_fees = load_fee_table("fee_table.csv")
   df_balance = load_balance("balance_snapshot.csv")
   df_flow = load_cashflow("cashflow_history.csv")
   ```
3. **Calculate safety stock** from historical cash flows:
   ```python
   from safety import calc_safety
   safety = calc_safety(df_flow)
   ```
4. **Optimise transfers** with the MILP model:
   ```python
   from optimise import build_model
   model = build_model(df_master, df_fees, df_balance, safety, lam=1.0)
   model.solve()
   ```
5. **Export plans and charts**:
   ```python
   from export import to_csv
   to_csv(plan, "transfer_plan.csv")
   from charts import plot_cost_comparison
   plot_cost_comparison(baseline, optimised)
   ```

Run tests with:

```bash
poetry run pytest
```

=======
This project provides a small toolkit for optimising interbank transfers. It focuses on loading transaction data from CSV files, estimating the cash safety stock required at each bank, and building a linear program to minimise transfer fees. Charts and export helpers round out the workflow so that the resulting plan can be visualised or written back to disk.

## Modules

- `schemas.py` — dataclass definitions describing each CSV schema.
- `data_load.py` — utility functions to load CSV files with strict dtype enforcement and column validation.
- `fee.py` — `FeeCalculator` for looking up transaction fees from the fee table.
- `safety.py` — `calc_safety` calculates safety stock levels based on rolling net outflows.
- `optimise.py` — builds and solves the optimisation model using `pulp`.
- `export.py` — writes transfer plans to CSV.
- `charts.py` — `plot_cost_comparison` saves a simple comparison bar chart.
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
