import unittest
import pandas as pd
import numpy as np
from src.scoring_engine import CandidateScoringEngine

class TestCandidateScoringEngine(unittest.TestCase):
    """
    Unit tests for CandidateScoringEngine.
    """
    def setUp(self):
        self.scoring_engine = CandidateScoringEngine()

    def test_trend_quality_52week_high(self):
        """
        Verify Distance to 52-Week High scoring logic.
        Points = clip(10 * (1 - Dist_Pct / 0.25), 0, 10)
        """
        dates = pd.date_range(start="2026-01-01", periods=250)
        
        # Test Case 1: Close is exactly at 52-week high -> Dist_Pct = 0% -> 10 points
        df_at_high = pd.DataFrame({
            "High": [100.0] * 249 + [100.0],
            "Close": [95.0] * 249 + [100.0]
        }, index=dates)
        
        score_dict = self.scoring_engine.calculate_score(
            stock_df=df_at_high,
            index_df=pd.DataFrame({"Close": [100.0] * 91}),
            grade="Grade A",
            vdu_ratio=0.05,
            readiness_status="STRICT READY"
        )
        self.assertAlmostEqual(score_dict["trend_52w_points"], 10.0)

        # Test Case 2: Close is 10% below 52-week high -> Dist_Pct = 10% -> 10 * (1 - 0.10/0.25) = 6.0 points
        df_10pct = pd.DataFrame({
            "High": [100.0] * 249 + [100.0],
            "Close": [95.0] * 249 + [90.0]
        }, index=dates)
        
        score_dict = self.scoring_engine.calculate_score(
            stock_df=df_10pct,
            index_df=pd.DataFrame({"Close": [100.0] * 91}),
            grade="Grade A",
            vdu_ratio=0.05,
            readiness_status="STRICT READY"
        )
        self.assertAlmostEqual(score_dict["trend_52w_points"], 6.0)

        # Test Case 3: Close is 25% or more below 52-week high -> Dist_Pct = 25% -> 0.0 points
        df_25pct = pd.DataFrame({
            "High": [100.0] * 249 + [100.0],
            "Close": [95.0] * 249 + [75.0]
        }, index=dates)
        
        score_dict = self.scoring_engine.calculate_score(
            stock_df=df_25pct,
            index_df=pd.DataFrame({"Close": [100.0] * 91}),
            grade="Grade A",
            vdu_ratio=0.05,
            readiness_status="STRICT READY"
        )
        self.assertAlmostEqual(score_dict["trend_52w_points"], 0.0)

    def test_trend_quality_rs_margin(self):
        """
        Verify Relative Strength Margin scoring logic.
        Points = clip((Stock_Return_90D - Index_Return_90D) * 50, 0, 10)
        """
        dates_stock = pd.date_range(start="2026-01-01", periods=91)
        dates_index = pd.date_range(start="2026-01-01", periods=91)

        # Test Case 1: Outperformance margin = 10% (Stock = 20%, Index = 10%) -> Margin = 0.10 -> 0.10 * 50 = 5 points
        # Stock: close 90d ago = 100, latest = 120 (return = 20%)
        # Index: close 90d ago = 100, latest = 110 (return = 10%)
        stock_closes = [100.0] * 90 + [120.0]
        stock_closes[0] = 100.0
        index_closes = [100.0] * 90 + [110.0]
        index_closes[0] = 100.0

        df_stock = pd.DataFrame({"High": stock_closes, "Close": stock_closes}, index=dates_stock)
        df_index = pd.DataFrame({"Close": index_closes}, index=dates_index)

        score_dict = self.scoring_engine.calculate_score(
            stock_df=df_stock,
            index_df=df_index,
            grade="Grade B",
            vdu_ratio=0.15,
            readiness_status="DEVELOPING"
        )
        self.assertAlmostEqual(score_dict["rs_points"], 5.0)

        # Test Case 2: Outperformance margin = 30% (Stock = 30%, Index = 0%) -> Margin = 0.30 -> 0.30 * 50 = 15 clipped to 10 points
        stock_closes_2 = [100.0] * 90 + [130.0]
        stock_closes_2[0] = 100.0
        index_closes_2 = [100.0] * 91

        df_stock_2 = pd.DataFrame({"High": stock_closes_2, "Close": stock_closes_2}, index=dates_stock)
        df_index_2 = pd.DataFrame({"Close": index_closes_2}, index=dates_index)

        score_dict = self.scoring_engine.calculate_score(
            stock_df=df_stock_2,
            index_df=df_index_2,
            grade="Grade B",
            vdu_ratio=0.15,
            readiness_status="DEVELOPING"
        )
        self.assertAlmostEqual(score_dict["rs_points"], 10.0)

        # Test Case 3: Underperformance -> Margin = -10% -> 0 points
        stock_closes_3 = [100.0] * 90 + [90.0]
        stock_closes_3[0] = 100.0
        index_closes_3 = [100.0] * 91

        df_stock_3 = pd.DataFrame({"High": stock_closes_3, "Close": stock_closes_3}, index=dates_stock)
        df_index_3 = pd.DataFrame({"Close": index_closes_3}, index=dates_index)

        score_dict = self.scoring_engine.calculate_score(
            stock_df=df_stock_3,
            index_df=df_index_3,
            grade="Grade B",
            vdu_ratio=0.15,
            readiness_status="DEVELOPING"
        )
        self.assertAlmostEqual(score_dict["rs_points"], 0.0)

    def test_vcp_quality_points(self):
        """
        Verify VCP Quality points.
        A=40, B=30, C=20, otherwise 0.
        """
        df = pd.DataFrame({"High": [100.0] * 91, "Close": [100.0] * 91})
        df_idx = pd.DataFrame({"Close": [100.0] * 91})

        # Grade A
        res = self.scoring_engine.calculate_score(df, df_idx, "Grade A", 0.05, "STRICT READY")
        self.assertEqual(res["vcp_quality_score"], 40.0)

        # Grade B
        res = self.scoring_engine.calculate_score(df, df_idx, "Grade B", 0.05, "STRICT READY")
        self.assertEqual(res["vcp_quality_score"], 30.0)

        # Grade C
        res = self.scoring_engine.calculate_score(df, df_idx, "Grade C", 0.05, "STRICT READY")
        self.assertEqual(res["vcp_quality_score"], 20.0)

        # Unknown Grade
        res = self.scoring_engine.calculate_score(df, df_idx, "Grade Unknown", 0.05, "STRICT READY")
        self.assertEqual(res["vcp_quality_score"], 0.0)

    def test_vdu_quality_points(self):
        """
        Verify VDU Quality points.
        <=10%: 20, <=20%: 15, <=30%: 10, <=40%: 5, otherwise 0
        """
        df = pd.DataFrame({"High": [100.0] * 91, "Close": [100.0] * 91})
        df_idx = pd.DataFrame({"Close": [100.0] * 91})

        # <=10%
        res = self.scoring_engine.calculate_score(df, df_idx, "Grade C", 0.08, "STRICT READY")
        self.assertEqual(res["vdu_quality_score"], 20.0)

        # <=20%
        res = self.scoring_engine.calculate_score(df, df_idx, "Grade C", 0.15, "STRICT READY")
        self.assertEqual(res["vdu_quality_score"], 15.0)

        # <=30%
        res = self.scoring_engine.calculate_score(df, df_idx, "Grade C", 0.28, "STRICT READY")
        self.assertEqual(res["vdu_quality_score"], 10.0)

        # <=40%
        res = self.scoring_engine.calculate_score(df, df_idx, "Grade C", 0.35, "STRICT READY")
        self.assertEqual(res["vdu_quality_score"], 5.0)

        # >40%
        res = self.scoring_engine.calculate_score(df, df_idx, "Grade C", 0.45, "STRICT READY")
        self.assertEqual(res["vdu_quality_score"], 0.0)

    def test_readiness_points(self):
        """
        Verify Readiness points.
        STRICT READY=20, FLEX READY=15, DEVELOPING=10, POST-BREAKOUT=5, otherwise 0.
        """
        df = pd.DataFrame({"High": [100.0] * 91, "Close": [100.0] * 91})
        df_idx = pd.DataFrame({"Close": [100.0] * 91})

        res = self.scoring_engine.calculate_score(df, df_idx, "Grade C", 0.08, "STRICT READY")
        self.assertEqual(res["readiness_score"], 20.0)

        res = self.scoring_engine.calculate_score(df, df_idx, "Grade C", 0.08, "FLEX READY")
        self.assertEqual(res["readiness_score"], 15.0)

        res = self.scoring_engine.calculate_score(df, df_idx, "Grade C", 0.08, "DEVELOPING")
        self.assertEqual(res["readiness_score"], 10.0)

        res = self.scoring_engine.calculate_score(df, df_idx, "Grade C", 0.08, "POST-BREAKOUT")
        self.assertEqual(res["readiness_score"], 5.0)

        res = self.scoring_engine.calculate_score(df, df_idx, "Grade C", 0.08, "UNKNOWN")
        self.assertEqual(res["readiness_score"], 0.0)

    def test_total_score_aggregation(self):
        """
        Verify that components sum up correctly.
        """
        # Dist to 52w high: Close is 10% below high of 100 -> 10 * (1 - 0.10/0.25) = 6.0
        # RS Margin: Stock return = 10%, Index return = 0% -> Margin = 10% -> 0.10 * 50 = 5.0
        # Total Trend = 11.0
        # Grade = Grade A -> 40.0
        # VDU Ratio = 15% -> 15.0
        # Readiness = FLEX READY -> 15.0
        # Total = 11.0 + 40.0 + 15.0 + 15.0 = 81.0
        dates = pd.date_range(start="2026-01-01", periods=250)
        df_stock = pd.DataFrame({
            "High": [100.0] * 250,
            "Close": [100.0] * 159 + [90.0] * 91 # Close 90d ago (index -91) is 100.0. Latest is 90.0? Wait, return would be negative.
            # Let's design the stock close prices carefully:
            # Stock: Close at index -91 is 81.81. Latest close is 90.0. Return = (90/81.81) - 1 = 10%.
            # Let's set high_52w = 100.0.
        }, index=dates)
        
        # Override values at index -91 and -1 to get exact returns
        df_stock.loc[df_stock.index[-91], "Close"] = 90.0 / 1.10
        df_stock.loc[df_stock.index[-1], "Close"] = 90.0
        # Ensure high_52w is 100
        df_stock.loc[df_stock.index[0], "High"] = 100.0

        df_index = pd.DataFrame({"Close": [100.0] * 91}, index=dates[-91:])

        res = self.scoring_engine.calculate_score(
            stock_df=df_stock,
            index_df=df_index,
            grade="Grade A",
            vdu_ratio=0.15,
            readiness_status="FLEX READY"
        )
        
        self.assertAlmostEqual(res["trend_52w_points"], 6.0)
        self.assertAlmostEqual(res["rs_points"], 5.0)
        self.assertEqual(res["vcp_quality_score"], 40.0)
        self.assertEqual(res["vdu_quality_score"], 15.0)
        self.assertEqual(res["readiness_score"], 15.0)
        self.assertAlmostEqual(res["total_score"], 81.0)

if __name__ == "__main__":
    unittest.main()
