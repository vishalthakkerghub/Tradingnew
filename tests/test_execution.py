import unittest
import pandas as pd
import numpy as np
from src.execution_engine import ExecutionEngine

class TestExecutionEngine(unittest.TestCase):
    """
    Unit tests for ExecutionEngine trade planning and simulation logic.
    """
    def setUp(self):
        self.config = {
            "system": {
                "default_capital": 1000000.0
            },
            "risk_management": {
                "risk_per_trade_pct": 0.01,
                "max_allocation_per_stock_pct": 0.25,
                "max_stop_pct": 0.08
            }
        }
        self.engine = ExecutionEngine(self.config)

    def test_calculate_trade_setup_uncapped(self):
        """
        Verify position size and stop placement when final contraction low is within the 8% stop cap.
        """
        # Pivot = 100.0, Contraction Low = 95.0. Stop distance is 5% (<= 8%). Stop loss should be 95.0.
        # Capital = 1,000,000. Risk = 1% (10,000 INR). Risk per share = 5.0. Shares = 2,000.
        setup = self.engine.calculate_trade_setup(
            symbol="TEST",
            pivot_price=100.0,
            contraction_low=95.0
        )
        self.assertEqual(setup["Entry_Price"], 100.0)
        self.assertEqual(setup["Stop_Loss"], 95.0)
        self.assertEqual(setup["Risk_Per_Share"], 5.0)
        self.assertEqual(setup["Position_Size"], 2000)
        self.assertEqual(setup["Trade_Status"], "PENDING_BREAKOUT")

    def test_calculate_trade_setup_capped(self):
        """
        Verify that stop loss is capped at 8% even if contraction low is deeper.
        """
        # Pivot = 100.0, Contraction Low = 90.0. Stop distance is 10%.
        # Capped at 8%, so Stop Loss should be 92.0.
        # Risk per share = 8.0. Shares = 10,000 / 8.0 = 1,250.
        setup = self.engine.calculate_trade_setup(
            symbol="TEST",
            pivot_price=100.0,
            contraction_low=90.0
        )
        self.assertEqual(setup["Stop_Loss"], 92.0)
        self.assertEqual(setup["Risk_Per_Share"], 8.0)
        self.assertEqual(setup["Position_Size"], 1250)

    def test_calculate_trade_setup_allocation_cap(self):
        """
        Verify position size is capped at 25% max allocation of capital.
        """
        # Pivot = 100.0, Contraction Low = 99.5. Stop distance is 0.5%. Risk per share = 0.5.
        # Target shares = 10,000 / 0.5 = 20,000 shares (Value = 2,000,000 INR).
        # Capped at 25% allocation: 250,000 INR / 100.0 = 2,500 shares.
        setup = self.engine.calculate_trade_setup(
            symbol="TEST",
            pivot_price=100.0,
            contraction_low=99.5
        )
        self.assertEqual(setup["Position_Size"], 2500)

    def test_simulate_trade_stopped_out(self):
        """
        Verify exit on hitting structural stop loss.
        """
        dates = pd.date_range(start="2026-01-01", periods=10)
        # Entry at index 2 (Day 3). Price is 100.0. Stop is 95.0.
        # Day 4 (index 3) low goes to 94.0 -> Stopped out at 95.0.
        data = {
            "Open":  [100.0] * 10,
            "High":  [101.0] * 10,
            "Low":   [99.0] * 10,
            "Close": [100.0] * 10
        }
        df = pd.DataFrame(data, index=dates)
        # Inject low on Day 4 below stop
        df.loc[df.index[3], "Low"] = 94.0

        res = self.engine.simulate_trade(
            stock_df=df,
            entry_idx=2,
            entry_price=100.0,
            stop_loss=95.0
        )
        self.assertEqual(res["trade_status"], "STOPPED_OUT")
        self.assertEqual(res["exit_price"], 95.0)
        self.assertEqual(res["days_active"], 1)
        self.assertEqual(res["reason"], "Stop loss hit")
        self.assertTrue(res["total_pnl"] < 0)

    def test_simulate_trade_time_exit(self):
        """
        Verify exit after 15 days if stock fails to gain 10% (sluggish breakout).
        """
        dates = pd.date_range(start="2026-01-01", periods=20)
        # Entry at index 1. Trade active for 15 days (index 2 to 16).
        # Prices hover at 101.0 (1% gain), never touching 110.0 (10% gain).
        data = {
            "Open":  [100.0] * 20,
            "High":  [102.0] * 20,
            "Low":   [98.0] * 20,
            "Close": [101.0] * 20
        }
        df = pd.DataFrame(data, index=dates)

        res = self.engine.simulate_trade(
            stock_df=df,
            entry_idx=1,
            entry_price=100.0,
            stop_loss=95.0
        )
        self.assertEqual(res["trade_status"], "TIME_EXIT")
        self.assertEqual(res["exit_price"], 101.0)
        self.assertEqual(res["days_active"], 15)
        self.assertIn("Sluggish breakout", res["reason"])

    def test_simulate_trade_power_play_breakeven(self):
        """
        Verify stop raises to breakeven after 10% gain within 3 weeks, and is stopped out there.
        """
        dates = pd.date_range(start="2026-01-01", periods=20)
        # Entry at index 1.
        # Day 4 (index 5) high goes to 111.0 (gain > 10%). Stop raises to 100.0 (breakeven).
        # Day 6 (index 7) low goes to 99.0 -> Stopped out at breakeven (100.0).
        data = {
            "Open":  [100.0] * 20,
            "High":  [101.0] * 20,
            "Low":   [99.0] * 20,
            "Close": [100.0] * 20
        }
        df = pd.DataFrame(data, index=dates)
        df.loc[df.index[5], "High"] = 111.0
        df.loc[df.index[6], "Low"] = 101.0
        df.loc[df.index[7], "Low"] = 99.0

        res = self.engine.simulate_trade(
            stock_df=df,
            entry_idx=1,
            entry_price=100.0,
            stop_loss=95.0
        )
        self.assertEqual(res["trade_status"], "STOPPED_OUT")
        self.assertEqual(res["exit_price"], 100.0) # Breakeven exit
        self.assertEqual(res["days_active"], 6)
        self.assertAlmostEqual(res["total_pnl"], 0.0)
        self.assertAlmostEqual(res["final_r_multiple"], 0.0)

    def test_simulate_trade_partial_profit_and_10ema(self):
        """
        Verify selling 50% at 20% gain, raising remaining stop to breakeven, and trailing out with 10 EMA.
        """
        dates = pd.date_range(start="2026-01-01", periods=10)
        # Entry at index 1.
        # Day 3 (index 4) high goes to 121.0 -> Partial profit triggers (sells 50% at 120.0). Stop moves to breakeven (100.0).
        # Day 4 (index 5) closes below 10 EMA -> Trailing stop triggers, exits remaining 50% at Close.
        # Closes: [100, 100, 101, 102, 118, 118, 104, 104, 104, 104]
        closes = [100.0] * 10
        closes[2] = 101.0
        closes[3] = 102.0
        closes[4] = 118.0
        closes[5] = 118.0
        closes[6] = 104.0
        closes[7] = 104.0
        closes[8] = 104.0
        closes[9] = 104.0
        
        highs = list(closes)
        highs[4] = 121.0 # High touches 21% gain on Day 3
        
        lows = [c - 2.0 for c in closes]

        df = pd.DataFrame({
            "Open":  closes,
            "High":  highs,
            "Low":   lows,
            "Close": closes
        }, index=dates)

        res = self.engine.simulate_trade(
            stock_df=df,
            entry_idx=1,
            entry_price=100.0,
            stop_loss=95.0
        )
        
        # Verify 50% shares sold at 120.0, 50% shares sold at Close on Day 5 (104.0)
        # Average exit price = (120.0 + 104.0) / 2 = 112.0
        self.assertEqual(res["trade_status"], "FULLY_EXITED")
        self.assertEqual(res["exit_price"], 104.0)
        self.assertEqual(res["days_active"], 5)
        self.assertEqual(res["shares_remaining"], 0)
        
        # Initial: 2000 shares @ 100.0 = 200,000 INR
        # Profit on first 1000 shares: 1000 * 20 = 20,000
        # Profit on second 1000 shares: 1000 * 4 = 4,000
        # Total profit = 24,000
        self.assertAlmostEqual(res["total_pnl"], 24000.0)
        # Initial risk = 2000 shares * 5.0 risk_per_share = 10,000 INR.
        # R-Multiple = 24,000 / 10,000 = 2.4 R
        self.assertAlmostEqual(res["final_r_multiple"], 2.4)

if __name__ == "__main__":
    unittest.main()
