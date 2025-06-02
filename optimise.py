from __future__ import annotations

from typing import Dict, Tuple
import pandas as pd
import pulp

from fee import FeeCalculator

__all__ = ["build_model"]


def build_model(
    df_master: pd.DataFrame,
    df_fee: pd.DataFrame,
    df_balance: pd.DataFrame,
    safety: pd.Series,
    lam: float = 1.0,
) -> Tuple[pulp.LpProblem, Dict[str, Dict[Tuple[str, str, str, str], float]]]:
    """Build MILP model for transfer optimisation."""
    fee_calc = FeeCalculator(df_fee)
    banks = df_master["bank_id"].unique().tolist()
    services = df_master["service_id"].unique().tolist()

    dates = df_balance.index.tolist() if isinstance(df_balance.index, pd.DatetimeIndex) else [0]
    model = pulp.LpProblem("transfer_plan", pulp.LpMinimize)

    x = pulp.LpVariable.dicts("x", [(i, j, s, d) for i in banks for j in banks for s in services for d in dates], lowBound=0)
    B = pulp.LpVariable.dicts("B", [(i, d) for i in banks for d in dates], lowBound=0)

    model += pulp.lpSum(
        fee_calc.get_fee(i, s, x[(i, j, s, d)], j, df_master[df_master["bank_id"] == j]["branch_id"].iloc[0])
        for i in banks for j in banks for s in services for d in dates
    ) + lam * pulp.lpSum(B[(i, d)] - safety.get(i, 0) for i in banks for d in dates)

    # Placeholder constraints for example
    for i in banks:
        for d in dates:
            model += B[(i, d)] >= safety.get(i, 0)

    return model, {"x": x, "B": B}
