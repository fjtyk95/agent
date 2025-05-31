import pandas as pd
from typing import Iterable

from schemas import BankMaster, FeeRow, BalanceSnapshot, CashflowRow

__all__ = [
    "load_bank_master",
    "load_fee_table",
    "load_balance",
    "load_cashflow",
]


def _validate_columns(df: pd.DataFrame, required: Iterable[str], path: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns {missing} in {path}")


def load_bank_master(path: str) -> pd.DataFrame:
    """Load bank_master.csv enforcing column types."""
    columns = list(BankMaster.__annotations__.keys())
    dtype = {
        "bank_id": str,
        "branch_id": str,
        "service_id": str,
        "cut_off_time": str,
    }
    df = pd.read_csv(path, dtype=dtype)
    _validate_columns(df, columns, path)
    return df[columns]


def load_fee_table(path: str) -> pd.DataFrame:
    """Load fee_table.csv enforcing column types."""
    columns = list(FeeRow.__annotations__.keys())
    dtype = {
        "from_bank": str,
        "service_id": str,
        "amount_bin": str,
        "to_bank": str,
        "to_branch": str,
        "fee": "int64",
    }
    df = pd.read_csv(path, dtype=dtype)
    _validate_columns(df, columns, path)
    return df[columns]


def load_balance(path: str) -> pd.DataFrame:
    """Load balance_snapshot.csv enforcing column types."""
    columns = list(BalanceSnapshot.__annotations__.keys())
    dtype = {
        "bank_id": str,
        "balance": "int64",
    }
    df = pd.read_csv(path, dtype=dtype)
    _validate_columns(df, columns, path)
    return df[columns]


def load_cashflow(path: str) -> pd.DataFrame:
    """Load cashflow_history.csv enforcing column types."""
    columns = list(CashflowRow.__annotations__.keys())
    dtype = {
        "date": str,
        "bank_id": str,
        "amount": "int64",
        "direction": str,
    }
    df = pd.read_csv(path, dtype=dtype)
    _validate_columns(df, columns, path)
    return df[columns]
