"""Tests for optimization module focusing on MILP model correctness."""

import pytest
import pandas as pd
from datetime import datetime, timedelta

import optimise


class TestOptimizationModel:
    """Test the optimization model behavior under various scenarios."""
    
    def test_basic_optimization_no_shortfall(self):
        """Test basic optimization with sufficient initial balances."""
        banks = ["A", "B"]
        branches = {"A": ["001"], "B": ["001"]}
        days = ["2025-06-08", "2025-06-09"]
        services = ["G"]
        
        # No net cash flows, adequate initial balances, no safety requirements
        net_cash = {(bank, day): 0 for bank in banks for day in days}
        initial_balance = {"A": 100000, "B": 100000}
        safety = {"A": 0, "B": 0}
        fee_lookup = {("A", "001", "B", "001", "G"): 220}
        
        result = optimise.build_model(
            banks=banks,
            branches=branches,
            days=days,
            services=services,
            net_cash=net_cash,
            initial_balance=initial_balance,
            safety=safety,
            fee_lookup=fee_lookup
        )
        
        # Should be no transfers needed
        transfers = result["transfers"]
        balances = result["balance"]
        
        # Check that all transfers are 0 or near 0
        total_transfers = sum(amount for amount in transfers.values())
        assert total_transfers == 0 or total_transfers < 1e-6
        
        # Check balances remain as expected
        assert abs(balances[("A", "2025-06-08")] - 100000) < 1e-6
        assert abs(balances[("B", "2025-06-08")] - 100000) < 1e-6
    
    def test_optimization_with_safety_requirement(self):
        """Test optimization when safety stocks require transfers."""
        banks = ["A", "B"]
        branches = {"A": ["001"], "B": ["001"]}
        days = ["2025-06-08"]
        services = ["G"]
        
        net_cash = {("A", "2025-06-08"): 0, ("B", "2025-06-08"): 0}
        initial_balance = {"A": 100000, "B": 10000}  # B has low balance
        safety = {"A": 50000, "B": 80000}  # B needs more safety stock
        fee_lookup = {("A", "001", "B", "001", "G"): 220}
        
        result = optimise.build_model(
            banks=banks,
            branches=branches,
            days=days,
            services=services,
            net_cash=net_cash,
            initial_balance=initial_balance,
            safety=safety,
            fee_lookup=fee_lookup
        )
        
        transfers = result["transfers"]
        balances = result["balance"]
        
        # Should have transfer from A to B to meet B's safety requirement
        total_transfers = sum(amount for amount in transfers.values())
        assert total_transfers > 0
        
        # Check safety constraints are met (balance + shortfall >= safety)
        assert balances[("A", "2025-06-08")] >= safety["A"] - 1e-6
        assert balances[("B", "2025-06-08")] >= safety["B"] - 1e-6
    
    def test_optimization_with_net_cash_outflow(self):
        """Test optimization with significant cash outflows."""
        banks = ["A", "B"]
        branches = {"A": ["001"], "B": ["001"]}
        days = ["2025-06-08"]
        services = ["G"]
        
        # Bank B has large outflow, Bank A has surplus
        net_cash = {("A", "2025-06-08"): 50000, ("B", "2025-06-08"): -80000}
        initial_balance = {"A": 200000, "B": 50000}
        safety = {"A": 100000, "B": 50000}
        fee_lookup = {("A", "001", "B", "001", "G"): 220}
        
        result = optimise.build_model(
            banks=banks,
            branches=branches,
            days=days,
            services=services,
            net_cash=net_cash,
            initial_balance=initial_balance,
            safety=safety,
            fee_lookup=fee_lookup
        )
        
        transfers = result["transfers"]
        balances = result["balance"]
        
        # Bank B should receive transfer to cover outflow and maintain safety
        expected_b_balance = 50000 - 80000  # initial - outflow = -30000
        # Since balance can't be negative, B needs at least 80000 + 50000 = 130000
        
        # Should have positive transfer amount
        total_transfers = sum(amount for amount in transfers.values())
        assert total_transfers > 0
        
        # Final balances should meet safety requirements
        assert balances[("B", "2025-06-08")] >= safety["B"] - 1e-6
    
    def test_cutoff_constraint_effect(self):
        """Test that cut-off time constraints defer transfers appropriately."""
        banks = ["A", "B"]
        branches = {"A": ["001"], "B": ["001"]}
        days = ["2025-06-08", "2025-06-09"]
        services = ["G"]
        
        # B needs cash on day 1
        net_cash = {
            ("A", "2025-06-08"): 0,
            ("A", "2025-06-09"): 0,
            ("B", "2025-06-08"): -50000,
            ("B", "2025-06-09"): 0,
        }
        initial_balance = {"A": 100000, "B": 20000}
        safety = {"A": 0, "B": 0}
        fee_lookup = {("A", "001", "B", "001", "G"): 220}
        
        # Test with cut-off that prevents same-day transfer
        cut_off = {("A", "G"): "14:00"}  # Cut-off before planning time (15:00)
        
        result = optimise.build_model(
            banks=banks,
            branches=branches,
            days=days,
            services=services,
            net_cash=net_cash,
            initial_balance=initial_balance,
            safety=safety,
            fee_lookup=fee_lookup,
            cut_off=cut_off,
            planning_time="15:00"
        )
        
        transfers = result["transfers"]
        
        # Transfer should be scheduled for next day due to cut-off
        day1_transfers = sum(
            amount for (fb, fbr, tb, tbr, s, d), amount in transfers.items()
            if d == "2025-06-08" and fb == "A" and tb == "B"
        )
        day2_transfers = sum(
            amount for (fb, fbr, tb, tbr, s, d), amount in transfers.items()
            if d == "2025-06-09" and fb == "A" and tb == "B"
        )
        
        # Due to cut-off, transfer should be minimal on day 1
        assert day1_transfers < 1e-6
        # And significant on day 2 to compensate
        assert day2_transfers > 0
    
    def test_multiple_branches_optimization(self):
        """Test optimization with multiple branches per bank."""
        banks = ["A", "B"]
        branches = {"A": ["001", "002"], "B": ["001", "002"]}
        days = ["2025-06-08"]
        services = ["G"]
        
        net_cash = {("A", "2025-06-08"): 0, ("B", "2025-06-08"): -100000}
        initial_balance = {"A": 200000, "B": 50000}
        safety = {"A": 50000, "B": 50000}
        
        # Different fees for different branch combinations
        fee_lookup = {
            ("A", "001", "B", "001", "G"): 220,
            ("A", "001", "B", "002", "G"): 330,
            ("A", "002", "B", "001", "G"): 330,
            ("A", "002", "B", "002", "G"): 440,
        }
        
        result = optimise.build_model(
            banks=banks,
            branches=branches,
            days=days,
            services=services,
            net_cash=net_cash,
            initial_balance=initial_balance,
            safety=safety,
            fee_lookup=fee_lookup
        )
        
        transfers = result["transfers"]
        
        # Should choose the lowest fee route (A-001 to B-001)
        optimal_transfer = transfers.get(("A", "001", "B", "001", "G", "2025-06-08"), 0)
        suboptimal_transfer = transfers.get(("A", "002", "B", "002", "G", "2025-06-08"), 0)
        
        # Optimal route should be preferred
        assert optimal_transfer >= suboptimal_transfer
    
    def test_multi_day_balance_continuity(self):
        """Test that balances are correctly carried forward across days."""
        banks = ["A"]
        branches = {"A": ["001"]}
        days = ["2025-06-08", "2025-06-09", "2025-06-10"]
        services = ["G"]
        
        # Progressive outflows over multiple days
        net_cash = {
            ("A", "2025-06-08"): -10000,
            ("A", "2025-06-09"): -15000,
            ("A", "2025-06-10"): -20000,
        }
        initial_balance = {"A": 100000}
        safety = {"A": 0}
        fee_lookup = {}  # No transfers possible, just balance tracking
        
        result = optimise.build_model(
            banks=banks,
            branches=branches,
            days=days,
            services=services,
            net_cash=net_cash,
            initial_balance=initial_balance,
            safety=safety,
            fee_lookup=fee_lookup
        )
        
        balances = result["balance"]
        
        # Check balance progression
        expected_day1 = 100000 - 10000  # 90000
        expected_day2 = expected_day1 - 15000  # 75000
        expected_day3 = expected_day2 - 20000  # 55000
        
        assert abs(balances[("A", "2025-06-08")] - expected_day1) < 1e-6
        assert abs(balances[("A", "2025-06-09")] - expected_day2) < 1e-6
        assert abs(balances[("A", "2025-06-10")] - expected_day3) < 1e-6
    
    def test_lambda_penalty_effect(self):
        """Test that lambda penalty affects shortfall tolerance."""
        banks = ["A"]
        branches = {"A": ["001"]}
        days = ["2025-06-08"]
        services = ["G"]
        
        # Scenario where safety stock cannot be met
        net_cash = {("A", "2025-06-08"): -80000}
        initial_balance = {"A": 50000}
        safety = {"A": 100000}  # Impossible to meet
        fee_lookup = {}  # No transfers available
        
        # Test with low penalty (should allow shortfall)
        result_low = optimise.build_model(
            banks=banks,
            branches=branches,
            days=days,
            services=services,
            net_cash=net_cash,
            initial_balance=initial_balance,
            safety=safety,
            fee_lookup=fee_lookup,
            lambda_penalty=0.1
        )
        
        # Test with high penalty (should minimize shortfall more aggressively)
        result_high = optimise.build_model(
            banks=banks,
            branches=branches,
            days=days,
            services=services,
            net_cash=net_cash,
            initial_balance=initial_balance,
            safety=safety,
            fee_lookup=fee_lookup,
            lambda_penalty=10.0
        )
        
        # Both should complete without error
        assert "balance" in result_low
        assert "balance" in result_high
        
        # Balance after outflow should be the same (no transfers available)
        expected_balance = 50000 - 80000  # -30000 (or 0 if non-negative constraint)
        assert result_low["balance"][("A", "2025-06-08")] >= -1e-6  # Balance >= 0
        assert result_high["balance"][("A", "2025-06-08")] >= -1e-6  # Balance >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])