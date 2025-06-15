from __future__ import annotations

import datetime as dt
from typing import Dict, Iterable, Mapping, Tuple

import pulp

# --------------------------------------------------------------------------- #
# Types
# --------------------------------------------------------------------------- #
Bank     = str
Branch   = str
Service  = str
DayLabel = str
XKey     = Tuple[Bank, Branch, Bank, Branch, Service, DayLabel]

__all__ = ["build_model"]


def build_model(
    banks: Iterable[Bank],
    branches: Mapping[Bank, Iterable[Branch]],
    days: Iterable[DayLabel],
    services: Iterable[Service],
    net_cash: Dict[Tuple[Bank, DayLabel], int],
    initial_balance: Dict[Bank, int],
    safety: Dict[Bank, int],
    fee_lookup: Dict[Tuple[Bank, Branch, Bank, Branch, Service], int],
    *,
    cut_off: Dict[Tuple[Bank, Service], str] | None = None,
    lambda_penalty: float = 1.0,
    planning_time: str = "15:00",
) -> Dict[str, Dict]:
    """
    Build and solve the transfer-optimisation MILP.

    Returns
    -------
    dict
        {
          "transfers": { (from_bank, from_branch, to_bank, to_branch, service, day): amount },
          "balance":   { (bank, day): balance_after_settlement },
        }
    """
    banks = list(banks)
    days = list(days)          # preserve order
    services = list(services)
    cut_off = cut_off or {}

    # --------------------------------------------------------------------- #
    # Cut-off判定: 送金が当日 or 翌日 settle するか
    # --------------------------------------------------------------------- #
    plan_time = dt.datetime.strptime(planning_time, "%H:%M").time()

    allow_same_day: Dict[Tuple[Bank, Service], bool] = {
        (b, s): dt.datetime.strptime(t_str, "%H:%M").time() >= plan_time
        if (t_str := cut_off.get((b, s))) is not None
        else True
        for b in banks
        for s in services
    }

    # sender 視点で「この送金がいつ着金するか」をマッピング
    effect_day: Dict[Tuple[Bank, Service, DayLabel], DayLabel] = {}
    for b in banks:
        for s in services:
            for idx, d in enumerate(days):
                if allow_same_day[(b, s)]:
                    effect_day[(b, s, d)] = d
                else:
                    effect_idx = min(idx + 1, len(days) - 1)
                    effect_day[(b, s, d)] = days[effect_idx]

    # --------------------------------------------------------------------- #
    # 変数定義
    # --------------------------------------------------------------------- #
    prob = pulp.LpProblem("fund_transfers", pulp.LpMinimize)

    x: Dict[XKey, pulp.LpVariable] = {}
    for i in banks:
        for ib in branches.get(i, []):
            for j in banks:
                for jb in branches.get(j, []):
                    if i == j and ib == jb:          # 自己送金は不要
                        continue
                    for s in services:
                        for d in days:
                            x[(i, ib, j, jb, s, d)] = pulp.LpVariable(
                                f"x_{i}_{ib}_{j}_{jb}_{s}_{d}", lowBound=0
                            )

    B = pulp.LpVariable.dicts("B", (banks, days), lowBound=0)
    shortfall = pulp.LpVariable.dicts("S", (banks, days), lowBound=0)

    # --------------------------------------------------------------------- #
    # 目的関数: 手数料 + ペナルティ
    # --------------------------------------------------------------------- #
    fee_expr = [
        fee_lookup.get((i, ib, j, jb, s), 0) * var
        for (i, ib, j, jb, s, _), var in x.items()
    ]
    penalty_expr = [shortfall[i][d] for i in banks for d in days]
    prob += pulp.lpSum(fee_expr) + lambda_penalty * pulp.lpSum(penalty_expr)

    # --------------------------------------------------------------------- #
    # 残高更新制約
    # --------------------------------------------------------------------- #
    for i in banks:
        for idx, d in enumerate(days):
            # 着金日が d になる incoming
            incoming = pulp.lpSum(
                var
                for (fb, fbr, tb, tbr, s, dd), var in x.items()
                if tb == i and effect_day[(fb, s, dd)] == d
            )
            # 発信日の outgoing が d に settle
            outgoing = pulp.lpSum(
                var
                for (fb, fbr, tb, tbr, s, dd), var in x.items()
                if fb == i and effect_day[(fb, s, dd)] == d
            )

            net = net_cash.get((i, d), 0)
            prev_balance = (
                initial_balance.get(i, 0) if idx == 0 else B[i][days[idx - 1]]
            )

            prob += (
                B[i][d] == prev_balance + net + incoming - outgoing,
                f"balance_{i}_{d}",
            )
            prob += (
                B[i][d] + shortfall[i][d] >= safety.get(i, 0),
                f"safety_{i}_{d}",
            )

    # --------------------------------------------------------------------- #
    # 求解
    # --------------------------------------------------------------------- #
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    transfers = {k: v.value() for k, v in x.items() if v.value() > 0}
    balances = {(i, d): B[i][d].value() for i in banks for d in days}

    return {"transfers": transfers, "balance": balances}
