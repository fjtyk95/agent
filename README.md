# Agent Repository

This repository provides helper utilities for loading bank-related CSV files and calculating required safety stock levels.

- **schemas.py**: Defines dataclasses describing each CSV schema.
- **data_load.py**: Functions to load each CSV with strict dtype enforcement and column validation.
- **safety.py**: Implements `calc_safety` to compute safety stock based on rolling net outflows.
