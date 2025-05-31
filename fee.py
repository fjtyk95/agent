import pandas as pd

__all__ = ["FeeCalculator"]

class FeeCalculator:
    """Lookup transaction fees from a fee table DataFrame."""

    def __init__(self, df_fee: pd.DataFrame) -> None:
        self.df = df_fee.copy()

    def _parse_bin(self, bin_str: str) -> tuple:
        """Return lower and upper bounds for an amount_bin string."""
        if bin_str.endswith('+'):
            lower = int(bin_str[:-1])
            return lower, float('inf')
        if '-' in bin_str:
            lower, upper = bin_str.split('-', 1)
            return int(lower), int(upper)
        raise ValueError(f"Invalid amount_bin {bin_str}")

    def get_fee(
        self,
        from_bank: str,
        service_id: str,
        amount: int,
        to_bank: str,
        to_branch: str,
    ) -> int:
        """Return fee for a transaction."""
        df_match = self.df[
            (self.df["from_bank"] == from_bank)
            & (self.df["service_id"] == service_id)
            & (self.df["to_bank"] == to_bank)
            & (self.df["to_branch"] == to_branch)
        ]
        for _, row in df_match.iterrows():
            lower, upper = self._parse_bin(row["amount_bin"])
            if lower <= amount < upper:
                return int(row["fee"])
        raise ValueError("No fee found for given parameters")
