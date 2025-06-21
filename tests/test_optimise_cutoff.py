import unittest
from optimise import build_model

class TestCutoffConstraint(unittest.TestCase):
    def test_cutoff_defers_transfer(self) -> None:
        banks = ["A", "B"]
        days = ["D1", "D2"]
        services = ["G"]
        net_cash = {("B", "D1"): -50}
        initial_balance = {"A": 100, "B": 0}
        safety = {"A": 0, "B": 0}
        fee_lookup = {("A", "B", "G"): 0}
        cut_off = {("A", "G"): "14:00"}

        branches = {"A": ["A1"], "B": ["B1"]}
        fee_lookup = {("A", "A1", "B", "B1", "G"): 0}
        
        result = build_model(
            banks=banks,
            branches=branches,
            days=days,
            services=services,
            net_cash=net_cash,
            initial_balance=initial_balance,
            safety=safety,
            fee_lookup=fee_lookup,
            cut_off=cut_off,
            lambda_penalty=1.0,
        )

        transfers = result["transfers"]
        self.assertEqual(transfers[("A", "A1", "B", "B1", "G", "D1")], 0)
        self.assertGreaterEqual(transfers[("A", "A1", "B", "B1", "G", "D2")], 50)


if __name__ == "__main__":
    unittest.main()
