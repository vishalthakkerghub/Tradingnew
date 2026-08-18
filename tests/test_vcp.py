import unittest
import pandas as pd
import numpy as np
from src.vcp_engine import VCPEngine

class TestVCPEngine(unittest.TestCase):
    """
    Unit test suite for the VCP Candidate Engine.
    """
    def setUp(self):
        self.mock_config = {
            "vcp_parameters": {
                "pivot_sensitivity_bars": 5,
                "min_contractions": 2,
                "max_contractions": 4,
                "min_base_duration_weeks": 5,
                "max_base_duration_weeks": 26,
                "watchlist_readiness_pct": 0.95
            }
        }
        self.engine = VCPEngine(self.mock_config)

    def test_pivot_swing_detection_strict(self):
        """
        Verify pivot high and low points are detected using 5-bar window in STRICT mode.
        """
        dates = pd.date_range(start="2026-01-01", periods=30)
        data = {
            "Open": [100.0] * 30,
            "High": [100.0] * 30,
            "Low": [90.0] * 30,
            "Close": [95.0] * 30,
            "Volume": [10000] * 30
        }
        df = pd.DataFrame(data, index=dates)

        # Inject Pivot High at index 10 (value 110)
        df.loc[df.index[10], "High"] = 110.0
        # Inject Pivot Low at index 20 (value 80)
        df.loc[df.index[20], "Low"] = 80.0

        pivots = self.engine.detect_pivot_swing_points(df, mode="STRICT")

        self.assertEqual(len(pivots), 2)
        self.assertEqual(pivots[0]['type'], 'high')
        self.assertEqual(pivots[0]['price'], 110.0)
        self.assertEqual(pivots[1]['type'], 'low')
        self.assertEqual(pivots[1]['price'], 80.0)

    def test_pivot_swing_detection_flex(self):
        """
        Verify pivot swing points are detected with a tighter 3-bar window in FLEX mode.
        """
        dates = pd.date_range(start="2026-01-01", periods=20)
        data = {
            "Open": [100.0] * 20,
            "High": [100.0] * 20,
            "Low": [90.0] * 20,
            "Close": [95.0] * 20,
            "Volume": [10000] * 20
        }
        df = pd.DataFrame(data, index=dates)

        # Inject high that is a pivot under 3-bar sensitivity but NOT under 5-bar sensitivity
        # High at index 6 is 110.0. Preceding 3 bars are 100, succeeding 3 are 100.
        # But high at index 2 is 105.0. If window is 5, index 6 has index 2 (which is 105) inside its left window,
        # but wait, 110 > 105, so index 6 is still a pivot.
        # Let's make index 6 higher than its 3-bar neighbors but lower than a neighbor 4 bars away.
        # E.g. Highs: [100, 100, 115, 100, 100, 100, 110, 100, 100, 100, 100]
        # For index 6 (110): 
        # Left 3 neighbors: index 3 (100), 4 (100), 5 (100) -> 110 is higher.
        # Right 3 neighbors: index 7 (100), 8 (100), 9 (100) -> 110 is higher.
        # So index 6 is a 3-bar pivot high.
        # But for 5-bar neighbors: index 2 is 115. 110 < 115, so index 6 is NOT a 5-bar pivot high!
        df["High"] = [100.0] * 20
        df.loc[df.index[2], "High"] = 115.0
        df.loc[df.index[6], "High"] = 110.0
        
        # Test STRICT (5-bar)
        pivots_strict = self.engine.detect_pivot_swing_points(df, mode="STRICT")
        # index 6 should NOT be in strict pivots (only index 2 is pivot high)
        strict_high_indices = [p['row_index'] for p in pivots_strict if p['type'] == 'high']
        self.assertNotIn(6, strict_high_indices)

        # Test FLEX (3-bar)
        pivots_flex = self.engine.detect_pivot_swing_points(df, mode="FLEX")
        # index 6 SHOULD be in flex pivots
        flex_high_indices = [p['row_index'] for p in pivots_flex if p['type'] == 'high']
        self.assertIn(6, flex_high_indices)

    def test_depth_contraction_sequence(self):
        """
        Verify successive depth shrinkage sequence check using STRICT (2%) and FLEX (3%) tolerance.
        """
        # depth: T1 = 20%, T2 = 22.5%.
        # STRICT tolerance is 2%: 22.5% <= 20% + 2% (False) -> Should fail in STRICT.
        # FLEX tolerance is 3%: 22.5% <= 20% + 3% (True) -> Should pass in FLEX.
        pivots = [
            {'type': 'high', 'price': 100.0, 'row_index': 10},
            {'type': 'low', 'price': 80.0, 'row_index': 15},
            {'type': 'high', 'price': 100.0, 'row_index': 20},
            {'type': 'low', 'price': 77.5, 'row_index': 25}
        ]
        
        contractions_strict = self.engine.calculate_contraction_sequence(pivots, mode="STRICT")
        self.assertEqual(len(contractions_strict), 0)

        contractions_flex = self.engine.calculate_contraction_sequence(pivots, mode="FLEX")
        self.assertEqual(len(contractions_flex), 2)
        self.assertAlmostEqual(contractions_flex[0]['depth'], 20.0)
        self.assertAlmostEqual(contractions_flex[1]['depth'], 22.5)

    def test_volume_dry_up_calculation(self):
        """
        Verify VDU check for STRICT (30%) and FLEX (40%) ratios.
        """
        dates = pd.date_range(start="2026-01-01", periods=50)
        # Volume: 100,000 for 45 days, 35,000 for last 5 days
        # 5-day average = 35,000. 50-day average = (45*100000 + 5*35000)/50 = 93,500.
        # Ratio = 35,000 / 93,500 = 0.374 (37.4%)
        # STRICT (30%) should fail. FLEX (40%) should pass.
        data = {
            "Open": [100.0] * 50,
            "High": [100.0] * 50,
            "Low": [90.0] * 50,
            "Close": [95.0] * 50,
            "Volume": [100000] * 45 + [35000] * 5
        }
        df = pd.DataFrame(data, index=dates)

        self.assertFalse(self.engine.check_volume_dry_up(df, mode="STRICT"))
        self.assertTrue(self.engine.check_volume_dry_up(df, mode="FLEX"))

    def test_watchlist_readiness_threshold(self):
        """
        Verify proximity check in STRICT (5%) and FLEX (10%).
        """
        # Pivot = 100.0. Close = 92.0.
        # STRICT range: [95.0, 100.0] -> Close 92.0 fails.
        # FLEX range: [90.0, 100.0] -> Close 92.0 passes.
        self.assertFalse(self.engine.is_watchlist_ready(92.0, 100.0, mode="STRICT"))
        self.assertTrue(self.engine.is_watchlist_ready(92.0, 100.0, mode="FLEX"))

    def test_is_vcp_candidate_end_to_end(self):
        """
        Verify STRICT mode end-to-end candidate matching.
        """
        dates = pd.date_range(start="2026-01-01", periods=100)
        highs = [90.0] * 100
        lows = [85.0] * 100
        closes = [87.0] * 100
        volume = [50000] * 100

        # Inject 5-bar swing pivots
        for i in range(15, 26): highs[i] = 95.0
        highs[20] = 100.0
        for i in range(35, 46): lows[i] = 85.0
        lows[40] = 80.0
        for i in range(55, 66): highs[i] = 85.0
        highs[60] = 90.0
        for i in range(75, 86): lows[i] = 85.0
        lows[80] = 81.0

        for i in range(95, 100): volume[i] = 10000
        closes[-1] = 88.0

        df = pd.DataFrame({"Open": closes, "High": highs, "Low": lows, "Close": closes, "Volume": volume}, index=dates)

        is_candidate, pivot_price, grade, k, depths, vdu_ratio, final_low = self.engine.is_vcp_candidate(df, mode="STRICT")
        self.assertTrue(is_candidate)
        self.assertEqual(pivot_price, 90.0)
        self.assertEqual(grade, "Grade B")
        self.assertEqual(k, 2)
        self.assertEqual(depths, "T1: 20.0% | T2: 10.0%")
        self.assertAlmostEqual(vdu_ratio, 10000 / 46000)

    def test_vcp_candidate_grading(self):
        """
        Verify quality grades calculation outputs.
        """
        dates = pd.date_range(start="2026-01-01", periods=100)
        highs = [95.0] * 100
        lows = [90.0] * 100
        closes = [92.0] * 100
        volume = [100000] * 100

        # T1: depth = 20%
        for i in range(15, 26): highs[i] = 95.0
        highs[20] = 100.0
        for i in range(35, 46): lows[i] = 85.0
        lows[40] = 80.0

        # T2: depth = 5%
        for i in range(55, 66): highs[i] = 88.0
        highs[60] = 90.0
        for i in range(75, 86): lows[i] = 87.0
        lows[80] = 85.5

        # VDU ratio = 5%
        for i in range(95, 100): volume[i] = 5000
        closes[-1] = 89.0

        df_a = pd.DataFrame({"Open": closes, "High": highs, "Low": lows, "Close": closes, "Volume": volume}, index=dates)

        is_candidate, pivot_price, grade, k, depths, vdu_ratio, final_low = self.engine.is_vcp_candidate(df_a, mode="STRICT")
        self.assertTrue(is_candidate)
        self.assertEqual(grade, "Grade A")

    def test_vcp_candidate_flex_fallback(self):
        """
        Verify that a stock which fails STRICT criteria passes under FLEX mode.
        """
        # Create a series of 100 bars
        dates = pd.date_range(start="2026-01-01", periods=100)
        highs = [90.0] * 100
        lows = [85.0] * 100
        closes = [87.0] * 100
        volume = [50000] * 100

        # Inject 3-bar swing pivots (which fail STRICT 5-bar detection)
        # H1 at index 20 (High 100)
        for i in range(17, 24): highs[i] = 95.0
        highs[20] = 100.0
        # L1 at index 35 (Low 80)
        for i in range(32, 39): lows[i] = 85.0
        lows[35] = 80.0
        # H2 at index 50 (High 90)
        for i in range(47, 54): highs[i] = 85.0
        highs[50] = 90.0
        # L2 at index 65 (Low 81)
        for i in range(62, 69): lows[i] = 85.0
        lows[65] = 81.0

        # Dry up volume to 35% (fails STRICT's 30%, but passes FLEX's 40%)
        # 5-day average is 17,500. 50-day average is (45*50000 + 5*17500)/50 = 46,750.
        # Ratio = 17,500 / 46,750 = 0.374 (37.4%)
        for i in range(95, 100): volume[i] = 17500

        # Close is 83.0 (Pivot is 90.0. Distance = 7.7% below pivot -> Fails STRICT 5% proximity, passes FLEX 10% proximity)
        closes[-1] = 83.0

        df = pd.DataFrame({"Open": closes, "High": highs, "Low": lows, "Close": closes, "Volume": volume}, index=dates)

        # STRICT check must fail
        is_cand_s, _, _, _, _, _, _ = self.engine.is_vcp_candidate(df, mode="STRICT")
        self.assertFalse(is_cand_s)

        # FLEX check must pass
        is_cand_f, pivot_f, grade_f, k_f, depths_f, vdu_f, final_low_f = self.engine.is_vcp_candidate(df, mode="FLEX")
        self.assertTrue(is_cand_f)
        self.assertEqual(pivot_f, 90.0)
        self.assertEqual(k_f, 2)
        self.assertEqual(grade_f, "Grade B")  # strict decrease (+1), final depth 10% <=10% (+1), VDU ratio 37% (0 pt) -> Total 2 -> Grade B

    def test_pivot_swing_detection_mini(self):
        """
        Verify that a stock qualifying for MINI VCP is correctly identified under MINI mode,
        while failing STRICT due to base duration or other parameters.
        """
        # Create a series of 50 bars
        dates = pd.date_range(start="2026-01-01", periods=50)
        highs = [90.0] * 50
        lows = [85.0] * 50
        closes = [87.0] * 50
        volume = [50000] * 50

        # Inject 3-bar swing pivots
        # H1 at index 15 (High 100)
        # L1 at index 22 (Low 80)
        # H2 at index 29 (High 95)
        # L2 at index 36 (Low 88)
        # Base duration = 29 - 15 = 14 trading days (which is 2.8 weeks, within 3 to 6 weeks range)
        # This will fail STRICT and FLEX base duration (STRICT: min 5 weeks = 23 days; FLEX: min 4 weeks = 18 days)
        
        # H1 setup
        for i in range(12, 19): highs[i] = 95.0
        highs[15] = 100.0
        # L1 setup
        for i in range(19, 26): lows[i] = 85.0
        lows[22] = 80.0
        # H2 setup
        for i in range(26, 33): highs[i] = 90.0
        highs[29] = 95.0
        # L2 setup
        for i in range(33, 40): lows[i] = 90.0
        lows[36] = 88.0

        # Dry up volume to 25% (passes MINI VDU 35% check)
        for i in range(45, 50): volume[i] = 12000

        df = pd.DataFrame({"Open": closes, "High": highs, "Low": lows, "Close": closes, "Volume": volume}, index=dates)

        # STRICT check must fail due to base duration (14 days < 23 days)
        is_cand_s, _, _, _, _, _, _ = self.engine.is_vcp_candidate(df, mode="STRICT")
        self.assertFalse(is_cand_s)

        # FLEX check must fail due to base duration (14 days < 18 days)
        is_cand_f, _, _, _, _, _, _ = self.engine.is_vcp_candidate(df, mode="FLEX")
        self.assertFalse(is_cand_f)

        # MINI check must pass
        is_cand_m, pivot_m, grade_m, k_m, depths_m, vdu_m, final_low_m = self.engine.is_vcp_candidate(df, mode="MINI")
        self.assertTrue(is_cand_m)
        self.assertEqual(pivot_m, 95.0)
        self.assertEqual(k_m, 2)
        self.assertEqual(final_low_m, 88.0)

if __name__ == "__main__":
    unittest.main()

