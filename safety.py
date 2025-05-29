import pandas as pd


def calc_safety(df_cash: pd.DataFrame, horizon_days: int = 30, quantile: float = 0.95) -> pd.Series:
    """Calculate safety stock by bank based on historical cashflows.

    Parameters
    ----------
    df_cash : pd.DataFrame
        DataFrame with columns ``date``, ``bank_id``, ``amount``, ``direction``.
    horizon_days : int, default 30
        Window size for rolling net outflow.
    quantile : float, default 0.95
        Quantile of rolling outflows to use for safety stock.
    """
    required = {"date", "bank_id", "amount", "direction"}
    missing = required - set(df_cash.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df = df_cash.copy()
    df["date"] = pd.to_datetime(df["date"])

    df["signed"] = df["amount"] * df["direction"].map({"out": -1, "in": 1})
    df.sort_values(["bank_id", "date"], inplace=True)

    net_outflow = (
        df.groupby("bank_id")["signed"]
        .rolling(f"{horizon_days}D", on=df["date"])
        .sum()
        .groupby(level=0)
        .apply(lambda x: x.clip(upper=0))
    )

    safety = net_outflow.groupby(level=0).quantile(quantile).abs().astype("int64")
    return safety
