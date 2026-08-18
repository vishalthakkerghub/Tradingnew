import os
import json
import logging
import math
import csv
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger("PaperTradingEngine")

class PaperTradingEngine:
    """
    Paper Trading and Trade Lifecycle Engine.
    Tracks signals from watchlist generation, through entry, partial exits, 
    EMA20 trailing exits, and final closure. Generates performance journals and analytics.
    """
    def __init__(self, config=None, state_file="data/paper_trading_state.json", data_engine=None):
        self.config = config or {}
        self.state_file = state_file
        self.data_engine = data_engine
        
        # System/Risk parameters
        self.capital_base = 1000000.0  # Rs.10 Lakhs capital
        self.risk_pct = 0.01          # 1% risk per trade
        self.max_allocation_pct = 0.25 # 25% max capital allocation per stock
        self.max_stop_pct = 0.08       # 8% maximum stop loss cap
        
        self.state = {
            "watchlist": {},
            "active_trades": {},
            "closed_trades": [],
            "cash": self.capital_base,
            "equity_history": {}
        }
        self.load_state()

    def load_state(self):
        """Loads paper trading portfolio state from JSON."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    loaded = json.load(f)
                    # Merge keys to support upgrade paths
                    self.state["watchlist"] = loaded.get("watchlist", {})
                    self.state["active_trades"] = loaded.get("active_trades", {})
                    self.state["closed_trades"] = loaded.get("closed_trades", [])
                    self.state["cash"] = float(loaded.get("cash", self.capital_base))
                    self.state["equity_history"] = loaded.get("equity_history", {})
                logger.info(f"Loaded paper trading state from {self.state_file}. Cash: Rs.{self.state['cash']:,.2f}")
            except Exception as e:
                logger.error(f"Failed to load paper trading state: {e}. Using default state.")
        else:
            # Ensure folder exists
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            self.save_state()

    def save_state(self):
        """Saves paper trading portfolio state to JSON."""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"Saved paper trading state to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save paper trading state: {e}")

    def update_watchlist(self, candidates, date_str, stock_df_dict=None):
        """
        Appends newly identified ready candidates to the watchlist.
        
        Args:
            candidates (list): List of daily scan candidate dicts.
            date_str (str): Date of the scan in 'YYYY-MM-DD' format.
            stock_df_dict (dict): Optional dict of Symbol -> stock DataFrame.
        """
        if stock_df_dict is None:
            stock_df_dict = {}

        updated = False
        for c in candidates:
            symbol = c["Symbol"].upper()
            status = c.get("Readiness Status", "")
            
            # We add STRICT READY and FLEX READY candidates
            if "READY" in status or status == "DEVELOPING":
                if symbol not in self.state["active_trades"] and symbol not in self.state["watchlist"]:
                    pivot_price = float(c["Pivot Price"])
                    contraction_low = float(c["Stop Loss"]) if "Stop Loss" in c else float(c.get("Stop_Loss", 0.0))
                    
                    # Defaults
                    entry_category = "HIGH_RISK_ENTRY"
                    trigger_price = pivot_price
                    stop_price = max(pivot_price * (1.0 - self.max_stop_pct), contraction_low)
                    
                    df = stock_df_dict.get(symbol)
                    if df is None or df.empty:
                        if self.data_engine:
                            try:
                                df = self.data_engine.fetch_historical_ohlcv(symbol, lookback_days=250)
                            except Exception:
                                pass

                    if df is not None and not df.empty and date_str in df.index:
                        try:
                            df_idx = df.index.get_loc(date_str)
                            close = float(df["Close"].iloc[df_idx])
                            
                            # 1. Check Tight Candle Cheat (4-day range <= 3.5%)
                            if df_idx >= 3:
                                sub_df_4d = df.iloc[df_idx-3 : df_idx+1]
                                h4 = float(sub_df_4d["High"].max())
                                l4 = float(sub_df_4d["Low"].min())
                                range_4d = ((h4 - l4) / l4) * 100
                                if range_4d <= 3.5:
                                    entry_category = "TIGHT_CHEAT_VCP"
                                    trigger_price = h4
                                    stop_price = l4
                                    
                            # 2. Check EMA Pullback (if not Cheat VCP and close within 1.5% of 10/20 EMA)
                            if entry_category == "HIGH_RISK_ENTRY" and df_idx >= 19:
                                ema10_series = df["Close"].ewm(span=10, adjust=False).mean()
                                ema20_series = df["Close"].ewm(span=20, adjust=False).mean()
                                ema10 = float(ema10_series.iloc[df_idx])
                                ema20 = float(ema20_series.iloc[df_idx])
                                
                                dist_ema10 = ((close - ema10) / ema10) * 100
                                dist_ema20 = ((close - ema20) / ema20) * 100
                                
                                if (0.0 <= dist_ema10 <= 1.5) or (0.0 <= dist_ema20 <= 1.5):
                                    entry_category = "EMA_PULLBACK"
                                    trigger_price = float(df["High"].iloc[df_idx-1])
                                    
                                    low_3d = float(df["Low"].iloc[max(0, df_idx-2) : df_idx+1].min())
                                    stop_price = max(ema20 * 0.99, low_3d)
                                    stop_price = max(trigger_price * (1.0 - self.max_stop_pct), stop_price)
                        except Exception as ex:
                            logger.warning(f"Error calculating tactical entry category for {symbol}: {ex}")

                    # Expectancy-based dynamic targets (minimum 5% for T1 and 10% for T2)
                    risk_pct = ((trigger_price - stop_price) / trigger_price) * 100 if trigger_price > 0 else 0.0
                    target_1 = trigger_price * (1.0 + max(0.05, 2.0 * (risk_pct / 100)))
                    target_2 = trigger_price * (1.0 + max(0.10, 3.5 * (risk_pct / 100)))

                    self.state["watchlist"][symbol] = {
                        "symbol": symbol,
                        "pivot_price": pivot_price,
                        "contraction_low": contraction_low,
                        "score": int(c["Score"]),
                        "grade": c["Grade"],
                        "engine_type": c["Engine_Type"],
                        "date_added": date_str,
                        "vdu_ratio": float(c.get("VDU %", "0.0").replace("%", "")) / 100.0 if isinstance(c.get("VDU %"), str) else float(c.get("VDU %", 0.0)),
                        "entry_category": entry_category,
                        "trigger_price": trigger_price,
                        "stop_price": stop_price,
                        "target_1": target_1,
                        "target_2": target_2
                    }
                    logger.info(f"Added {symbol} to Paper Trading watchlist on {date_str} as {entry_category}. Trigger: Rs.{trigger_price:.2f}, Stop: Rs.{stop_price:.2f}")
                    updated = True
        if updated:
            self.save_state()

    def evaluate_daily_lifecycle(self, stock_df_dict, date_str):
        """
        Evaluates entries and trailing exits for the current day.
        
        Args:
            stock_df_dict (dict): Map of Symbol -> stock DataFrame.
            date_str (str): Date to evaluate in 'YYYY-MM-DD' format.
        """
        # 1. Evaluate Watchlist for Breakout Entries
        triggered_entries = []
        for symbol, item in list(self.state["watchlist"].items()):
            df = stock_df_dict.get(symbol)
            if df is None or df.empty:
                if self.data_engine:
                    try:
                        df = self.data_engine.fetch_historical_ohlcv(symbol, lookback_days=250)
                    except Exception as e:
                        logger.warning(f"Could not fetch data for watchlist symbol {symbol}: {e}")
                        continue
                else:
                    continue
            
            if date_str not in df.index:
                continue
            
            # Fetch daily data
            row = df.loc[date_str]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[-1]
            
            close = float(row["Close"])
            high = float(row["High"])
            low = float(row["Low"])
            open_val = float(row["Open"])
            volume = float(row["Volume"])
            
            trigger_price = item.get("trigger_price", item["pivot_price"])
            
            # Calculate 50 Volume SMA
            df_idx = df.index.get_loc(date_str)
            if df_idx < 49:
                # Insufficient volume history to compute 50 SMA
                continue
                
            vol_sma50 = df["Volume"].iloc[max(0, df_idx-49):df_idx+1].mean()
            
            # Breakout condition: Close > trigger_price and Volume >= 1.50 * Volume_SMA50
            if close > trigger_price and volume >= 1.50 * vol_sma50:
                entry_price = max(trigger_price, open_val)
                raw_stop = item.get("stop_price", item["contraction_low"])
                
                # Sizing calculations
                max_stop_loss_limit = entry_price * (1.0 - self.max_stop_pct)
                stop_loss = max(max_stop_loss_limit, raw_stop)
                risk_per_share = entry_price - stop_loss
                
                if risk_per_share > 0:
                    shares = math.floor((self.capital_base * self.risk_pct) / risk_per_share)
                else:
                    shares = 0
                    
                max_shares = math.floor((self.capital_base * self.max_allocation_pct) / entry_price)
                shares = min(shares, max_shares)
                
                if shares > 0:
                    cost = shares * entry_price
                    # Check if we have enough cash (standard margin/paper trading check)
                    if self.state["cash"] >= cost:
                        self.state["cash"] -= cost
                        self.state["active_trades"][symbol] = {
                            "symbol": symbol,
                            "entry_date": date_str,
                            "entry_price": entry_price,
                            "initial_stop": stop_loss,
                            "current_stop": stop_loss,
                            "initial_shares": shares,
                            "shares_remaining": shares,
                            "partial_exit_taken": False,
                            "partial_exit_price": 0.0,
                            "partial_exit_date": None,
                            "days_active": 0,
                            "max_high_reached": high,
                            "target_1": float(item.get("target_1", entry_price * 1.10)),
                            "target_2": float(item.get("target_2", entry_price * 1.20)),
                            "vdu_ratio": item["vdu_ratio"],
                            "score": item["score"],
                            "grade": item["grade"],
                            "engine_type": item["engine_type"],
                            "entry_category": item.get("entry_category", "HIGH_RISK_ENTRY"),
                            "status": "ACTIVE"
                        }
                        triggered_entries.append(symbol)
                        logger.info(f"BUY TRIGGERED: {symbol} entered at Rs.{entry_price:.2f} on {date_str} ({item.get('entry_category', 'HIGH_RISK_ENTRY')}). Shares: {shares}, Stop: Rs.{stop_loss:.2f}")
                    else:
                        logger.warning(f"Insolvent: Insufficient cash to enter trade for {symbol}. Needed Rs.{cost:,.2f}, cash is Rs.{self.state['cash']:,.2f}")
                
        # Remove entered stocks from watchlist
        for symbol in triggered_entries:
            self.state["watchlist"].pop(symbol, None)

        # 1B. Prune Watchlist (Remove items that have broken below contraction low or aged out)
        pruned_symbols = []
        for symbol, item in list(self.state["watchlist"].items()):
            df = stock_df_dict.get(symbol)
            if df is not None and not df.empty and date_str in df.index:
                row = df.loc[date_str]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[-1]
                close = float(row["Close"])
                
                # Check 1: Invalidation (Close below contraction low/stop)
                if close < item["contraction_low"]:
                    pruned_symbols.append(symbol)
                    logger.info(f"PRUNED FROM WATCHLIST: {symbol} setup invalidated (Close Rs.{close:.2f} < Contraction Low Rs.{item['contraction_low']:.2f})")
                    continue
                
                # Check 2: Expiry (Aged out - e.g. on watchlist for > 30 trading days)
                date_added = item["date_added"]
                if date_added in df.index:
                    df_idx_added = df.index.get_loc(date_added)
                    df_idx_today = df.index.get_loc(date_str)
                    days_on_watchlist = df_idx_today - df_idx_added
                    if days_on_watchlist > 30:
                        pruned_symbols.append(symbol)
                        logger.info(f"PRUNED FROM WATCHLIST: {symbol} aged out (>30 trading days without breakout)")
                        
        for symbol in pruned_symbols:
            self.state["watchlist"].pop(symbol, None)

        # 2. Evaluate Active Trades for Exits and Stop Adjustments
        closed_this_day = []
        for symbol, trade in list(self.state["active_trades"].items()):
            df = stock_df_dict.get(symbol)
            if df is None or df.empty:
                if self.data_engine:
                    try:
                        df = self.data_engine.fetch_historical_ohlcv(symbol, lookback_days=250)
                    except Exception as e:
                        logger.warning(f"Could not fetch data for active symbol {symbol}: {e}")
                        continue
                else:
                    continue
            
            if date_str not in df.index:
                continue
            
            # Fetch daily data
            row = df.loc[date_str]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[-1]
                
            close = float(row["Close"])
            high = float(row["High"])
            low = float(row["Low"])
            open_val = float(row["Open"])
            
            trade["days_active"] += 1
            trade["max_high_reached"] = max(trade["max_high_reached"], high)
            
            entry_price = trade["entry_price"]
            current_stop = trade["current_stop"]
            days_active = trade["days_active"]
            max_high = trade["max_high_reached"]
            shares_rem = trade["shares_remaining"]
            initial_shares = trade["initial_shares"]
            initial_risk = initial_shares * (entry_price - trade["initial_stop"])
            
            # Calculate daily EMA20
            # To avoid re-calculating on each day, we can compute it on df
            df_idx = df.index.get_loc(date_str)
            # Fetch rolling/EMA20 up to this date
            ema20_series = df["Close"].ewm(span=20, adjust=False).mean()
            day_ema20 = float(ema20_series.iloc[df_idx])
            
            exited = False
            exit_price = 0.0
            exit_reason = ""
            exit_status = "FULLY_EXITED"
            
            # Check 1: Hard Stop Loss Hit
            if low <= current_stop:
                exited = True
                exit_price = min(current_stop, open_val)
                exit_reason = "Stop loss hit"
                exit_status = "STOPPED_OUT"
                
            # Check 2: Target 1 reached in 3 Weeks Rule
            elif days_active <= 15 and max_high >= trade.get("target_1", 1.10 * entry_price):
                # Move stop to breakeven
                if trade["current_stop"] < entry_price:
                    trade["current_stop"] = entry_price
                    logger.info(f"Stop moved to breakeven for {symbol} on day {days_active} (Target 1 high reached). New Stop: Rs.{entry_price:.2f}")
                    
            if not exited and days_active == 15 and max_high < trade.get("target_1", 1.10 * entry_price):
                exited = True
                exit_price = close
                exit_reason = "Sluggish breakout time stop (failed to reach Target 1 in 3 weeks)"
                exit_status = "TIME_EXIT"
                
            # Check 3: Target 2 Partial Profit Target
            t2_target = trade.get("target_2", 1.20 * entry_price)
            if not exited and not trade["partial_exit_taken"] and high >= t2_target:
                trade["partial_exit_taken"] = True
                trade["partial_exit_date"] = date_str
                trade["partial_exit_price"] = max(t2_target, open_val)
                
                partial_shares = shares_rem // 2
                self.state["cash"] += partial_shares * trade["partial_exit_price"]
                trade["shares_remaining"] -= partial_shares
                shares_rem = trade["shares_remaining"]
                
                # Stop moves to breakeven for remaining
                trade["current_stop"] = entry_price
                logger.info(f"PARTIAL EXIT: {symbol} hit Target 2 (Rs.{t2_target:.2f}). Sold {partial_shares} shares at Rs.{trade['partial_exit_price']:.2f}. Stop raised to breakeven.")
                
            # Check 4: EMA20 Trailing Exit (activated after 5 days of trade progress)
            if not exited and days_active > 5 and close < day_ema20:
                exited = True
                exit_price = close
                exit_reason = "Closed below EMA20 trailing stop"
                exit_status = "FULLY_EXITED"
                
            if exited:
                # Fully exit the remaining shares
                payout = shares_rem * exit_price
                self.state["cash"] += payout
                
                # Calculate realized P&L
                realized_pnl = payout - (shares_rem * entry_price)
                if trade["partial_exit_taken"]:
                    realized_pnl += (initial_shares - shares_rem) * trade["partial_exit_price"] - ((initial_shares - shares_rem) * entry_price)
                    
                r_mult = realized_pnl / initial_risk if initial_risk > 0 else 0.0
                
                closed_record = {
                    "symbol": symbol,
                    "entry_date": trade["entry_date"],
                    "exit_date": date_str,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "initial_stop": trade["initial_stop"],
                    "initial_shares": initial_shares,
                    "pnl_net": realized_pnl,
                    "r_multiple": r_mult,
                    "status": exit_status,
                    "exit_reason": exit_reason
                }
                self.state["closed_trades"].append(closed_record)
                closed_this_day.append(symbol)
                logger.info(f"EXIT TRIGGERED: {symbol} closed on {date_str} at Rs.{exit_price:.2f} (Reason: {exit_reason}). PnL: Rs.{realized_pnl:,.2f} ({r_mult:.2f}R)")
                
        # Remove closed trades
        for symbol in closed_this_day:
            self.state["active_trades"].pop(symbol, None)
            
        # 3. Track Equity Curve for the day
        active_value = 0.0
        for symbol, trade in self.state["active_trades"].items():
            df = stock_df_dict.get(symbol)
            if df is not None and not df.empty and date_str in df.index:
                row = df.loc[date_str]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[-1]
                close_val = float(row["Close"])
                active_value += trade["shares_remaining"] * close_val
            else:
                active_value += trade["shares_remaining"] * trade["entry_price"]
                
        daily_equity = self.state["cash"] + active_value
        self.state["equity_history"][date_str] = daily_equity
        logger.info(f"EOD State for {date_str}: Cash = Rs.{self.state['cash']:,.2f} | Active Position Value = Rs.{active_value:,.2f} | Total Equity = Rs.{daily_equity:,.2f}")
        
        self.save_state()

    def generate_performance_reports(self, stock_df_dict=None):
        """Generates trade journal CSV and markdown performance reports."""
        if stock_df_dict is None:
            stock_df_dict = {}
        reports_dir = "reports"
        daily_reports_dir = "reports/daily"
        os.makedirs(daily_reports_dir, exist_ok=True)
        
        # Determine suffix from state file to separate reports
        suffix = ""
        state_filename = os.path.basename(self.state_file).lower()
        if "vcp" in state_filename:
            suffix = "_vcp"
        elif "flag" in state_filename:
            suffix = "_flag"
            
        # 1. Compile CSV Trade Journal
        journal_file = os.path.join(daily_reports_dir, f"trade_journal{suffix}.csv")
        try:
            with open(journal_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Symbol", "Entry Date", "Exit Date", "Entry Price", "Exit Price", 
                    "Initial Stop", "Initial Shares", "PnL Net", "R-Multiple", "Status", "Exit Reason"
                ])
                for t in self.state["closed_trades"]:
                    writer.writerow([
                        t["symbol"], t["entry_date"], t["exit_date"],
                        f"{t['entry_price']:.2f}", f"{t['exit_price']:.2f}",
                        f"{t['initial_stop']:.2f}", t["initial_shares"],
                        f"{t['pnl_net']:.2f}", f"{t['r_multiple']:.2f}",
                        t["status"], t["exit_reason"]
                    ])
            logger.info(f"Trade journal saved successfully at {journal_file}")
        except Exception as e:
            logger.error(f"Failed to generate CSV trade journal: {e}")
            
        # 2. Compile Performance Analytics Report
        closed_trades = self.state["closed_trades"]
        total_trades = len(closed_trades)
        wins = [t for t in closed_trades if t["pnl_net"] > 0]
        losses = [t for t in closed_trades if t["pnl_net"] <= 0]
        
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0
        
        total_gains = sum(t["pnl_net"] for t in wins)
        total_losses = abs(sum(t["pnl_net"] for t in losses))
        profit_factor = total_gains / total_losses if total_losses > 0 else (float('inf') if total_gains > 0 else 1.0)
        
        total_r = sum(t["r_multiple"] for t in closed_trades)
        avg_win = sum(t["pnl_net"] for t in wins) / len(wins) if wins else 0.0
        avg_loss = sum(t["pnl_net"] for t in losses) / len(losses) if losses else 0.0
        
        # Calculate Max Drawdown from equity history
        equity_vals = []
        # Sort by date
        sorted_dates = sorted(self.state["equity_history"].keys())
        for d in sorted_dates:
            equity_vals.append(self.state["equity_history"][d])
            
        max_dd = 0.0
        peak = 0.0
        for eq in equity_vals:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
                
        analytics_file = os.path.join(reports_dir, f"performance_analytics{suffix}.md")
        try:
            with open(analytics_file, "w", encoding="utf-8") as f:
                f.write("# Performance Analytics Report\n\n")
                f.write(f"- **Generated At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"- **Current Balance (Cash):** Rs.{self.state['cash']:,.2f}\n")
                f.write(f"- **Current Account Equity:** Rs.{equity_vals[-1]:,.2f}\n\n" if equity_vals else "\n")
                
                f.write("## Core Performance Metrics\n\n")
                f.write("| Metric | Value |\n")
                f.write("| :--- | :--- |\n")
                f.write(f"| **Total Closed Trades** | {total_trades} |\n")
                f.write(f"| **Winning Trades** | {len(wins)} |\n")
                f.write(f"| **Losing Trades** | {len(losses)} |\n")
                f.write(f"| **Win Rate (%)** | {win_rate:.2f}% |\n")
                f.write(f"| **Profit Factor** | {f'{profit_factor:.2f}' if profit_factor != float('inf') else 'Infinity'} |\n")
                f.write(f"| **Total R-Multiple** | {total_r:+.2f}R |\n")
                f.write(f"| **Average Win** | Rs.{avg_win:,.2f} |\n")
                f.write(f"| **Average Loss** | Rs.{avg_loss:,.2f} |\n")
                f.write(f"| **Max Drawdown** | {max_dd * 100:.2f}% |\n\n")
                
                f.write("## Active Holdings\n\n")
                active_trades = self.state["active_trades"]
                if active_trades:
                    f.write("| Symbol | Entry Date | Entry Price | Current Stop | Initial Shares | Shares Remaining | P&L Net | R-Multiple |\n")
                    f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
                    for sym, t in active_trades.items():
                        # We use entry price as fallback for current price if not available
                        current_price = t["entry_price"]
                        df = stock_df_dict.get(sym)
                        if df is not None and not df.empty and sorted_dates:
                            last_date = sorted_dates[-1]
                            if last_date in df.index:
                                current_price = float(df.loc[last_date, "Close"])
                                
                        val = t["shares_remaining"] * current_price
                        cost = t["shares_remaining"] * t["entry_price"]
                        pnl = val - cost
                        if t["partial_exit_taken"]:
                            pnl += (t["initial_shares"] - t["shares_remaining"]) * t["partial_exit_price"] - ((t["initial_shares"] - t["shares_remaining"]) * t["entry_price"])
                            
                        risk_per_share = t["entry_price"] - t["initial_stop"]
                        init_risk = t["initial_shares"] * risk_per_share
                        r_mult = pnl / init_risk if init_risk > 0 else 0.0
                        
                        f.write(f"| **{sym}** | {t['entry_date']} | Rs.{t['entry_price']:.2f} | Rs.{t['current_stop']:.2f} | {t['initial_shares']} | {t['shares_remaining']} | Rs.{pnl:+.2f} | {r_mult:+.2f}R |\n")
                else:
                    f.write("*No active holdings currently.*\n\n")
                    
                f.write("## Historical Trade Journal\n\n")
                if closed_trades:
                    f.write("| Symbol | Entry Date | Exit Date | Entry Price | Exit Price | Initial Shares | P&L Net | R-Multiple | Exit Reason |\n")
                    f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
                    for t in reversed(closed_trades):
                        f.write(f"| **{t['symbol']}** | {t['entry_date']} | {t['exit_date']} | Rs.{t['entry_price']:.2f} | Rs.{t['exit_price']:.2f} | {t['initial_shares']} | Rs.{t['pnl_net']:+,.2f} | {t['r_multiple']:+.2f}R | {t['exit_reason']} |\n")
                else:
                    f.write("*No historical trades closed yet.*\n")
                    
            logger.info(f"Performance analytics report saved successfully at {analytics_file}")
        except Exception as e:
            logger.error(f"Failed to generate markdown performance analytics: {e}")
