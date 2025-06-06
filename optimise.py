import pulp
from typing import Iterable, Dict, Tuple, Mapping


def build_model(
    banks: Iterable[str],
    branches: Mapping[str, Iterable[str]],
    days: Iterable[str],
    services: Iterable[str],
    net_cash: Dict[Tuple[str, str], int],
    initial_balance: Dict[str, int],
    safety: Dict[str, int],
    fee_lookup: Dict[Tuple[str, str, str, str, str], int],
    lambda_penalty: float = 1.0,
) -> Dict[str, Dict[Tuple[str, str, str, str, str, str], float]]:
    """Build and solve transfer optimisation model.

    Parameters
    ----------
    banks : Iterable[str]
        Bank identifiers.
    branches : Mapping[str, Iterable[str]]
        Branch identifiers for each bank.
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
    fee_lookup : Dict[Tuple[str, str, str, str, str], int]
        Mapping of (from_bank, from_branch, to_bank, to_branch, service) to unit fee.
    lambda_penalty : float, default 1.0
        Weight for safety shortfall penalty.

    Returns
    -------
    Dict[str, Dict]
        Transfers and balances keyed by variable tuples.
    """
    banks = list(banks)
    days = list(days)
    services = list(services)

    prob = pulp.LpProblem("fund_transfers", pulp.LpMinimize)

    x: Dict[Tuple[str, str, str, str, str, str], pulp.LpVariable] = {}
    for i in banks:
        for ib in branches.get(i, []):
            for j in banks:
                for jb in branches.get(j, []):
                    if i == j and ib == jb:
                        continue
                    for s in services:
                        for d in days:
                            x[(i, ib, j, jb, s, d)] = pulp.LpVariable(
                                f"x_{i}_{ib}_{j}_{jb}_{s}_{d}", lowBound=0
                            )
    B = pulp.LpVariable.dicts("B", (banks, days), lowBound=0)
    shortfall = pulp.LpVariable.dicts("S", (banks, days), lowBound=0)

    fee_expr = [
        fee_lookup.get((i, ib, j, jb, s), 0) * var
        for (i, ib, j, jb, s, d), var in x.items()
    ]

    penalty_expr = [shortfall[i][d] for i in banks for d in days]

    prob += pulp.lpSum(fee_expr) + lambda_penalty * pulp.lpSum(penalty_expr)

    for i in banks:
        for idx, d in enumerate(days):
            incoming = pulp.lpSum(
                var
                for (fb, fbr, tb, tbr, s, dd), var in x.items()
                if tb == i and dd == d
            )
            outgoing = pulp.lpSum(
                var
                for (fb, fbr, tb, tbr, s, dd), var in x.items()
                if fb == i and dd == d
            )
            net = net_cash.get((i, d), 0)
            if idx == 0:
                prev = initial_balance.get(i, 0)
            else:
                prev = B[i][days[idx - 1]]
            prob += B[i][d] == prev + net + incoming - outgoing
            prob += B[i][d] + shortfall[i][d] >= safety.get(i, 0)

    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    transfers = {key: var.value() for key, var in x.items()}
    balances = {(i, d): B[i][d].value() for i in banks for d in days}

    return {"transfers": transfers, "balance": balances}
