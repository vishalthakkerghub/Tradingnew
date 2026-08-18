import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("VCPEngine")

class VCPEngine:
    """
    Interface for VCP pattern identification and watchlist readiness screening.
    Supports STRICT_VCP and FLEX_VCP modes with distinct parameters.
    """
    def __init__(self, config: dict):
        self.config = config
        self.params = config.get("vcp_parameters", {})
        self.min_c = self.params.get("min_contractions", 2)
        self.max_c = self.params.get("max_contractions", 4)
        
        # Define Mode Profiles
        self.profiles = {
            "STRICT": {
                "sensitivity": self.params.get("pivot_sensitivity_bars", 5),
                "tolerance": 0.0,
                "vdu": 0.30,
                "proximity": self.params.get("watchlist_readiness_pct", 0.95),
                "min_weeks": self.params.get("min_base_duration_weeks", 5),
                "max_weeks": self.params.get("max_base_duration_weeks", 26)
            },
            "FLEX": {
                "sensitivity": 3,
                "tolerance": 3.0,
                "vdu": 0.40,
                "proximity": 0.90,
                "min_weeks": 4,
                "max_weeks": 26
            },
            "MINI": {
                "sensitivity": 3,
                "tolerance": 2.0,
                "vdu": 0.35,
                "proximity": 0.95,
                "min_weeks": 3,
                "max_weeks": 6
            }
        }
        logger.info(
            f"VCPEngine initialized. STRICT Profile (Sensitivity={self.profiles['STRICT']['sensitivity']}, Tolerance={self.profiles['STRICT']['tolerance']}%, VDU={self.profiles['STRICT']['vdu']}, Proximity={self.profiles['STRICT']['proximity']}) | "
            f"FLEX Profile (Sensitivity={self.profiles['FLEX']['sensitivity']}, Tolerance={self.profiles['FLEX']['tolerance']}%, VDU={self.profiles['FLEX']['vdu']}, Proximity={self.profiles['FLEX']['proximity']})"
        )

    def detect_pivot_swing_points(self, stock_df: pd.DataFrame, mode: str = "STRICT") -> list:
        """
        Locates Pivot High and Pivot Low points using a rolling sensitivity window.
        Uses profile parameters specific to STRICT or FLEX mode.
        """
        sensitivity = self.profiles.get(mode, self.profiles["STRICT"])["sensitivity"]
        logger.info(f"Running pivot swing point detection (Mode: {mode}, Sensitivity: {sensitivity} left/right)")
        
        pivots = []
        n = len(stock_df)
        if n < 2 * sensitivity + 1:
            logger.warning(f"Stock price history is insufficient ({n} bars) to detect pivots with sensitivity {sensitivity}.")
            return []

        highs = stock_df['High'].values
        lows = stock_df['Low'].values
        timestamps = stock_df.index

        is_high = np.ones(n, dtype=bool)
        is_low = np.ones(n, dtype=bool)

        for offset in range(-sensitivity, sensitivity + 1):
            if offset == 0:
                continue
            slice_highs = highs[sensitivity : n - sensitivity]
            compare_highs = highs[sensitivity + offset : n - sensitivity + offset]
            is_high[sensitivity : n - sensitivity] &= (slice_highs > compare_highs)

            slice_lows = lows[sensitivity : n - sensitivity]
            compare_lows = lows[sensitivity + offset : n - sensitivity + offset]
            is_low[sensitivity : n - sensitivity] &= (slice_lows < compare_lows)

        high_indices = set(np.where(is_high[sensitivity : n - sensitivity])[0] + sensitivity)
        low_indices = set(np.where(is_low[sensitivity : n - sensitivity])[0] + sensitivity)

        for idx in range(sensitivity, n - sensitivity):
            if idx in high_indices:
                pivots.append({
                    'index': timestamps[idx],
                    'row_index': idx,
                    'type': 'high',
                    'price': float(highs[idx])
                })
            elif idx in low_indices:
                pivots.append({
                    'index': timestamps[idx],
                    'row_index': idx,
                    'type': 'low',
                    'price': float(lows[idx])
                })

        return pivots

    def _filter_alternating_pivots(self, pivots: list, stock_df: pd.DataFrame = None) -> list:
        """
        Groups consecutive pivots of the same type and keeps the most extreme one.
        If stock_df is provided, reconstructs missing intermediate swing points
        by searching for local extremes between consecutive same-type pivots.
        Ensures the final returned sequence alternates, starting with a High and ending with a Low.
        """
        if not pivots:
            return []

        # Sort pivots by row index
        pivots = sorted(pivots, key=lambda x: x['row_index'])
        
        if stock_df is None:
            # Old behavior: Keep the more extreme price level for same type pivots
            alternating = []
            for p in pivots:
                if not alternating:
                    alternating.append(p)
                else:
                    last = alternating[-1]
                    if p['type'] == last['type']:
                        if p['type'] == 'high':
                            if p['price'] > last['price']:
                                alternating[-1] = p
                        else:  # low
                            if p['price'] < last['price']:
                                alternating[-1] = p
                    else:
                        alternating.append(p)
            while alternating and alternating[0]['type'] == 'low':
                alternating.pop(0)
            while alternating and alternating[-1]['type'] == 'high':
                alternating.pop()
            return alternating

        # Reconstruct intermediate swings
        reconstructed = []
        for p in pivots:
            if not reconstructed:
                reconstructed.append(p)
            else:
                last = reconstructed[-1]
                if p['type'] == last['type']:
                    idx1 = last['row_index']
                    idx2 = p['row_index']
                    
                    if idx2 > idx1 + 1:
                        if p['type'] == 'low':
                            # Find maximum high between idx1 + 1 and idx2 - 1
                            sub_df = stock_df.iloc[idx1 + 1 : idx2]
                            max_idx = sub_df['High'].idxmax()
                            max_row_idx = stock_df.index.get_loc(max_idx)
                            max_price = float(stock_df['High'].iloc[max_row_idx])
                            
                            synthetic_high = {
                                'index': max_idx,
                                'row_index': max_row_idx,
                                'type': 'high',
                                'price': max_price
                            }
                            reconstructed.append(synthetic_high)
                            reconstructed.append(p)
                        else:
                            # Find minimum low between idx1 + 1 and idx2 - 1
                            sub_df = stock_df.iloc[idx1 + 1 : idx2]
                            min_idx = sub_df['Low'].idxmin()
                            min_row_idx = stock_df.index.get_loc(min_idx)
                            min_price = float(stock_df['Low'].iloc[min_row_idx])
                            
                            synthetic_low = {
                                'index': min_idx,
                                'row_index': min_row_idx,
                                'type': 'low',
                                'price': min_price
                            }
                            reconstructed.append(synthetic_low)
                            reconstructed.append(p)
                    else:
                        # Adjacent indices, keep more extreme
                        if p['type'] == 'high':
                            if p['price'] > last['price']:
                                reconstructed[-1] = p
                        else:
                            if p['price'] < last['price']:
                                reconstructed[-1] = p
                else:
                    reconstructed.append(p)

        # Standard clean up
        alternating = []
        for p in reconstructed:
            if not alternating:
                alternating.append(p)
            else:
                last = alternating[-1]
                if p['type'] == last['type']:
                    if p['type'] == 'high':
                        if p['price'] > last['price']:
                            alternating[-1] = p
                    else:
                        if p['price'] < last['price']:
                            alternating[-1] = p
                else:
                    alternating.append(p)

        while alternating and alternating[0]['type'] == 'low':
            alternating.pop(0)
        while alternating and alternating[-1]['type'] == 'high':
            alternating.pop()

        return alternating

    def calculate_contraction_sequence(self, pivots: list, mode: str = "STRICT") -> list:
        """
        Calculates depths for identified waves and checks the sequence rule:
        D(n) <= D(n-1) + Tolerance
        """
        tolerance = self.profiles.get(mode, self.profiles["STRICT"])["tolerance"]
        logger.info(f"Evaluating contraction sequence depths (Mode: {mode}, Tolerance: {tolerance}%)")
        
        alternating = self._filter_alternating_pivots(pivots)
        num_pairs = len(alternating) // 2

        contractions = []
        for i in range(num_pairs):
            high_p = alternating[2 * i]
            low_p = alternating[2 * i + 1]
            depth = (high_p['price'] - low_p['price']) / high_p['price'] * 100
            contractions.append({
                'high_pivot': high_p,
                'low_pivot': low_p,
                'depth': depth
            })

        # Evaluate contraction sequence rule
        for i in range(1, len(contractions)):
            if contractions[i]['depth'] > contractions[i - 1]['depth'] + tolerance:
                logger.debug(
                    f"Violation of contraction sequence rule: "
                    f"Contraction {i} Depth ({contractions[i]['depth']:.2f}%) > "
                    f"Contraction {i-1} Depth ({contractions[i-1]['depth']:.2f}%) + {tolerance}%"
                )
                return []

        return contractions

    def check_volume_dry_up(self, stock_df: pd.DataFrame, mode: str = "STRICT") -> bool:
        """
        Validates Volume Dry-Up (VDU) rule:
        Average(Volume, 5) <= VDU_Threshold * Average(Volume, 50)
        """
        vdu_threshold = self.profiles.get(mode, self.profiles["STRICT"])["vdu"]
        logger.info(f"Executing 5-day vs 50-day Volume Dry-Up check (Mode: {mode}, Threshold: {vdu_threshold})")
        
        if len(stock_df) < 50:
            logger.warning(f"Stock price history is insufficient ({len(stock_df)} bars) to calculate 50-day Volume SMA.")
            return False

        avg_vol_5 = stock_df['Volume'].iloc[-5:].mean()
        avg_vol_50 = stock_df['Volume'].iloc[-50:].mean()

        if pd.isna(avg_vol_5) or pd.isna(avg_vol_50) or avg_vol_50 == 0:
            return False

        result = avg_vol_5 <= vdu_threshold * avg_vol_50
        logger.debug(f"Volume Dry-Up check results: 5-Day Avg: {avg_vol_5:.1f} | 50-Day Avg: {avg_vol_50:.1f}. Passed: {result}")
        return result

    def is_watchlist_ready(self, current_price: float, pivot_price: float, mode: str = "STRICT") -> bool:
        """
        Checks if the current price is within the window below or equal to the pivot price:
        Proximity * Pivot Price <= Current Price <= Pivot Price
        """
        proximity = self.profiles.get(mode, self.profiles["STRICT"])["proximity"]
        logger.info(f"Evaluating watchlist readiness proximity threshold (Mode: {mode}, Proximity: {proximity})")
        
        if pivot_price <= 0:
            return False
            
        result = (proximity * pivot_price <= current_price <= pivot_price)
        logger.debug(f"Watchlist readiness check: Current: {current_price} | Pivot: {pivot_price} | Thresholds: [{proximity * pivot_price:.2f}, {pivot_price:.2f}]. Passed: {result}")
        return result

    def is_vcp_candidate(self, stock_df: pd.DataFrame, mode: str = "STRICT") -> tuple:
        """
        Runs comprehensive checks to classify ticker as a VCP Candidate under the specified mode.
        Returns a tuple of (is_candidate, pivot_price, grade, contraction_count, depths_str, vdu_ratio, final_contraction_low).
        """
        logger.info(f"Evaluating VCP candidacy criteria under mode: {mode}")
        if len(stock_df) < 50:
            logger.warning(f"Data length ({len(stock_df)} bars) is too short to evaluate VCP.")
            return False, 0.0, None, 0, "", 0.0, 0.0

        pivots = self.detect_pivot_swing_points(stock_df, mode=mode)
        alternating = self._filter_alternating_pivots(pivots, stock_df)

        # Check suffixes of the pivot list for contraction counts from max_c down to min_c
        for k in range(self.max_c, self.min_c - 1, -1):
            if len(alternating) < 2 * k:
                continue

            candidate_pivots = alternating[-2 * k:]
            contractions = self.calculate_contraction_sequence(candidate_pivots, mode=mode)
            if not contractions or len(contractions) != k:
                continue

            # Check base duration (in trading days, represented by bar count between first pivot high and final pivot high)
            high_1 = contractions[0]['high_pivot']
            high_n = contractions[-1]['high_pivot']
            low_n = contractions[-1]['low_pivot']
            base_duration = high_n['row_index'] - high_1['row_index']

            pivot_price = float(high_n['price'])
            current_price = float(stock_df['Close'].iloc[-1])
            is_post_breakout = current_price > pivot_price

            # Check VDU at final contraction low if breakout occurred, otherwise check at end of dataframe
            vdu_idx = None
            if is_post_breakout:
                vdu_idx = low_n['row_index'] + 1
            
            if vdu_idx is not None:
                avg_vol_5 = stock_df['Volume'].iloc[vdu_idx-5:vdu_idx].mean()
                avg_vol_50 = stock_df['Volume'].iloc[vdu_idx-50:vdu_idx].mean()
                vdu_ratio = avg_vol_5 / avg_vol_50 if avg_vol_50 > 0 else 1.0
            else:
                avg_vol_5 = stock_df['Volume'].iloc[-5:].mean()
                avg_vol_50 = stock_df['Volume'].iloc[-50:].mean()
                vdu_ratio = avg_vol_5 / avg_vol_50 if avg_vol_50 > 0 else 1.0

            # Power Play Check
            h1_idx = high_1['row_index']
            start_idx = max(0, h1_idx - 60)
            min_low_prior = float(stock_df['Low'].iloc[start_idx:h1_idx].min())
            prior_gain = (high_1['price'] - min_low_prior) / min_low_prior * 100 if min_low_prior > 0 else 0.0
            
            is_power_play = prior_gain >= 75.0 and contractions[0]['depth'] <= 25.0

            if is_power_play:
                min_days = 15 # 3 weeks for Power Play
                vdu_threshold = 0.50 if mode == "STRICT" else 0.70
            else:
                min_days = self.profiles[mode]["min_weeks"] * 5 - 2
                vdu_threshold = self.profiles[mode]["vdu"]


            max_days = self.profiles[mode]["max_weeks"] * 5

            if base_duration < min_days or base_duration > max_days:
                logger.debug(f"Base duration {base_duration} trading days falls outside [{min_days}, {max_days}] range for contraction count {k}.")
                continue

            if vdu_ratio > vdu_threshold:
                logger.debug(f"VDU check failed: ratio {vdu_ratio:.2f} > threshold {vdu_threshold:.2f} for contraction count {k} in mode {mode}.")
                continue

            # Calculate Quality Grades
            # 1. Contraction Quality Score (Max 3 points)
            strict_decrease = True
            for i in range(1, len(contractions)):
                if contractions[i]['depth'] >= contractions[i - 1]['depth']:
                    strict_decrease = False
                    break
            
            contraction_score = 0
            if strict_decrease:
                contraction_score += 1
            
            final_depth = contractions[-1]['depth']
            if final_depth <= 6.0:
                contraction_score += 2
            elif final_depth <= 10.0:
                contraction_score += 1

            # 2. VDU Quality Score (Max 3 points)
            vdu_score = 0
            if vdu_ratio <= 0.15:
                vdu_score += 3
            elif vdu_ratio <= 0.20:
                vdu_score += 2
            elif vdu_ratio <= 0.25:
                vdu_score += 1

            total_points = contraction_score + vdu_score
            if total_points >= 4:
                grade = "Grade A"
            elif total_points >= 2:
                grade = "Grade B"
            else:
                grade = "Grade C"

            depths_str = " | ".join([f"T{i+1}: {c['depth']:.1f}%" for i, c in enumerate(contractions)])
            final_contraction_low = float(low_n['price'])

            logger.info(f"Ticker qualifies as a {mode}_VCP candidate with {k} contractions! Grade: {grade} (Points: {total_points}/6) | Base duration: {base_duration} trading days. Pivot Price: {pivot_price} | Final Low: {final_contraction_low}")
            return True, pivot_price, grade, k, depths_str, vdu_ratio, final_contraction_low

        return False, 0.0, None, 0, "", 0.0, 0.0
