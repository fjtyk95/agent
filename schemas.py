from dataclasses import dataclass

__all__ = [
    "BankMaster",
    "FeeRow",
    "BalanceSnapshot",
    "CashflowRow",
]

@dataclass
class BankMaster:
    """Schema for bank_master.csv rows."""

    bank_id: str
    branch_id: str
    service_id: str
    cut_off_time: str  # HH:MM


@dataclass
class FeeRow:
    """Schema for fee_table.csv rows."""

    from_bank: str
    service_id: str
    amount_bin: str
    to_bank: str
    to_branch: str
    fee: int


@dataclass
class BalanceSnapshot:
    """Schema for balance_snapshot.csv rows."""

    bank_id: str
    balance: int


@dataclass
class CashflowRow:
    """Schema for cashflow_history.csv rows."""

    date: str  # YYYY-MM-DD
    bank_id: str
    amount: int
    direction: str  # in|out
