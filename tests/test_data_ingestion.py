import os
import unittest
import time
import shutil
import pandas as pd
from unittest.mock import patch, MagicMock
from src.data_ingestion import DataIngestionEngine

class TestDataIngestionEngine(unittest.TestCase):
    """
    Unit tests validating caching, data integrity, formats, and simulation fallbacks
    for the Data Ingestion module.
    """
    def setUp(self):
        # Create a temporary cache directory for isolated test execution
        self.test_cache_dir = os.path.abspath("data/test_cache")
        self.engine = DataIngestionEngine(cache_dir=self.test_cache_dir)

    def tearDown(self):
        # Clean up the test cache directory
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir)

    def test_format_nse_ticker(self):
        """
        Verify that ticker symbols are correctly formatted for yfinance.
        """
        self.assertEqual(self.engine._format_nse_ticker("RELIANCE"), "RELIANCE.NS")
        self.assertEqual(self.engine._format_nse_ticker("RELIANCE.NS"), "RELIANCE.NS")
        self.assertEqual(self.engine._format_nse_ticker("NIFTY_MIDSML400"), "^NSEMDCP50")
        self.assertEqual(self.engine._format_nse_ticker("^NSEI"), "^NSEI")

    def test_validate_data_valid(self):
        """
        Verify that a properly structured DataFrame passes validation checks.
        """
        data = {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.5, 102.0],
            "Volume": [50000, 60000]
        }
        df = pd.DataFrame(data, index=["2026-06-12", "2026-06-13"])
        df.index.name = "Date"
        self.assertTrue(self.engine.validate_data(df))

    def test_validate_data_invalid_columns(self):
        """
        Verify that data missing required columns fails validation checks.
        """
        data = {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Close": [101.5, 102.0]  # Missing Low and Volume
        }
        df = pd.DataFrame(data, index=["2026-06-12", "2026-06-13"])
        df.index.name = "Date"
        self.assertFalse(self.engine.validate_data(df))

    def test_validate_data_zero_or_negative_values(self):
        """
        Verify that negative prices or zero volumes fail validation checks.
        """
        # Negative Close price
        data_neg = {
            "Open": [100.0], "High": [102.0], "Low": [99.0], "Close": [-1.5], "Volume": [50000]
        }
        df_neg = pd.DataFrame(data_neg, index=["2026-06-12"])
        df_neg.index.name = "Date"
        self.assertFalse(self.engine.validate_data(df_neg))

        # Zero Volume
        data_zero = {
            "Open": [100.0], "High": [102.0], "Low": [99.0], "Close": [101.5], "Volume": [0]
        }
        df_zero = pd.DataFrame(data_zero, index=["2026-06-12"])
        df_zero.index.name = "Date"
        self.assertFalse(self.engine.validate_data(df_zero))

    def test_simulated_data_generator(self):
        """
        Verify that simulated fallback data has the correct dimensions, schema, and positive values.
        """
        df = self.engine._generate_simulated_ohlcv("MOCK_STOCK", size=100)
        self.assertEqual(len(df), 100)
        self.assertTrue(self.engine.validate_data(df))
        self.assertTrue((df["High"] >= df["Low"]).all())
        self.assertTrue((df["High"] >= df["Close"]).all())
        self.assertTrue((df["High"] >= df["Open"]).all())
        self.assertTrue((df["Low"] <= df["Open"]).all())

    @patch("yfinance.Ticker")
    def test_fetch_ohlcv_cache_expiration(self, mock_ticker_class):
        """
        Test cache expiration: age < 18 hours loads cache directly; age > 18 hours triggers download.
        """
        # Create a mock cache file
        df_mock = self.engine._generate_simulated_ohlcv("RELIANCE", size=50)
        cache_path = os.path.join(self.test_cache_dir, "RELIANCE.CSV")
        self.engine._save_cache_file(df_mock, cache_path)

        # Mock the yfinance Ticker return
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df_mock
        mock_ticker_class.return_value = mock_ticker

        # 1. Fresh Cache: age = 2 hours (should hit cache, no download attempt)
        past_time = time.time() - (2 * 3600)
        os.utime(cache_path, (past_time, past_time))
        
        df_res = self.engine.fetch_historical_ohlcv("RELIANCE", lookback_days=10)
        self.assertEqual(len(df_res), 10)
        mock_ticker.history.assert_not_called()

        # 2. Stale Cache: age = 20 hours (should trigger download)
        stale_time = time.time() - (20 * 3600)
        os.utime(cache_path, (stale_time, stale_time))

        df_res = self.engine.fetch_historical_ohlcv("RELIANCE", lookback_days=10)
        self.assertEqual(len(df_res), 10)
        mock_ticker.history.assert_called_once()

    @patch("yfinance.Ticker")
    def test_fetch_ohlcv_network_failure_fallback_to_stale_cache(self, mock_ticker_class):
        """
        Verify that if the network fails (yfinance throws exception) on stale cache, 
        the engine gracefully falls back to loading the existing stale cache file.
        """
        df_mock = self.engine._generate_simulated_ohlcv("INFY", size=50)
        cache_path = os.path.join(self.test_cache_dir, "INFY.CSV")
        self.engine._save_cache_file(df_mock, cache_path)

        # Make cache stale (20 hours old)
        stale_time = time.time() - (20 * 3600)
        os.utime(cache_path, (stale_time, stale_time))

        # Mock yfinance to raise an exception
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = Exception("API connection timed out.")
        mock_ticker_class.return_value = mock_ticker

        # Fetch data (should try download, fail, and load cache)
        df_res = self.engine.fetch_historical_ohlcv("INFY", lookback_days=10)
        self.assertEqual(len(df_res), 10)
        mock_ticker.history.assert_called_once()

    def _df(self, rows):
        df = pd.DataFrame(rows, columns=["Date", "Open", "High", "Low", "Close", "Volume"]).set_index("Date")
        return df

    def test_merge_restores_date_missing_from_download(self):
        """A session the vendor omits must not erase the cached candle (2026-10-12 bug)."""
        path = os.path.join(self.test_cache_dir, "GAP.csv")
        old = self._df([("2026-10-09", 100, 101, 99, 100, 10), ("2026-10-12", 100, 103, 99, 102, 11), ("2026-10-13", 102, 104, 101, 103, 12)])
        old["Delivery_Pct"] = [0.0, 55.0, 0.0]
        old.to_csv(path)
        new = self._df([("2026-10-09", 100, 101, 99, 100, 10), ("2026-10-13", 102, 104, 101, 103, 12)])
        merged = self.engine._merge_with_cache(new, path)
        self.assertEqual(list(merged.index), ["2026-10-09", "2026-10-12", "2026-10-13"])
        self.assertAlmostEqual(merged.loc["2026-10-12", "Close"], 102.0)
        self.assertEqual(merged.loc["2026-10-12", "Delivery_Pct"], 55.0)

    def test_merge_rescales_restored_row_after_readjustment(self):
        path = os.path.join(self.test_cache_dir, "ADJ.csv")
        old = self._df([("2026-10-09", 100, 100, 100, 100, 10), ("2026-10-12", 110, 110, 110, 110, 10), ("2026-10-13", 120, 120, 120, 120, 10)])
        old.to_csv(path)
        # vendor re-adjusted history by 0.5x and omitted 10-12
        new = self._df([("2026-10-09", 50, 50, 50, 50, 10), ("2026-10-13", 60, 60, 60, 60, 10)])
        merged = self.engine._merge_with_cache(new, path)
        self.assertAlmostEqual(merged.loc["2026-10-12", "Close"], 55.0)

    def test_merge_does_not_resurrect_dates_before_download_window(self):
        path = os.path.join(self.test_cache_dir, "OLD.csv")
        self._df([("2020-01-01", 1, 1, 1, 1, 1), ("2026-10-09", 100, 100, 100, 100, 10)]).to_csv(path)
        new = self._df([("2026-10-09", 100, 100, 100, 100, 10), ("2026-10-13", 101, 101, 101, 101, 10)])
        merged = self.engine._merge_with_cache(new, path)
        self.assertNotIn("2020-01-01", merged.index)

    def test_find_calendar_gaps_flags_missing_and_ignores_prelisting(self):
        cal = ["2026-10-08", "2026-10-09", "2026-10-12", "2026-10-13"]
        self._df([(d, 1, 1, 1, 1, 1) for d in cal]).to_csv(os.path.join(self.test_cache_dir, "NIFTY_50.csv"))
        self._df([(d, 1, 1, 1, 1, 1) for d in ["2026-10-08", "2026-10-09", "2026-10-13"]]).to_csv(os.path.join(self.test_cache_dir, "GAPPED.csv"))
        self._df([(d, 1, 1, 1, 1, 1) for d in ["2026-10-12", "2026-10-13"]]).to_csv(os.path.join(self.test_cache_dir, "NEWIPO.csv"))
        self._df([(d, 1, 1, 1, 1, 1) for d in ["2026-10-08", "2026-10-09"]]).to_csv(os.path.join(self.test_cache_dir, "STALE.csv"))
        res = self.engine.find_calendar_gaps(["GAPPED", "NEWIPO", "STALE"], window=4)
        self.assertEqual(res["GAPPED"], ["2026-10-12"])
        self.assertNotIn("NEWIPO", res)
        self.assertEqual(res["__stale__"], ["STALE"])

if __name__ == "__main__":
    unittest.main()
