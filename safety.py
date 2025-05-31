import pandas as pd

__all__ = ["calc_safety"]

def calc_safety(
    df_cash: pd.DataFrame,
    horizon_days: int = 30,
    quantile: float = 0.95
) -> pd.Series:
    """Return required safety stock per bank.

    Parameters
    ----------
    df_cash : pd.DataFrame
        DataFrame with columns ['date', 'bank_id', 'amount', 'direction']
    horizon_days : int, default 30
        Rolling window size in days.
    quantile : float, default 0.95
        Quantile to compute from rolling net outflows.
    """
    required_cols = {"date", "bank_id", "amount", "direction"}
    if not required_cols.issubset(df_cash.columns):
        missing = required_cols - set(df_cash.columns)
        raise ValueError(f"Missing columns {missing}")

    df = df_cash.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["bank_id", "date"])

    direction_map = {"out": 1, "in": -1}
    if not set(df["direction"]).issubset(direction_map.keys()):
        raise ValueError("direction column must contain only 'in' or 'out'")
    df["net"] = df["amount"] * df["direction"].map(direction_map)

    window = f"{horizon_days}D"
    rolling = (
        df.set_index("date")
        .groupby("bank_id")["net"]
        .rolling(window, min_periods=1)
        .sum()
        .reset_index()
    )
    quant = rolling.groupby("bank_id")["net"].quantile(quantile)

    # Safety stock cannot be negative
    quant = quant.clip(lower=0)
    return quant.round().astype(int)
