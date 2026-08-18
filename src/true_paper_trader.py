import os
import json
import logging
import math
import csv
from datetime import datetime
import pandas as pd

logger = logging.getLogger("TruePaperTrader")

STATE_FILE = "data/true_paper_portfolio.json"

BANNED_COMBOS = {
    'A': ['PULLBACK_EMA10'],
    'B': ['PULLBACK_EMA10','INSIDE_BAR_FLAG','FLEX_VCP'],
    'C': ['PULLBACK_EMA20','INSIDE_BAR_FLAG']
}

def get_mbi_allowed_grades(mbi_idx):
    if mbi_idx >= 70: return ['A','B','C']
    if mbi_idx >= 55: return ['B','A','C']
    if mbi_idx >= 45: return ['B','C']
    if mbi_idx >= 30: return ['C']
    return []

def get_cmp_from_cache(symbol):
    path = f"data/cache/{symbol.upper()}.csv"
    if not os.path.exists(path):
        return None, None, None
    try:
        df = pd.read_csv(path)
        if df.empty:
            return None, None, None
        df.columns = [c.strip() for c in df.columns]
        last = df.iloc[-1]
        close = float(last.get("Close", 0))
        high = float(last.get("High", 0))
        low = float(last.get("Low", 0))
        return close, high, low
    except Exception as e:
        logger.warning(f"Error reading cache for {symbol}: {e}")
        return None, None, None

class TruePaperTrader:
    def __init__(self, state_file=STATE_FILE):
        self.state_file = state_file
        self.state = {
            "meta": {
                "initial_capital": 100000.0,
                "started_on": datetime.now().strftime("%Y-%m-%d"),
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "version": "1.0"
            },
            "cash": 100000.0,
            "open_trades": [],
            "closed_trades": [],
            "daily_snapshots": {},
            "process_log": []
        }
        self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge keys to support upgrade paths
                    for k in self.state:
                        if k in loaded:
                            self.state[k] = loaded[k]
                logger.info(f"Loaded True Paper Portfolio. Cash: Rs.{self.state['cash']:.2f}")
            except Exception as e:
                logger.error(f"Failed to load True Paper Portfolio state: {e}")
        else:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            self.save_state()

    def save_state(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save True Paper Portfolio: {e}")

    def rollback_day(self, date_str):
        logger.info(f"Rolling back execution for date: {date_str}...")
        
        # 1. Remove new trades entered today
        remaining_open = []
        for t in self.state["open_trades"]:
            if t["entry_date"] == date_str:
                # Return capital to cash
                self.state["cash"] += t["invested"]
                logger.info(f"Rollback: Removed new trade {t['symbol']} and refunded {t['invested']:.2f} cash.")
            else:
                remaining_open.append(t)
        self.state["open_trades"] = remaining_open

        # 2. Restore closed trades that exited today
        remaining_closed = []
        for t in self.state["closed_trades"]:
            if t["exit_date"] == date_str:
                # Restore to open trades
                init_risk = t["initial_qty"] * (t["entry_price"] - t["stop_loss"])
                open_trade = {
                    "id": f"{t['symbol']}_{t['entry_date']}",
                    "symbol": t["symbol"],
                    "entry_date": t["entry_date"],
                    "entry_price": t["entry_price"],
                    "trigger_price": t.get("trigger_price", t["entry_price"]),
                    "stop_loss": t.get("stop_loss", 0.0),
                    "trailing_sl": t.get("stop_loss", 0.0),
                    "t1": t.get("t1", 0.0),
                    "t2": t.get("t2", 0.0),
                    "initial_qty": t["initial_qty"],
                    "open_qty": t["initial_qty"], # Restore full qty
                    "invested": t["initial_qty"] * t["entry_price"],
                    "risk_per_share": round(t["entry_price"] - t.get("stop_loss", 0.0), 2),
                    "risk_amount": round(init_risk, 2),
                    "grade": t["grade"],
                    "engine_type": t["engine_type"],
                    "sector": t.get("sector", "Neutral"),
                    "sector_zone": t.get("sector_zone", "Neutral"),
                    "gates": ["MBI", "Sector", "Pattern", "SL Band"],
                    "phase": "PRE-T1",
                    "cmp": t["exit_price"],
                    "unrealized_pnl": 0.0,
                    "unrealized_r": 0.0,
                    "days_active": 0,
                    "t1_hit": False,
                    "t2_hit": False,
                    "sl_hit": False,
                    "partial_exits": []
                }
                
                # Restore partial exits that did not happen today
                for pe in t.get("partial_exits", []):
                    if pe["date"] != date_str:
                        open_trade["partial_exits"].append(pe)
                        open_trade["open_qty"] -= pe["qty"]
                        if pe["target"] == "T1":
                            open_trade["t1_hit"] = True
                            open_trade["trailing_sl"] = open_trade["entry_price"]
                        elif pe["target"] == "T2":
                            open_trade["t2_hit"] = True
                            
                # Dynamically set trailing SL based on targets hit prior to today
                max_high = t.get("max_high_reached", t["entry_price"])
                if open_trade["t2_hit"]:
                    open_trade["trailing_sl"] = max(open_trade["entry_price"], round(max_high * 0.95, 2))
                elif open_trade["t1_hit"]:
                    open_trade["trailing_sl"] = open_trade["entry_price"]
                else:
                    open_trade["trailing_sl"] = open_trade["stop_loss"]

                # Subtract today's exit proceeds from cash
                exit_proceeds = t["open_qty"] * t["exit_price"]
                self.state["cash"] -= exit_proceeds
                self.state["open_trades"].append(open_trade)
                logger.info(f"Rollback: Restored closed trade {t['symbol']} back to open positions.")
            else:
                remaining_closed.append(t)
        self.state["closed_trades"] = remaining_closed

        # 3. Rollback partial exits that happened today on remaining open trades
        for t in self.state["open_trades"]:
            # Decrement days active
            if t["entry_date"] != date_str:
                t["days_active"] = max(0, t["days_active"] - 1)
            
            # Filter out today's partial exits
            remaining_pes = []
            for pe in t.get("partial_exits", []):
                if pe["date"] == date_str:
                    # Refund qty and deduct cash
                    t["open_qty"] += pe["qty"]
                    self.state["cash"] -= pe["qty"] * pe["price"]
                    logger.info(f"Rollback: Reversed partial exit for {t['symbol']} (Target {pe['target']}) of {pe['qty']} shares.")
                    # Reset target flags
                    if pe["target"] == "T1":
                        t["t1_hit"] = False
                        t["trailing_sl"] = t["stop_loss"] # reset to original
                    elif pe["target"] == "T2":
                        t["t2_hit"] = False
                else:
                    remaining_pes.append(pe)
            t["partial_exits"] = remaining_pes

        # 4. Remove snapshot
        if date_str in self.state["daily_snapshots"]:
            del self.state["daily_snapshots"][date_str]

        # 5. Remove process logs for today
        self.state["process_log"] = [log for log in self.state["process_log"] if not log.startswith(f"[{date_str}]")]

    def get_previous_trading_date(self, date_str):
        # Load NIFTY_50 cache to find the trading day immediately preceding date_str
        nifty_file = "data/cache/NIFTY_50.csv"
        if os.path.exists(nifty_file):
            try:
                df = pd.read_csv(nifty_file)
                df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
                dates = sorted(df['Date'].unique())
                if date_str in dates:
                    idx = dates.index(date_str)
                    if idx > 0:
                        return dates[idx - 1]
            except Exception as e:
                logger.warning(f"Error finding previous date from Nifty cache: {e}")
                
        # Fallback: scan reports/daily/ for vcp_candidates_*.csv files
        try:
            candidates_dates = []
            for fname in os.listdir("reports/daily"):
                if fname.startswith("vcp_candidates_") and fname.endswith(".csv"):
                    d_part = fname.replace("vcp_candidates_", "").replace(".csv", "")
                    if len(d_part) == 8:
                        candidates_dates.append(f"{d_part[:4]}-{d_part[4:6]}-{d_part[6:]}")
            candidates_dates = sorted(candidates_dates)
            if date_str in candidates_dates:
                idx = candidates_dates.index(date_str)
                if idx > 0:
                    return candidates_dates[idx - 1]
            older_dates = [d for d in candidates_dates if d < date_str]
            if older_dates:
                return older_dates[-1]
        except Exception as e:
            logger.warning(f"Error finding previous date from candidate files: {e}")
            
        return None

    def add_log(self, date_str, msg):
        log_entry = f"[{date_str}] {msg}"
        self.state["process_log"].append(log_entry)
        # Keep last 200 logs
        if len(self.state["process_log"]) > 200:
            self.state["process_log"] = self.state["process_log"][-200:]
        logger.info(log_entry)

    def validate_gates(self, s, mbi_rules, category):
        grade_raw = (s.get("Setup_Grade") or s.get("Grade") or 'Grade C').upper()
        grade_key = 'A' if 'GRADE A' in grade_raw else 'B' if 'GRADE B' in grade_raw else 'C'
        pattern = (s.get("Setup_Type") or s.get("Engine_Type") or s.get("Pattern") or '').upper().replace('_','')
        
        # Resolve risk percent
        risk_pct = float(s.get("Risk_Pct") or s.get("risk_pct") or 0)
        if risk_pct == 0:
            entry = float(s.get("Entry") or s.get("Entry_Price") or s.get("Trigger") or 0)
            sl = float(s.get("Stop_Loss") or s.get("stop_loss") or 0)
            if entry > 0 and sl > 0 and entry > sl:
                risk_pct = (entry - sl) / entry * 100

        # Gate 1: MBI
        mbi_ok = grade_key in mbi_rules
        
        # Gate 2: Sector
        sector_ok = category in ['Confirmed Uptrend', 'Early Uptrend']

        # Gate 3: Pattern
        is_banned = False
        for b in BANNED_COMBOS.get(grade_key, []):
            if b.replace('_', '') in pattern:
                is_banned = True
                break
        pattern_ok = not is_banned

        # Gate 4: SL Band
        sl_ok = True
        if grade_key == 'A':
            if 3.0 <= risk_pct < 4.0:
                sl_ok = False
            elif risk_pct > 7.0:
                sl_ok = False
        elif grade_key == 'B':
            if risk_pct > 7.0:
                sl_ok = False
        else: # C
            if risk_pct > 3.5:
                sl_ok = False

        all_pass = mbi_ok and sector_ok and pattern_ok and sl_ok
        return all_pass, grade_key, {
            "mbi": mbi_ok,
            "sector": sector_ok,
            "pattern": pattern_ok,
            "sl": sl_ok
        }

    def run_daily_update(self, date_str=None):
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # Run rollback first to ensure idempotency (clean slate for date_str)
        self.rollback_day(date_str)

        # ── 1. Load MBI ────────────────────────────────────────────────────────
        mbi_file = "data/market_breadth.json"
        mbi_idx = 50.0
        if os.path.exists(mbi_file):
            try:
                mbi_data = json.load(open(mbi_file, "r", encoding="utf-8"))
                mbi_idx = float(mbi_data.get("Index", 50.0))
            except Exception as e:
                logger.error(f"Failed to load MBI for paper trading: {e}")
        
        mbi_allowed = get_mbi_allowed_grades(mbi_idx)
        self.add_log(date_str, f"EOD Ingestion completed. MBI: {mbi_idx:.1f} (Allowed Grades: {', '.join(mbi_allowed)})")

        # ── 2. Load Watchlist and Sector Map ──────────────────────────────────
        # Load previous trading date's watchlist to avoid lookahead bias
        prev_date = self.get_previous_trading_date(date_str)
        if not prev_date:
            logger.warning(f"No previous trading date found for {date_str}. Using current date as fallback.")
            prev_date = date_str
            
        self.add_log(date_str, f"Loading watchlist from previous session: {prev_date}")
        try:
            import server
            wl_data = server.get_latest_watchlist_data(prev_date)
        except Exception as e:
            logger.error(f"Failed to get watchlist from server: {e}")
            wl_data = {"strategic_watchlist": [], "daily_focus_watchlist": []}

        # Combine into curated pool (Strategic + Daily Focus)
        curated_pool = {}
        for s in wl_data.get("strategic_watchlist", []) + wl_data.get("daily_focus_watchlist", []):
            sym = s.get("Symbol", "").upper().strip()
            if sym:
                curated_pool[sym] = s

        # Load sector categories
        sector_cats = {}
        ipr_file = "data/industry_participation_report.json"
        if os.path.exists(ipr_file):
            try:
                ipr_list = json.load(open(ipr_file, "r", encoding="utf-8"))
                for item in ipr_list:
                    sector_cats[item["Industry"].upper().strip()] = item.get("Category", "Avoid")
            except Exception as e:
                logger.error(f"Failed to load industry categories: {e}")

        # ── 3. Evaluate Exits for Open Positions ──────────────────────────────
        exited_symbols = []
        active_trades = []
        for t in self.state["open_trades"]:
            sym = t["symbol"]
            cmp, high, low = get_cmp_from_cache(sym)
            if cmp is None:
                # Keep active trade if no price data available
                active_trades.append(t)
                continue

            t["days_active"] += 1
            t["cmp"] = cmp
            
            # Record historical high reached
            t["max_high_reached"] = max(t.get("max_high_reached", t["entry_price"]), high)
            max_high = t["max_high_reached"]
            
            # Initial risk
            init_risk = t["initial_qty"] * (t["entry_price"] - t["stop_loss"])

            # Exit flags
            sl_hit = False
            t1_hit = t.get("t1_hit", False)
            t2_hit = t.get("t2_hit", False)
            exit_price = 0.0
            exit_reason = ""

            # Check Stop Loss
            if low <= t["trailing_sl"]:
                sl_hit = True
                exit_price = t["trailing_sl"]
                exit_reason = "Hard stop hit"
                self.add_log(date_str, f"EXIT: {sym} stopped out at ₹{exit_price:.2f} (Trailing SL: ₹{t['trailing_sl']:.2f})")
            
            # Check T1 (exit 40%, trail rest to entry)
            elif not t1_hit and high >= t["t1"]:
                t1_hit = True
                t["t1_hit"] = True
                
                # Sell 40%
                sell_qty = math.floor(t["open_qty"] * 0.40)
                if sell_qty > 0:
                    realized_pnl = sell_qty * (t["t1"] - t["entry_price"])
                    self.state["cash"] += sell_qty * t["t1"]
                    t["open_qty"] -= sell_qty
                    t["partial_exits"].append({
                        "date": date_str,
                        "qty": sell_qty,
                        "price": t["t1"],
                        "pnl": realized_pnl,
                        "target": "T1"
                    })
                    self.add_log(date_str, f"PARTIAL EXIT: {sym} hit T1 (₹{t['t1']:.2f}). Sold {sell_qty} shares. SL trailed to entry ₹{t['entry_price']:.2f}.")
                
                # Trail SL to entry (breakeven)
                t["trailing_sl"] = t["entry_price"]

            # Check T2 (exit 50% of remaining, trail runner at 5% from high)
            elif t1_hit and not t2_hit and high >= t["t2"]:
                t2_hit = True
                t["t2_hit"] = True
                
                # Sell 50% of remaining
                sell_qty = math.floor(t["open_qty"] * 0.50)
                if sell_qty > 0:
                    realized_pnl = sell_qty * (t["t2"] - t["entry_price"])
                    self.state["cash"] += sell_qty * t["t2"]
                    t["open_qty"] -= sell_qty
                    t["partial_exits"].append({
                        "date": date_str,
                        "qty": sell_qty,
                        "price": t["t2"],
                        "pnl": realized_pnl,
                        "target": "T2"
                    })
                    self.add_log(date_str, f"PARTIAL EXIT: {sym} hit T2 (₹{t['t2']:.2f}). Sold {sell_qty} shares. Active runner trailing SL started.")
                
                # Trail SL for runner
                t["trailing_sl"] = max(t["trailing_sl"], round(max_high * 0.95, 2))

            # Trail runner if T2 has already been hit
            if t2_hit and not sl_hit:
                new_trail = round(max_high * 0.95, 2)
                if new_trail > t["trailing_sl"]:
                    t["trailing_sl"] = new_trail
                    self.add_log(date_str, f"TRAIL SL: {sym} runner stop trailed up to ₹{new_trail:.2f}")

            # Time stop: Day 10 if no movement past 5%
            if not sl_hit and t["days_active"] >= 10 and not t1_hit and cmp < t["entry_price"] * 1.05:
                sl_hit = True
                exit_price = cmp
                exit_reason = "Time stop triggered (10 days without 5% move)"
                self.add_log(date_str, f"EXIT: {sym} time stop triggered at ₹{exit_price:.2f} (Day {t['days_active']})")

            # Finalize exited position
            if sl_hit:
                # Realize remaining
                pnl = t["open_qty"] * (exit_price - t["entry_price"])
                self.state["cash"] += t["open_qty"] * exit_price
                t["open_qty"] = 0
                
                # Calculate total net P&L across exits
                total_realized_pnl = sum(pe["pnl"] for pe in t["partial_exits"]) + pnl
                r_mult = total_realized_pnl / init_risk if init_risk > 0 else 0.0

                closed_trade = {
                    "symbol": sym,
                    "grade": t["grade"],
                    "engine_type": t["engine_type"],
                    "entry_date": t["entry_date"],
                    "exit_date": date_str,
                    "entry_price": t["entry_price"],
                    "exit_price": exit_price,
                    "initial_qty": t["initial_qty"],
                    "pnl_net": round(total_realized_pnl, 2),
                    "r_multiple": round(r_mult, 2),
                    "status": "CLOSED",
                    "exit_reason": exit_reason,
                    "partial_exits": t["partial_exits"]
                }
                self.state["closed_trades"].append(closed_trade)
                exited_symbols.append(sym)
            else:
                # Update unrealized
                current_value = t["open_qty"] * cmp
                cost_value = t["open_qty"] * t["entry_price"]
                partial_pnl = sum(pe["pnl"] for pe in t["partial_exits"])
                t["unrealized_pnl"] = round(current_value - cost_value + partial_pnl, 2)
                t["unrealized_r"] = round(t["unrealized_pnl"] / init_risk, 2) if init_risk > 0 else 0.0
                active_trades.append(t)

        self.state["open_trades"] = active_trades

        # ── 4. Evaluate New Entries from Curated List ─────────────────────────
        # Determine free slots (max 8 positions)
        # Check weekday (0 = Monday, 6 = Sunday). Only trade Monday-Friday.
        is_weekday = True
        try:
            is_weekday = datetime.strptime(date_str, "%Y-%m-%d").weekday() < 5
        except Exception:
            pass

        free_slots = 8 - len(self.state["open_trades"])
        if free_slots > 0 and is_weekday:
            entered_count = 0
            for sym, s in curated_pool.items():
                if entered_count >= free_slots:
                    break
                
                # Check if already holding
                if any(t["symbol"] == sym for t in self.state["open_trades"]):
                    continue

                ind = s.get("Industry", "").upper().strip()
                cat = sector_cats.get(ind, "Neutral")
                
                # Check 4 gates
                passes_gates, gk, gd = self.validate_gates(s, mbi_allowed, cat)
                if not passes_gates:
                    continue

                # Gates passed! Check daily price cache to see if trigger hit
                cmp, high, low = get_cmp_from_cache(sym)
                trigger_price = float(s.get("Entry") or s.get("Entry_Price") or 0)
                sl = float(s.get("Stop_Loss") or 0)

                if trigger_price <= 0 or sl <= 0 or sl >= trigger_price:
                    continue

                # Breakout trigger condition: today's High >= trigger
                if high is not None and high >= trigger_price:
                    # Determine entry price (cap at trigger + 2% for gap-up check)
                    entry_price = trigger_price
                    # If EOD Close has already dropped below SL, skip the entry
                    if cmp is not None and cmp <= sl:
                        continue

                    # Position Sizing
                    # Risk amount = 2% of current account equity
                    # Calculate current equity
                    open_val = sum(t["open_qty"] * t["cmp"] for t in self.state["open_trades"])
                    total_equity = self.state["cash"] + open_val
                    risk_to_take = total_equity * 0.02

                    risk_per_share = entry_price - sl
                    qty = math.floor(risk_to_take / risk_per_share)
                    
                    # 25% max capital allocation limit
                    max_alloc_qty = math.floor((total_equity * 0.25) / entry_price)
                    qty = min(qty, max_alloc_qty)

                    if qty > 0:
                        cost = qty * entry_price
                        if self.state["cash"] >= cost:
                            self.state["cash"] -= cost
                            
                            new_trade = {
                                "id": f"{sym}_{date_str}",
                                "symbol": sym,
                                "entry_date": date_str,
                                "entry_price": entry_price,
                                "trigger_price": trigger_price,
                                "stop_loss": sl,
                                "trailing_sl": sl,
                                "t1": float(s.get("Target_1") or (entry_price + 1.5 * risk_per_share)),
                                "t2": float(s.get("Target_2") or (entry_price + 2.5 * risk_per_share)),
                                "initial_qty": qty,
                                "open_qty": qty,
                                "invested": cost,
                                "risk_per_share": round(risk_per_share, 2),
                                "risk_amount": round(qty * risk_per_share, 2),
                                "grade": s.get("Setup_Grade") or s.get("Grade") or "Grade C",
                                "engine_type": s.get("Setup_Type") or s.get("Engine_Type") or "VCP",
                                "sector": s.get("Industry", "Neutral"),
                                "sector_zone": cat,
                                "gates": ["MBI", "Sector", "Pattern", "SL Band"],
                                "phase": "PRE-T1",
                                "cmp": cmp if cmp else entry_price,
                                "unrealized_pnl": round(qty * ((cmp if cmp else entry_price) - entry_price), 2),
                                "unrealized_r": round(((cmp if cmp else entry_price) - entry_price) / risk_per_share, 2) if risk_per_share > 0 else 0.0,
                                "days_active": 0,
                                "t1_hit": False,
                                "t2_hit": False,
                                "sl_hit": False,
                                "partial_exits": []
                            }
                            self.state["open_trades"].append(new_trade)
                            entered_count += 1
                            self.add_log(date_str, f"BUY TRIGGERED: Entered {sym} at ₹{entry_price:.2f} (Triggered on High ₹{high:.2f}). Qty: {qty}. Stop: ₹{sl:.2f}, T1: ₹{new_trade['t1']:.2f}, T2: ₹{new_trade['t2']:.2f}")

        # ── 5. Record Equity Snapshot ─────────────────────────────────────────
        open_val = sum(t["open_qty"] * t["cmp"] for t in self.state["open_trades"])
        total_equity = self.state["cash"] + open_val
        self.state["daily_snapshots"][date_str] = {
            "cash": round(self.state["cash"], 2),
            "open_value": round(open_val, 2),
            "equity": round(total_equity, 2),
            "open_positions": len(self.state["open_trades"])
        }
        self.add_log(date_str, f"Daily Snapshot: Cash = ₹{self.state['cash']:.2f} | Positions Value = ₹{open_val:.2f} | Total Equity = ₹{total_equity:.2f}")

        # ── 6. Save State ─────────────────────────────────────────────────────
        self.save_state()

if __name__ == "__main__":
    import sys
    # Dry run check
    t = TruePaperTrader()
    dt = datetime.now().strftime("%Y-%m-%d")
    t.run_daily_update(dt)
