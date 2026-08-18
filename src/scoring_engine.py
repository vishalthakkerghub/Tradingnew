import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("ScoringEngine")

class CandidateScoringEngine:
    """
    Computes a multi-factor score out of 100 points for VCP candidates.
    Factors: Trend Quality (20 pts), VCP Quality (40 pts), VDU Quality (20 pts), and Readiness (20 pts).
    """
    def __init__(self, config: dict = None):
        self.config = config or {}

    def calculate_score(
        self,
        stock_df: pd.DataFrame,
        index_df: pd.DataFrame,
        grade: str,
        vdu_ratio: float,
        readiness_status: str,
        risk_pct: float = None
    ) -> dict:
        """
        Calculates the components and total score for a candidate.
        Returns a dictionary with component details and the final score.
        """
        # 1. Trend Quality (Max 20 points)
        # A. Distance to 52-Week High (10 points)
        # Using 250 bars lookback for 52-week high, consistent with TrendTemplateEngine
        if len(stock_df) >= 250:
            high_52w = float(stock_df["High"].iloc[-250:].max())
        else:
            high_52w = float(stock_df["High"].max())

        close = float(stock_df["Close"].iloc[-1])
        
        if high_52w > 0:
            dist_pct = (high_52w - close) / high_52w
        else:
            dist_pct = 0.0

        trend_52w_points = float(np.clip(10.0 * (1.0 - (dist_pct / 0.25)), 0.0, 10.0))

        # B. Relative Strength Margin (10 points)
        # Using 90 trading days (91st row from end) return comparison, consistent with TrendTemplateEngine
        if len(stock_df) >= 91:
            stock_close_90d_ago = float(stock_df["Close"].iloc[-91])
        else:
            stock_close_90d_ago = float(stock_df["Close"].iloc[0])

        if len(index_df) >= 91:
            index_close_90d_ago = float(index_df["Close"].iloc[-91])
        else:
            index_close_90d_ago = float(index_df["Close"].iloc[0])

        stock_return_90d = (close / stock_close_90d_ago) - 1.0 if stock_close_90d_ago > 0 else 0.0
        index_close_latest = float(index_df["Close"].iloc[-1])
        index_return_90d = (index_close_latest / index_close_90d_ago) - 1.0 if index_close_90d_ago > 0 else 0.0

        margin = stock_return_90d - index_return_90d
        rs_points = float(np.clip(margin * 50.0, 0.0, 10.0))
        
        trend_quality = trend_52w_points + rs_points

        # 2. VCP Quality (Max 40 points)
        vcp_quality = 0.0
        if grade:
            grade_clean = grade.upper().strip()
            if "GRADE A" in grade_clean or grade_clean == "A":
                vcp_quality = 40.0
            elif "GRADE B" in grade_clean or grade_clean == "B":
                vcp_quality = 30.0
            elif "GRADE C" in grade_clean or grade_clean == "C":
                vcp_quality = 20.0

        # 3. VDU Quality (Max 20 points)
        vdu_quality = 0.0
        if vdu_ratio <= 0.10:
            vdu_quality = 20.0
        elif vdu_ratio <= 0.20:
            vdu_quality = 15.0
        elif vdu_ratio <= 0.30:
            vdu_quality = 10.0
        elif vdu_ratio <= 0.40:
            vdu_quality = 5.0

        # 4. Readiness (Max 20 points)
        readiness = 0.0
        if readiness_status:
            status_clean = readiness_status.upper().strip()
            if status_clean == "STRICT READY":
                readiness = 20.0
            elif status_clean == "FLEX READY" or status_clean == "MINI READY":
                readiness = 15.0
            elif status_clean == "DEVELOPING":
                readiness = 10.0
            elif status_clean == "POST-BREAKOUT":
                readiness = 5.0

        # 5. Risk Penalty (Max risk tolerance: 3-6%)
        risk_penalty = 0.0
        if risk_pct is not None and risk_pct > 6.0:
            risk_penalty = 15.0

        total_score = trend_quality + vcp_quality + vdu_quality + readiness - risk_penalty

        logger.debug(
            f"Scoring Breakdown: 52w High={trend_52w_points:.2f}, RS Margin={rs_points:.2f} (Total Trend={trend_quality:.2f}) | "
            f"VCP Quality={vcp_quality:.1f} (Grade: {grade}) | "
            f"VDU Quality={vdu_quality:.1f} (Ratio: {vdu_ratio*100:.1f}%) | "
            f"Readiness={readiness:.1f} (Status: {readiness_status}) | "
            f"Risk Penalty={risk_penalty:.1f} (Risk %: {risk_pct if risk_pct is not None else 0.0:.1f}%) | "
            f"Total Score={total_score:.2f}"
        )

        return {
            "trend_52w_points": trend_52w_points,
            "rs_points": rs_points,
            "trend_quality_score": trend_quality,
            "vcp_quality_score": vcp_quality,
            "vdu_quality_score": vdu_quality,
            "readiness_score": readiness,
            "risk_penalty": risk_penalty,
            "total_score": max(0.0, total_score)
        }
