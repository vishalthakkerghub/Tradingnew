import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger("TradeManager")

class TradeManager:
    """
    Post-Entry Trade Management Engine.
    Objectively evaluates open positions, calculates EQS, TBS, Expectancy Regime,
    runs Failure Detection, and determines the optimal daily trade action (HOLD, Trail, Add, Exit).
    """
    def __init__(self, config: dict):
        self.config = config
        self.journal_file = "data/trade_journal_data.json"
        if not os.path.exists(self.journal_file):
            self.journal_file = os.path.join("minervini_os", self.journal_file)
        self.earnings_calendar = {}
        ec_path = "data/earnings_calendar.json"
        if not os.path.exists(ec_path):
            ec_path = os.path.join("minervini_os", ec_path)
        if os.path.exists(ec_path):
            try:
                with open(ec_path, "r", encoding="utf-8") as f:
                    self.earnings_calendar = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load earnings calendar: {e}")
            
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculates Average True Range."""
        if len(df) < period + 1:
            return df["High"].max() - df["Low"].min() if not df.empty else 1.0
        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift()).abs()
        low_close = (df["Low"] - df["Close"].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(period).mean().iloc[-1]
        return float(atr) if not pd.isna(atr) else 1.0

    def get_market_health_score(self, as_of_date: str = None) -> float:
        """Loads and calculates Market Health Score (0-100) from last scan / index state."""
        try:
            index_file = "data/cache/NIFTY_50.csv"
            if not os.path.exists(index_file):
                index_file = os.path.join("minervini_os", index_file)
            if os.path.exists(index_file):
                df = pd.read_csv(index_file)
                if as_of_date:
                    df = df[df["Date"] <= as_of_date]
                if len(df) >= 200:
                    close = float(df["Close"].iloc[-1])
                    sma50 = float(df["Close"].iloc[-50:].mean())
                    sma200 = float(df["Close"].iloc[-200:].mean())
                    
                    score = 0
                    if close > sma200: score += 30
                    if close > sma50: score += 30
                    if sma50 > sma200: score += 20
                    
                    dist_days = 0
                    for i in range(-20, 0):
                        if df["Close"].iloc[i] < df["Close"].iloc[i-1] * 0.998 and df["Volume"].iloc[i] > df["Volume"].iloc[i-1]:
                            dist_days += 1
                    if dist_days <= 4:
                        score += 20
                    return float(score)
            return 50.0
        except Exception as e:
            logger.warning(f"Error calculating market health score: {e}")
            return 50.0

    def evaluate_single_trade_state(self, t: dict, df_slice: pd.DataFrame, mhs: float) -> dict:
        """
        Evaluates the trade parameters dynamically using a slice of historical stock data.
        This enables both current evaluation and historical progression checks.
        """
        symbol = t.get("symbol", "").upper()
        entry_price = float(t.get("entry_price", 0.0))
        stop_loss = float(t.get("stop_loss", 0.0))
        entry_date_str = t.get("entry_date", "")
        
        current_price = float(df_slice["Close"].iloc[-1])
        prev_close = float(df_slice["Close"].iloc[-2]) if len(df_slice) > 1 else current_price
        high_today = float(df_slice["High"].iloc[-1])
        low_today = float(df_slice["Low"].iloc[-1])
        prev_high = float(df_slice["High"].iloc[-2]) if len(df_slice) > 1 else high_today
        volume_today = float(df_slice["Volume"].iloc[-1])
        avg_vol_50 = float(df_slice["Volume"].iloc[-50:].mean())
        vol_ratio = round(volume_today / avg_vol_50, 2) if avg_vol_50 > 0 else 1.0
        
        days_active = len(df_slice[df_slice["Date"] >= entry_date_str]) if "Date" in df_slice.columns else 1
        if days_active <= 0:
            days_active = 1
            
        atr = self.calculate_atr(df_slice)
        ema10 = float(df_slice["Close"].ewm(span=10, adjust=False).mean().iloc[-1])
        ema20 = float(df_slice["Close"].ewm(span=20, adjust=False).mean().iloc[-1])
        sma50 = float(df_slice["Close"].iloc[-50:].mean())

        # --- Quantified Metrics (for day-over-day delta display) ---
        ema10_dist_pct = round((current_price - ema10) / ema10 * 100, 2) if ema10 > 0 else 0.0
        vdu_ratio = round(volume_today / avg_vol_50, 2) if avg_vol_50 > 0 else 1.0
        higher_high = high_today > prev_high
        # RS proxy: distance of close above 50-SMA relative to ATR, normalized 0-100
        rs_score = round(min(100, max(0, 50 + ((current_price - sma50) / atr) * 10)), 1) if atr > 0 else 50.0

        setup_type = t.get("setup_type", "STRICT_VCP")
        grade_str = t.get("grade", "Grade A")
        
        setup_base_map = {
            "STRICT_VCP": 100,
            "FLEX_VCP": 90,
            "MINI_VCP": 90,
            "FLAG_SETUP": 85,
            "INSIDE_BAR_FLAG": 80,
            "EMA_PULLBACK": 75
        }
        grade_mult_map = {
            "Grade A": 1.0,
            "Grade B": 0.8,
            "Grade C": 0.6
        }
        
        base_score = setup_base_map.get(setup_type, 80)
        mult = grade_mult_map.get(grade_str, 0.8)
        eqs = base_score * mult
        
        tbs = 100
        tbs_rationales = []
        
        initial_risk_price = entry_price - stop_loss if entry_price > stop_loss else 0.05 * entry_price
        r_multiple = (current_price - entry_price) / initial_risk_price if initial_risk_price > 0 else 0.0
        max_price_since_entry = float(df_slice[df_slice["Date"] >= entry_date_str]["Close"].max()) if "Date" in df_slice.columns else current_price
        max_r_multiple = (max_price_since_entry - entry_price) / initial_risk_price if initial_risk_price > 0 else 0.0
        
        if max_r_multiple >= 1.0:
            tbs += 10
            tbs_rationales.append("Hit +1R progress target (+10 pts).")
            if days_active <= 5:
                tbs += 10
                tbs_rationales.append("High-velocity breakout: Hit +1R in under 5 days (+10 pts).")
        else:
            if days_active > 5:
                tbs -= 15
                tbs_rationales.append(f"Progress Lag: Active for {days_active} days without hitting +1R (-15 pts).")
                
        if max_r_multiple >= 2.0:
            tbs += 15
            tbs_rationales.append("Hit +2R targets milestone (+15 pts).")
            if days_active <= 5:
                tbs += 15
                tbs_rationales.append("High velocity: Hit +2R in under 5 days (+15 pts).")
                
        if current_price > ema10:
            tbs += 10
            tbs_rationales.append("Price holding above 10 EMA (strong short-term momentum) (+10 pts).")
        elif current_price < ema20:
            tbs -= 20
            tbs_rationales.append("Price below 20 EMA (weakening short-term support) (-20 pts).")
            
        if current_price < sma50:
            tbs -= 30
            tbs_rationales.append("Price below 50 SMA (intermediate trend support breached) (-30 pts).")
            
        day_range = high_today - low_today
        closing_position = (current_price - low_today) / day_range if day_range > 0 else 0.5
        if closing_position >= 0.75:
            tbs += 5
            tbs_rationales.append("Strong daily close: Price finished in top 25% of day range (+5 pts).")
        elif closing_position <= 0.25:
            tbs -= 10
            tbs_rationales.append("Weak daily close: Price finished in bottom 25% of day range (-10 pts).")
            
        is_up_day = current_price > prev_close
        is_high_volume = volume_today > 1.2 * avg_vol_50
        if is_up_day and is_high_volume:
            tbs += 5
            tbs_rationales.append("Institutional Buying: Up day on heavy volume (+5 pts).")
        elif not is_up_day and is_high_volume:
            tbs -= 15
            tbs_rationales.append("Institutional Distribution: Down day on heavy volume (-15 pts).")
            
        is_inside_day = high_today <= float(df_slice["High"].iloc[-2]) and low_today >= float(df_slice["Low"].iloc[-2]) if len(df_slice) > 1 else False
        if (not is_up_day or is_inside_day) and volume_today < 0.6 * avg_vol_50:
            tbs += 10
            tbs_rationales.append("Volume Dry Up (VDU): Price tightening on low volume (+10 pts).")
            
        if current_price > ema10 + (3.0 * atr) and day_range > 2.0 * atr:
            tbs -= 15
            tbs_rationales.append("Climax Extension: Price overextended (>3 ATR above 10 EMA) on high volatility (-15 pts).")
            
        tbs = max(0, min(100, tbs))
        
        if eqs >= 85:
            p_c3, p_c2, p_c1 = 0.35, 0.45, 0.20
        elif eqs >= 70:
            p_c3, p_c2, p_c1 = 0.15, 0.50, 0.35
        else:
            p_c3, p_c2, p_c1 = 0.05, 0.35, 0.60
            
        pbm = (current_price - entry_price) / (atr * days_active) if (atr * days_active) > 0 else 0.0
        
        if pbm > 1.5:
            p_c3 += 0.40
            p_c1 -= 0.30
            p_c2 -= 0.10
        elif pbm < -0.3:
            p_c1 += 0.50
            p_c3 -= 0.35
            p_c2 -= 0.15
            
        probs = np.clip([p_c3, p_c2, p_c1], 0.01, 0.99)
        probs /= probs.sum()
        p_c3, p_c2, p_c1 = float(probs[0]), float(probs[1]), float(probs[2])
        
        dominant_idx = np.argmax([p_c3, p_c2, p_c1])
        regime_map = {0: "Category 3 (Exceptional)", 1: "Category 2 (Strong)", 2: "Category 1 (Average)"}
        expectancy_regime = regime_map[dominant_idx]
        
        fci = 0
        fail_reasons = []
        
        # Hard Check for Stop Loss Breach
        is_current_day_sl_breached = False
        current_breach_type = ""
        is_past_day_sl_breached = False
        first_breach_date = None
        current_date = df_slice["Date"].iloc[-1] if "Date" in df_slice.columns else ""
        
        if stop_loss > 0 and entry_date_str:
            df_since_entry = df_slice[df_slice["Date"] >= entry_date_str]
            for _, row in df_since_entry.iterrows():
                r_close = float(row["Close"])
                r_low = float(row["Low"]) if "Low" in row else r_close
                r_date = row["Date"]
                
                if r_date == current_date:
                    if r_close <= stop_loss:
                        is_current_day_sl_breached = True
                        current_breach_type = "Close"
                    elif r_low <= stop_loss:
                        is_current_day_sl_breached = True
                        current_breach_type = "Intraday Low"
                else:
                    if r_close <= stop_loss or r_low <= stop_loss:
                        if not is_past_day_sl_breached:
                            is_past_day_sl_breached = True
                            first_breach_date = r_date
                            
        if is_current_day_sl_breached:
            fci = 100
            tbs = 0
            if current_breach_type == "Close":
                fail_reasons.append(f"Stop Loss Breach on Close [Violates RULE 4: Stop Loss is Sacred & RULE #0: No Hesitation to Exit]: Close price Rs.{current_price:.2f} is below Stop Loss Rs.{stop_loss:.2f}.")
            else:
                fail_reasons.append(f"Stop Loss Breach Intraday [Violates RULE 4: Stop Loss is Sacred & RULE #0: No Hesitation to Exit]: Intraday Low Rs.{low_today:.2f} touched Stop Loss Rs.{stop_loss:.2f}.")
        else:
            # Evaluate normally but add a past breach warning if applicable
            if is_past_day_sl_breached:
                fail_reasons.append(f"[CONSTITUTION WARNING: Stop Loss was historically breached on close/intraday on {first_breach_date}, violating Rule 4 & Rule 0. Active position is currently held in violation of stop.]")
                
            if days_active <= 5 and current_price < entry_price:
                fci += 30
                fail_reasons.append("Squat Breakout Failure [Violates RULE 8: Expect Instant Accretion]: Stock trading below entry price within 5 days of breakout.")
                if is_high_volume and not is_up_day:
                    fci += 15
                    fail_reasons.append("High Volume Rejection on Failure [Violates RULE 5: Track Institutional Footprints].")
                    
            was_climax = max_price_since_entry > ema10 + (2.5 * atr) if ema10 > 0 else False
            if was_climax and current_price < ema10:
                fci += 45
                fail_reasons.append("Climax Reversal [Violates RULE 6: Sell on Strength/Climax Crossover]: Closed below 10 EMA after severe overextension.")
                
            if not is_up_day and volume_today > 1.5 * avg_vol_50 and closing_position <= 0.20:
                fci += 35
                fail_reasons.append("Institutional Distribution [Violates RULE 5: Track Institutional Footprints]: Heavy volume sell-off with weak close.")
                
            sub_10 = df_slice.iloc[-10:] if len(df_slice) >= 10 else df_slice
            largest_down_pct = 0.0
            if len(sub_10) > 1:
                pct_changes = sub_10["Close"].pct_change() * 100
                largest_down_pct = float(pct_changes.min())
            
            today_change_pct = ((current_price - prev_close) / prev_close) * 100
            if today_change_pct < -3.0 and today_change_pct <= largest_down_pct * 0.95:
                fci += 25
                fail_reasons.append(f"Character Change [Violates RULE 2: Keep Losses Small / Change of Behavior]: Today's drop of {today_change_pct:.1f}% is the largest down day in the last 10 days.")
                
            fci = min(100, fci)
        
        allow_pyramid = False
        pyramid_reason = ""
        
        if r_multiple >= 2.0:
            is_tight_flag = float(df_slice["High"].iloc[-5:].max() - df_slice["Low"].iloc[-5:].min()) / float(df_slice["Low"].iloc[-5:].min()) <= 0.05
            is_ema_pb = abs(current_price - ema10) / ema10 <= 0.015 or abs(current_price - ema20) / ema20 <= 0.015
            
            if is_tight_flag or is_inside_day or is_ema_pb:
                allow_pyramid = True
                pyramid_reason = "Profitable position (>= 2R) with current tight pullback/inside day setup. Entire position can be raised to a breakeven stop loss."
                
        recommended_sl = stop_loss
        sl_reason = "Keep original stop loss (default protection window)"
        
        if r_multiple >= 1.0:
            recommended_sl = entry_price
            sl_reason = "Move stop loss to Cost (breakeven) to lock in risk-free status as trade has hit +1R."
            
        if dominant_idx == 0:
            if current_price > ema10 * 1.05 and ema10 > entry_price:
                recommended_sl = max(recommended_sl, ema10)
                sl_reason = "Trail 10 EMA tightly (Category 3 Exceptional Trend strategy)."
        elif dominant_idx == 1:
            if current_price > ema20 * 1.03 and ema20 > entry_price:
                recommended_sl = max(recommended_sl, ema20)
                sl_reason = "Trail 20 EMA (Category 2 Strong Trend strategy)."
                
        recommended_sl = max(recommended_sl, stop_loss)
        
        # Determine base constructive rationales based on TBS factors
        constructive_reasons = tbs_rationales if tbs_rationales else ["Stock is behaving within normal parameters."]

        confidence = 80
        if is_current_day_sl_breached:
            action = "🚨 EXIT NOW (SL BREACHED)"
            confidence = 100
            reasons = [
                "CONSTITUTION RULE 4 VIOLATION: Stop Loss has been breached! You must exit immediately. No hope, no ego. Sell now."
            ] + fail_reasons
        elif is_past_day_sl_breached:
            action = "🚨 EXIT NOW (CONSTITUTION BREACH)"
            confidence = 100
            reasons = [
                "CONSTITUTION VIOLATION: This position is being held in violation of a past stop loss breach! Cut the trade immediately. Save your capital."
            ] + fail_reasons
        elif fci >= 65:
            action = "EXIT"
            confidence = int(fci)
            reasons = fail_reasons if fail_reasons else ["Stop Loss Breach or high-severity failure signature detected."]
        elif fci >= 45:
            action = "TAKE PARTIAL PROFITS"
            confidence = int(70 + (fci / 2))
            reasons = fail_reasons + ["Protecting gains on emerging distribution/weakness signatures."] + constructive_reasons
        elif allow_pyramid and mhs >= 75:
            action = "BUY MORE"
            confidence = int(min(95, tbs - 5))
            reasons = [
                "Stage: TREND RUNNER. Position is highly profitable. Pullback setup identified. Consider adding to position."
            ] + fail_reasons + [pyramid_reason] + constructive_reasons
        elif tbs >= 80:
            action = "HOLD"
            confidence = int(tbs)
            stage_msg = "Stage: PRE-T1. Stock behaving normally. Do not cut early — give the trade room to hit T1." if r_multiple < 1.0 else "Stage: POST-T1. Risk-free runner. Stop trailed to cost. Let it run."
            reasons = [stage_msg] + fail_reasons + constructive_reasons
        else:
            action = "HOLD & TRAIL"
            confidence = int(max(50, tbs))
            stage_msg = "Stage: PRE-T1. Normal pullback. Do not cut early." if r_multiple < 1.0 else "Stage: POST-T1. Risk-free runner. Stop trailed to cost. Let it run."
            reasons = [stage_msg] + fail_reasons + constructive_reasons + [sl_reason]
            
        partial_exit_pct = 0
        if action == "TAKE PARTIAL PROFITS":
            if fci >= 60:
                partial_exit_pct = 50
            elif fci >= 50:
                partial_exit_pct = 33
            else:
                partial_exit_pct = 25
        elif action == "EXIT":
            partial_exit_pct = 100
            
        # --- Day Summary Label (specific, action-linked human-readable description) ---
        if is_current_day_sl_breached:
            if current_breach_type == "Close":
                day_summary = "SL Breached (Close)"
            else:
                day_summary = "SL Touched Intraday"
        elif action == "EXIT" and not is_current_day_sl_breached:
            # Non-SL exits: climax reversal or character breakdown
            if was_climax and current_price < ema10:
                day_summary = "Climax Reversal Exit"
            elif fci >= 65:
                day_summary = "Technical Breakdown"
            else:
                day_summary = "Exit Signal"
        elif action == "TAKE PARTIAL PROFITS":
            if was_climax:
                day_summary = "Climax — Partial Exit"
            elif not is_up_day and vol_ratio > 1.2:
                day_summary = "Distribution — Partial Exit"
            else:
                day_summary = "Partial Profit Taken"
        elif is_past_day_sl_breached and current_price > stop_loss:
            day_summary = "Recovery Attempt"
        elif rs_score >= 70 and higher_high and vol_ratio > 1.2 and is_up_day:
            day_summary = "Breakout Accelerated"
        elif rs_score >= 60 and ema10_dist_pct > 0 and is_up_day and higher_high:
            day_summary = "Trend Strengthened"
        elif rs_score >= 50 and ema10_dist_pct > 0 and not is_up_day and vdu_ratio < 0.7:
            day_summary = "Healthy Pullback"
        elif current_price > ema10 and prev_close < ema10:
            day_summary = "Trend Confirmed"
        elif is_up_day and not higher_high and vdu_ratio < 0.8:
            day_summary = "Momentum Slowed"
        elif ema10_dist_pct > 5.0:
            day_summary = "Climax Warning"
        elif not is_up_day and vol_ratio > 1.2:
            day_summary = "Distribution Day"
        elif not is_up_day and vdu_ratio < 0.6:
            day_summary = "Healthy Consolidation"
        elif is_up_day:
            day_summary = "Holding Strong"
        else:
            day_summary = "Holding Pattern"

        ec_info = self.earnings_calendar.get(symbol, {})
        earnings_date = ec_info.get("Earnings_Date")
        days_to_earnings = ec_info.get("Days_To_Earnings")

        return {
            "id": t.get("id"),
            "symbol": symbol,
            "earnings_date": earnings_date,
            "days_to_earnings": days_to_earnings,
            "setup_type": setup_type,
            "grade": grade_str,
            "entry_price": entry_price,
            "current_price": current_price,
            "days_active": days_active,
            "r_multiple": round(r_multiple, 2),
            "eqs": int(eqs),
            "tbs": int(tbs),
            "fci": int(fci),
            "mhs": int(mhs),
            "expectancy_regime": expectancy_regime,
            "probs": {
                "category_3": round(p_c3 * 100, 1),
                "category_2": round(p_c2 * 100, 1),
                "category_1": round(p_c1 * 100, 1)
            },
            "recommended_stop": round(recommended_sl, 2),
            "stop_reason": sl_reason,
            "action": action,
            "confidence": confidence,
            "reasons": reasons,
            "partial_exit_pct": partial_exit_pct,
            "allow_pyramid": allow_pyramid,
            "day_summary": day_summary,
            "metrics": {
                "rs_score": rs_score,
                "ema10": round(ema10, 2),
                "ema10_dist_pct": ema10_dist_pct,
                "vdu_ratio": vdu_ratio,
                "vol_ratio": vol_ratio,
                "higher_high": higher_high,
                "stop_loss": round(stop_loss, 2),
                "recommended_stop": round(recommended_sl, 2),
                "closing_position_pct": round(closing_position * 100, 1),
                "is_up_day": is_up_day,
            }
        }

    def evaluate_all_trades(self) -> dict:
        """
        Loads all OPEN trades from journal and performs post-entry quantitative audit.
        Returns a dict of evaluated trades and recommendations.
        """
        if not os.path.exists(self.journal_file):
            logger.warning("Trade journal file not found.")
            return {"trades": [], "summary": "No journal found"}
            
        try:
            with open(self.journal_file, "r", encoding="utf-8") as f:
                journal = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load trade journal: {e}")
            return {"trades": [], "summary": f"Error: {e}"}
            
        open_trades = [t for t in journal if t.get("status") == "OPEN"]
        if not open_trades:
            return {"trades": [], "summary": "No active open positions"}
            
        evaluated_trades = []
        mhs = self.get_market_health_score()
        
        for t in open_trades:
            symbol = t.get("symbol", "").upper()
            cache_file = f"data/cache/{symbol}.csv"
            if not os.path.exists(cache_file):
                cache_file = os.path.join("minervini_os", cache_file)
                
            if not os.path.exists(cache_file):
                logger.warning(f"No cache file found for {symbol}. Skipping dynamic evaluation.")
                continue
                
            try:
                df = pd.read_csv(cache_file)
                df.columns = [c.strip() for c in df.columns]
                if df.empty or len(df) < 50:
                    continue
            except Exception as e:
                logger.error(f"Error loading cache for {symbol}: {e}")
                continue
                
            try:
                evaluated_trade = self.evaluate_single_trade_state(t, df, mhs)
                evaluated_trades.append(evaluated_trade)
            except Exception as e:
                logger.error(f"Error evaluating trade state for {symbol}: {e}")
                continue
                
        return {
            "trades": evaluated_trades,
            "summary": f"Analyzed {len(evaluated_trades)} open positions successfully."
        }

    def evaluate_trades_history(self) -> dict:
        """
        Calculates the day-by-day evaluation state of all OPEN positions since their entry dates.
        Returns a timeline list for each active position.
        """
        if not os.path.exists(self.journal_file):
            logger.warning("Trade journal file not found.")
            return {"positions": [], "summary": "No journal found"}
            
        try:
            with open(self.journal_file, "r", encoding="utf-8") as f:
                journal = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load trade journal: {e}")
            return {"positions": [], "summary": "Error"}
            
        open_trades = [t for t in journal if t.get("status") == "OPEN"]
        if not open_trades:
            return {"positions": [], "summary": "No active open positions"}
            
        positions_history = []
        
        for t in open_trades:
            symbol = t.get("symbol", "").upper()
            entry_price = float(t.get("entry_price", 0.0))
            entry_date_str = t.get("entry_date", "")
            
            cache_file = f"data/cache/{symbol}.csv"
            if not os.path.exists(cache_file):
                cache_file = os.path.join("minervini_os", cache_file)
                
            if not os.path.exists(cache_file):
                continue
                
            try:
                df = pd.read_csv(cache_file)
                df.columns = [c.strip() for c in df.columns]
                if df.empty or len(df) < 50 or "Date" not in df.columns:
                    continue
            except Exception as e:
                logger.error(f"Error loading cache for {symbol} in history: {e}")
                continue
                
            history_dates = df[df["Date"] >= entry_date_str]["Date"].tolist()
            if not history_dates:
                history_dates = [df["Date"].iloc[-1]]
                
            trade_history = []
            
            for date_str in history_dates:
                df_slice = df[df["Date"] <= date_str]
                if len(df_slice) < 15:
                    continue
                mhs = self.get_market_health_score(date_str)
                try:
                    state = self.evaluate_single_trade_state(t, df_slice, mhs)
                    state["date"] = date_str
                    trade_history.append(state)
                except Exception as e:
                    logger.warning(f"Error evaluating history state for {symbol} on {date_str}: {e}")
                    
            positions_history.append({
                "id": t.get("id"),
                "symbol": symbol,
                "entry_price": entry_price,
                "entry_date": entry_date_str,
                "stop_loss": float(t.get("stop_loss", 0.0)),
                "setup_type": t.get("setup_type", "STRICT_VCP"),
                "grade": t.get("grade", "Grade A"),
                "history": trade_history
            })
            
        return {
            "positions": positions_history,
            "summary": f"Calculated history for {len(positions_history)} positions successfully."
        }
