import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("FlagEngine")

class FlagEngine:
    """
    Emerging Leader Flag Engine.
    Detects tight bull flags and mini-consolidations independent of the standard Stage 2 Trend Template.
    """
    def __init__(self, config: dict):
        self.config = config
        self.min_volume = config.get("liquidity", {}).get("min_volume_sma50", 50000)
        
    def is_flag_candidate(self, stock_df: pd.DataFrame, index_df: pd.DataFrame) -> tuple:
        """
        Evaluates the stock for a tight bull flag.
        
        Returns:
            tuple: (is_candidate, trigger_price, stop_price, target_1, target_2, range_n, vdu_ratio, flag_length)
        """
        n = len(stock_df)
        if n < 50:
            return False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0
            
        close = float(stock_df["Close"].iloc[-1])
        
        # 1. Liquidity Floor check
        avg_vol_50 = float(stock_df["Volume"].iloc[-50:].mean())
        if avg_vol_50 < self.min_volume:
            logger.debug(f"Failed liquidity check: Avg Volume 50 ({avg_vol_50}) < Floor ({self.min_volume})")
            return False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0
            
        # 2. Relaxed Trend Check: Close > 50 SMA
        sma50 = float(stock_df["Close"].iloc[-50:].mean())
        if close <= sma50:
            logger.debug(f"Failed trend check: Close ({close}) <= 50 SMA ({sma50})")
            return False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0
            
        # 3. Prior Momentum Check: Strong run-up before consolidation
        # Prior gain over the last 30 trading days >= 15%
        # (Compare close 30 trading days ago with the highest close in the window)
        idx_start = max(0, n - 30)
        close_start = float(stock_df["Close"].iloc[idx_start])
        highest_close = float(stock_df["Close"].iloc[idx_start:].max())
        prior_gain = ((highest_close - close_start) / close_start) * 100
        if prior_gain < 15.0:
            logger.debug(f"Failed prior momentum check: 30D Gain ({prior_gain:.1f}%) < 15%")
            return False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0
            
        # 4. Relative Strength Check: 90-day return > index return (only if index_df is provided and large enough)
        if index_df is not None and len(index_df) >= 91 and n >= 91:
            stock_close_90d = float(stock_df["Close"].iloc[-91])
            index_close_90d = float(index_df["Close"].iloc[-91])
            stock_return = (close / stock_close_90d) - 1.0
            index_return = (float(index_df["Close"].iloc[-1]) / index_close_90d) - 1.0
            if stock_return <= index_return:
                logger.debug(f"Failed relative strength check: Stock Return ({stock_return*100:.1f}%) <= Index Return ({index_return*100:.1f}%)")
                return False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0
                
        # 5. Consolidation Filter (Tight Flag):
        # We search for a consolidation window length N (5 <= N <= 15)
        # where the range is <= 12% and close is within 3% of consolidation High.
        # We start searching from shortest (5 days) to longest (15 days).
        best_n = 0
        best_range = 0.0
        best_high = 0.0
        best_low = 0.0
        
        for N in range(5, 16):
            if n < N:
                continue
            sub_df = stock_df.iloc[-N:]
            h_max = float(sub_df["High"].max())
            l_min = float(sub_df["Low"].min())
            rng = ((h_max - l_min) / l_min) * 100
            
            # Check readiness: Close within 3% of the N-day consolidation High
            dist_to_high = ((h_max - close) / h_max) * 100
            
            if rng <= 12.0 and dist_to_high <= 3.0:
                best_n = N
                best_range = rng
                best_high = h_max
                best_low = l_min
                break # Prefer the shortest tight flag
                
        if best_n == 0:
            logger.debug("Failed consolidation filter: No N-day window (5<=N<=15) with range <= 12% and Close within 3% of High found.")
            return False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0
            
        # 6. Volume Dry-Up (VDU) Check
        avg_vol_5 = float(stock_df["Volume"].iloc[-5:].mean())
        vdu_ratio = avg_vol_5 / avg_vol_50 if avg_vol_50 > 0 else 1.0
        if vdu_ratio > 1.50:
            logger.debug(f"Failed VDU check: Ratio ({vdu_ratio:.2f}) > 1.50")
            return False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0
            
        # 7. Calculate trigger and stop loss parameters
        trigger_price = best_high
        max_stop_pct = 0.08
        max_stop_loss_limit = trigger_price * (1.0 - max_stop_pct)
        stop_price = max(max_stop_loss_limit, best_low)
        
        # Expectancy-based dynamic targets (minimum 5% for T1 and 10% for T2)
        risk_pct = ((trigger_price - stop_price) / trigger_price) * 100 if trigger_price > 0 else 0.0
        target_1 = trigger_price * (1.0 + max(0.05, 2.0 * (risk_pct / 100)))
        target_2 = trigger_price * (1.0 + max(0.10, 3.5 * (risk_pct / 100)))
        
        logger.info(f"Emerging Leader Flag Pattern detected! Length: {best_n} days | Range: {best_range:.1f}% | Trigger: Rs. {trigger_price:.2f} | Stop: Rs. {stop_price:.2f} | T1: Rs. {target_1:.2f} | T2: Rs. {target_2:.2f}")
        return True, trigger_price, stop_price, target_1, target_2, best_range, vdu_ratio, best_n
