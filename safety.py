import math
import pandas as pd
from typing import Iterable

__all__ = ["calc_safety"]


def _validate_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")


def calc_safety(
    df_cash: pd.DataFrame, horizon_days: int = 30, quantile: float = 0.95
) -> pd.Series:
    """Calculate safety stock per bank.

    Parameters
    ----------
    df_cash: DataFrame with columns date, bank_id, amount, direction
    horizon_days: rolling window size in days
    quantile: percentile of rolling net outflow
    """
    req = ["date", "bank_id", "amount", "direction"]
    _validate_columns(df_cash, req)

    df = df_cash.copy()
    df["date"] = pd.to_datetime(df["date"])
    sign = df["direction"].map({"out": 1, "in": -1})
    if sign.isna().any():
        raise ValueError("direction must be 'in' or 'out'")
    df["signed"] = df["amount"] * sign
    df = df.sort_values(["bank_id", "date"])

    rolled = (
        df.set_index("date")
        .groupby("bank_id")["signed"]
        .rolling(f"{horizon_days}D")
        .sum()
    )

    safety = rolled.groupby("bank_id").quantile(quantile).fillna(0)
    # round up to integer safety stock
    return safety.apply(lambda x: int(math.ceil(x)))
