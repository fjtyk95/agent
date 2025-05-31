import pandas as pd
import numpy as np


def calc_safety(df_cash: pd.DataFrame, horizon_days: int = 30, quantile: float = 0.95) -> pd.Series:
    """Return required safety stock per bank using rolling net outflow.

    Parameters
    ----------
    df_cash : pd.DataFrame
        Must contain columns ["date", "bank_id", "amount", "direction"].
    horizon_days : int, default 30
        Rolling window size in days.
    quantile : float, default 0.95
        Quantile to compute from rolling net outflows.
    """
    if not {"date", "bank_id", "amount", "direction"}.issubset(df_cash.columns):
        raise ValueError("df_cash missing required columns")

    df = df_cash.copy()
    df["date"] = pd.to_datetime(df["date"])
    # outflow as positive, inflow as negative
    df["net"] = np.where(df["direction"] == "out", df["amount"], -df["amount"])
    df = df.sort_values(["bank_id", "date"])

    def calc_quantile(group: pd.DataFrame) -> float:
        net_roll = (
            group.set_index("date")["net"].rolling(f"{horizon_days}D").sum()
        )
        q = net_roll.quantile(quantile)
        return max(float(q), 0.0)

    safety = df.groupby("bank_id").apply(calc_quantile)
    return safety.astype(int)
