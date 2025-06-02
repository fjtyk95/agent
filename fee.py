from __future__ import annotations

import pandas as pd
import re

__all__ = ["FeeCalculator"]

class FeeCalculator:
    """Lookup transaction fees from a fee table DataFrame."""

    def __init__(self, df_fee: pd.DataFrame) -> None:
        required = [
            "from_bank",
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
        bounds = self.df_fee["amount_bin"].apply(self._parse_bin)
        self.df_fee["_low"] = bounds.str[0]
        self.df_fee["_high"] = bounds.str[1]

    @staticmethod
    def _parse_bin(bin_str: str) -> tuple[int, float]:
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
        service_id: str,
        amount: int,
        to_bank: str,
        to_branch: str,
    ) -> int:
        df = self.df_fee
        mask = (
            (df["from_bank"] == from_bank)
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
