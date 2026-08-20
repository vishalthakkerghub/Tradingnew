import logging
import pandas as pd
import os
import json

logger = logging.getLogger("MarketConditions")

class MarketConditionsEngine:
    """
    Interface for tracking index trends, distribution days, and general market health posture.
    """
    def __init__(self, config: dict):
        self.config = config
        self.index_symbol = config.get("system", {}).get("primary_index", "NIFTY_MIDSML400")
        logger.info(f"MarketConditionsEngine initialized monitoring benchmark: {self.index_symbol}")

    def track_distribution_days(self, index_df: pd.DataFrame) -> int:
        """
        Scans index history for distribution days in a rolling 20-session window.
        A distribution day is index close down >= 0.20% on volume higher than the prior day.
        """
        logger.info("Calculating distribution day load.")
        if index_df.empty or len(index_df) < 21:
            logger.warning("Insufficient historical data for rolling 20-day distribution check.")
            return 0
        
        # Take the last 21 sessions to evaluate the rolling 20-session window (since we need day-before comparison)
        recent_df = index_df.iloc[-21:]
        
        distribution_days = 0
        for i in range(1, len(recent_df)):
            close_today = float(recent_df["Close"].iloc[i])
            close_prev = float(recent_df["Close"].iloc[i-1])
            vol_today = float(recent_df["Volume"].iloc[i])
            vol_prev = float(recent_df["Volume"].iloc[i-1])
            
            # Close down >= 0.20%
            pct_change = (close_today - close_prev) / close_prev
            if pct_change <= -0.0020 and vol_today > vol_prev:
                distribution_days += 1
                
        return distribution_days

    def get_detailed_breakup(self, index_df: pd.DataFrame, breakout_success_rate: float = 0.70, date_str: str = None) -> dict:
        """
        Returns a dictionary containing the detailed health score breakup, posture, and recommendation.
        Posture and score are derived directly from the MBI (Market Breadth Index).
        Index SMA alignment and distribution days are computed for informational purposes.
        """
        # 1. Resolve and Load MBI Score
        mbi_score = 50.0
        mb_file = "data/market_breadth.json"
        if date_str:
            cleaned_date = date_str.replace("-", "")
            dated_mb = f"data/market_breadth_{cleaned_date}.json"
            if os.path.exists(dated_mb):
                mb_file = dated_mb
            elif os.path.exists(os.path.join("minervini_os", dated_mb)):
                mb_file = os.path.join("minervini_os", dated_mb)

        if not os.path.exists(mb_file) and os.path.exists(os.path.join("minervini_os", mb_file)):
            mb_file = os.path.join("minervini_os", mb_file)

        if os.path.exists(mb_file):
            try:
                with open(mb_file, "r", encoding="utf-8") as f_mb:
                    mb_data = json.load(f_mb)
                    mbi_score = float(mb_data.get("Index", 50.0))
            except Exception as mb_ex:
                logger.error(f"Error loading market breadth file {mb_file} inside posture engine: {mb_ex}")

        # Derive Posture, Score, and Recommendation from MBI
        if mbi_score >= 65.0:
            posture = "GREEN"
            total_score = min(10, max(8, round(mbi_score / 10.0)))
            recommendation = f"Favorable Market Breadth (MBI: {mbi_score:.1f}%): Fully fund new long positions, focus on high-conviction breakouts, and pyramid working trades."
        elif mbi_score >= 45.0:
            posture = "YELLOW"
            if mbi_score >= 55.0:
                total_score = 6 if mbi_score < 60.0 else 7
            else:
                total_score = 5
            recommendation = f"Caution / Defensive Mode (MBI: {mbi_score:.1f}%): Keep position sizes small, tighten stop losses, and buy only the absolute strongest leaders."
        else:
            posture = "RED"
            total_score = min(4, max(0, round(mbi_score / 10.0)))
            recommendation = f"Weak Market Breadth (MBI: {mbi_score:.1f}%): Suspend all new buying, raise stop losses, and hold cash to protect capital."

        # Compute index informational metrics
        above_200 = False
        above_50 = False
        sma_50_above_200 = False
        latest_close = 0.0
        sma_50 = 0.0
        sma_200 = 0.0
        dist_days = 0
        dist_days_ok = False
        pts_200 = 0
        pts_50 = 0
        pts_50_200 = 0
        pts_dist = 0

        if index_df is not None and not index_df.empty:
            close_series = index_df["Close"]
            latest_close = float(close_series.iloc[-1])
            
            # Calculate 50 SMA
            if len(close_series) >= 50:
                sma_50 = float(close_series.rolling(window=50).mean().iloc[-1])
            else:
                sma_50 = float(close_series.mean())
                
            # Calculate 200 SMA
            if len(close_series) >= 200:
                sma_200 = float(close_series.rolling(window=200).mean().iloc[-1])
            else:
                sma_200 = float(close_series.mean())
                
            above_200 = latest_close > sma_200
            pts_200 = 2 if above_200 else 0
            
            above_50 = latest_close > sma_50
            pts_50 = 2 if above_50 else 0
            
            sma_50_above_200 = sma_50 > sma_200
            pts_50_200 = 2 if sma_50_above_200 else 0
            
            dist_days = self.track_distribution_days(index_df)
            dist_days_ok = dist_days <= 4
            pts_dist = 2 if dist_days_ok else 0

        success_rate = breakout_success_rate
        feedback_file = "data/trade_feedback.json"
        if not os.path.exists(feedback_file) and os.path.exists(os.path.join("minervini_os", feedback_file)):
            feedback_file = os.path.join("minervini_os", feedback_file)
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file, "r") as f:
                    feedback_data = json.load(f)
                if len(feedback_data) > 0:
                    worked_count = sum(1 for item in feedback_data if item.get("status") == "worked")
                    success_rate = worked_count / len(feedback_data)
            except Exception as e:
                logger.error(f"Error reading trade feedback database: {e}")
                
        success_ok = success_rate >= 0.70
        pts_lead = 2 if success_ok else 0

        return {
            "score": total_score,
            "posture": posture,
            "recommendation": recommendation,
            "mbi_score": mbi_score,
            "breakdown": {
                "above_200_sma": {"status": bool(above_200), "value": float(latest_close), "sma": float(sma_200), "points": pts_200},
                "above_50_sma": {"status": bool(above_50), "value": float(latest_close), "sma": float(sma_50), "points": pts_50},
                "sma_50_above_200": {"status": bool(sma_50_above_200), "sma_50": float(sma_50), "sma_200": float(sma_200), "points": pts_50_200},
                "distribution_days": {"status": bool(dist_days_ok), "count": int(dist_days), "points": pts_dist},
                "breakout_success": {"status": bool(success_ok), "rate": float(success_rate), "points": pts_lead}
            }
        }


    def compute_market_health_score(self, index_df: pd.DataFrame, breakout_success_rate: float = 0.70) -> int:
        """
        Calculates the 10-point Market Health Score based on:
        - Index above 200 SMA (2 pts)
        - Index above 50 SMA (2 pts)
        - Index 50 SMA > 200 SMA (2 pts)
        - Distribution days <= 4 (2 pts)
        - Leadership success rate >= 70% (2 pts)
        """
        breakup = self.get_detailed_breakup(index_df, breakout_success_rate)
        
        # Log consolidated summary stats
        bd = breakup["breakdown"]
        logger.info("==================================================")
        logger.info(f"MARKET HEALTH SCORE BREAKDOWN (Benchmark: {self.index_symbol})")
        logger.info("==================================================")
        logger.info(f"1. Index Close ({bd['above_200_sma']['value']:.2f}) > 200 SMA ({bd['above_200_sma']['sma']:.2f}): {bd['above_200_sma']['points']} pts")
        logger.info(f"2. Index Close ({bd['above_50_sma']['value']:.2f}) > 50 SMA ({bd['above_50_sma']['sma']:.2f}): {bd['above_50_sma']['points']} pts")
        logger.info(f"3. 50 SMA ({bd['sma_50_above_200']['sma_50']:.2f}) > 200 SMA ({bd['sma_50_above_200']['sma_200']:.2f}): {bd['sma_50_above_200']['points']} pts")
        logger.info(f"4. Distribution Days ({bd['distribution_days']['count']} in rolling 20 days) <= 4: {bd['distribution_days']['points']} pts")
        logger.info(f"5. Leadership Win Rate ({bd['breakout_success']['rate']*100:.1f}%) >= 70%: {bd['breakout_success']['points']} pts")
        logger.info(f"==> Cumulative Score: {breakup['score']}/10 (Posture: {breakup['posture']})")
        logger.info(f"Recommendation: {breakup['recommendation']}")
        logger.info("==================================================")
        
        return breakup["score"]

    def get_market_posture(self, health_score: int) -> str:
        """
        Translates health score to active posture:
        - 8-10: GREEN
        - 5-7: YELLOW
        - < 5: RED
        """
        if health_score >= 8:
            return "GREEN"
        elif health_score >= 5:
            return "YELLOW"
        else:
            return "RED"
