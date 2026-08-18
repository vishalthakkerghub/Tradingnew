import unittest
import pandas as pd
import numpy as np
from src.market_conditions import MarketConditionsEngine

class TestMarketConditions(unittest.TestCase):
    def setUp(self):
        self.mock_config = {
            "system": {
                "primary_index": "NIFTY_MIDSML400"
            }
        }
        self.engine = MarketConditionsEngine(self.mock_config)

    def test_get_market_posture(self):
        """
        Verify score mapping to posture:
        - 8-10: GREEN
        - 5-7: YELLOW
        - < 5: RED
        """
        self.assertEqual(self.engine.get_market_posture(10), "GREEN")
        self.assertEqual(self.engine.get_market_posture(8), "GREEN")
        self.assertEqual(self.engine.get_market_posture(7), "YELLOW")
        self.assertEqual(self.engine.get_market_posture(5), "YELLOW")
        self.assertEqual(self.engine.get_market_posture(4), "RED")
        self.assertEqual(self.engine.get_market_posture(0), "RED")

    def test_track_distribution_days(self):
        """
        Verify distribution days calculation (rolling 20 sessions).
        A distribution day is index close down >= 0.20% on volume higher than the prior day.
        """
        # Create 21 sessions of data
        dates = pd.date_range(start="2026-06-01", periods=21)
        
        # Base close is 10000, base volume is 1000
        close = [10000] * 21
        volume = [1000] * 21
        
        # Let's make some normal sessions, and some distribution sessions:
        # Session 5: Close down 0.5%, Volume up 1200 (Distribution day)
        close[5] = 9950  # -0.5%
        volume[5] = 1200 # higher than prior 1000
        
        # Session 10: Close down 0.1%, Volume up 1300 (NOT distribution day, down < 0.2%)
        close[10] = 9985  # -0.15% from 10000
        volume[10] = 1300
        
        # Session 15: Close down 1.0%, Volume down 900 (NOT distribution day, volume is lower)
        close[15] = 9840.65 # -1% from 9940.05
        volume[15] = 900 # lower than prior 1300
        
        # Session 20: Close down 0.3%, Volume up 1500 (Distribution day)
        close[20] = 9811.12 # -0.3% from 9840.65
        volume[20] = 1500 # higher than prior 1000 (after 900)
        
        df = pd.DataFrame({
            "Date": dates.strftime("%Y-%m-%d"),
            "Close": close,
            "Volume": volume
        })
        
        dist_count = self.engine.track_distribution_days(df)
        # Should count exactly 2 distribution days (session 5 and session 20)
        self.assertEqual(dist_count, 2)

    def test_compute_market_health_score(self):
        """
        Verify the 10-point health score logic.
        """
        # Create a DataFrame of 250 sessions
        # Let's design it so:
        # - Close is consistently above 50 SMA and 200 SMA (4 points)
        # - 50 SMA is above 200 SMA (2 points)
        # - Distribution days is 0 (<= 4) (2 points)
        # - Leadership success rate is 80% (>= 70%) (2 points)
        # Total points should be 10/10.
        dates = pd.date_range(start="2025-06-01", periods=250)
        # Prices in clear uptrend
        close = [10000 + i * 10 for i in range(250)]
        # Constant volume
        volume = [1000] * 250
        
        df = pd.DataFrame({
            "Date": dates.strftime("%Y-%m-%d"),
            "Close": close,
            "Volume": volume
        })
        
        breakup = self.engine.get_detailed_breakup(df, breakout_success_rate=0.80)
        self.assertEqual(breakup["score"], 10)
        self.assertEqual(breakup["posture"], "GREEN")
        self.assertTrue(breakup["breakdown"]["above_200_sma"]["status"])
        self.assertTrue(breakup["breakdown"]["above_50_sma"]["status"])
        self.assertTrue(breakup["breakdown"]["sma_50_above_200"]["status"])
        self.assertTrue(breakup["breakdown"]["distribution_days"]["status"])
        self.assertTrue(breakup["breakdown"]["breakout_success"]["status"])

if __name__ == "__main__":
    unittest.main()
