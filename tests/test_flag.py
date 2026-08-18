import unittest
import pandas as pd
import numpy as np
from src.flag_engine import FlagEngine

class TestFlagEngine(unittest.TestCase):
    def setUp(self):
        self.config = {
            "liquidity": {
                "min_volume_sma50": 1000
            }
        }
        self.engine = FlagEngine(self.config)
        
        # Build 100 days of mock index data
        dates = pd.date_range(start="2026-01-01", periods=100).strftime("%Y-%m-%d")
        self.index_df = pd.DataFrame(index=dates)
        self.index_df["Close"] = 1000.0

    def test_valid_flag_candidate(self):
        """Verify that a stock meeting all flag and momentum criteria is correctly identified."""
        dates = pd.date_range(start="2026-01-01", periods=100).strftime("%Y-%m-%d")
        df = pd.DataFrame(index=dates)
        
        # 1. Base trend: 50 SMA is around 100
        df["Close"] = 100.0
        df["Open"] = 100.0
        df["High"] = 100.0
        df["Low"] = 100.0
        df["Volume"] = 2000.0
        
        # 2. Strong prior momentum: run up to 130 over the prior 30 days
        # We set closes from index 60 to 90 to run up from 100 to 130
        for idx in range(60, 91):
            val = 100.0 + (idx - 60) * 1.0  # Runs up to 130
            df.iloc[idx, df.columns.get_loc("Close")] = val
            df.iloc[idx, df.columns.get_loc("High")] = val + 1.0
            df.iloc[idx, df.columns.get_loc("Low")] = val - 1.0
            
        # 3. Consolidation (last 9 days): tight flag between 128 and 132 (range ~3.1%)
        # Close at 131.5 (within 3% of High 132.0)
        for idx in range(91, 100):
            df.iloc[idx, df.columns.get_loc("Close")] = 130.0
            df.iloc[idx, df.columns.get_loc("High")] = 132.0
            df.iloc[idx, df.columns.get_loc("Low")] = 128.0
            df.iloc[idx, df.columns.get_loc("Volume")] = 800.0 # VDU
            
        # Last day close near High
        df.iloc[-1, df.columns.get_loc("Close")] = 131.5
        df.iloc[-1, df.columns.get_loc("High")] = 132.0
        df.iloc[-1, df.columns.get_loc("Low")] = 129.0
        df.iloc[-1, df.columns.get_loc("Volume")] = 500.0
        
        is_cand, trigger, stop, t1, t2, rng, vdu, length = self.engine.is_flag_candidate(df, self.index_df)
        
        self.assertTrue(is_cand)
        self.assertEqual(trigger, 132.0)
        self.assertEqual(stop, 128.0) # Consolidation low (within 8%)
        self.assertAlmostEqual(t1, 132.0 * 1.10)
        self.assertAlmostEqual(t2, 132.0 * 1.20)
        self.assertEqual(length, 5)
        self.assertLessEqual(rng, 12.0)
        self.assertLessEqual(vdu, 1.50)

    def test_failed_prior_momentum(self):
        """Verify stock with loose consolidation and weak prior run is rejected."""
        dates = pd.date_range(start="2026-01-01", periods=100).strftime("%Y-%m-%d")
        df = pd.DataFrame(index=dates)
        
        df["Close"] = 100.0
        df["Open"] = 100.0
        df["High"] = 101.0
        df["Low"] = 99.0
        df["Volume"] = 2000.0
        
        # prior gain is flat (100 -> 100) -> 0% gain
        is_cand, _, _, _, _, _, _, _ = self.engine.is_flag_candidate(df, self.index_df)
        self.assertFalse(is_cand)

    def test_failed_consolidation_range(self):
        """Verify stock with too wide consolidation range is rejected."""
        dates = pd.date_range(start="2026-01-01", periods=100).strftime("%Y-%m-%d")
        df = pd.DataFrame(index=dates)
        
        df["Close"] = 100.0
        df["Open"] = 100.0
        df["High"] = 100.0
        df["Low"] = 100.0
        df["Volume"] = 2000.0
        
        # prior gain: 100 to 130
        for idx in range(60, 91):
            val = 100.0 + (idx - 60) * 1.0
            df.iloc[idx, df.columns.get_loc("Close")] = val
            df.iloc[idx, df.columns.get_loc("High")] = val + 1.0
            df.iloc[idx, df.columns.get_loc("Low")] = val - 1.0
            
        # last 9 days has wide range (110 to 135) -> range (135-110)/110 = 22.7% > 12.0%
        for idx in range(91, 100):
            df.iloc[idx, df.columns.get_loc("Close")] = 125.0
            df.iloc[idx, df.columns.get_loc("High")] = 135.0
            df.iloc[idx, df.columns.get_loc("Low")] = 110.0
            df.iloc[idx, df.columns.get_loc("Volume")] = 800.0
            
        df.iloc[-1, df.columns.get_loc("Close")] = 134.0
        
        is_cand, _, _, _, _, _, _, _ = self.engine.is_flag_candidate(df, self.index_df)
        self.assertFalse(is_cand)

if __name__ == "__main__":
    unittest.main()
