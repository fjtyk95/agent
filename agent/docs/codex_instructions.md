# Codex 指示セット（コピー＆ペースト用）

以下は Codex（または GitHub Copilot Chat）にそのまま貼り付ければ各タスクを自動生成できる粒度で記述したコマンド例です。

## 基本タスク (1-10)

```text
### ⬇️ Task 1: CSV スキーマ dataclass を生成
Create four Python dataclasses named BankMaster, FeeRow, BalanceSnapshot, CashflowRow that exactly match these CSV headers:
- bank_master.csv: bank_id (str), branch_id (str), service_id (str), cut_off_time (str HH:MM)
- fee_table.csv: from_bank (str), service_id (str), amount_bin (str), to_bank (str), to_branch (str), fee (int)
- balance_snapshot.csv: bank_id (str), balance (int)
- cashflow_history.csv: date (str YYYY-MM-DD), bank_id (str), amount (int), direction (str in|out)
Use __all__ and type hints.
```

```text
### ⬇️ Task 2: CSV 読込ユーティリティ
Write `data_load.py` with functions:
- `load_bank_master(path) -> pd.DataFrame`
- `load_fee_table(path) -> pd.DataFrame`
- `load_balance(path) -> pd.DataFrame`
- `load_cashflow(path) -> pd.DataFrame`
Ensure dtype enforcement and raise ValueError on missing columns.
```

```text
### ⬇️ Task 3: Safety Stock 関数
Implement `calc_safety(df_cash, horizon_days=30, quantile=0.95)` that returns a Series indexed by bank_id with required safety stock (int). Assume `df_cash` has columns date, bank_id, amount, direction. Use net outflow (out–in) rolling sum.
```

```text
### ⬇️ Task 4: FeeCalculator クラス
Create `fee.py` with class `FeeCalculator(df_fee: pd.DataFrame)` exposing `get_fee(from_bank, service_id, amount, to_bank, to_branch) -> int`. Select correct amount_bin by amount.
```

```text
### ⬇️ Task 5: MILP モデル構築
In `optimise.py`, build a PuLP model:
- Variables: x[(i,j,s,d)] ≥0, B[(i,d)] ≥0
- Objective: sum(fee(x))+λ*sum(shortfall penalty)
- Constraints: balance propagation, B≥0.
Return dict of transfers and balances.
```

```text
### ⬇️ Task 6: transfer_plan.csv 出力
Write `export.py` with `to_csv(plan, path)`. Columns: execute_date, from_bank, to_bank, service_id, amount, expected_fee.
```

```text
### ⬇️ Task 7: コスト比較チャート
Using matplotlib, plot stacked bar of (baseline cost, optimised cost). Save to /output/cost_comparison.png.
```

```text
### ⬇️ Task 8: Notebook UI
Create `interactive_notebook.ipynb` that loads CSVs, shows ipywidgets sliders (horizon, quantile, lambda), executes optimisation, and displays results + download links.
```

```text
### ⬇️ Task 9: pytest
Generate tests for calc_safety (edge cases: zero flows, all inflows) and FeeCalculator bin selection.
```

```text
### ⬇️ Task 10: README
Draft a README explaining project purpose, setup (`poetry install`), and day‑to‑day usage (step‑by‑step).
```

## v0.2 拡張タスク (11-15)

### Codex 指示例（Task 11–15 完全版）

以下の 5 つのプロンプトを **1 タスクずつ Copilot Chat / ChatGPT Codex** に貼り付けてください。貼り付けた直後に Enter を押せば、各ブランチに必要な雛形コードが生成されます。

```text
# Task 11 – monitor.py で実行時間計測
You are ChatGPT Codex. Create a new file **monitor.py** in the root of the repo.
Requirements:
1. Implement a context manager class `Timer(label: str)` using `time.perf_counter()`.
2. Add `timed_run(fn: Callable, *args, **kwargs) -> Tuple[Any, float]` that executes `fn` and returns the result and elapsed seconds.
3. All timings must be logged via the built‑in `logging` module at INFO level, e.g. "[Timer] <label>: 2.345 sec".
4. Add `if __name__ == "__main__":` demo section.
5. Include type‑hints (Python 3.11) and update **__init__.py** to export `Timer` and `timed_run`.
```

```text
# Task 12 – kpi_logger.py で KPI を JSON 永続化
Create **kpi_logger.py**.
Requirements:
1. Define `KPIRecord` dataclass with fields: timestamp (datetime), total_fee (int), total_shortfall (int), runtime_sec (float).
2. Implement `append_kpi(record: KPIRecord, path: Path = Path("logs/kpi.jsonl"))` which appends the record as a JSON line (ISO 8601 time) and ensures the directory exists.
3. Provide `load_recent(days: int = 30) -> list[KPIRecord]` to read & filter.
4. Unit tests: write to a tmp dir, append two records, verify count.
5. Update README usage.
```

```text
# Task 13 – Cut‑off 時刻制約を MILP に追加
Refactor **optimise.py**.
Requirements:
1. Extend decision variable index with `service_id` cut‑off awareness.
2. For each service, only allow transfers to be executed on day d when its cut‑off (from `bank_master.cut_off_time`) is > 15:00 assumed planning time; otherwise defer to day d+1 automatically.
3. Enforce via binary indicator or by zeroing x[i,j,s,d] when cut‑off miss.
4. Keep model linear.
5. Update tests to cover scenario where G‑service after 15:00 is shifted to next day.
```

```text
# Task 14 – Branch 対応 & i=j 除外
Modify **optimise.py** & related data classes.
Requirements:
1. Introduce `branch_id` dimension for both from_bank & to_bank using existing `bank_master`.
2. Disallow transfers where `from_bank==to_bank and from_branch==to_branch` (no self‑transfer).
3. Adjust fee lookup to include branch.
4. Regenerate fee matrix builder to accommodate 6×6 branches.
5. Maintain solver performance < 60 sec with CBC.
```

```text
# Task 15 – CLI & Poetry Script
Generate **cli.py** and update **pyproject.toml**.
Requirements:
1. `python -m bankoptimize run --balance balance_snapshot.csv --cash cashflow_history.csv --out transfer_plan.csv`
   should execute the full pipeline (load → safety → optimise → export → KPI log).
2. Use `argparse` for CLI.
3. Register a Poetry script `[tool.poetry.scripts] optimize = "bankoptimize.cli:main"`.
4. Add docstring usage example.
5. Provide `tests/test_cli.py` with `pytest` using `click.testing.CliRunner` or `subprocess`.
```

---

© 2025 Mizuho Digital Planning Team