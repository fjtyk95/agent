"""Command line interface for bank optimisation.

Example
-------
Run the full pipeline::

    python -m bankoptimize run --balance balance_snapshot.csv \
        --cash cashflow_history.csv --out transfer_plan.csv
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from .data_load import (
    load_bank_master,
    load_fee_table,
    load_balance,
    load_cashflow,
)
from .fee import build_fee_lookup
from .safety import calc_safety
from .optimise import build_model
from .export import to_csv
from .kpi_logger import KPIRecord, append_kpi
from .monitor import Timer


def _run_pipeline(
    master: Path,
    fee_table: Path,
    balance: Path,
    cashflow: Path,
    out: Path,
) -> None:
    """Execute optimisation pipeline and write ``out`` CSV."""
    logging.info("Loading input files")
    df_master = load_bank_master(str(master))
    df_fee = load_fee_table(str(fee_table))
    df_balance = load_balance(str(balance))
    df_cash = load_cashflow(str(cashflow))

    safety = calc_safety(df_cash)

    banks = list(df_master["bank_id"].unique())
    branches = {
        b: list(df_master[df_master["bank_id"] == b]["branch_id"].unique())
        for b in banks
    }
    days = sorted(df_cash["date"].unique())
    services = list(df_master["service_id"].unique())

    df_cash["signed"] = df_cash["amount"] * df_cash["direction"].map({"in": -1, "out": 1})
    net_cash = df_cash.groupby(["bank_id", "date"])["signed"].sum().to_dict()

    initial_balance = df_balance.set_index("bank_id")["balance"].to_dict()
    fee_lookup = build_fee_lookup(df_fee)

    result = build_model(
        banks=banks,
        branches=branches,
        days=days,
        services=services,
        net_cash=net_cash,
        initial_balance=initial_balance,
        safety=safety.to_dict(),
        fee_lookup=fee_lookup,
    )

    plan = []
    for (i, ib, j, jb, s, d), amt in result["transfers"].items():
        if amt is None or amt <= 0:
            continue
        fee = fee_lookup.get((i, ib, j, jb, s), 0) * amt
        plan.append(
            {
                "execute_date": d,
                "from_bank": i,
                "to_bank": j,
                "service_id": s,
                "amount": int(round(amt)),
                "expected_fee": int(round(fee)),
            }
        )

    to_csv(plan, str(out))

    total_fee = sum(row["expected_fee"] for row in plan)
    runtime = Timer("pipeline").elapsed if hasattr(Timer, "elapsed") else 0.0
    append_kpi(
        KPIRecord(
            timestamp=datetime.now(),
            total_fee=int(total_fee),
            total_shortfall=0,
            runtime_sec=float(runtime or 0.0),
        )
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="bankoptimize", description="Optimise interbank transfers")
    sub = parser.add_subparsers(dest="command")
    run_p = sub.add_parser("run", help="execute optimisation pipeline")
    run_p.add_argument("--master", default="bank_master.csv", help="bank master CSV path")
    run_p.add_argument("--fee", default="fee_table.csv", help="fee table CSV path")
    run_p.add_argument("--balance", required=True, help="balance snapshot CSV path")
    run_p.add_argument("--cash", required=True, help="cashflow history CSV path")
    run_p.add_argument("--out", required=True, help="output CSV path")

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    if args.command == "run":
        with Timer("pipeline"):
            _run_pipeline(Path(args.master), Path(args.fee), Path(args.balance), Path(args.cash), Path(args.out))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
