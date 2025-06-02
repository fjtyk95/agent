import pandas as pd
from fee import FeeCalculator
from safety import calc_safety


def test_calc_safety_zero_flow():
    df = pd.DataFrame({
        'date': ['2022-01-01'],
        'bank_id': ['A'],
        'amount': [0],
        'direction': ['out'],
    })
    result = calc_safety(df, horizon_days=1)
    assert result['A'] == 0


def test_calc_safety_all_inflows():
    df = pd.DataFrame({
        'date': ['2022-01-01', '2022-01-02'],
        'bank_id': ['A', 'A'],
        'amount': [100, 200],
        'direction': ['in', 'in'],
    })
    result = calc_safety(df, horizon_days=2)
    assert result['A'] == 0


def test_fee_calculator_bin():
    df_fee = pd.DataFrame({
        'from_bank': ['A'],
        'service_id': ['S'],
        'amount_bin': ['0-100'],
        'to_bank': ['B'],
        'to_branch': ['1'],
        'fee': [10],
    })
    calc = FeeCalculator(df_fee)
    assert calc.get_fee('A', 'S', 50, 'B', '1') == 10
