import unittest
import os
import json
import pandas as pd
import numpy as np
from src.paper_trading_engine import PaperTradingEngine

class TestPaperTradingEngine(unittest.TestCase):
    """
    Unit tests for PaperTradingEngine watchlist addition, breakout entry,
    partial exit, and EMA20 trailing exits.
    """
    def setUp(self):
        self.state_file = "tests/test_paper_trading_state.json"
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
            except Exception:
                pass
            
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
        self.engine = PaperTradingEngine(config=self.config, state_file=self.state_file)

    def tearDown(self):
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
            except Exception:
                pass

    def test_watchlist_addition(self):
        """Verify adding candidate to watchlist works and formats keys correctly."""
        candidates = [{
            "Symbol": "TESTSTOCK",
            "Pivot Price": 100.0,
            "Stop Loss": 95.0,
            "Score": 75,
            "Grade": "Grade A",
            "Engine_Type": "STRICT_VCP",
            "Readiness Status": "STRICT READY",
            "VDU %": "15.0%"
        }]
        self.engine.update_watchlist(candidates, "2026-06-01")
        self.assertIn("TESTSTOCK", self.engine.state["watchlist"])
        item = self.engine.state["watchlist"]["TESTSTOCK"]
        self.assertEqual(item["pivot_price"], 100.0)
        self.assertEqual(item["contraction_low"], 95.0)
        self.assertEqual(item["score"], 75)
        self.assertEqual(item["vdu_ratio"], 0.15)

    def test_breakout_entry(self):
        """Verify watchlist items transition to active_trades on breakout (price and volume expansion)."""
        self.engine.state["watchlist"]["TESTSTOCK"] = {
            "symbol": "TESTSTOCK",
            "pivot_price": 100.0,
            "contraction_low": 95.0,
            "score": 75,
            "grade": "Grade A",
            "engine_type": "STRICT_VCP",
            "date_added": "2026-06-01",
            "vdu_ratio": 0.15
        }
        
        # Create 60 days of data for Volume SMA50 calculation
        dates = pd.date_range(start="2026-04-01", periods=60).strftime("%Y-%m-%d")
        df = pd.DataFrame(index=dates)
        df["Open"] = 98.0
        df["High"] = 99.0
        df["Low"] = 97.0
        df["Close"] = 98.0
        df["Volume"] = 10000.0
        
        # Inject breakout on last day
        breakout_date = dates[-1]
        df.loc[breakout_date, "Open"] = 101.0
        df.loc[breakout_date, "High"] = 105.0
        df.loc[breakout_date, "Low"] = 100.5
        df.loc[breakout_date, "Close"] = 104.0
        df.loc[breakout_date, "Volume"] = 50000.0  # > 1.4 * 10000
        
        stock_df_dict = {"TESTSTOCK": df}
        self.engine.evaluate_daily_lifecycle(stock_df_dict, breakout_date)
        
        # Verify it entered active_trades
        self.assertNotIn("TESTSTOCK", self.engine.state["watchlist"])
        self.assertIn("TESTSTOCK", self.engine.state["active_trades"])
        trade = self.engine.state["active_trades"]["TESTSTOCK"]
        self.assertEqual(trade["entry_price"], 101.0)  # max(pivot, Open) -> max(100.0, 101.0) = 101.0
        self.assertEqual(trade["initial_shares"], 1666)  # Risk = 10000, risk/share = 101.0 - 95.0 = 6.0. 10000/6.0 = 1666

    def test_partial_exit_and_ema20_trailing(self):
        """Verify +20% partial profit target and EMA20 trailing exit transitions."""
        self.engine.state["active_trades"]["TESTSTOCK"] = {
            "symbol": "TESTSTOCK",
            "entry_date": "2026-06-01",
            "entry_price": 100.0,
            "initial_stop": 95.0,
            "current_stop": 95.0,
            "initial_shares": 1000,
            "shares_remaining": 1000,
            "partial_exit_taken": False,
            "partial_exit_price": 0.0,
            "partial_exit_date": None,
            "days_active": 0,
            "max_high_reached": 100.0,
            "vdu_ratio": 0.15,
            "score": 80,
            "grade": "Grade A",
            "engine_type": "STRICT_VCP",
            "status": "ACTIVE"
        }
        self.engine.state["cash"] = 900000.0 # Initial cash
        
        # Construct historical context to compute a stable EMA20
        hist_dates = pd.date_range(end="2026-06-03", periods=40).strftime("%Y-%m-%d")
        df = pd.DataFrame(index=hist_dates)
        df["Open"] = 100.0
        df["High"] = 100.0
        df["Low"] = 100.0
        df["Close"] = 100.0
        df["Volume"] = 10000.0
        
        # Inject breakout/partial day and drop/exit day
        # EMA20 calculations use span=20.
        df.loc["2026-06-02"] = {"Open": 101.0, "High": 121.0, "Low": 99.0, "Close": 115.0, "Volume": 10000.0}
        df.loc["2026-06-03"] = {"Open": 114.0, "High": 115.0, "Low": 101.0, "Close": 100.0, "Volume": 10000.0}
        
        stock_df_dict = {"TESTSTOCK": df}
        
        # Evaluate Day 1 (June 2): should trigger partial exit
        self.engine.evaluate_daily_lifecycle(stock_df_dict, "2026-06-02")
        trade = self.engine.state["active_trades"]["TESTSTOCK"]
        self.assertTrue(trade["partial_exit_taken"])
        self.assertEqual(trade["shares_remaining"], 500)
        self.assertEqual(trade["partial_exit_price"], 120.0)
        self.assertEqual(trade["current_stop"], 100.0) # Stop moved to breakeven
        self.assertEqual(self.engine.state["cash"], 900000.0 + (500 * 120.0)) # Cash increased by partial sale
        
        # Evaluate Day 2 (June 3): Close drops to 100.0, which is below EMA20 (~102.5). Should trigger exit.
        self.engine.evaluate_daily_lifecycle(stock_df_dict, "2026-06-03")
        self.assertNotIn("TESTSTOCK", self.engine.state["active_trades"])
        self.assertEqual(len(self.engine.state["closed_trades"]), 1)
        closed = self.engine.state["closed_trades"][0]
        self.assertEqual(closed["status"], "FULLY_EXITED")
        self.assertEqual(closed["exit_price"], 100.0)
        self.assertEqual(closed["exit_reason"], "Closed below EMA20 trailing stop")
        
        # Verify P&L
        # Cost = 1000 * 100.0 = 100,000
        # Partial payout = 500 * 120.0 = 60,000
        # Final payout = 500 * 100.0 = 50,000
        # Total payout = 110,000
        # PnL = 10,000
        self.assertEqual(closed["pnl_net"], 10000.0)
        # Initial risk = 1000 * (100.0 - 95.0) = 5000
        # R-multiple = 10000 / 5000 = 2.0R
        self.assertAlmostEqual(closed["r_multiple"], 2.0)

    def test_tactical_classification_tight_cheat(self):
        """Verify TIGHT_CHEAT_VCP classification (4-day range <= 3.5%)."""
        dates = ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"]
        df = pd.DataFrame(index=dates)
        df["High"] = [100.0, 101.0, 101.5, 102.0]
        df["Low"] = [99.0, 99.5, 100.0, 100.0]
        df["Close"] = [99.5, 100.5, 101.0, 101.5]
        df["Open"] = [99.2, 99.8, 100.2, 100.8]
        df["Volume"] = [1000.0, 1000.0, 1000.0, 1000.0]
        
        candidates = [{
            "Symbol": "TIGHTSTOCK",
            "Pivot Price": 105.0,
            "Stop Loss": 95.0,
            "Score": 85,
            "Grade": "Grade A",
            "Engine_Type": "STRICT_VCP",
            "Readiness Status": "STRICT READY",
            "VDU %": "10%"
        }]
        
        stock_df_dict = {"TIGHTSTOCK": df}
        self.engine.update_watchlist(candidates, "2026-06-04", stock_df_dict)
        
        self.assertIn("TIGHTSTOCK", self.engine.state["watchlist"])
        item = self.engine.state["watchlist"]["TIGHTSTOCK"]
        self.assertEqual(item["entry_category"], "TIGHT_CHEAT_VCP")
        self.assertEqual(item["trigger_price"], 102.0) # 4-day High
        self.assertEqual(item["stop_price"], 99.0)   # 4-day Low
        self.assertAlmostEqual(item["target_1"], 102.0 * 1.10)
        self.assertAlmostEqual(item["target_2"], 102.0 * 1.20)

    def test_tactical_classification_ema_pullback(self):
        """Verify EMA_PULLBACK classification (Close within 1.5% of 10/20 EMA)."""
        # Create 20 days of stable data to compute EMA
        dates = pd.date_range(start="2026-05-01", periods=20).strftime("%Y-%m-%d")
        df = pd.DataFrame(index=dates)
        df["Open"] = 100.0
        df["High"] = 100.0
        df["Low"] = 100.0
        df["Close"] = 100.0
        df["Volume"] = 1000.0
        
        # Last day's yesterday (index 18)
        df.iloc[-2, df.columns.get_loc("High")] = 102.0 # Yesterday's High
        
        # Last day (index 19)
        df.iloc[-1, df.columns.get_loc("Close")] = 101.0
        # High-Low range for the last 4 days should exceed 3.5% to avoid Cheat VCP
        df.iloc[-3, df.columns.get_loc("Low")] = 96.0  # 4-day range is (102.0 - 96.0)/96.0 = 6.25% > 3.5%
        df.iloc[-1, df.columns.get_loc("Low")] = 98.0
        
        candidates = [{
            "Symbol": "PULLBACKSTOCK",
            "Pivot Price": 105.0,
            "Stop Loss": 95.0,
            "Score": 85,
            "Grade": "Grade A",
            "Engine_Type": "STRICT_VCP",
            "Readiness Status": "STRICT READY",
            "VDU %": "10%"
        }]
        
        stock_df_dict = {"PULLBACKSTOCK": df}
        self.engine.update_watchlist(candidates, dates[-1], stock_df_dict)
        
        self.assertIn("PULLBACKSTOCK", self.engine.state["watchlist"])
        item = self.engine.state["watchlist"]["PULLBACKSTOCK"]
        self.assertEqual(item["entry_category"], "EMA_PULLBACK")
        self.assertEqual(item["trigger_price"], 102.0) # Yesterday's High
        
        ema20_series = df["Close"].ewm(span=20, adjust=False).mean()
        expected_ema20 = float(ema20_series.iloc[-1])
        low_3d = float(df["Low"].iloc[-3:].min())
        expected_stop = max(expected_ema20 * 0.99, low_3d)
        expected_stop = max(102.0 * 0.92, expected_stop)
        self.assertAlmostEqual(item["stop_price"], expected_stop)

    def test_tactical_classification_high_risk(self):
        """Verify HIGH_RISK_ENTRY classification (no cheat, no pullback)."""
        dates = pd.date_range(start="2026-05-01", periods=20).strftime("%Y-%m-%d")
        df = pd.DataFrame(index=dates)
        df["Open"] = 100.0
        df["High"] = 100.0
        df["Low"] = 90.0
        df["Close"] = 100.0
        df["Volume"] = 1000.0
        
        # Last day has a massive gap up/run away from EMAs
        df.iloc[-1, df.columns.get_loc("High")] = 120.0
        df.iloc[-1, df.columns.get_loc("Close")] = 120.0
        
        candidates = [{
            "Symbol": "RISKYSTOCK",
            "Pivot Price": 105.0,
            "Stop Loss": 95.0,
            "Score": 85,
            "Grade": "Grade A",
            "Engine_Type": "STRICT_VCP",
            "Readiness Status": "STRICT READY",
            "VDU %": "10%"
        }]
        
        stock_df_dict = {"RISKYSTOCK": df}
        self.engine.update_watchlist(candidates, dates[-1], stock_df_dict)
        
        self.assertIn("RISKYSTOCK", self.engine.state["watchlist"])
        item = self.engine.state["watchlist"]["RISKYSTOCK"]
        self.assertEqual(item["entry_category"], "HIGH_RISK_ENTRY")
        self.assertEqual(item["trigger_price"], 105.0)
        self.assertAlmostEqual(item["stop_price"], 96.6)  # max(105 * 0.92, 95.0) = 96.6

    def test_tactical_execution(self):
        """Verify simulated entries trigger off the tactical trigger_price and stop_price."""
        self.engine.state["watchlist"]["TESTSTOCK"] = {
            "symbol": "TESTSTOCK",
            "pivot_price": 105.0,
            "contraction_low": 95.0,
            "score": 85,
            "grade": "Grade A",
            "engine_type": "STRICT_VCP",
            "date_added": "2026-06-01",
            "vdu_ratio": 0.10,
            "entry_category": "TIGHT_CHEAT_VCP",
            "trigger_price": 102.0,
            "stop_price": 99.0,
            "target_1": 112.2,
            "target_2": 122.4
        }
        
        # 60 days of data
        dates = pd.date_range(start="2026-04-01", periods=60).strftime("%Y-%m-%d")
        df = pd.DataFrame(index=dates)
        df["Open"] = 100.0
        df["High"] = 101.0
        df["Low"] = 99.0
        df["Close"] = 100.0
        df["Volume"] = 10000.0
        
        # Breakout on last day above trigger_price (102.0) but below pivot_price (105.0)
        breakout_date = dates[-1]
        df.loc[breakout_date, "Open"] = 101.5
        df.loc[breakout_date, "High"] = 104.0
        df.loc[breakout_date, "Low"] = 101.0
        df.loc[breakout_date, "Close"] = 103.5
        df.loc[breakout_date, "Volume"] = 50000.0  # volume expansion
        
        stock_df_dict = {"TESTSTOCK": df}
        self.engine.evaluate_daily_lifecycle(stock_df_dict, breakout_date)
        
        # Verify it entered active_trades (even though Close < pivot_price, it is Close > trigger_price)
        self.assertNotIn("TESTSTOCK", self.engine.state["watchlist"])
        self.assertIn("TESTSTOCK", self.engine.state["active_trades"])
        trade = self.engine.state["active_trades"]["TESTSTOCK"]
        self.assertEqual(trade["entry_price"], 102.0)  # max(trigger_price, Open) -> max(102.0, 101.5) = 102.0
        self.assertEqual(trade["initial_stop"], 99.0)  # stop_price
        self.assertEqual(trade["current_stop"], 99.0)
