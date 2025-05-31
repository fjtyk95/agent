# Agent Repository

This repository defines CSV schemas using Python dataclasses and provides utilities for loading data, calculating required safety stock, and generating charts.

## Modules

- **schemas.py**: Dataclass definitions for each CSV file.
- **data_load.py**: Functions to load CSV files with strict dtype enforcement and column validation.
- **safety.py**: Implements `calc_safety` to compute safety stock levels based on rolling net outflows.
- **charts.py**: Contains `plot_cost_comparison` to create a stacked bar chart comparing baseline and optimised costs, saved as `/output/cost_comparison.png`.
