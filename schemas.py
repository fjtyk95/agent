from dataclasses import dataclass

__all__ = [
    "BankMaster",
    "FeeRow",
    "BalanceSnapshot",
    "CashflowRow",
]


@dataclass
class BankMaster:
    bank_id: str
    branch_id: str
    service_id: str
    cut_off_time: str  # HH:MM


@dataclass
class FeeRow:
    from_bank: str
    service_id: str
    amount_bin: str
    to_bank: str
    to_branch: str
    fee: int


@dataclass
class BalanceSnapshot:
    bank_id: str
    balance: int


@dataclass
class CashflowRow:
    date: str  # YYYY-MM-DD
    bank_id: str
    amount: int
    direction: str  # in|out
