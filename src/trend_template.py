import logging
import pandas as pd

logger = logging.getLogger("TrendTemplate")

class TrendTemplateEngine:
    """
    Evaluates Mark Minervini's 10 approved Trend Template rules to confirm if a stock
    is in a Stage 2 Uptrend, qualifying it for further VCP analysis.
    """
    def __init__(self, config: dict):
        self.config = config
        self.min_volume = config.get("liquidity", {}).get("min_volume_sma50", 50000)
        logger.info(f"TrendTemplateEngine active. Liquidity filter: {self.min_volume} average daily shares.")

    def evaluate_10_rules(self, stock_df: pd.DataFrame, index_df: pd.DataFrame, relaxed: bool = False) -> dict:
        """
        Calculates moving averages and price channels, and evaluates the 10 Trend Template
        rules plus the liquidity baseline.
        Returns a dictionary containing True/False results for each rule.
        """
        # Ensure we have enough data to calculate standard indicators (min 250 bars for 52-week channel)
        if len(stock_df) < 250:
            logger.warning("Stock price history is insufficient (<250 bars) to compute 52-week levels.")
            return {f"Rule_{i}": False for i in range(1, 11)}
            
        if len(index_df) < 91:
            logger.warning("Index price history is insufficient (<91 bars) to compute 90D relative returns.")
            return {f"Rule_{i}": False for i in range(1, 11)}

        # 1. Calculate indicators on the stock DataFrame
        close = stock_df["Close"].iloc[-1]
        volume = stock_df["Volume"].iloc[-1]
        
        sma50 = float(stock_df["Close"].iloc[-50:].mean())
        sma150 = float(stock_df["Close"].iloc[-150:].mean())
        sma200 = float(stock_df["Close"].iloc[-200:].mean())
        
        # 200 SMA value from 20 trading days ago
        sma200_20days_ago = float(stock_df["Close"].iloc[-219:-19].mean())
        
        low_52w = float(stock_df["Low"].iloc[-250:].min())
        high_52w = float(stock_df["High"].iloc[-250:].max())
        
        volume_sma50 = float(stock_df["Volume"].iloc[-50:].mean())

        # 2. Calculate 90-day returns for Relative Strength (Rule 10)
        # Shift(90) gets the close 90 trading days ago (which is the 91st row from the end)
        stock_close_90d_ago = stock_df["Close"].iloc[-91]
        index_close_90d_ago = index_df["Close"].iloc[-91]
        
        stock_return_90d = (close / stock_close_90d_ago) - 1
        index_return_90d = (index_df["Close"].iloc[-1] / index_close_90d_ago) - 1

        # 3. Evaluate the 10 approved rules
        rules = {}
        rules["Rule_1"] = close > sma150
        rules["Rule_2"] = close > sma200
        rules["Rule_3"] = (sma150 > sma200) if not relaxed else True
        rules["Rule_4"] = (sma200 > sma200_20days_ago) if not relaxed else True
        rules["Rule_5"] = sma50 > sma150
        rules["Rule_6"] = sma50 > sma200
        rules["Rule_7"] = close > sma50
        rules["Rule_8"] = ((close - low_52w) / low_52w) >= 0.30
        rules["Rule_9"] = ((high_52w - close) / high_52w) <= 0.25
        rules["Rule_10"] = stock_return_90d > index_return_90d
        
        # 4. Evaluate Liquidity Rule (user-defined placeholder)
        rules["Liquidity_Pass"] = volume_sma50 > self.min_volume

        # Log failures at debug level to avoid log clutter
        failed_rules = [r for r, val in rules.items() if not val]
        if failed_rules:
            logger.debug(f"Trend Template evaluation failed rules: {failed_rules}")
            
        return rules

    def is_stage2_aligned(self, stock_df: pd.DataFrame, index_df: pd.DataFrame, relaxed: bool = False) -> bool:
        """
        Returns True only if the stock satisfies all 10 approved Stage 2 Trend Template rules
        and passes the liquidity volume SMA(50) floor.
        """
        rules = self.evaluate_10_rules(stock_df, index_df, relaxed=relaxed)
        
        # All 10 trend rules must be True
        trend_pass = all(rules[f"Rule_{i}"] for i in range(1, 11))
        
        # Liquidity baseline filter must pass
        liquidity_pass = rules.get("Liquidity_Pass", False)
        
        is_aligned = trend_pass and liquidity_pass
        logger.debug(f"Trend template alignment check: {'PASSED' if is_aligned else 'FAILED'}")
        
        return is_aligned
