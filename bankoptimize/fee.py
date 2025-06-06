"""Utilities to calculate transfer fees."""

from __future__ import annotations

import pandas as pd
import re

__all__ = ["FeeCalculator", "build_fee_lookup"]


class FeeCalculator:
    """Lookup fees from a fee table DataFrame.

    Parameters
    ----------
    df_fee : pd.DataFrame
        DataFrame containing columns [from_bank, from_branch, service_id,
        amount_bin, to_bank, to_branch, fee]. The ``amount_bin`` column should
        specify ranges as "low-high" or open-ended as "low+".
    """

    def __init__(self, df_fee: pd.DataFrame) -> None:
        required = [
            "from_bank",
            "from_branch",
            "service_id",
            "amount_bin",
            "to_bank",
            "to_branch",
            "fee",
        ]
        missing = [c for c in required if c not in df_fee.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        self.df_fee = df_fee.copy()
        # Parse amount_bin into numerical ranges
        bounds = self.df_fee["amount_bin"].apply(self._parse_bin)
        self.df_fee["_low"] = bounds.str[0]
        self.df_fee["_high"] = bounds.str[1]

    @staticmethod
    def _parse_bin(bin_str: str) -> tuple[int, float]:
        """Return (lower, upper] from an amount_bin string."""
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", bin_str)
        if m:
            return int(m.group(1)), float(m.group(2))
        m = re.match(r"^(\d+)\+?$", bin_str)
        if m:
            return int(m.group(1)), float("inf")
        raise ValueError(f"Invalid amount_bin: {bin_str}")

    def get_fee(
        self,
        from_bank: str,
        from_branch: str,
        service_id: str,
        amount: int,
        to_bank: str,
        to_branch: str,
    ) -> int:
        """Return fee for given transaction parameters."""
        df = self.df_fee
        mask = (
            (df["from_bank"] == from_bank)
            & (df["from_branch"] == from_branch)
            & (df["service_id"] == service_id)
            & (df["to_bank"] == to_bank)
            & (df["to_branch"] == to_branch)
            & (amount >= df["_low"])
            & (amount <= df["_high"])
        )
        rows = df.loc[mask]
        if rows.empty:
            raise KeyError("No fee rule matches the given inputs")
        return int(rows.iloc[0]["fee"])


def build_fee_lookup(df_fee: pd.DataFrame) -> Dict[Tuple[str, str, str, str, str], int]:
    """Return mapping from (from_bank, from_branch, to_bank, to_branch, service) to fee."""
    calc = FeeCalculator(df_fee)
    lookup: Dict[Tuple[str, str, str, str, str], int] = {}
    for _, row in df_fee.iterrows():
        key = (
            row["from_bank"],
            row["from_branch"],
            row["to_bank"],
            row["to_branch"],
            row["service_id"],
        )
        # Use upper bound of first bin to compute per-unit fee approx if needed
        lookup[key] = int(row["fee"])
    return lookup
