import pulp
from typing import Iterable, Dict, Tuple
from datetime import datetime


def build_model(
    banks: Iterable[str],
    days: Iterable[str],
    services: Iterable[str],
    net_cash: Dict[Tuple[str, str], int],
    initial_balance: Dict[str, int],
    safety: Dict[str, int],
    fee_lookup: Dict[Tuple[str, str, str], int],
    cut_off: Dict[Tuple[str, str], str] | None = None,
    lambda_penalty: float = 1.0,
    planning_time: str = "15:00",
) -> Dict[str, Dict[Tuple[str, str, str, str], float]]:
    """Build and solve transfer optimisation model.

    Parameters
    ----------
    banks : Iterable[str]
        Bank identifiers.
    days : Iterable[str]
        Ordered sequence of day labels.
    services : Iterable[str]
        Service identifiers.
    net_cash : Dict[Tuple[str, str], int]
        Net cash flow per (bank, day).
    initial_balance : Dict[str, int]
        Starting balance per bank.
    safety : Dict[str, int]
        Required minimum balance per bank.
    fee_lookup : Dict[Tuple[str, str, str], int]
        Mapping of (from_bank, to_bank, service) to unit fee.
    cut_off : Dict[Tuple[str, str], str], optional
        Mapping of (bank_id, service_id) to HH:MM cut-off time.
        Transfers scheduled after ``planning_time`` settle on the next day.
    lambda_penalty : float, default 1.0
        Weight for safety shortfall penalty.
    planning_time : str, default "15:00"
        Time of day when planning decisions are assumed to occur.

    Returns
    -------
    Dict[str, Dict]
        Transfers and balances keyed by variable tuples.
    """
    banks = list(banks)
    days = list(days)
    services = list(services)

    cut_off = cut_off or {}
    plan_time = datetime.strptime(planning_time, "%H:%M").time()
    allow_same_day: Dict[Tuple[str, str], bool] = {}
    for b in banks:
        for s in services:
            t_str = cut_off.get((b, s))
            if t_str is None:
                allow_same_day[(b, s)] = True
            else:
                allow_same_day[(b, s)] = datetime.strptime(t_str, "%H:%M").time() >= plan_time

    # Map each (from_bank, service, day) to the day when funds settle
    effect_day: Dict[Tuple[str, str, str], str] = {}
    for b in banks:
        for s in services:
            for idx, d in enumerate(days):
                if allow_same_day[(b, s)]:
                    effect_day[(b, s, d)] = d
                else:
                    effect_idx = min(idx + 1, len(days) - 1)
                    effect_day[(b, s, d)] = days[effect_idx]

    prob = pulp.LpProblem("fund_transfers", pulp.LpMinimize)

    x = pulp.LpVariable.dicts(
        "x", (banks, banks, services, days), lowBound=0
    )
    B = pulp.LpVariable.dicts("B", (banks, days), lowBound=0)
    shortfall = pulp.LpVariable.dicts("S", (banks, days), lowBound=0)

    fee_expr = [
        fee_lookup.get((i, j, s), 0) * x[i][j][s][d]
        for i in banks
        for j in banks
        for s in services
        for d in days
    ]

    penalty_expr = [shortfall[i][d] for i in banks for d in days]

    prob += pulp.lpSum(fee_expr) + lambda_penalty * pulp.lpSum(penalty_expr)

    for i in banks:
        for idx, d in enumerate(days):
            incoming = pulp.lpSum(
                x[j][i][s][dp]
                for j in banks
                for s in services
                for dp in days
                if effect_day[(j, s, dp)] == d
            )
            outgoing = pulp.lpSum(
                x[i][j][s][dp]
                for j in banks
                for s in services
                for dp in days
                if effect_day[(i, s, dp)] == d
            )
            net = net_cash.get((i, d), 0)
            if idx == 0:
                prev = initial_balance.get(i, 0)
            else:
                prev = B[i][days[idx - 1]]
            prob += B[i][d] == prev + net + incoming - outgoing
            prob += B[i][d] + shortfall[i][d] >= safety.get(i, 0)

    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    transfers = {
        (i, j, s, d): x[i][j][s][d].value()
        for i in banks
        for j in banks
        for s in services
        for d in days
    }
    balances = {(i, d): B[i][d].value() for i in banks for d in days}

    return {"transfers": transfers, "balance": balances}
