import pandas as pd
from fee import FeeCalculator
from safety import calc_safety


def test_calc_safety_zero_flows():
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02"],
        "bank_id": ["A", "A"],
        "amount": [0, 0],
        "direction": ["out", "in"],
    })
    result = calc_safety(df, horizon_days=2, quantile=0.95)
    assert result.loc["A"] == 0


def test_calc_safety_all_inflows():
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02"],
        "bank_id": ["A", "A"],
        "amount": [100, 200],
        "direction": ["in", "in"],
    })
    result = calc_safety(df, horizon_days=2, quantile=0.95)
    assert result.loc["A"] == 0


def test_fee_calculator_bin_selection():
    df_fee = pd.DataFrame({
        "from_bank": ["A", "A"],
        "from_branch": ["Y", "Y"],
        "service_id": ["S", "S"],
        "amount_bin": ["0-100", "100+"],
        "to_bank": ["B", "B"],
        "to_branch": ["X", "X"],
        "fee": [10, 20],
    })
    calc = FeeCalculator(df_fee)
    assert calc.get_fee("A", "Y", "S", 50, "B", "X") == 10
    assert calc.get_fee("A", "Y", "S", 100, "B", "X") == 20
    assert calc.get_fee("A", "Y", "S", 150, "B", "X") == 20
