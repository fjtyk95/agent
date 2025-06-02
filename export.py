import pandas as pd

__all__ = ["to_csv"]

COLUMNS = [
    "execute_date",
    "from_bank",
    "to_bank",
    "service_id",
    "amount",
    "expected_fee",
]

def to_csv(plan: pd.DataFrame, path: str) -> None:
    """Write transfer plan to CSV with fixed column order."""
    plan[COLUMNS].to_csv(path, index=False)
