# Agent Repository

This project provides helper utilities for handling bank transaction CSV files. It defines CSV schemas using Python dataclasses and provides utilities for loading data, calculating required safety stock, and generating charts.

## Modules

- `schemas.py` — dataclass definitions for each CSV file.
- `data_load.py` — functions to load CSV files with strict dtype enforcement and column validation.
- `safety.py` — `calc_safety` computes safety stock levels based on rolling net outflows.
- `charts.py` — `plot_cost_comparison` creates a stacked bar chart comparing baseline and optimised costs, saved to `/output/cost_comparison.png`.
- `interactive_notebook.ipynb` — Jupyter notebook with sliders to run an optimisation example.
