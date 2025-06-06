import pandas as pd
from typing import Iterable, Mapping

__all__ = ["to_csv"]

def to_csv(plan: Iterable[Mapping], path: str) -> None:
    """Export transfer plan to CSV.

    Parameters
    ----------
    plan : Iterable[Mapping]
        Iterable of transfer plan records. Each record should provide
        execute_date, from_bank, to_bank, service_id, amount, and
        expected_fee fields.
    path : str
        Destination CSV file path.
    """
    columns = [
        "execute_date",
        "from_bank",
        "to_bank",
        "service_id",
        "amount",
        "expected_fee",
    ]

    df = pd.DataFrame(list(plan))
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns {missing} in plan")

    df = df[columns]
    df.to_csv(path, index=False)
