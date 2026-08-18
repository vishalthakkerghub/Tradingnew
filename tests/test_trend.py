import unittest
import pandas as pd
import numpy as np
from src.trend_template import TrendTemplateEngine

class TestTrendTemplateEngine(unittest.TestCase):
    """
    Unit test suite verifying the Trend Template Engine's mathematical calculations
    and conditional evaluations of the 10 approved rules.
    """
    def setUp(self):
        self.mock_config = {
            "liquidity": {"min_volume_sma50": 50000}
        }
        self.engine = TrendTemplateEngine(self.mock_config)
        
    def _create_mock_data(self, price_series, volume_series=None, size=300):
        """
        Helper to create a pandas DataFrame containing mock Open, High, Low, Close, Volume.
        """
        dates = pd.date_range(end=pd.Timestamp.now(), periods=size, freq="B").strftime("%Y-%m-%d")
        df = pd.DataFrame(index=dates)
        df.index.name = "Date"
        
        df["Close"] = price_series
        df["Open"] = price_series
        df["High"] = price_series * 1.01
        df["Low"] = price_series * 0.99
        
        if volume_series is not None:
            df["Volume"] = volume_series
        else:
            df["Volume"] = 100000  # Default to passing liquidity (100k > 50k)
            
        return df

    def test_insufficient_data_history(self):
        """
        Verify that history of less than 250 bars immediately fails the trend template.
        """
        prices = np.linspace(10, 50, 100)
        df_stock = self._create_mock_data(prices, size=100)
        df_index = self._create_mock_data(prices, size=100)
        
        rules = self.engine.evaluate_10_rules(df_stock, df_index)
        self.assertFalse(any(rules.values()))
        self.assertFalse(self.engine.is_stage2_aligned(df_stock, df_index))

    def test_all_rules_passing(self):
        """
        Verify that a perfectly aligned Stage 2 stock returns True for all rules.
        """
        # Create a clean, smoothly rising price series to ensure SMA alignment
        # and slope requirements are met
        prices = np.linspace(100.0, 500.0, 300)
        df_stock = self._create_mock_data(prices, size=300)
        
        # Index rises slower than stock to ensure outperformance (Rule 10)
        index_prices = np.linspace(100.0, 200.0, 300)
        df_index = self._create_mock_data(index_prices, size=300)
        
        rules = self.engine.evaluate_10_rules(df_stock, df_index)
        
        # Verify all 10 trend rules and liquidity pass
        for i in range(1, 11):
            self.assertTrue(rules[f"Rule_{i}"], f"Rule_{i} failed on passing test case")
        self.assertTrue(rules["Liquidity_Pass"])
        self.assertTrue(self.engine.is_stage2_aligned(df_stock, df_index))

    def test_rule_1_fail_close_below_150_sma(self):
        """
        Rule 1: Price must be above 150 SMA.
        """
        # Create a series where prices rise and then sharply drop at the end
        prices = np.linspace(100.0, 200.0, 300)
        prices[-1] = 90.0  # Sharp drop below the 150 SMA average
        df_stock = self._create_mock_data(prices, size=300)
        df_index = self._create_mock_data(np.linspace(100, 120, 300), size=300)
        
        rules = self.engine.evaluate_10_rules(df_stock, df_index)
        self.assertFalse(rules["Rule_1"])
        self.assertFalse(self.engine.is_stage2_aligned(df_stock, df_index))

    def test_rule_3_fail_150_below_200_sma(self):
        """
        Rule 3: 150 SMA must be higher than 200 SMA.
        """
        # Create a declining price series (downtrend) where 150 is below 200
        prices = np.linspace(500.0, 100.0, 300)
        df_stock = self._create_mock_data(prices, size=300)
        df_index = self._create_mock_data(np.linspace(100, 120, 300), size=300)
        
        rules = self.engine.evaluate_10_rules(df_stock, df_index)
        self.assertFalse(rules["Rule_3"])
        self.assertFalse(self.engine.is_stage2_aligned(df_stock, df_index))

    def test_rule_4_fail_200_sma_slope_down(self):
        """
        Rule 4: 200 SMA today must be higher than 200 SMA 20 trading days ago.
        """
        # Create a series where price starts flat and declines at the end
        prices = np.concatenate([np.linspace(100.0, 100.0, 200), np.linspace(100.0, 50.0, 100)])
        df_stock = self._create_mock_data(prices, size=300)
        df_index = self._create_mock_data(np.linspace(100, 120, 300), size=300)
        
        rules = self.engine.evaluate_10_rules(df_stock, df_index)
        self.assertFalse(rules["Rule_4"])
        self.assertFalse(self.engine.is_stage2_aligned(df_stock, df_index))

    def test_rule_8_fail_low_buffer(self):
        """
        Rule 8: Current price must be at least 30% above its 52-week low.
        """
        # Create a series that rises but stays close to the baseline low
        prices = np.linspace(100.0, 110.0, 300)  # Only 10% above 52-week low (100)
        df_stock = self._create_mock_data(prices, size=300)
        df_index = self._create_mock_data(np.linspace(100, 110, 300), size=300)
        
        rules = self.engine.evaluate_10_rules(df_stock, df_index)
        self.assertFalse(rules["Rule_8"])
        self.assertFalse(self.engine.is_stage2_aligned(df_stock, df_index))

    def test_rule_9_fail_high_buffer(self):
        """
        Rule 9: Current price must be within 25% of its 52-week high.
        """
        # Create a series that peaks at 200 and drops to 140 (which is 30% off high)
        prices = np.linspace(100.0, 100.0, 300)
        prices[150] = 200.0  # High of 200
        prices[-1] = 140.0   # Current is 140 (off high by 30%)
        df_stock = self._create_mock_data(prices, size=300)
        # Ensure high column reflects the peak
        df_stock.loc[df_stock.index[150], "High"] = 200.0
        
        df_index = self._create_mock_data(np.linspace(100, 110, 300), size=300)
        
        rules = self.engine.evaluate_10_rules(df_stock, df_index)
        self.assertFalse(rules["Rule_9"])
        self.assertFalse(self.engine.is_stage2_aligned(df_stock, df_index))

    def test_rule_10_fail_rs_underperform(self):
        """
        Rule 10: Stock 90D return must beat index 90D return.
        """
        # Stock rises 20%, but index rises 50%
        stock_prices = np.linspace(100.0, 120.0, 300)
        index_prices = np.linspace(100.0, 150.0, 300)
        
        df_stock = self._create_mock_data(stock_prices, size=300)
        df_index = self._create_mock_data(index_prices, size=300)
        
        rules = self.engine.evaluate_10_rules(df_stock, df_index)
        self.assertFalse(rules["Rule_10"])
        self.assertFalse(self.engine.is_stage2_aligned(df_stock, df_index))

    def test_liquidity_fail(self):
        """
        Liquidity check: 50-day average volume must exceed U_volume (e.g. 50k).
        """
        prices = np.linspace(100.0, 500.0, 300)
        # Volume set to 40k average (which is below 50k limit)
        df_stock = self._create_mock_data(prices, volume_series=pd.Series(40000, index=range(300)), size=300)
        df_index = self._create_mock_data(np.linspace(100, 150, 300), size=300)
        
        rules = self.engine.evaluate_10_rules(df_stock, df_index)
        self.assertFalse(rules["Liquidity_Pass"])
        self.assertFalse(self.engine.is_stage2_aligned(df_stock, df_index))

if __name__ == "__main__":
    unittest.main()
