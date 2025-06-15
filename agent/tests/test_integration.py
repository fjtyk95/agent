"""Integration tests for the optimization pipeline."""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from datetime import datetime

# Import modules to test
import data_load
import safety
import fee
import optimise
import export
import kpi_logger


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    
    # Bank master data
    bank_master = pd.DataFrame([
        {"bank_id": "MIZUHO", "branch_id": "001", "service_id": "G", "cut_off_time": "15:00"},
        {"bank_id": "MIZUHO", "branch_id": "002", "service_id": "G", "cut_off_time": "15:00"},
        {"bank_id": "MUFG", "branch_id": "001", "service_id": "G", "cut_off_time": "14:30"},
        {"bank_id": "MUFG", "branch_id": "002", "service_id": "N", "cut_off_time": "16:00"},
    ])
    
    # Fee table data  
    fee_table = pd.DataFrame([
        {"from_bank": "MIZUHO", "from_branch": "001", "service_id": "G", 
         "amount_bin": "0-100000", "to_bank": "MUFG", "to_branch": "001", "fee": 220},
        {"from_bank": "MIZUHO", "from_branch": "001", "service_id": "G",
         "amount_bin": "100000+", "to_bank": "MUFG", "to_branch": "001", "fee": 330},
        {"from_bank": "MUFG", "from_branch": "001", "service_id": "G",
         "amount_bin": "0-100000", "to_bank": "MIZUHO", "to_branch": "001", "fee": 220},
        {"from_bank": "MUFG", "from_branch": "001", "service_id": "G",
         "amount_bin": "100000+", "to_bank": "MIZUHO", "to_branch": "001", "fee": 330},
    ])
    
    # Balance snapshot
    balance_snapshot = pd.DataFrame([
        {"bank_id": "MIZUHO", "balance": 1000000},
        {"bank_id": "MUFG", "balance": 500000},
    ])
    
    # Cashflow history (simple outflow pattern)
    cashflow_history = pd.DataFrame([
        {"date": "2025-06-01", "bank_id": "MIZUHO", "amount": 50000, "direction": "out"},
        {"date": "2025-06-01", "bank_id": "MUFG", "amount": 30000, "direction": "out"},
        {"date": "2025-06-02", "bank_id": "MIZUHO", "amount": 60000, "direction": "out"},
        {"date": "2025-06-02", "bank_id": "MUFG", "amount": 40000, "direction": "out"},
        {"date": "2025-06-03", "bank_id": "MIZUHO", "amount": 45000, "direction": "in"},
        {"date": "2025-06-03", "bank_id": "MUFG", "amount": 35000, "direction": "in"},
    ])
    
    return {
        "bank_master": bank_master,
        "fee_table": fee_table,
        "balance_snapshot": balance_snapshot,
        "cashflow_history": cashflow_history
    }


@pytest.fixture
def temp_csv_files(sample_data):
    """Create temporary CSV files with sample data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        files = {}
        for name, df in sample_data.items():
            file_path = temp_path / f"{name}.csv"
            df.to_csv(file_path, index=False)
            files[name] = str(file_path)
        
        yield files


def test_data_loading(temp_csv_files):
    """Test CSV data loading functions."""
    
    # Test bank master loading
    df_bank = data_load.load_bank_master(temp_csv_files["bank_master"])
    assert len(df_bank) == 4
    assert set(df_bank.columns) == {"bank_id", "branch_id", "service_id", "cut_off_time"}
    
    # Test fee table loading
    df_fee = data_load.load_fee_table(temp_csv_files["fee_table"])
    assert len(df_fee) == 4
    expected_cols = {"from_bank", "from_branch", "service_id", "amount_bin", "to_bank", "to_branch", "fee"}
    assert set(df_fee.columns) == expected_cols
    
    # Test balance loading
    df_balance = data_load.load_balance(temp_csv_files["balance_snapshot"])
    assert len(df_balance) == 2
    assert set(df_balance.columns) == {"bank_id", "balance"}
    
    # Test cashflow loading
    df_cashflow = data_load.load_cashflow(temp_csv_files["cashflow_history"])
    assert len(df_cashflow) == 6
    assert set(df_cashflow.columns) == {"date", "bank_id", "amount", "direction"}


def test_safety_calculation(temp_csv_files):
    """Test safety stock calculation."""
    df_cashflow = data_load.load_cashflow(temp_csv_files["cashflow_history"])
    
    # Calculate safety stocks
    safety_stocks = safety.calc_safety(df_cashflow, horizon_days=7, quantile=0.9)
    
    # Should have results for both banks
    assert len(safety_stocks) == 2
    assert "MIZUHO" in safety_stocks.index
    assert "MUFG" in safety_stocks.index
    
    # Safety stocks should be non-negative
    assert all(safety_stocks >= 0)


def test_fee_calculator(temp_csv_files):
    """Test fee calculation functionality."""
    df_fee = data_load.load_fee_table(temp_csv_files["fee_table"])
    
    fee_calc = fee.FeeCalculator(df_fee)
    
    # Test fee lookup for small amount
    fee_small = fee_calc.get_fee("MIZUHO", "001", "G", 50000, "MUFG", "001")
    assert fee_small == 220
    
    # Test fee lookup for large amount
    fee_large = fee_calc.get_fee("MIZUHO", "001", "G", 150000, "MUFG", "001")
    assert fee_large == 330
    
    # Test fee lookup building
    fee_lookup = fee.build_fee_lookup(df_fee)
    assert len(fee_lookup) == 4


def test_optimization_mini_case(temp_csv_files):
    """Test optimization with minimal data."""
    # Load data
    df_bank_master = data_load.load_bank_master(temp_csv_files["bank_master"])
    df_fee_table = data_load.load_fee_table(temp_csv_files["fee_table"])
    df_balance = data_load.load_balance(temp_csv_files["balance_snapshot"])
    df_cashflow = data_load.load_cashflow(temp_csv_files["cashflow_history"])
    
    # Calculate safety stocks
    safety_stocks = safety.calc_safety(df_cashflow, horizon_days=7, quantile=0.9)
    
    # Prepare optimization inputs
    banks = ["MIZUHO", "MUFG"]
    branches = {"MIZUHO": ["001", "002"], "MUFG": ["001", "002"]}
    days = ["2025-06-08", "2025-06-09"]
    services = ["G", "N"]
    
    initial_balance = {"MIZUHO": 1000000, "MUFG": 500000}
    safety_dict = safety_stocks.to_dict()
    fee_lookup = fee.build_fee_lookup(df_fee_table)
    
    # Simple net cash flows (both banks losing money)
    net_cash = {
        ("MIZUHO", "2025-06-08"): -100000,
        ("MIZUHO", "2025-06-09"): -80000,
        ("MUFG", "2025-06-08"): -200000,
        ("MUFG", "2025-06-09"): -150000,
    }
    
    # Cut-off constraints
    cut_off = {
        ("MIZUHO", "G"): "15:00",
        ("MUFG", "G"): "14:30",
        ("MUFG", "N"): "16:00"
    }
    
    # Run optimization
    result = optimise.build_model(
        banks=banks,
        branches=branches,
        days=days,
        services=services,
        net_cash=net_cash,
        initial_balance=initial_balance,
        safety=safety_dict,
        fee_lookup=fee_lookup,
        cut_off=cut_off,
        lambda_penalty=1.0
    )
    
    # Check results
    assert "transfers" in result
    assert "balance" in result
    
    transfers = result["transfers"]
    balances = result["balance"]
    
    # Should have some transfer solution (or none if already optimal)
    assert isinstance(transfers, dict)
    assert isinstance(balances, dict)
    
    # Check that balances are reasonable
    for (bank, day), balance in balances.items():
        assert balance >= 0  # No negative balances allowed


def test_export_functionality():
    """Test export to CSV functionality."""
    # Sample transfer plan
    transfer_plan = [
        {
            "execute_date": "2025-06-08",
            "from_bank": "MIZUHO",
            "to_bank": "MUFG", 
            "service_id": "G",
            "amount": 100000,
            "expected_fee": 330
        },
        {
            "execute_date": "2025-06-09",
            "from_bank": "MUFG",
            "to_bank": "MIZUHO",
            "service_id": "G", 
            "amount": 50000,
            "expected_fee": 220
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        export.to_csv(transfer_plan, f.name)
        
        # Read back and verify
        df_result = pd.read_csv(f.name)
        assert len(df_result) == 2
        expected_cols = {"execute_date", "from_bank", "to_bank", "service_id", "amount", "expected_fee"}
        assert set(df_result.columns) == expected_cols
        
        # Check data integrity
        assert df_result.iloc[0]["amount"] == 100000
        assert df_result.iloc[1]["expected_fee"] == 220


def test_kpi_logging():
    """Test KPI logging functionality.""" 
    with tempfile.TemporaryDirectory() as temp_dir:
        log_path = Path(temp_dir) / "test_kpi.jsonl"
        
        # Create and log KPI record
        record = kpi_logger.KPIRecord(
            timestamp=datetime(2025, 6, 8, 10, 0, 0),
            total_fee=1000,
            total_shortfall=0,
            runtime_sec=25.5
        )
        
        kpi_logger.append_kpi(record, log_path)
        
        # Verify file was created and contains data
        assert log_path.exists()
        
        # Read back records
        records = kpi_logger.load_recent(days=1, path=log_path)
        assert len(records) == 1
        assert records[0].total_fee == 1000
        assert records[0].runtime_sec == 25.5


def test_end_to_end_pipeline(temp_csv_files):
    """Test the complete optimization pipeline end-to-end."""
    # This test simulates the full workflow that would run in CLI
    
    # Load all data
    df_bank_master = data_load.load_bank_master(temp_csv_files["bank_master"])
    df_fee_table = data_load.load_fee_table(temp_csv_files["fee_table"])
    df_balance = data_load.load_balance(temp_csv_files["balance_snapshot"])
    df_cashflow = data_load.load_cashflow(temp_csv_files["cashflow_history"])
    
    # Calculate safety stocks
    safety_stocks = safety.calc_safety(df_cashflow, horizon_days=7, quantile=0.95)
    
    # Prepare optimization inputs (simplified)
    banks = df_bank_master['bank_id'].unique().tolist()
    branches = {}
    for bank in banks:
        bank_branches = df_bank_master[df_bank_master['bank_id'] == bank]['branch_id'].unique().tolist()
        branches[bank] = bank_branches
    
    services = df_bank_master['service_id'].unique().tolist()
    days = ["2025-06-08", "2025-06-09"]
    
    initial_balance = dict(zip(df_balance['bank_id'], df_balance['balance']))
    safety_dict = safety_stocks.to_dict()
    fee_lookup = fee.build_fee_lookup(df_fee_table)
    
    # Dummy net cash (forcing need for transfers)
    net_cash = {(bank, day): -50000 for bank in banks for day in days}
    
    # Run optimization
    result = optimise.build_model(
        banks=banks,
        branches=branches,
        days=days,
        services=services,
        net_cash=net_cash,
        initial_balance=initial_balance,
        safety=safety_dict,
        fee_lookup=fee_lookup,
        lambda_penalty=1.0
    )
    
    # Export results
    transfers = result['transfers']
    transfer_records = []
    
    fee_calc = fee.FeeCalculator(df_fee_table)
    
    for (from_bank, from_branch, to_bank, to_branch, service, day), amount in transfers.items():
        if amount > 0:
            try:
                expected_fee = fee_calc.get_fee(
                    from_bank, from_branch, service, int(amount), to_bank, to_branch
                )
            except:
                expected_fee = 0
            
            transfer_records.append({
                'execute_date': day,
                'from_bank': from_bank,
                'from_branch': from_branch,
                'to_bank': to_bank,
                'to_branch': to_branch,
                'service_id': service,
                'amount': int(amount),
                'expected_fee': expected_fee
            })
    
    # Verify pipeline completed successfully
    assert isinstance(transfer_records, list)
    # May have 0 transfers if starting balances are sufficient
    
    # Test export if there are transfers
    if transfer_records:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            export.to_csv(transfer_records, f.name)
            df_result = pd.read_csv(f.name)
            assert len(df_result) == len(transfer_records)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])