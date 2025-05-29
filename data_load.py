import pandas as pd
from typing import Iterable

from schemas import BankMaster, FeeRow, BalanceSnapshot, CashflowRow


def _validate_columns(df: pd.DataFrame, required: Iterable[str]):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")


def load_bank_master(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={
        'bank_id': str,
        'branch_id': str,
        'service_id': str,
        'cut_off_time': str,
    })
    _validate_columns(df, BankMaster.__annotations__.keys())
    return df


def load_fee_table(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={
        'from_bank': str,
        'service_id': str,
        'amount_bin': str,
        'to_bank': str,
        'to_branch': str,
        'fee': 'int64',
    })
    _validate_columns(df, FeeRow.__annotations__.keys())
    return df


def load_balance(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={
        'bank_id': str,
        'balance': 'int64',
    })
    _validate_columns(df, BalanceSnapshot.__annotations__.keys())
    return df


def load_cashflow(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={
        'date': str,
        'bank_id': str,
        'amount': 'int64',
        'direction': str,
    })
    _validate_columns(df, CashflowRow.__annotations__.keys())
    return df
