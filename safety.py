import pandas as pd
from typing import Iterable

__all__ = ["calc_safety"]


_REQUIRED_COLS = {"date", "bank_id", "amount", "direction"}


def _ensure_columns(df: pd.DataFrame) -> None:
    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns {sorted(missing)}")


def _net_amount(row: pd.Series) -> int:
    return row["amount"] if row["direction"] == "out" else -row["amount"]


def calc_safety(df_cash: pd.DataFrame, horizon_days: int = 30, quantile: float = 0.95) -> pd.Series:
    """Return required safety stock per bank as a Series of integers."""
    _ensure_columns(df_cash)

    df = df_cash.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["net"] = df.apply(_net_amount, axis=1)

    # Aggregate by bank and date to ensure daily frequency
    daily = (
        df.groupby(["bank_id", "date"], sort=True)["net"].sum().unstack("bank_id").sort_index()
    )

    # Reindex to daily frequency for each bank
    daily = daily.asfreq("D", fill_value=0)

    safety = {}
    for bank in daily.columns:
        rolling = daily[bank].rolling(horizon_days, min_periods=1).sum()
        level = rolling.quantile(quantile)
        safety[bank] = int(round(level))

    return pd.Series(safety)
