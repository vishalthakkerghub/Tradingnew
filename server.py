import http.server
import socketserver
import json
import os
import urllib.request
import urllib.parse
import re
import pandas as pd
from datetime import datetime
from src.utils import load_config
from src.market_conditions import MarketConditionsEngine
from src.momentum_score import AntigravityMomentumEngine
import glob

# Load configuration and initialize market conditions engine
config = load_config("config/config.yaml")
market_engine = MarketConditionsEngine(config)

PORT = int(os.environ.get("PORT", 8080))
DIRECTORY = "web"

def get_cached_delivery_data(symbol, date_str):
    """
    Reads Delivery_Pct from stock's cached CSV file.
    Returns a dict with Traded, Deliverable, and Delivery_Pct.
    """
    cache_dir = "data/cache"
    cache_file = os.path.join(cache_dir, f"{symbol.upper()}.csv")
    if not os.path.exists(cache_file):
        cache_file = os.path.join("minervini_os", cache_file)
        
    mto_info = {"Traded": 0, "Deliverable": 0, "Delivery_Pct": 0.0}
    if os.path.exists(cache_file):
        try:
            df = pd.read_csv(cache_file, index_col="Date")
            row = None
            if date_str in df.index:
                row = df.loc[date_str]
            elif not df.empty:
                row = df.iloc[-1]
                
            if row is not None:
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[-1]
                
                volume = int(row.get("Volume", 0))
                deliv_pct = float(row.get("Delivery_Pct", 0.0))
                mto_info["Traded"] = volume
                mto_info["Delivery_Pct"] = deliv_pct
                mto_info["Deliverable"] = int(round(volume * deliv_pct / 100))
        except Exception:
            pass
            
    return mto_info

def calculate_watchlist_tier(ms_score, ind_cat):
    if ms_score >= 85 and ind_cat == "Confirmed Uptrend":
        return "Tier 1"
    elif ms_score >= 85 and ind_cat == "Early Uptrend":
        return "Tier 2"
    elif 80 <= ms_score <= 84 and ind_cat == "Confirmed Uptrend":
        return "Tier 3"
    else:
        return "Tier 4"

def get_available_scan_dates():
    """
    Scans reports/daily for dated vcp candidates csv files and returns a list of sorted dates.
    """
    dates = set()
    reports_dir = "reports/daily"
    if os.path.exists(reports_dir):
        for name in os.listdir(reports_dir):
            match = re.match(r"vcp_candidates_(\d{8})\.csv", name)
            if match:
                date_str = match.group(1)
                formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                dates.add(formatted)
    return sorted(list(dates), reverse=True)

def get_discipline_history_report():
    import pandas as pd
    import json
    import os
    
    # 1. Get dates
    dates = get_available_scan_dates()
    if not dates:
        return []
    # Sort chronological
    dates = sorted(dates)[-15:]
    
    # 2. Load journal
    journal_file = "data/trade_journal_data.json"
    if not os.path.exists(journal_file):
        journal_file = os.path.join("minervini_os", journal_file)
        
    journal = []
    if os.path.exists(journal_file):
        try:
            with open(journal_file, "r", encoding="utf-8") as f:
                journal = json.load(f)
        except Exception:
            pass
            
    # Pre-load stock histories for quick lookup
    symbol_histories = {}
    
    report_data = []
    for d in dates:
        # Find active open trades on this date
        active_trades = []
        for t in journal:
            entry_d = t.get("entry_date", "")
            exit_d = t.get("exit_date")
            
            if entry_d <= d:
                # Still open if status is OPEN, or if closed but closed after date d
                if t.get("status") == "OPEN":
                    active_trades.append(t)
                elif exit_d and exit_d > d:
                    active_trades.append(t)
                    
        score = 100
        for t in active_trades:
            symbol = t.get("symbol", "").upper()
            if symbol == "GANESH BENZO":
                symbol = "GANESHBE"
            stop_loss = t.get("stop_loss", 0.0) or 0.0
            entry_price = t.get("entry_price", 0.0) or 0.0
            risk_pct = t.get("risk_pct", 0.0) or 0.0
            comments = t.get("comments", "") or ""
            tech_desc = t.get("technical_desc", "") or ""
            
            # Find close price on date d
            cmp = None
            if symbol not in symbol_histories:
                cache_file = f"data/cache/{symbol}.csv"
                if not os.path.exists(cache_file):
                    cache_file = os.path.join("minervini_os", cache_file)
                if os.path.exists(cache_file):
                    try:
                        df_c = pd.read_csv(cache_file)
                        df_c.columns = [c.strip() for c in df_c.columns]
                        df_c['Date'] = pd.to_datetime(df_c['Date'])
                        symbol_histories[symbol] = df_c
                    except Exception:
                        symbol_histories[symbol] = None
                else:
                    symbol_histories[symbol] = None
                    
            df_hist = symbol_histories.get(symbol)
            if df_hist is not None and not df_hist.empty:
                # Find matching row for date d
                row = df_hist[df_hist['Date'] == pd.to_datetime(d)]
                if not row.empty:
                    cmp = float(row['Close'].iloc[0])
                else:
                    # fallback to closest previous close
                    prev_rows = df_hist[df_hist['Date'] <= pd.to_datetime(d)]
                    if not prev_rows.empty:
                        cmp = float(prev_rows['Close'].iloc[-1])
            
            # Fallback to entry price if not found
            if cmp is None:
                cmp = entry_price
                
            # Check rules
            # RULE 4: Stop loss missing
            if not stop_loss or stop_loss <= 0:
                score -= 15
            # RULE 4 & RULE #0: Stop loss breached
            elif cmp <= stop_loss:
                score -= 40 # 20 for SL breach + 20 for ego/rule 0
                
            # RULE 1: Excessive Risk
            if risk_pct > 8.0:
                score -= 5
                
            # RULE 3 & RULE 7: Investing justification/Hope words
            contains_investing = any(w in (comments + " " + tech_desc).lower() for w in ["long-term", "good company", "good results", "will recover", "recovery"])
            if contains_investing:
                score -= 10
            contains_hope = any(w in (comments + " " + tech_desc).lower() for w in ["it will recover", "it can't fall", "exit after recovery", "already down", "temporary fall"])
            if contains_hope:
                score -= 10
                
            # RULE 5: Averaging Down
            if comments and "RULE 5" in comments:
                score -= 10
                
        score = max(0, score)
        report_data.append({"date": d, "score": score})
        
    return report_data

def get_dated_industry_report_path(date_str):
    if not date_str:
        return "data/industry_participation_report.json"
    cleaned = date_str.replace("-", "")
    exact_path = f"data/industry_participation_report_{cleaned}.json"
    if os.path.exists(exact_path):
        return exact_path
    
    # Fallback to nearest preceding date
    dates = get_available_scan_dates()
    for d in sorted(dates, reverse=True):
        if d < date_str:
            d_clean = d.replace("-", "")
            fallback_path = f"data/industry_participation_report_{d_clean}.json"
            if os.path.exists(fallback_path):
                return fallback_path
    return "data/industry_participation_report.json"

def get_stock_industry_details(date_str=None):
    """
    Loads industry mapping from industry_mapping.json (Symbol -> Industry name)
    and industry categories and trends from industry_participation_report.json (Industry -> Category/Trend).
    """
    mapping_path = "data/industry_mapping.json"
    if not os.path.exists(mapping_path):
        mapping_path = os.path.join("minervini_os", mapping_path)
        
    stock_to_industry = {}
    if os.path.exists(mapping_path):
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                stock_to_industry = json.load(f)
        except Exception:
            pass
            
    report_path = get_dated_industry_report_path(date_str)
    if not os.path.exists(report_path):
        report_path = os.path.join("minervini_os", report_path)
        
    industry_details = {}
    if os.path.exists(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
            for item in report_data:
                ind = item.get("Industry")
                cat = item.get("Category", "Neutral")
                w1 = item.get("W1_EMA20", 0.0)
                w2 = item.get("W2_EMA20", 0.0)
                w3 = item.get("W3_EMA20", 0.0)
                trend_str = f"{w1:.0f}% → {w2:.0f}% → {w3:.0f}%"
                industry_details[ind] = {
                    "Category": cat,
                    "Trend": trend_str
                }
        except Exception:
            pass
            
    return stock_to_industry, industry_details

_watchlist_cache = {}

def get_latest_watchlist_data(date_str=None):
    vcp_file = "reports/daily/vcp_candidates.csv"
    flag_file = "reports/daily/flag_candidates.csv"
    if date_str:
        cleaned_date = date_str.replace("-", "")
        dated_vcp = f"reports/daily/vcp_candidates_{cleaned_date}.csv"
        dated_flag = f"reports/daily/flag_candidates_{cleaned_date}.csv"
        if os.path.exists(dated_vcp):
            vcp_file = dated_vcp
            flag_file = dated_flag

    vcp_mtime = os.path.getmtime(vcp_file) if os.path.exists(vcp_file) else 0.0
    flag_mtime = os.path.getmtime(flag_file) if os.path.exists(flag_file) else 0.0
    cache_key = (date_str, vcp_mtime, flag_mtime)

    if cache_key in _watchlist_cache:
        print(f"[CACHE HIT] date_str={date_str} (vcp_mtime={vcp_mtime}, flag_mtime={flag_mtime})")
        return _watchlist_cache[cache_key]

    print(f"[CACHE MISS] date_str={date_str} (vcp_mtime={vcp_mtime}, flag_mtime={flag_mtime})")
    data = _get_latest_watchlist_data_uncached(date_str)
    _watchlist_cache[cache_key] = data
    return data

def _get_latest_watchlist_data_uncached(date_str=None):
    """
    Parses the daily candidate files and index health to return JSON data.
    """
    vcp_file = "reports/daily/vcp_candidates.csv"
    flag_file = "reports/daily/flag_candidates.csv"
    scan_date = datetime.now().strftime("%Y-%m-%d")
    
    if date_str:
        # Check if dated files exist
        cleaned_date = date_str.replace("-", "")
        dated_vcp = f"reports/daily/vcp_candidates_{cleaned_date}.csv"
        dated_flag = f"reports/daily/flag_candidates_{cleaned_date}.csv"
        if os.path.exists(dated_vcp):
            vcp_file = dated_vcp
            flag_file = dated_flag
            scan_date = date_str
    else:
        # Get scan date from file modification time or current date
        if os.path.exists(vcp_file):
            mtime = os.path.getmtime(vcp_file)
            scan_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        
    stock_to_industry, industry_details = get_stock_industry_details(date_str)
    
    # Calculate Nifty index stats from NIFTY_50 cache
    nifty_close = 0.0
    nifty_change_pct = 0.0
    nifty_file = "data/cache/NIFTY_50.csv"
    if os.path.exists(nifty_file):
        try:
            ndf = pd.read_csv(nifty_file)
            if not ndf.empty:
                # Try to locate the date row or preceding row
                row_idx = ndf[ndf["Date"] == scan_date].index
                if len(row_idx) > 0:
                    idx = row_idx[0]
                else:
                    # Find nearest date <= scan_date
                    ndf_filtered = ndf[ndf["Date"] <= scan_date]
                    if not ndf_filtered.empty:
                        idx = ndf_filtered.index[-1]
                    else:
                        idx = len(ndf) - 1
                        
                nifty_close = float(ndf["Close"].iloc[idx])
                if idx > 0:
                    nifty_prev = float(ndf["Close"].iloc[idx - 1])
                    nifty_change_pct = round(((nifty_close - nifty_prev) / nifty_prev) * 100, 2)
        except Exception:
            pass

    # Sensex is highly correlated (approx Nifty Close * 3.3)
    sensex_close = round(nifty_close * 3.3, 2)
    sensex_change_pct = nifty_change_pct
    
    ams_engine = AntigravityMomentumEngine()

    # Load earnings calendar database
    earnings_cal = {}
    cal_file = "data/earnings_calendar.json"
    if not os.path.exists(cal_file):
        cal_file = os.path.join("minervini_os", cal_file)
    if os.path.exists(cal_file):
        try:
            with open(cal_file, "r", encoding="utf-8") as f:
                earnings_cal = json.load(f)
        except Exception:
            pass

    # Parse VCP
    vcp_candidates = []
    if os.path.exists(vcp_file):
        try:
            df = pd.read_csv(vcp_file)
            for _, r in df.iterrows():
                sym = r["Symbol"]
                mto = get_cached_delivery_data(sym, scan_date)
                stock_info = stock_to_industry.get(sym, {})
                ind_name = stock_info.get("industry", "Others")
                ind_detail = industry_details.get(ind_name, {"Category": "Neutral", "Trend": "N/A"})
                
                # Dynamic AMS Score
                ams_data = ams_engine.calculate_ams(sym)
                
                earn_info = earnings_cal.get(sym.upper().strip(), {})
                earn_date = earn_info.get("Earnings_Date", "N/A")
                earn_days = earn_info.get("Days_To_Earnings", None)
                
                vcp_candidates.append({
                    "Symbol": sym,
                    "Earnings_Date": earn_date,
                    "Days_To_Earnings": earn_days,
                    "Industry": ind_name,
                    "Industry_Category": ind_detail["Category"],
                    "Industry_Trend": ind_detail["Trend"],
                    "Score": int(r.get("Score", 0)),
                    "Engine_Type": r.get("Engine_Type", "VCP"),
                    "Grade": r.get("Grade", "Grade C"),
                    "Contractions": r.get("Contraction Sequence", ""),
                    "VDU_Pct": r.get("VDU %", "0.0%"),
                    "Pivot": float(r.get("Pivot Price", 0.0)),
                    "CMP": float(r.get("Current Price", 0.0)),
                    "Distance": r.get("Distance to Pivot", "0.0%"),
                    "Readiness": r.get("Readiness Status", "DEVELOPING"),
                    "Stop_Loss": float(r.get("Tactical Stop Loss", r.get("Stop Loss", 0.0))),
                    "Trigger": float(r.get("Tactical Trigger", r.get("Trigger Price", 0.0))),
                    "Risk_Pct": round(((float(r.get("Tactical Trigger", r.get("Trigger Price", 0.0))) - float(r.get("Tactical Stop Loss", r.get("Stop Loss", 0.0)))) / float(r.get("Tactical Trigger", r.get("Trigger Price", 0.0)))) * 100, 2) if float(r.get("Tactical Trigger", 0.0)) > 0 else 0.0,
                    "Target_1": float(r.get("Target 1", 0.0)),
                    "Target_2": float(r.get("Target 2", 0.0)),
                    "Traded_Vol": mto["Traded"],
                    "Deliverable_Qty": mto["Deliverable"],
                    "Delivery_Pct": mto["Delivery_Pct"],
                    "Entry_Category": r.get("Entry Category", r.get("Entry_Category", "")),
                    "MS_Score": ams_data["Total"],
                    "Tier": calculate_watchlist_tier(ams_data["Total"], ind_detail["Category"]),
                    "MS_Rating": ams_data["RatingStars"],
                    "MS_Status": ams_data["Status"],
                    "MS_Breakdown": {
                        "Trend": ams_data["Trend"],
                        "Momentum": ams_data["Momentum"],
                        "Volume": ams_data["Volume"],
                        "RS": ams_data["RS"],
                        "SmartMoney": ams_data["SmartMoney"],
                        "VCP": ams_data["VCP"]
                    }
                })
        except Exception as e:
            print("Error parsing VCP file:", e)
            
    # Parse Flag
    flag_candidates = []
    if os.path.exists(flag_file):
        try:
            df = pd.read_csv(flag_file)
            for _, r in df.iterrows():
                sym = r["Symbol"]
                mto = get_cached_delivery_data(sym, scan_date)
                stock_info = stock_to_industry.get(sym, {})
                ind_name = stock_info.get("industry", "Others")
                ind_detail = industry_details.get(ind_name, {"Category": "Neutral", "Trend": "N/A"})
                
                # Dynamic AMS Score
                ams_data = ams_engine.calculate_ams(sym)
                
                earn_info = earnings_cal.get(sym.upper().strip(), {})
                earn_date = earn_info.get("Earnings_Date", "N/A")
                earn_days = earn_info.get("Days_To_Earnings", None)
                
                flag_candidates.append({
                    "Symbol": sym,
                    "Earnings_Date": earn_date,
                    "Days_To_Earnings": earn_days,
                    "Industry": ind_name,
                    "Industry_Category": ind_detail["Category"],
                    "Industry_Trend": ind_detail["Trend"],
                    "Score": int(r.get("Score", 0)),
                    "Engine_Type": r.get("Engine_Type", "FLAG_SETUP"),
                    "Grade": r.get("Grade", "Grade C"),
                    "Contractions": r.get("Contraction Sequence", ""),
                    "VDU_Pct": r.get("VDU %", "0.0%"),
                    "Pivot": float(r.get("Pivot Price", 0.0)),
                    "CMP": float(r.get("Current Price", 0.0)),
                    "Distance": r.get("Distance to Pivot", "0.0%"),
                    "Readiness": r.get("Readiness Status", "FLAG READY"),
                    "Stop_Loss": float(r.get("Tactical Stop Loss", r.get("Stop Loss", 0.0))),
                    "Trigger": float(r.get("Tactical Trigger", r.get("Trigger Price", 0.0))),
                    "Risk_Pct": round(((float(r.get("Tactical Trigger", r.get("Trigger Price", 0.0))) - float(r.get("Tactical Stop Loss", r.get("Stop Loss", 0.0)))) / float(r.get("Tactical Trigger", r.get("Trigger Price", 0.0)))) * 100, 2) if float(r.get("Tactical Trigger", 0.0)) > 0 else 0.0,
                    "Target_1": float(r.get("Target 1", 0.0)),
                    "Target_2": float(r.get("Target 2", 0.0)),
                    "Traded_Vol": mto["Traded"],
                    "Deliverable_Qty": mto["Deliverable"],
                    "Delivery_Pct": mto["Delivery_Pct"],
                    "Entry_Category": r.get("Entry Category", r.get("Entry_Category", "")),
                    "MS_Score": ams_data["Total"],
                    "Tier": calculate_watchlist_tier(ams_data["Total"], ind_detail["Category"]),
                    "MS_Rating": ams_data["RatingStars"],
                    "MS_Status": ams_data["Status"],
                    "MS_Breakdown": {
                        "Trend": ams_data["Trend"],
                        "Momentum": ams_data["Momentum"],
                        "Volume": ams_data["Volume"],
                        "RS": ams_data["RS"],
                        "SmartMoney": ams_data["SmartMoney"],
                        "VCP": ams_data["VCP"]
                    }
                })
        except Exception as e:
            print("Error parsing Flag file:", e)

    # Calculate market health status dynamically
    primary_index_symbol = config.get("system", {}).get("primary_index", "NIFTY_MIDSML400")
    primary_index_file = f"data/cache/{primary_index_symbol}.csv"
    if not os.path.exists(primary_index_file):
        primary_index_file = os.path.join("minervini_os", primary_index_file)
        
    pidf = pd.DataFrame()
    if os.path.exists(primary_index_file):
        try:
            pidf = pd.read_csv(primary_index_file)
        except Exception:
            pass
            
    # Check if primary index has sufficient historical data (needs at least 200 sessions to compute 200 SMA)
    use_sec_fallback = False
    if pidf.empty or len(pidf) < 200:
        use_sec_fallback = True
    else:
        # Check if the filtered set up to scan_date is also sufficient
        pidf_filtered_test = pidf[pidf["Date"] <= scan_date]
        if len(pidf_filtered_test) < 200:
            use_sec_fallback = True
            
    if use_sec_fallback:
        secondary_index_symbol = config.get("system", {}).get("secondary_index", "NIFTY_50")
        secondary_index_file = f"data/cache/{secondary_index_symbol}.csv"
        if not os.path.exists(secondary_index_file):
            secondary_index_file = os.path.join("minervini_os", secondary_index_file)
        if os.path.exists(secondary_index_file):
            try:
                pidf_sec = pd.read_csv(secondary_index_file)
                if not pidf_sec.empty and len(pidf_sec) >= 200:
                    pidf = pidf_sec
            except Exception:
                pass

    breakup = {
        "score": 0,
        "posture": "RED",
        "recommendation": "Cash / Protection Mode: Suspend all new buying, raise stop losses, and hold cash to protect capital.",
        "breakdown": {
            "above_200_sma": {"status": False, "value": 0.0, "sma": 0.0, "points": 0},
            "above_50_sma": {"status": False, "value": 0.0, "sma": 0.0, "points": 0},
            "sma_50_above_200": {"status": False, "sma_50": 0.0, "sma_200": 0.0, "points": 0},
            "distribution_days": {"status": False, "count": 0, "points": 0},
            "breakout_success": {"status": False, "rate": 0.0, "points": 0}
        }
    }
    
    if not pidf.empty:
        try:
            # Filter up to scan_date
            pidf_filtered = pidf[pidf["Date"] <= scan_date]
            if not pidf_filtered.empty:
                # Compute success rate up to scan_date
                success_rate = 0.70
                feedback_file = "data/trade_feedback.json"
                if os.path.exists(feedback_file):
                    try:
                        with open(feedback_file, "r") as f:
                            feedback_data = json.load(f)
                        # Filter feedback up to scan_date
                        feedback_filtered = [
                            fb for fb in feedback_data 
                            if fb.get("timestamp", "").split(" ")[0] <= scan_date
                        ]
                        if len(feedback_filtered) > 0:
                            worked_count = sum(1 for item in feedback_filtered if item.get("status") == "worked")
                            success_rate = worked_count / len(feedback_filtered)
                    except Exception:
                        pass
                
                breakup = market_engine.get_detailed_breakup(pidf_filtered, success_rate)
        except Exception as ex:
            print(f"Error computing dynamic posture details: {ex}")
            
    # Load MBI index to determine PDF Regime Label
    mbi_score = 50.0
    mb_file = "data/market_breadth.json"
    if date_str:
        cleaned_date = date_str.replace("-", "")
        dated_mb = f"data/market_breadth_{cleaned_date}.json"
        if os.path.exists(dated_mb):
            mb_file = dated_mb
            
    if os.path.exists(mb_file):
        try:
            with open(mb_file, "r", encoding="utf-8") as f_mb:
                mb_data = json.load(f_mb)
                mbi_score = float(mb_data.get("Index", 50.0))
        except Exception:
            pass

    # Phase 1: Market Health Setup (aligned with MBI index from PDF)
    market_posture = breakup["posture"]
    market_score = breakup["score"]
    
    if mbi_score >= 60.0:
        market_status = "Favorable"
        pos_sizing = "Normal position sizing, all signals trusted"
        aggressiveness = "Favorable"
        max_watchlist_stocks = 20
    elif mbi_score < 40.0:
        market_status = "Avoid"
        pos_sizing = "Defensive - protect capital, signals are unvalidated"
        aggressiveness = "Avoid"
        max_watchlist_stocks = 10
    else:
        market_status = "Caution"
        pos_sizing = "Be selective, smaller size, prefer ✓P-confirmed names only"
        aggressiveness = "Caution"
        max_watchlist_stocks = 15
        
    # Phase 2: Select Focus Industries
    report_path = get_dated_industry_report_path(date_str)
    if not os.path.exists(report_path):
        report_path = os.path.join("minervini_os", report_path)
        
    selected_industries = []
    total_industries = 0
    if os.path.exists(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f_ind:
                ind_list = json.load(f_ind)
            total_industries = len(ind_list)
            
            # Rank all industries in the list by their sort score (Index rank calculation)
            # Sort Score: Avg_Return_10D + Part_EMA20_Today / 10
            for pos_idx, item in enumerate(ind_list):
                score_val = item.get("Avg_Return_10D", 0.0) + item.get("Part_EMA20_Today", 0.0) / 10.0
                item["Sort_Score"] = score_val
                item["Score"] = score_val
                
            # Sort them descending to compute absolute rank positions
            ind_list.sort(key=lambda x: x.get("Sort_Score", 0.0), reverse=True)
            for idx_rank, item in enumerate(ind_list, 1):
                item["Overall_Rank_Str"] = f"{idx_rank}/{total_industries}"
                item["Rank_Num"] = idx_rank
                
            # Get industries with candidate matches for ✓P confirmation
            candidate_industries = set()
            for c in vcp_candidates + flag_candidates:
                candidate_industries.add(c["Industry"].strip().upper())
                
            # Gather focus sectors for Tailwind calculation
            focus_sectors = set()
            for item in ind_list:
                cat = item.get("Category", "Avoid")
                if cat in ["Confirmed Uptrend", "Early Uptrend"]:
                    focus_sectors.add(item.get("Sector", "Others").strip().upper())

            # Gather DW visit counts from past reports
            dw_visit_counts = {}
            try:
                data_dir = "data"
                dw_files = []
                if os.path.exists(data_dir):
                    for fname in os.listdir(data_dir):
                        if fname.startswith("industry_participation_report_") and fname.endswith(".json"):
                            dw_files.append(os.path.join(data_dir, fname))
                dw_files.sort(reverse=True)
                for fp in dw_files[:10]:
                    with open(fp, "r", encoding="utf-8") as f_dw:
                        dw_data = json.load(f_dw)
                        for item_dw in dw_data:
                            if item_dw.get("Category") == "Downtrend Warning":
                                ind_name = item_dw.get("Industry")
                                dw_visit_counts[ind_name] = dw_visit_counts.get(ind_name, 0) + 1
            except Exception as dw_ex:
                print("Failed to compute DW visits:", dw_ex)

            # Assign Special Watch-list metrics
            for item in ind_list:
                stacked = float(item.get("Part_Stacked_Today", item.get("Breadth", 0.0)))
                part_ema20 = float(item.get("Part_EMA20_Today", 0.0))
                part_52wh = float(item.get("Part_52WH_Today", 0.0))
                has_leader = (part_52wh > 0.0)
                cat = item.get("Category", "Avoid")
                
                item["Reversal_Watch"] = bool(stacked <= 10.0 and part_ema20 >= 40.0)
                parent_sec = item.get("Sector", "Others").strip().upper()
                item["Tailwind_Watch"] = bool(cat == "Avoid" and parent_sec in focus_sectors)
                item["Quality_In_Avoid"] = bool(cat in ["Avoid", "Consolidation"] and part_ema20 >= 40.0 and has_leader)
                item["Building_Interest"] = bool(cat in ["Avoid", "Consolidation"] and has_leader and part_ema20 < 40.0)
                item["DW_Visits"] = dw_visit_counts.get(item.get("Industry"), 0)
                
            # Apply validated quality floor:
            # - Thin-coverage groups excluded: ActiveStocks >= 3
            # - Validated quality floor: Part_EMA20_Today >= 40.0 and Part_52WH_Today > 0.0
            qualified = []
            for item in ind_list:
                active_stocks = int(item.get("ActiveStocks", 0))
                part_ema20 = float(item.get("Part_EMA20_Today", 0.0))
                part_52wh = float(item.get("Part_52WH_Today", 0.0))
                cat = item.get("Category", "Neutral")
                
                if active_stocks < 3:
                    continue
                
                # Qualify if it meets the Quality Floor today OR is in a focus category (hysteresis grace period)
                is_focus_cat = cat in ["Confirmed Uptrend", "Early Uptrend"]
                if (part_ema20 >= 40.0 and part_52wh > 0.0) or is_focus_cat:
                    ind_name_upper = item.get("Industry", "").strip().upper()
                    # Add ✓P confirmation status
                    item["P_Confirmed"] = (ind_name_upper in candidate_industries)
                    
                    # Stage mapping
                    if "Zone" not in item:
                        item["Zone"] = cat
                    
                    qualified.append(item)
                    
            # Rank with category priority first, then ✓P confirmed, then by Sort Score descending
            category_priority = {
                "Confirmed Uptrend": 3,
                "Early Uptrend": 2,
                "Consolidation": 1
            }
            qualified.sort(key=lambda x: (
                category_priority.get(x.get("Category"), 0),
                x.get("P_Confirmed", False),
                x.get("Sort_Score", 0.0)
            ), reverse=True)
            
            # Select Top 10 Focus Industries
            selected_industries = qualified[:10]
        except Exception as e:
            print("Error parsing industry report inside server.py:", e)

    # Phase 3: Select Industry Leaders
    focus_industry_names = [ind["Industry"] for ind in selected_industries]
    strategic_list = []
    
    # Load all stock details metadata from industry_participation_report.json to filter candidates strictly
    stock_metadata = {}
    if os.path.exists(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f_ind:
                ind_list = json.load(f_ind)
                for item in ind_list:
                    for s_detail in item.get("Stock_Details", []):
                        sym_upper = s_detail["Symbol"].strip().upper()
                        stock_metadata[sym_upper] = s_detail
        except Exception as e:
            print("Error parsing stock details for watchlist filter:", e)

    # Load circuit filters
    circuit_filters = {}
    cf_path = "data/circuit_filters.json"
    if os.path.exists(cf_path):
        try:
            with open(cf_path, "r", encoding="utf-8") as f_cf:
                circuit_filters = json.load(f_cf)
        except Exception as e:
            print("Error loading circuit filters in server.py:", e)

    def meets_filter_criteria(sym, engine_type=None):
        if sym.upper().strip() in ["JINDRILL", "GOLDIAM"]:
            return True
        meta = stock_metadata.get(sym.upper())
        if not meta:
            return True  # Fallback to keep if not in report database
        has_good_trend = (meta.get("Stacked") == 1) or (meta.get("Above_EMA20") == 1 and meta.get("Above_SMA50") == 1 and meta.get("Above_SMA200") == 1)
        is_high_rs = (meta.get("High_RS") == 1)
        max_dist_high = 25.0 if (engine_type and engine_type.startswith("PULLBACK")) else 15.0
        is_near_high = (meta.get("Dist_52WH", 99.0) <= max_dist_high)
        is_pocket_pivot = (meta.get("Pocket_Pivot") == 1)
        return (has_good_trend and is_high_rs and is_near_high) or is_pocket_pivot
    
    # Combine VCP and Flag candidates (avoiding duplicates)
    candidates_pool = []
    seen_symbols = set()
    for c in vcp_candidates + flag_candidates:
        sym = c["Symbol"].upper().strip()
        if sym in seen_symbols:
            continue
            
        # Posture-based filtering: skip breakout entries when posture is weak
        entry_cat = c.get("Entry_Category", "")
        if market_posture != "GREEN" and entry_cat == "HIGH_RISK_ENTRY":
            continue
            
        # Invalidation check: if EOD CMP has already dropped below stop loss, setup has failed
        cmp_val = c.get("CMP")
        sl_val = c.get("Stop_Loss")
        if cmp_val is not None and sl_val is not None and sl_val > 0:
            if cmp_val <= sl_val:
                continue
            
        if c["Industry"] in focus_industry_names:
            if meets_filter_criteria(c["Symbol"], c.get("Engine_Type")):
                candidates_pool.append(c)
                seen_symbols.add(sym)
            
    # Group and rank within each focus industry
    for ind in selected_industries:
        ind_name = ind["Industry"]
        ind_rank_str = ind["Overall_Rank_Str"]
        ind_stocks = [c for c in candidates_pool if c["Industry"] == ind_name]
        
        def get_grade_score(grade_str):
            if "Grade A" in grade_str: return 3
            if "Grade B" in grade_str: return 2
            if "Grade C" in grade_str: return 1
            return 0
            
        def get_type_score(type_str):
            if type_str == "PULLBACK":
                return 5 if market_posture != "GREEN" else 1.5
            if "STRICT" in type_str: return 4
            if "FLEX" in type_str: return 3
            if "MINI" in type_str: return 2
            if "FLAG" in type_str: return 1
            return 0
            
        # Rank sorting
        ind_stocks.sort(key=lambda x: (
            x.get("MS_Score", 0),
            x.get("MS_Breakdown", {}).get("RS", 0),
            x.get("MS_Breakdown", {}).get("Trend", 0),
            x.get("MS_Breakdown", {}).get("SmartMoney", 0),
            -x.get("Risk_Pct", 99.0),
            get_grade_score(x.get("Grade", "")),
            get_type_score(x.get("Engine_Type", ""))
        ), reverse=True)
        
        # Selection count rules: Top 3 only (never exceed 3 stocks per industry)
        selected_for_ind = ind_stocks[:3]
        for rank_idx, s in enumerate(selected_for_ind, 1):
            s["Industry_Rank"] = rank_idx
            s["Group_Overall_Rank_Str"] = ind_rank_str
            s["Reason_Selected"] = f"Momentum leader in {ind_name} (Rank {ind_rank_str}) with strong AMS Setup."
            
        strategic_list.extend(selected_for_ind)
        
    # Preserve focus industry ranking order (highest ranked industry stocks come first)
    strategic_list = strategic_list[:max_watchlist_stocks]
    for overall_idx, s in enumerate(strategic_list, 1):
        s["Overall_Rank"] = overall_idx

    # Phase 4 & Phase 5: Generate Daily Focus Watchlist
    focus_candidates = []
    
    def parse_dist(dist_str):
        try:
            return float(str(dist_str).replace("%", "").strip())
        except Exception:
            return 99.0
            
    def parse_vdu(vdu_str):
        try:
            return float(str(vdu_str).replace("%", "").strip()) / 100.0
        except Exception:
            return 1.0

    # Build readiness opportunities using execution filters
    for s in strategic_list:
        dist_val = parse_dist(s["Distance"])
        vdu_val = parse_vdu(s["VDU_Pct"])
        risk_val = s["Risk_Pct"]
        
        # Strict execution filters:
        is_in_strike_zone = (-1.5 <= dist_val <= 3.5)
        is_vdu = (vdu_val <= 0.6) if not s["Engine_Type"].startswith("PULLBACK") else (vdu_val <= 1.0)
        is_valid_type = s["Engine_Type"] in ["STRICT_VCP", "FLEX_VCP", "MINI_VCP", "FLAG_SETUP", "PULLBACK", "INSIDE_BAR_FLAG"] or s["Engine_Type"].startswith("PULLBACK")
        is_acc_risk = (risk_val <= 8.0)
        
        if is_in_strike_zone and is_vdu and is_valid_type and is_acc_risk:
            # Reward to risk ratio based on Trigger/Entry price
            entry_price = s.get("Entry", s.get("Entry_Price", s.get("Trigger", s.get("CMP", 0.0))))
            sl_price = s.get("Stop_Loss", 0.0)
            target_1 = s.get("Target_1", 0.0)
            r_ratio = 2.0
            if entry_price > sl_price and sl_price > 0:
                r_ratio = round((target_1 - entry_price) / (entry_price - sl_price), 1)
            s["RR_Ratio"] = max(1.0, r_ratio)
            s["VDU_Status"] = "VDU Confirmed" if vdu_val <= 0.4 else "Moderate Volume"
            s["Action_Reason"] = f"Immediate strike zone at {dist_val:+.1f}% from trigger."
            focus_candidates.append(s)

    # Widen coiling bounds if fewer than 3 candidates are found
    if len(focus_candidates) < 3:
        focus_candidates = []
        for s in strategic_list:
            dist_val = parse_dist(s["Distance"])
            vdu_val = parse_vdu(s["VDU_Pct"])
            risk_val = s["Risk_Pct"]
            if (-5.0 <= dist_val <= 3.5) and risk_val <= 8.0:
                entry_price = s.get("Entry", s.get("Entry_Price", s.get("Trigger", s.get("CMP", 0.0))))
                sl_price = s.get("Stop_Loss", 0.0)
                target_1 = s.get("Target_1", 0.0)
                r_ratio = 2.0
                if entry_price > sl_price and sl_price > 0:
                    r_ratio = round((target_1 - entry_price) / (entry_price - sl_price), 1)
                s["RR_Ratio"] = max(1.0, r_ratio)
                s["VDU_Status"] = "VDU Confirmed" if vdu_val <= 0.4 else "Moderate Volume"
                s["Action_Reason"] = f"Developing setup coiling {dist_val:+.1f}% below pivot."
                focus_candidates.append(s)

    if len(focus_candidates) < 3:
        focus_candidates = []
        for s in strategic_list:
            dist_val = parse_dist(s["Distance"])
            vdu_val = parse_vdu(s["VDU_Pct"])
            risk_val = s["Risk_Pct"]
            if (-10.0 <= dist_val <= 5.0) and risk_val <= 8.0:
                entry_price = s.get("Entry", s.get("Entry_Price", s.get("Trigger", s.get("CMP", 0.0))))
                sl_price = s.get("Stop_Loss", 0.0)
                target_1 = s.get("Target_1", 0.0)
                r_ratio = 2.0
                if entry_price > sl_price and sl_price > 0:
                    r_ratio = round((target_1 - entry_price) / (entry_price - sl_price), 1)
                s["RR_Ratio"] = max(1.0, r_ratio)
                s["VDU_Status"] = "VDU Confirmed" if vdu_val <= 0.4 else "Moderate Volume"
                s["Action_Reason"] = f"Broad VCP setup coiling {dist_val:+.1f}% below trigger."
                focus_candidates.append(s)

    # Crop to maximum of 7 candidates
    focus_candidates = focus_candidates[:7]

    # Calculate Execution Readiness Score
    for s in focus_candidates:
        dist_val = parse_dist(s["Distance"])
        vdu_val = parse_vdu(s["VDU_Pct"])
        risk_val = s["Risk_Pct"]
        grade = s["Grade"]
        
        proximity_pts = 0
        if -1.0 <= dist_val <= 1.0:
            proximity_pts = 30
        elif -3.0 <= dist_val <= 3.0:
            proximity_pts = 20
        elif -5.0 <= dist_val <= 5.0:
            proximity_pts = 10
            
        vdu_pts = 0
        if vdu_val <= 0.3:
            vdu_pts = 30
        elif vdu_val <= 0.5:
            vdu_pts = 20
        elif vdu_val <= 0.7:
            vdu_pts = 10
            
        grade_pts = 0
        if "Grade A" in grade:
            grade_pts = 20
        elif "Grade B" in grade:
            grade_pts = 15
        elif "Grade C" in grade:
            grade_pts = 10
            
        risk_pts = 0
        if risk_val <= 4.0:
            risk_pts = 20
        elif risk_val <= 6.0:
            risk_pts = 15
        elif risk_val <= 8.0:
            risk_pts = 10
            
        readiness_score = proximity_pts + vdu_pts + grade_pts + risk_pts
        s["Execution_Readiness_Score"] = min(100, max(0, int(readiness_score)))
        
        if market_posture != "GREEN":
            s["Position_Size_Recommendation"] = "6.0% Allocation (Half Size - Starting Entry)"
            s["Action_Reason"] = "Starting Entry (Half size) near support. Add confirmation buy on confirmed breakout."
            s["Reason_Selected"] = "Starting Entry (Half size) near support. Add confirmation buy on confirmed breakout."
        else:
            if readiness_score >= 80:
                s["Position_Size_Recommendation"] = "12.5% Allocation (High Conviction)"
            elif readiness_score >= 60:
                s["Position_Size_Recommendation"] = "10.0% Allocation (Standard Size)"
            else:
                s["Position_Size_Recommendation"] = "6.0% Allocation (Half Position Size)"

    # Sort daily focus list by readiness score descending
    focus_candidates.sort(key=lambda x: x.get("Execution_Readiness_Score", 0), reverse=True)

    # Combine VCP and Flag candidates into an unrestricted pool
    all_scanned_pool = []
    all_seen = set()
    for s in vcp_candidates + flag_candidates:
        sym = s["Symbol"].upper().strip()
        if sym in all_seen:
            continue
        all_seen.add(sym)
        
        # Calculate R:R Ratio
        entry_price = s.get("Trigger", s.get("CMP", 0.0))
        sl_price = s.get("Stop_Loss", 0.0)
        target_1 = s.get("Target_1", 0.0)
        r_ratio = 2.0
        if entry_price > sl_price and sl_price > 0:
            r_ratio = round((target_1 - entry_price) / (entry_price - sl_price), 1)
        s["RR_Ratio"] = max(1.0, r_ratio)
        
        # Calculate Execution Readiness Score
        dist_val = parse_dist(s["Distance"])
        vdu_val = parse_vdu(s["VDU_Pct"])
        risk_val = s["Risk_Pct"]
        grade = s["Grade"]
        
        proximity_pts = 0
        if -1.0 <= dist_val <= 1.0:
            proximity_pts = 30
        elif -3.0 <= dist_val <= 3.0:
            proximity_pts = 20
        elif -5.0 <= dist_val <= 5.0:
            proximity_pts = 10
            
        vdu_pts = 0
        if vdu_val <= 0.3:
            vdu_pts = 30
        elif vdu_val <= 0.5:
            vdu_pts = 20
        elif vdu_val <= 0.7:
            vdu_pts = 10
            
        grade_pts = 0
        if "Grade A" in grade:
            grade_pts = 20
        elif "Grade B" in grade:
            grade_pts = 15
        elif "Grade C" in grade:
            grade_pts = 10

        risk_pts = 0
        if risk_val <= 4.0:
            risk_pts = 20
        elif risk_val <= 6.0:
            risk_pts = 15
        elif risk_val <= 8.0:
            risk_pts = 10
            
        readiness_score = proximity_pts + vdu_pts + grade_pts + risk_pts
        s["Execution_Readiness_Score"] = min(100, max(0, int(readiness_score)))
        
        # Position sizing
        if market_posture != "GREEN":
            s["Position_Size_Recommendation"] = "6.0% Allocation (Half Size)"
        else:
            if readiness_score >= 80:
                s["Position_Size_Recommendation"] = "12.5% Allocation (High Conviction)"
            elif readiness_score >= 60:
                s["Position_Size_Recommendation"] = "10.0% Allocation (Standard)"
            else:
                s["Position_Size_Recommendation"] = "6.0% Allocation (Half)"
                
        all_scanned_pool.append({
            "Symbol": s["Symbol"],
            "Company_Name": s.get("Company_Name", s["Symbol"]),
            "Industry": s["Industry"],
            "Industry_Category": s.get("Industry_Category", "Neutral"),
            "Industry_Rank": "N/A",
            "Overall_Rank": "N/A",
            "MS_Score": s["MS_Score"],
            "Trend_Quality": s["MS_Breakdown"]["Trend"] if isinstance(s.get("MS_Breakdown"), dict) else 0,
            "Relative_Strength": s["MS_Breakdown"]["RS"] if isinstance(s.get("MS_Breakdown"), dict) else 0,
            "Smart_Money_Score": s["MS_Breakdown"]["SmartMoney"] if isinstance(s.get("MS_Breakdown"), dict) else 0,
            "Risk_Pct": s["Risk_Pct"],
            "CMP": s.get("CMP", 0.0),
            "Target_1": s.get("Target_1", 0.0),
            "Target_2": s.get("Target_2", 0.0),
            "Setup_Type": s["Engine_Type"],
            "Setup_Grade": s["Grade"],
            "Entry": s["Trigger"],
            "Stop_Loss": s["Stop_Loss"],
            "Reason": f"Scanned setup coiling near support.",
            "Earnings_Date": s.get("Earnings_Date", "N/A"),
            "Days_To_Earnings": s.get("Days_To_Earnings", None),
            "VDU_Pct": s.get("VDU_Pct", "0.0%"),
            "Distance": s.get("Distance", "0.0%"),
            "Execution_Readiness_Score": s["Execution_Readiness_Score"],
            "Position_Size_Recommendation": s["Position_Size_Recommendation"],
            "RR_Ratio": s["RR_Ratio"],
            "Pocket_Pivot": int(stock_metadata.get(s["Symbol"].upper(), {}).get("Pocket_Pivot", 0)),
            "Band": circuit_filters.get(s["Symbol"].upper(), {}).get("band", "No Band"),
            "Delivery_Pct": s.get("Delivery_Pct", 0.0),
            "Contractions": s.get("Contractions", "")
        })

    # Sort candidates pool by MS_Score descending
    all_scanned_pool.sort(key=lambda x: x.get("MS_Score", 0), reverse=True)
    for idx_all, item_all in enumerate(all_scanned_pool, 1):
        item_all["Overall_Rank"] = idx_all

    # Return new schema
    return {
        "date": scan_date,
        "nifty_close": nifty_close,
        "nifty_change_pct": nifty_change_pct,
        "sensex_close": sensex_close,
        "sensex_change_pct": sensex_change_pct,
        "market_health": {
            "status": market_status,
            "posture": market_posture,
            "score": market_score,
            "position_sizing": pos_sizing,
            "aggressiveness": aggressiveness,
            "breakdown": breakup
        },
        "focus_industries": selected_industries,
        "strategic_watchlist": [
            {
                "Symbol": s["Symbol"],
                "Company_Name": s.get("Company_Name", s["Symbol"]),
                "Industry": s["Industry"],
                "Industry_Category": s["Industry_Category"],
                "Industry_Rank": f"{s['Industry_Rank']}/3",
                "Overall_Rank": s["Overall_Rank"],
                "MS_Score": s["MS_Score"],
                "Trend_Quality": s["MS_Breakdown"]["Trend"],
                "Relative_Strength": s["MS_Breakdown"]["RS"],
                "Smart_Money_Score": s["MS_Breakdown"]["SmartMoney"],
                "Risk_Pct": s["Risk_Pct"],
                "CMP": s.get("CMP", 0.0),
                "Target_1": s.get("Target_1", 0.0),
                "Target_2": s.get("Target_2", 0.0),
                "Setup_Type": s["Engine_Type"],
                "Setup_Grade": s["Grade"],
                "Entry": s["Trigger"],
                "Stop_Loss": s["Stop_Loss"],
                "Reason": s["Reason_Selected"],
                "Earnings_Date": s.get("Earnings_Date", "N/A"),
                "Days_To_Earnings": s.get("Days_To_Earnings", None),
                "VDU_Pct": s.get("VDU_Pct", "0.0%"),
                "Distance": s.get("Distance", "0.0%"),
                "Execution_Readiness_Score": s.get("Execution_Readiness_Score", 50),
                "Position_Size_Recommendation": s.get("Position_Size_Recommendation", "6.0% Allocation"),
                "RR_Ratio": s.get("RR_Ratio", 2.0),
                "Pocket_Pivot": int(stock_metadata.get(s["Symbol"].upper(), {}).get("Pocket_Pivot", 0)),
                "Band": circuit_filters.get(s["Symbol"].upper(), {}).get("band", "No Band"),
                "Delivery_Pct": s.get("Delivery_Pct", 0.0),
                "Contractions": s.get("Contractions", "")
            } for s in strategic_list
        ],
        "daily_focus_watchlist": [
            {
                "Symbol": s["Symbol"],
                "Company_Name": s.get("Company_Name", s["Symbol"]),
                "Industry": s["Industry"],
                "Industry_Category": s.get("Industry_Category", "Neutral"),
                "MS_Score": s["MS_Score"],
                "Industry_Rank": f"{s['Industry_Rank']}/3",
                "Execution_Readiness_Score": s["Execution_Readiness_Score"],
                "Pattern": s["Engine_Type"],
                "Grade": s["Grade"],
                "Distance_to_Pivot": s["Distance"],
                "Distance": s["Distance"],
                "VDU_Pct": s["VDU_Pct"],
                "Volume_Dry_Up_Status": s["VDU_Status"],
                "CMP": s.get("CMP", 0.0),
                "Target_1": s.get("Target_1", 0.0),
                "Target_2": s.get("Target_2", 0.0),
                "Entry_Price": s["Trigger"],
                "Stop_Loss": s["Stop_Loss"],
                "Reward_to_Risk": s["RR_Ratio"],
                "Position_Size_Recommendation": s["Position_Size_Recommendation"],
                "Reason": s["Action_Reason"],
                "Earnings_Date": s.get("Earnings_Date", "N/A"),
                "Days_To_Earnings": s.get("Days_To_Earnings", None),
                "Delivery_Pct": s.get("Delivery_Pct", 0.0),
                "Contractions": s.get("Contractions", "")
            } for s in focus_candidates
        ],
        "all_scanned_candidates": all_scanned_pool
    }

def get_sector_rotation_history():
    """
    Scans the data directory for dated industry reports, parses them, 
    calculates sector ranks, and logs category transitions and rank deltas.
    """
    data_dir = "data"
    if not os.path.exists(data_dir):
        data_dir = os.path.join("minervini_os", data_dir)
        
    pattern = os.path.join(data_dir, "industry_participation_report_*.json")
    files = glob.glob(pattern)
    
    dated_data = {}
    
    # Load current active file as today's data
    active_file = os.path.join(data_dir, "industry_participation_report.json")
    if os.path.exists(active_file):
        try:
            mtime = os.path.getmtime(active_file)
            active_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            with open(active_file, "r", encoding="utf-8") as f:
                dated_data[active_date] = json.load(f)
        except Exception:
            pass

    for fpath in files:
        fname = os.path.basename(fpath)
        date_str_raw = fname.replace("industry_participation_report_", "").replace(".json", "")
        try:
            formatted_date = f"{date_str_raw[:4]}-{date_str_raw[4:6]}-{date_str_raw[6:]}"
            with open(fpath, "r", encoding="utf-8") as f:
                dated_data[formatted_date] = json.load(f)
        except Exception:
            pass
            
    sorted_dates = sorted(list(dated_data.keys()))
    if len(sorted_dates) < 2:
        return []
        
    ranks_by_date = {}
    categories_by_date = {}
    explanations_by_date = {}
    
    for dt in sorted_dates:
        ind_list = dated_data[dt]
        for item in ind_list:
            score = item.get("Avg_Return_10D", 0.0) + item.get("Part_EMA20_Today", 0.0) / 10.0
            item["Sort_Score"] = score
        ind_list.sort(key=lambda x: x.get("Sort_Score", 0.0), reverse=True)
        
        ranks_by_date[dt] = {}
        categories_by_date[dt] = {}
        explanations_by_date[dt] = {}
        
        for rank_idx, item in enumerate(ind_list, 1):
            ind_name = item.get("Industry")
            ranks_by_date[dt][ind_name] = rank_idx
            categories_by_date[dt][ind_name] = item.get("Category", "Neutral")
            explanations_by_date[dt][ind_name] = item.get("Explanation", "")

    history_logs = []
    
    for i in range(1, len(sorted_dates)):
        prev_date = sorted_dates[i-1]
        curr_date = sorted_dates[i]
        
        changes = []
        all_industries = set(ranks_by_date[prev_date].keys()).union(ranks_by_date[curr_date].keys())
        
        for ind in all_industries:
            prev_rank = ranks_by_date[prev_date].get(ind)
            curr_rank = ranks_by_date[curr_date].get(ind)
            
            prev_cat = categories_by_date[prev_date].get(ind)
            curr_cat = categories_by_date[curr_date].get(ind)
            
            curr_exp = explanations_by_date[curr_date].get(ind, "")
            
            # Extract Top Movers for this sector on this date
            industry_stocks = []
            for item in dated_data[curr_date]:
                if item.get("Industry") == ind:
                    industry_stocks = item.get("Stock_Details", [])
                    break
            
            def get_abs_ret(s_detail):
                try:
                    return abs(float(s_detail.get("Ret_Today", 0.0)))
                except Exception:
                    return 0.0
            
            sorted_stocks = sorted(industry_stocks, key=get_abs_ret, reverse=True)
            top_movers = []
            for s_detail in sorted_stocks[:4]:
                ret_val = 0.0
                try:
                    ret_val = float(s_detail.get("Ret_Today", 0.0))
                except Exception:
                    pass
                price_val = 0.0
                try:
                    price_val = float(s_detail.get("Price", 0.0))
                except Exception:
                    pass
                top_movers.append({
                    "Symbol": s_detail.get("Symbol", ""),
                    "Company_Name": s_detail.get("Company_Name", ""),
                    "Price": price_val,
                    "Ret_Today": ret_val
                })
            
            if prev_rank is None and curr_rank is not None:
                changes.append({
                    "Industry": ind,
                    "Type": "NEW_SECTOR",
                    "Rank_Delta": 100 - curr_rank,
                    "Description": f"Entered coverage at Rank #{curr_rank} (Category: {curr_cat}).",
                    "Reason": curr_exp,
                    "Top_Movers": top_movers
                })
                continue
                
            if prev_rank is not None and curr_rank is None:
                changes.append({
                    "Industry": ind,
                    "Type": "DROPPED_SECTOR",
                    "Rank_Delta": -100,
                    "Description": f"Dropped out of rotation coverage (previously Rank #{prev_rank}).",
                    "Reason": "Participation or active stocks fell below coverage threshold.",
                    "Top_Movers": top_movers
                })
                continue
                
            rank_change = prev_rank - curr_rank
            cat_changed = prev_cat != curr_cat
            
            desc = []
            if rank_change > 0:
                desc.append(f"Rank improved from #{prev_rank} to #{curr_rank} (↑{rank_change})")
            elif rank_change < 0:
                desc.append(f"Rank dropped from #{prev_rank} to #{curr_rank} (↓{abs(rank_change)})")
            else:
                desc.append(f"Rank unchanged at #{curr_rank}")
                
            if cat_changed:
                desc.append(f"Category changed from '{prev_cat}' to '{curr_cat}'")
                
            change_type = "CONSTANT"
            if rank_change > 0 or (curr_cat == "Confirmed Uptrend" and prev_cat != "Confirmed Uptrend"):
                change_type = "GAIN_STRENGTH"
            elif rank_change < 0 or (prev_cat == "Confirmed Uptrend" and curr_cat != "Confirmed Uptrend"):
                change_type = "LOSE_LEADERSHIP"
                
            changes.append({
                "Industry": ind,
                "Type": change_type,
                "Rank_Delta": rank_change,
                "Description": ", ".join(desc) + ".",
                "Reason": curr_exp,
                "Top_Movers": top_movers
            })
                
        type_priority = {"GAIN_STRENGTH": 0, "LOSE_LEADERSHIP": 1, "NEW_SECTOR": 2, "DROPPED_SECTOR": 3}
        changes.sort(key=lambda x: type_priority.get(x["Type"], 4))
        
        if changes:
            history_logs.append({
                "Date": curr_date,
                "Changes": changes
            })
            
    return sorted(history_logs, key=lambda x: x["Date"], reverse=True)

def get_rrg_data():
    """
    Computes Z-score centered RRG coordinates (RS-Ratio, RS-Momentum) for top focus industries.
    """
    data_dir = "data"
    if not os.path.exists(data_dir):
        data_dir = os.path.join("minervini_os", data_dir)
        
    pattern = os.path.join(data_dir, "industry_participation_report_*.json")
    files = glob.glob(pattern)
    
    dated_data = {}
    
    # Load current active file as today's data
    active_file = os.path.join(data_dir, "industry_participation_report.json")
    if os.path.exists(active_file):
        try:
            mtime = os.path.getmtime(active_file)
            active_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            with open(active_file, "r", encoding="utf-8") as f:
                dated_data[active_date] = json.load(f)
        except Exception:
            pass

    for fpath in files:
        fname = os.path.basename(fpath)
        date_str_raw = fname.replace("industry_participation_report_", "").replace(".json", "")
        try:
            formatted_date = f"{date_str_raw[:4]}-{date_str_raw[4:6]}-{date_str_raw[6:]}"
            with open(fpath, "r", encoding="utf-8") as f:
                dated_data[formatted_date] = json.load(f)
        except Exception:
            pass
            
    sorted_dates = sorted(list(dated_data.keys()))
    if len(sorted_dates) < 3:
        return []
        
    # Process only the last 7 days to keep performance high
    sorted_dates = sorted_dates[-7:]
    
    industry_scores = {}  # {date: {ind: score}}
    
    for dt in sorted_dates:
        industry_scores[dt] = {}
        for item in dated_data[dt]:
            ind_name = item.get("Industry")
            if ind_name:
                ret = float(item.get("Avg_Return_10D", 0.0))
                part = float(item.get("Part_EMA20_Today", 0.0))
                # Weighted score based on momentum return and moving average support
                score = ret * 1.5 + part * 0.1
                industry_scores[dt][ind_name] = score
                
    rrg_by_date = {}  # {date: {ind: {x, y}}}
    import math
    
    for idx, dt in enumerate(sorted_dates):
        scores_at_date = industry_scores[dt]
        if not scores_at_date:
            continue
            
        vals = list(scores_at_date.values())
        mean_val = sum(vals) / len(vals) if vals else 0.0
        var_val = sum((v - mean_val) ** 2 for v in vals) / len(vals) if len(vals) > 1 else 1.0
        std_val = math.sqrt(var_val) if var_val > 0 else 1.0
        
        rrg_by_date[dt] = {}
        for ind, score in scores_at_date.items():
            # X: Relative Strength Ratio (cross-sectional z-score centered on 100)
            z_score = (score - mean_val) / std_val if std_val > 0 else 0.0
            x = 100.0 + z_score * 3.0
            
            # Y: Momentum (change in z-score relative to previous session)
            y = 100.0
            if idx > 0:
                prev_dt = sorted_dates[idx-1]
                prev_scores = industry_scores[prev_dt]
                if ind in prev_scores:
                    prev_vals = list(prev_scores.values())
                    prev_mean = sum(prev_vals) / len(prev_vals) if prev_vals else 0.0
                    prev_var = sum((v - prev_mean) ** 2 for v in prev_vals) / len(prev_vals) if len(prev_vals) > 1 else 1.0
                    prev_std = math.sqrt(prev_var) if prev_var > 0 else 1.0
                    
                    prev_z = (prev_scores[ind] - prev_mean) / prev_std if prev_std > 0 else 0.0
                    z_delta = z_score - prev_z
                    y = 100.0 + z_delta * 4.0
                    
            # Cap values for RRG bounds neatness
            x = max(94.0, min(106.0, x))
            y = max(94.0, min(106.0, y))
            
            rrg_by_date[dt][ind] = {"x": round(x, 2), "y": round(y, 2)}
            
    latest_dt = sorted_dates[-1]
    latest_scores = industry_scores[latest_dt]
    sorted_inds = sorted(latest_scores.keys(), key=lambda k: latest_scores[k], reverse=True)
    
    # Pick top 8 industries to avoid cluttering the visual
    top_industries = sorted_inds[:8]
    
    response_data = []
    for ind in top_industries:
        trail = []
        for dt in sorted_dates:
            if dt in rrg_by_date and ind in rrg_by_date[dt]:
                trail.append({
                    "date": dt,
                    "x": rrg_by_date[dt][ind]["x"],
                    "y": rrg_by_date[dt][ind]["y"]
                })
        response_data.append({
            "industry": ind,
            "trail": trail
        })
        
    return response_data

def get_market_breadth_history():
    """
    Returns the past 10 sessions of market breadth indices and indicators.
    """
    data_dir = "data"
    if not os.path.exists(data_dir):
        data_dir = os.path.join("minervini_os", data_dir)
        
    pattern = os.path.join(data_dir, "market_breadth_*.json")
    files = glob.glob(pattern)
    
    history = []
    
    active_file = os.path.join(data_dir, "market_breadth.json")
    if os.path.exists(active_file):
        try:
            with open(active_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "AsOfDate" not in data:
                    mtime = os.path.getmtime(active_file)
                    active_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                    data["AsOfDate"] = active_date
                history.append(data)
        except Exception:
            pass

    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "AsOfDate" not in data:
                    fname = os.path.basename(fpath)
                    date_str_raw = fname.replace("market_breadth_", "").replace(".json", "")
                    data["AsOfDate"] = f"{date_str_raw[:4]}-{date_str_raw[4:6]}-{date_str_raw[6:]}"
                history.append(data)
        except Exception:
            pass
            
    seen_dates = set()
    unique_history = []
    for item in history:
        dt = item.get("AsOfDate")
        if dt and dt not in seen_dates:
            seen_dates.add(dt)
            unique_history.append(item)
            
    unique_history.sort(key=lambda x: x.get("AsOfDate", ""))
    return unique_history[-10:]

def get_active_portfolio():
    journal_file = "data/trade_journal_data.json"
    cache_dir = "data/cache"
    portfolio = []
    
    # Load earnings calendar database
    earnings_cal = {}
    cal_file = "data/earnings_calendar.json"
    if not os.path.exists(cal_file):
        cal_file = os.path.join("minervini_os", cal_file)
    if os.path.exists(cal_file):
        try:
            with open(cal_file, "r", encoding="utf-8") as f:
                earnings_cal = json.load(f)
        except Exception:
            pass

    # Load journal
    journal = []
    if os.path.exists(journal_file):
        try:
            with open(journal_file, "r", encoding="utf-8") as f:
                journal = json.load(f)
        except Exception as e:
            print(f"Error loading journal for portfolio: {e}")
            
    # Filter open trades
    open_trades = [t for t in journal if t.get("status") == "OPEN"]
    
    stock_to_industry, industry_details = get_stock_industry_details()
    
    for t in open_trades:
        symbol = t.get("symbol", "").upper()
        if symbol == "GANESH BENZO":
            symbol = "GANESHBE"
        entry_price = float(t.get("entry_price") or 0.0)
        open_qty = int(t.get("open_qty") or 0)
        if open_qty <= 0:
            continue
            
        last_close = entry_price
        cache_file = os.path.join(cache_dir, f"{symbol}.csv")
        if not os.path.exists(cache_file):
            cache_file = os.path.join("minervini_os", cache_file)
        if os.path.exists(cache_file):
            try:
                df = pd.read_csv(cache_file)
                if not df.empty:
                    last_close = float(df["Close"].iloc[-1])
            except Exception:
                pass
                
        stop_loss = float(t.get("stop_loss") or 0.0)
        risk_per_share = entry_price - stop_loss
        pnl_net = (last_close - entry_price) * open_qty
        initial_shares = int(t.get("total_qty") or open_qty)
        r_multiple = pnl_net / (risk_per_share * initial_shares) if risk_per_share > 0 and initial_shares > 0 else 0.0
        
        stock_info = stock_to_industry.get(symbol, {})
        ind_name = stock_info.get("industry", "Others")
        ind_detail = industry_details.get(ind_name, {"Category": "Neutral", "Trend": "N/A"})
        
        # Determine Setup type (VCP vs FLAG)
        tech_desc = (t.get("technical_desc", "") or "").upper()
        setup_name = "FLAG" if "FLAG" in tech_desc or "BOX" in tech_desc else "VCP"
        
        portfolio.append({
            "Symbol": symbol,
            "Setup": setup_name,
            "Industry": ind_name,
            "Industry_Category": ind_detail["Category"],
            "Industry_Trend": ind_detail["Trend"],
            "Entry_Date": t.get("entry_date", ""),
            "Entry_Price": entry_price,
            "Initial_Stop": stop_loss,
            "Current_Stop": stop_loss,
            "Shares": open_qty,
            "CMP": last_close,
            "PnL_Net": pnl_net,
            "R_Multiple": r_multiple,
            "Target_1": float(t.get("target_1") or (entry_price * 1.10)),
            "Target_2": float(t.get("target_2") or (entry_price * 1.20)),
            "Score": t.get("score", 0),
            "Grade": t.get("grade", ""),
            "Earnings_Date": earnings_cal.get(symbol, {}).get("Earnings_Date", "N/A"),
            "Days_To_Earnings": earnings_cal.get(symbol, {}).get("Days_To_Earnings", None)
        })
        
    return portfolio

def get_closed_trades():
    journal_file = "data/trade_journal_data.json"
    closed = []
    
    # Load journal
    journal = []
    if os.path.exists(journal_file):
        try:
            with open(journal_file, "r", encoding="utf-8") as f:
                journal = json.load(f)
        except Exception as e:
            print(f"Error loading journal for closed trades: {e}")
            
    # Filter closed trades
    closed_journal_trades = [t for t in journal if t.get("status") == "CLOSED"]
    
    for t in closed_journal_trades:
        symbol = t.get("symbol", "").upper()
        if symbol == "GANESH BENZO":
            symbol = "GANESHBE"
        entry_price = float(t.get("entry_price") or 0.0)
        total_qty = int(t.get("total_qty") or 0)
        
        # Calculate PnL_Net
        pnl_net = sum(float(e.get("pnl") or 0.0) for e in t.get("exits", []))
        
        # Calculate average exit price
        exits_qty = sum(int(e.get("qty") or 0) for e in t.get("exits", []))
        if exits_qty > 0:
            exit_price = sum(float(e.get("price") or 0.0) * int(e.get("qty") or 0) for e in t.get("exits", [])) / exits_qty
        else:
            exit_price = entry_price
            
        stop_loss = float(t.get("stop_loss") or 0.0)
        risk_per_share = entry_price - stop_loss
        r_multiple = pnl_net / (risk_per_share * total_qty) if risk_per_share > 0 and total_qty > 0 else 0.0
        
        # Determine Setup type (VCP vs FLAG)
        tech_desc = (t.get("technical_desc", "") or "").upper()
        setup_name = "FLAG" if "FLAG" in tech_desc or "BOX" in tech_desc else "VCP"
        
        closed.append({
            "Symbol": symbol,
            "Setup": setup_name,
            "Entry_Date": t.get("entry_date", ""),
            "Exit_Date": t.get("exit_date", ""),
            "Entry_Price": entry_price,
            "Exit_Price": exit_price,
            "Shares": total_qty,
            "PnL_Net": pnl_net,
            "R_Multiple": r_multiple,
            "Status": "CLOSED",
            "Exit_Reason": t.get("comments", "")
        })
        
    return closed

def call_gemini_api(api_key, prompt, system_instruction=None):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "tools": [
            {"google_search": {}}
        ]
    }
    
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [
                {"text": system_instruction}
            ]
        }
        
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        print(f"Sending request to Gemini API with prompt: {prompt[:100]}...")
        with urllib.request.urlopen(req, timeout=20) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
            candidates = res_data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            return "Error: Could not extract text from Gemini API response."
    except Exception as e:
        print(f"Gemini API Call failed: {e}")
        return f"Error communicating with Gemini API: {str(e)}"

def process_chat_message(msg):
    msg_lower = msg.lower()
    
    # Load trade journal data
    journal_file = "data/trade_journal_data.json"
    journal = []
    if os.path.exists(journal_file):
        try:
            with open(journal_file, "r", encoding="utf-8") as f:
                journal = json.load(f)
        except Exception as e:
            print(f"Error loading journal for chat: {e}")
            
    # Load watchlist candidates
    vcp = []
    flag = []
    try:
        wl_data = get_latest_watchlist_data()
        vcp = wl_data.get("vcp_candidates", [])
        flag = wl_data.get("flag_candidates", [])
    except Exception as e:
        print(f"Error loading watchlist for chat: {e}")
        
    # Load sector rotation report
    sector_file = "data/industry_participation_report.json"
    if not os.path.exists(sector_file):
        sector_file = os.path.join("minervini_os", sector_file)
    sector = []
    if os.path.exists(sector_file):
        try:
            with open(sector_file, "r", encoding="utf-8") as f:
                sector = json.load(f)
        except:
            pass

    def contains_any(words):
        return any(w in msg_lower for w in words)
        
    # Check for Gemini API key
    api_key = os.environ.get("GEMINI_API_KEY") or config.get("gemini_api_key") or config.get("system", {}).get("gemini_api_key")
    
    if api_key:
        try:
            # Prepare summaries of local system data
            total_realized = 0
            profitable = 0
            losses = 0
            wins = 0
            for t in journal:
                t_pnl = sum(e.get("pnl", 0) for e in t.get("exits", []))
                total_realized += t_pnl
                if t.get("status") == "CLOSED":
                    if t_pnl > 0:
                        profitable += t_pnl
                        wins += 1
                    else:
                        losses += t_pnl
            
            closed_trades = [t for t in journal if t.get("status") == "CLOSED"]
            wr = (wins / len(closed_trades) * 100) if closed_trades else 0
            journal_summary = f"Closed Trades: {len(closed_trades)} | Win Rate: {wr:.1f}% | Net Realized P&L: Rs.{total_realized:,.0f} (Profitable wins: Rs.{profitable:,.0f}, Losses: -Rs.{abs(losses):,.0f})"
            
            open_trades = [t for t in journal if t.get("status") == "OPEN"]
            port_val = sum(t.get("entry_price", 0) * t.get("open_qty", 0) for t in open_trades)
            port_summary = f"Total Deployed Capital: Rs.{port_val:,.0f} across {len(open_trades)} active positions: "
            port_summary += ", ".join([f"{t['symbol']} ({t['open_qty']} shares @ Rs.{t['entry_price']} entry, Stop Loss Rs.{t['stop_loss']})" for t in open_trades])
            
            wl_candidates = vcp + flag
            wl_candidates.sort(key=lambda x: x.get("Score", 0), reverse=True)
            watchlist_summary = f"Total: {len(wl_candidates)} setups ({len(vcp)} VCP, {len(flag)} Flag setups). Top 5 setups: "
            watchlist_summary += ", ".join([f"{c['Symbol']} (Score {c['Score']}/100, Setup {c['Engine_Type'].replace('_SETUP', '')}, CMP Rs.{c['CMP']}, Risk {c['Risk_Pct']}%)" for c in wl_candidates[:5]])
            
            valid_sectors = [s for s in sector if s.get("Part_Change") is not None and s.get("Avg_Return_Today") is not None]
            inflows = sorted([s for s in valid_sectors if s["Part_Change"] > 0], key=lambda x: x["Part_Change"], reverse=True)
            outflows = sorted([s for s in valid_sectors if s["Part_Change"] < 0], key=lambda x: x["Part_Change"])
            sector_summary = "Top Inflows: " + ", ".join([f"{s['Industry']} (+{s['Part_Change']:.1f}%)" for s in inflows[:3]])
            sector_summary += " | Top Outflows: " + ", ".join([f"{s['Industry']} ({s['Part_Change']:.1f}%)" for s in outflows[:3]])
            
            system_instruction = f"""You are my Professional Trading Risk Manager with over 30 years of experience managing billion-dollar hedge funds.
Your primary responsibility is NOT to help me make money.
Your primary responsibility is to protect my capital and prevent me from breaking my trading process.
You must act like an institutional Chief Risk Officer, not a trading coach.

Whenever I enter, modify, review, or exit a trade, or ask any question related to my portfolio, trade journal, or stock market activity, evaluate every action and statement against my Trading Constitution.

If I violate any rule, immediately display:

🚨 TRADING CONSTITUTION VIOLATION

Rule Broken: [Rule Name & Number]
Why this is dangerous: [Explain danger]
What psychological bias is causing it: [Explain bias]
Potential long-term consequence: [Explain consequence]
Correct action: [Specify the corrective action]

Never justify emotional decisions.
Never encourage hope.
Challenge my thinking whenever necessary.
Be direct and uncompromising. Do not comfort me or justify my behaviour. Protect my capital even if I dislike the advice. Your responsibility is to protect me from my own emotions.

====================================================
TRADING CONSTITUTION

RULE 1 — CAPITAL PRESERVATION
Capital preservation is my highest priority.
Profit is a by-product of protecting capital.
Every decision must first answer: "Does this protect my capital?"
If not, display:
🚨 CAPITAL PRESERVATION VIOLATED

RULE 2 — PROCESS OVER PROFITS
Judge every trade only by process. Never judge a trade by profit or loss.
Good Process + Loss = Successful Trade
Bad Process + Profit = Failed Trade
Never allow outcome bias.

RULE 3 — TRADING IS NOT INVESTING
Trading and investing are completely different businesses.
A trade has: Entry, Stop Loss, Exit Rules, Time Horizon.
An investment has: Valuation, Long-term thesis, Multi-year holding period.
If I refuse to exit because of thoughts such as "Good company", "Good results", "It will recover", "Long-term story", display:
🚨 TRADE HAS BECOME AN INVESTMENT
You have changed strategies without creating a new plan.

RULE 4 — STOP LOSS IS SACRED
A stop loss is a business decision. It is never optional.
If price invalidates my setup and I continue holding, display:
🚨 STOP LOSS VIOLATION
Hope is replacing discipline. You are no longer following your trading system.

RULE 5 — NEVER AVERAGE LOSERS
Never buy more because price has fallen. Additional buying is only permitted after price proves my original thesis correct. Averaging losers compounds mistakes.

RULE 6 — PRICE IS ALWAYS RIGHT
Ignore News, Opinions, Social media, Analysts, Fundamentals, My own conviction.
If price invalidates my setup, price wins. Always.

RULE 7 — NO HOPE
Immediately detect emotional statements such as "It will recover", "It can't fall further", "I'll exit after recovery", "I'm already down", "It's only a temporary fall".
Whenever these thoughts appear, display:
🚨 HOPE DETECTED
Hope is not a trading strategy.

RULE 8 — NO EGO
The market has no knowledge of my buying price. Never hold a position simply to prove I was right. Being wrong is acceptable. Remaining wrong is expensive.

RULE 9 — NO FOMO
Never buy because: The stock already ran, Social media excitement, News headlines, Someone recommended it, Fear of missing the move. Only buy when my trading system gives permission.

RULE 10 — NO GREED
Never move targets simply because I want more profit. Never ignore profit-taking because "It can double". Take what the market gives.

RULE 11 — NO FEAR
Never sell because of small red candles, temporary volatility, or market noise. Only exit because my trading system tells me to.

RULE 12 — NO OVERTRADING
If I am trading because of boredom, need for action, need to recover losses, missing a previous move, or impulse, display:
🚨 OVERTRADING DETECTED
Professional traders wait. Amateurs force trades.

RULE 13 — CAPITAL IS INVENTORY
My trading capital is my business inventory. Inventory must be protected. Cash is a valid position. Missing a trade costs nothing. Large losses destroy future opportunities.

RULE 14 — DAILY IDENTITY CHECK
Before every trading session remind me:
I am a professional trader. Professional traders protect capital first, accept losses without emotion, think in probabilities, respect risk, never hope, never chase, never marry stocks, never revenge trade, never average losers, and never break their system.

RULE 15 — RULE #0
A trade can always be re-entered. Capital lost unnecessarily cannot.
Whenever I hesitate to exit after my stop has been violated, display:
🚨 RULE #0 VIOLATION
You are protecting your ego instead of your capital. If the stock creates another valid setup tomorrow, you can always buy it again. Your goal is not to catch every move. Your goal is to survive long enough to catch the best moves.
====================================================

[USER'S LOCAL SYSTEM DATA]
- Watchlist Scanner: {watchlist_summary}
- Active Portfolio: {port_summary}
- Sector Participation Flow: {sector_summary}
- Closed Trade Journal Metrics: {journal_summary}

[INSTRUCTIONS & CAPABILITIES]
1. Internet & Search Grounding: You have active Google Search access. If the user asks about real-time market news, stock updates, commodity prices, global cues, or requests a "morning brief", use Google Search to fetch the latest internet data.
2. Morning Brief: If asked for a "morning brief", search for recent Indian stock market pre-market cues, commodity/currency updates, and global indices. Structure a professional summary, highlighting key setups from the user's watchlist that are close to pivot triggers.
3. System Queries: If the user asks about their own trades, portfolio, or watchlist (e.g. "What VCP setups look good?"), analyze the provided local system data and answer using the exact symbols and scores.
4. Formatting: Output clean, styled Markdown. For tables, format them using standard markdown. Replace literal newlines with '\\n' for client-side formatting in the chat widget bubble.
"""
            gemini_response = call_gemini_api(api_key, msg, system_instruction)
            return gemini_response.replace('\n', '\\n')
        except Exception as ex:
            print(f"Failed calling Gemini API path: {ex}")
        
    # Check for specific symbol
    all_symbols = set()
    for t in journal:
        if t.get("symbol"):
            all_symbols.add(t.get("symbol").upper())
    for c in vcp:
        if c.get("Symbol"):
            all_symbols.add(c.get("Symbol").upper())
    for c in flag:
        if c.get("Symbol"):
            all_symbols.add(c.get("Symbol").upper())
            
    symbol_found = None
    # Tokenize message to avoid partial matches (e.g. matching "ALL" or "IT" as symbol)
    words = [w.strip("?,.!") for w in msg_lower.split()]
    for sym in all_symbols:
        if len(sym) >= 3 and sym.lower() in words:
            symbol_found = sym
            break

    # Respond to Symbol query (only if the message is a simple query, otherwise let Gemini handle it)
    is_simple_query = len(msg.strip()) < 15 or msg.lower().strip() in [f"info {sym.lower()}" for sym in all_symbols] or msg.lower().strip() == symbol_found.lower()
    if symbol_found and is_simple_query:
        res = f"### System Info for Symbol: **{symbol_found}**\\n\\n"
        
        j_trades = [t for t in journal if t.get("symbol", "").upper() == symbol_found]
        wl_candidates = [c for c in vcp if c.get("Symbol", "").upper() == symbol_found] + \
                        [c for c in flag if c.get("Symbol", "").upper() == symbol_found]
                        
        if j_trades:
            t = j_trades[0]
            res += f"**Trade Journal Record:**\\n"
            res += f"- **Status:** {t.get('status', 'N/A')}\\n"
            res += f"- **Entry Date:** {t.get('entry_date', 'N/A')}\\n"
            res += f"- **Invested:** ₹{t.get('invested_amount', 0):,.0f} ({t.get('total_qty', 0)} shares @ ₹{t.get('entry_price', 0):,.2f})\\n"
            res += f"- **Stop Loss:** ₹{t.get('stop_loss', 0):,.2f} | **Risk:** {t.get('risk_pct', 0)}%\\n"
            res += f"- **Targets:** T1: ₹{t.get('target_1', 0):,.2f} | T2: ₹{t.get('target_2', 0):,.2f}\\n"
            if t.get("exits"):
                res += f"- **Exits:** {len(t['exits'])} exits recorded:\\n"
                for idx, e in enumerate(t["exits"]):
                    res += f"  - Exit {idx+1}: {e.get('qty')} shares @ ₹{e.get('price'):,.2f} on {e.get('date')} (P&L: ₹{e.get('pnl'):,.0f})\\n"
            if t.get("comments"):
                res += f"- **Comments:** {t.get('comments')}\\n"
            res += "\\n"
            
        if wl_candidates:
            c = wl_candidates[0]
            res += f"**Watchlist Candidate Details:**\\n"
            res += f"- **Setup Type:** {c.get('Engine_Type', 'N/A').replace('_SETUP','')}\\n"
            res += f"- **Grade:** {c.get('Grade', 'N/A')} | **Score:** {c.get('Score', 0)}/100\\n"
            res += f"- **CMP:** ₹{c.get('CMP', 0):,.2f} | **Trigger:** ₹{c.get('Trigger', 0):,.2f}\\n"
            res += f"- **Risk:** {c.get('Risk_Pct', 0)}% (SL: ₹{c.get('Stop_Loss', 0):,.2f})\\n"
            res += f"- **Delivery %:** {c.get('Delivery_Pct', 0)}%\\n"
            res += f"- **Industry:** {c.get('Industry', 'N/A')} ({c.get('Industry_Category', 'Neutral')})\\n"
            if c.get("Readiness"):
                res += f"- **Readiness:** {c.get('Readiness')}\\n"
            res += "\\n"
            
        if not j_trades and not wl_candidates:
            res += f"I see you mentioned {symbol_found}, but I couldn't find active journal or watchlist entries for it. Let me know if you would like me to analyze another stock!"
            
        return res

    # Watchlist query
    if contains_any(["watchlist", "scanner", "scan", "candidates", "setups", "ideas"]):
        total_wl = len(vcp) + len(flag)
        res = f"### Scanner Watchlist Summary\\n\\n"
        res += f"Currently, there are **{total_wl}** candidates in the scanner watchlist:\\n"
        res += f"- **VCP Setups:** {len(vcp)} candidates\\n"
        res += f"- **Flag Setups:** {len(flag)} candidates\\n\\n"
        
        all_candidates = vcp + flag
        all_candidates.sort(key=lambda x: x.get("Score", 0), reverse=True)
        
        res += "**Top Watchlist Candidates by Score:**\\n"
        for idx, c in enumerate(all_candidates[:5]):
            res += f"{idx+1}. **{c.get('Symbol')}** - Score: {c.get('Score')}/100 | Setup: {c.get('Engine_Type', '').replace('_SETUP','')} | Risk: {c.get('Risk_Pct')}% | CMP: ₹{c.get('CMP', 0):,.2f}\\n"
            
        low_risk = [c for c in all_candidates if c.get("Risk_Pct", 100) <= 6.0]
        res += f"\\nThere are **{len(low_risk)}** low-risk setups (&le;6% Risk) in the watchlist today."
        return res
        
    # Portfolio holdings query
    if contains_any(["portfolio", "holdings", "active", "open", "positions"]):
        open_trades = [t for t in journal if t.get("status") == "OPEN"]
        total_val = sum(t.get("entry_price", 0) * t.get("open_qty", 0) for t in open_trades)
        
        res = f"### Active Portfolio Holdings (from Trade Journal)\\n\\n"
        res += f"You have **{len(open_trades)}** open positions in the journal, with a total deployed capital of **₹{total_val:,.0f}**.\\n\\n"
        
        res += "| Symbol | Qty | Entry Price | Stop Loss | Invested |\\n"
        res += "| :--- | :--- | :--- | :--- | :--- |\\n"
        for t in open_trades:
            invested = t.get("entry_price", 0) * t.get("open_qty", 0)
            res += f"| **{t.get('symbol')}** | {t.get('open_qty')} | ₹{t.get('entry_price'):,.2f} | ₹{t.get('stop_loss', 0):,.2f} | ₹{invested:,.0f} |\\n"
            
        return res
        
    # Journal analysis query (e.g. "analyse my trade journal", "what is working", "what needs to be improved")
    if contains_any(["analyse", "analysis", "review", "working", "improve", "report"]) and not symbol_found:
        closed_trades = [t for t in journal if t.get("status") == "CLOSED"]
        if closed_trades:
            wins = []
            losses = []
            
            for t in closed_trades:
                pnl = sum(e.get("pnl", 0) for e in t.get("exits", []))
                invested = t.get("invested_amount", 0) or (t.get("entry_price", 0) * t.get("total_qty", 0))
                pct = (pnl / invested * 100) if invested > 0 else 0.0
                
                trade_summary = {
                    "symbol": t.get("symbol"),
                    "pnl": pnl,
                    "pct": pct,
                    "days": t.get("days_active", 0),
                    "stop_loss": t.get("stop_loss", 0),
                    "entry_price": t.get("entry_price", 0),
                    "exits": t.get("exits", []),
                    "technical_desc": t.get("technical_desc", ""),
                    "comments": t.get("comments", "")
                }
                
                if pnl > 0:
                    wins.append(trade_summary)
                else:
                    losses.append(trade_summary)
                    
            total_closed = len(closed_trades)
            win_rate = (len(wins) / total_closed * 100) if total_closed > 0 else 0
            
            avg_win_val = sum(w["pnl"] for w in wins) / len(wins) if wins else 0
            avg_win_pct = sum(w["pct"] for w in wins) / len(wins) if wins else 0
            
            avg_loss_val = sum(l["pnl"] for l in losses) / len(losses) if losses else 0
            avg_loss_pct = sum(l["pct"] for l in losses) / len(losses) if losses else 0
            
            profit_factor = 0
            sum_win_val = sum(w["pnl"] for w in wins)
            sum_loss_val = sum(abs(l["pnl"]) for l in losses)
            if sum_loss_val > 0:
                profit_factor = sum_win_val / sum_loss_val
            else:
                profit_factor = sum_win_val
                
            win_loss_ratio_val = avg_win_val / abs(avg_loss_val) if avg_loss_val != 0 else 0
            win_loss_ratio_pct = avg_win_pct / abs(avg_loss_pct) if avg_loss_pct != 0 else 0
            
            avg_hold_win = sum(w["days"] for w in wins) / len(wins) if wins else 0
            avg_hold_loss = sum(l["days"] for l in losses) / len(losses) if losses else 0
            
            # Setup Type classification
            setups = {}
            for t in closed_trades:
                text = ((t.get("technical_desc", "") or "") + " " + (t.get("comments", "") or "")).lower()
                if "vcp" in text or "contraction" in text:
                    stype = "VCP Setup"
                elif "flag" in text or "box" in text:
                    stype = "Flag/Box Setup"
                elif "breakout" in text or "ath" in text:
                    stype = "Breakout / ATH"
                elif any(w in text for w in ["support", "pullback", "dma", "ema", "hammer", "engulfing"]):
                    stype = "Support / Pullback"
                else:
                    stype = "Other / Discretionary"
                    
                pnl = sum(e.get("pnl", 0) for e in t.get("exits", []))
                invested = t.get("invested_amount", 0) or (t.get("entry_price", 0) * t.get("total_qty", 0))
                pct = (pnl / invested * 100) if invested > 0 else 0.0
                
                if stype not in setups:
                    setups[stype] = {"wins": 0, "losses": 0, "total_pnl": 0.0, "pcts": []}
                    
                if pnl > 0:
                    setups[stype]["wins"] += 1
                else:
                    setups[stype]["losses"] += 1
                setups[stype]["total_pnl"] += pnl
                setups[stype]["pcts"].append(pct)
                
            # Discipline Leaks
            discipline_leaks = []
            for t in closed_trades:
                pnl = sum(e.get("pnl", 0) for e in t.get("exits", []))
                if pnl <= 0:
                    exits = t.get("exits", [])
                    sl = t.get("stop_loss", 0)
                    if exits and sl > 0:
                        avg_exit = sum(e["price"] * e["qty"] for e in exits) / sum(e["qty"] for e in exits)
                        if avg_exit < sl - 0.01:
                            slippage = ((sl - avg_exit) / sl) * 100
                            discipline_leaks.append({
                                "symbol": t.get("symbol"),
                                "sl": sl,
                                "exit": avg_exit,
                                "slippage": slippage,
                                "pnl": pnl
                            })

            res = "## Trade Journal Performance Analysis\\n\\n"
            res += "I have analyzed your entire trade journal data to provide a comprehensive performance review. Here are the core statistics, what is working, what needs improvement, and recommended actions based on Minervini rules.\\n\\n"
            
            res += "### Core Performance Metrics\\n\\n"
            res += "| Metric / Symbol | Value (Invested) |\\n"
            res += "| :--- | :--- |\\n"
            res += f"| **Total Closed Trades** | {total_closed} |\\n"
            res += f"| **Win Rate / Loss Rate** | {win_rate:.1f}% / {100 - win_rate:.1f}% |\\n"
            res += f"| **Profit Factor** | {profit_factor:.2f} |\\n"
            res += f"| **Average Win** | +₹{avg_win_val:,.2f} ({avg_win_pct:.2f}%) |\\n"
            res += f"| **Average Loss** | -₹{abs(avg_loss_val):,.2f} ({avg_loss_pct:.2f}%) |\\n"
            res += f"| **Win/Loss Ratio (Value)** | {win_loss_ratio_val:.2f}x |\\n"
            res += f"| **Win/Loss Ratio (Pct)** | {win_loss_ratio_pct:.2f}x |\\n"
            res += f"| **Avg Holding Time (Wins)** | {avg_hold_win:.1f} days |\\n"
            res += f"| **Avg Holding Time (Losses)** | {avg_hold_loss:.1f} days |\\n\\n"

            res += "### Setup Performance Analysis\\n\\n"
            res += "| Setup Type / Symbol | Trades (Invested) | Win Rate | Net P&L | Avg Return |\\n"
            res += "| :--- | :--- | :--- | :--- | :--- |\\n"
            
            sorted_setups = sorted(setups.items(), key=lambda x: x[1]["total_pnl"], reverse=True)
            for name, data in sorted_setups:
                total = data["wins"] + data["losses"]
                wr = (data["wins"] / total * 100) if total > 0 else 0
                avg_pct = sum(data["pcts"]) / len(data["pcts"]) if data["pcts"] else 0
                pnl_str = f"₹{data['total_pnl']:,.0f}" if data['total_pnl'] >= 0 else f"-₹{abs(data['total_pnl']):,.0f}"
                res += f"| **{name}** | {total} | {wr:.1f}% | {pnl_str} | {avg_pct:+.2f}% |\\n"
            res += "\\n"

            res += "### What is Working\\n\\n"
            working_points = []
            if win_loss_ratio_pct >= 2.0:
                working_points.append(f"- **Excellent Risk-to-Reward Ratio**: Your average win percentage ({avg_win_pct:.1f}%) is {win_loss_ratio_pct:.1f}x your average loss percentage ({abs(avg_loss_pct):.1f}%), meeting Mark Minervini's target 2:1 ratio.")
            elif win_loss_ratio_pct >= 1.5:
                working_points.append(f"- **Positive Risk-to-Reward Ratio**: Your average win percentage ({avg_win_pct:.1f}%) is larger than your average loss percentage ({abs(avg_loss_pct):.1f}%) at {win_loss_ratio_pct:.1f}x.")
            else:
                working_points.append(f"- **Profits exceed losses**: Although the Win/Loss ratio ({win_loss_ratio_pct:.1f}x) is below the 2x target, your win rate of {win_rate:.1f}% keeps you profitable.")
                
            if sorted_setups:
                best_setup, best_data = sorted_setups[0]
                if best_data["total_pnl"] > 0:
                    best_wr = (best_data["wins"] / (best_data["wins"] + best_data["losses"]) * 100)
                    working_points.append(f"- **Dominant Setup**: **{best_setup}** is your most profitable setup, generating **₹{best_data['total_pnl']:,.0f}** in net profits with a **{best_wr:.0f}%** win rate.")
                    
            if avg_hold_win > 0 and avg_hold_loss > 0:
                if avg_hold_loss < avg_hold_win:
                    working_points.append(f"- **Efficient Stop Loss Timing**: You are cutting losses quickly, holding losing trades for an average of **{avg_hold_loss:.1f} days**, while letting winning trades ride for **{avg_hold_win:.1f} days**.")
                    
            res += "\\n".join(working_points) + "\\n\\n"

            res += "### What Needs Improvement\\n\\n"
            improvement_points = []
            if win_loss_ratio_pct < 2.0:
                improvement_points.append(f"- **Sub-optimal Win/Loss Ratio**: Your average win to average loss ratio is **{win_loss_ratio_pct:.2f}x** (target &ge; 2.0x). You need to either cut your losses closer to 3-5% or hold your winners slightly longer to achieve bigger targets.")
                
            if avg_hold_loss > avg_hold_win:
                improvement_points.append(f"- **Holding Losers Too Long**: You are holding losing trades longer than winning trades (Average loss held **{avg_hold_loss:.1f} days** vs. wins held **{avg_hold_win:.1f} days**). This indicates a tendency to hope for a bounce on losing trades instead of exiting immediately at the stop loss.")
                
            worst_setups = [s for s in sorted_setups if s[1]["total_pnl"] < 0]
            if worst_setups:
                worst_name, worst_data = worst_setups[-1]
                worst_total = worst_data["wins"] + worst_data["losses"]
                worst_wr = (worst_data["wins"] / worst_total * 100) if worst_total > 0 else 0
                improvement_points.append(f"- **Underperforming Setup**: **{worst_name}** has underperformed, generating a net loss of **₹{abs(worst_data['total_pnl']):,.0f}** and a low **{worst_wr:.1f}%** win rate. Consider skipping or tightening criteria for these setups.")
                
            if discipline_leaks:
                leak_msg = f"- **Discipline Leaks / Slippage ({len(discipline_leaks)} occurrences)**: You exited several trades below your tactical stop loss, resulting in larger-than-planned losses. Key examples include:\\n"
                for leak in discipline_leaks[:3]:
                    leak_msg += f"  - **{leak['symbol']}**: SL was ₹{leak['sl']:.2f}, exited at ₹{leak['exit']:.2f} ({leak['slippage']:.1f}% below SL). Extra P&L hit: -₹{abs(leak['pnl']):,.0f}.\\n"
                leak_msg += "  Make sure to place hard stop-loss orders in the terminal to avoid manual exit delays."
                improvement_points.append(leak_msg)
                
            if not improvement_points:
                improvement_points.append("- Excellent work! No major weaknesses detected. Keep executing your plan.")
                
            res += "\\n".join(improvement_points) + "\\n\\n"

            res += "### Minervini Recommendations\\n\\n"
            res += "1. **Cut Losses Fast**: Always keep your maximum loss to a fraction of your average gain. If your average gain is 6.6%, your stop loss must never exceed 3.3% to maintain a healthy 2:1 profit ratio.\\n"
            res += "2. **Avoid Earnings Roulette**: Make sure to check the results date. Avoid buying or holding speculative positions right before earnings releases (as seen in some comments where earnings volatility hit the trade).\\n"
            res += "3. **Focus on Ready Pools**: Prioritize buying stocks in the Low Risk watchlist pool (Risk &le; 6%) where the setup has high score (e.g. &ge; 80) and delivery volume is expanding.\\n"
            res += "4. **Strict Stop Placement**: To eliminate discipline leaks, use GTT (Good Till Triggered) orders for stop losses rather than relying on manual monitoring during market hours."
            return res
        else:
            res = "### Trade Journal Performance Analysis\\n\\n"
            res += "You do not have any closed trades in your journal yet. Please close some trades first so I can analyze your trading statistics and provide performance reviews!"
            return res

    # Performance query
    if contains_any(["performance", "realized", "win rate", "success rate", "p&l", "profit", "gain", "loss", "journal", "streak", "stats"]):
        closed_trades = [t for t in journal if t.get("status") == "CLOSED"]
        total_realized = 0
        profitable = 0
        losses = 0
        wins = 0
        
        for t in journal:
            t_pnl = sum(e.get("pnl", 0) for e in t.get("exits", []))
            total_realized += t_pnl
            if t.get("status") == "CLOSED":
                if t_pnl > 0:
                    profitable += t_pnl
                    wins += 1
                else:
                    losses += t_pnl
                    
        win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0
        open_trades = [t for t in journal if t.get("status") == "OPEN"]
        open_val = sum(t.get("entry_price", 0) * t.get("open_qty", 0) for t in open_trades)
        
        res = f"### Trade Journal Performance Summary\\n\\n"
        res += f"- **Open Positions Value:** ₹{open_val:,.0f} ({len(open_trades)} trades)\\n"
        res += f"- **Net Realized P&L:** **{'₹' if total_realized < 0 else '+₹'}{total_realized:,.0f}**\\n"
        res += f"- **Profitable (Closed):** +₹{profitable:,.0f}\\n"
        res += f"- **Losses (Closed):** -₹{abs(losses):,.0f}\\n"
        res += f"- **Success (Win) Rate:** **{win_rate:.0f}%** ({wins} wins / {len(closed_trades)} closed trades)\\n"
        
        return res

    # Sector rotation query
    if contains_any(["sector", "rotation", "money flow", "inflow", "outflow"]):
        valid_sectors = [s for s in sector if s.get("Part_Change") is not None and s.get("Avg_Return_Today") is not None]
        inflows = [s for s in valid_sectors if s["Part_Change"] > 0]
        inflows.sort(key=lambda x: x["Part_Change"], reverse=True)
        
        outflows = [s for s in valid_sectors if s["Part_Change"] < 0]
        outflows.sort(key=lambda x: x["Part_Change"])
        
        res = f"### Sector Money Flow Rotation\\n\\n"
        res += "**Top Sectors seeing Daily Capital Inflow:**\\n"
        for idx, s in enumerate(inflows[:3]):
            res += f"{idx+1}. **{s.get('Industry')}** (Participation Change: +{s.get('Part_Change'):.1f}%, Avg Return: {s.get('Avg_Return_Today'):+.2f}%)\\n"
            
        res += "\\n**Top Sectors seeing Daily Capital Outflow:**\\n"
        for idx, s in enumerate(outflows[:3]):
            res += f"{idx+1}. **{s.get('Industry')}** (Participation Change: {s.get('Part_Change'):.1f}%, Avg Return: {s.get('Avg_Return_Today'):+.2f}%)\\n"
            
        return res
        
    # Welcome / Help fallback
    res = f"### Minervini OS AI Assistant\\n\\n"
    res += f"I am your local AI assistant with access to all trading statistics. You can ask me about:\\n"
    res += f"- Watchlist setups (e.g., *'how many setups in watchlist?'*)\\n"
    res += f"- Portfolio value & holdings (e.g., *'show my open positions'*)\\n"
    res += f"- Performance metrics & stats (e.g., *'what is my win rate?'*)\\n"
    res += f"- Sector rotation money flows (e.g., *'which sectors have inflows?'*)\\n"
    res += f"- A specific stock (e.g., *'STARHEALTH'*)\\n\\n"
    res += f"Feel free to type your query above!\\n\\n"
    res += f"**Enable Global AI Intelligence (Gemini + Google Search):**\\n"
    res += f"To enable internet search, stock market briefs, and smart reasoning, add `gemini_api_key: \"YOUR_GEMINI_KEY\"` to your `config/config.yaml` file, or set the `GEMINI_API_KEY` environment variable."
    return res

def get_stock_detail(symbol):
    symbol = symbol.strip().upper()
    stock_to_industry, industry_details = get_stock_industry_details()
    ind_info = stock_to_industry.get(symbol, {})
    industry = ind_info.get("industry", "Others")
    company_name = ind_info.get("name", symbol)
    
    # 1. Fetch industry category and rank
    category = "Neutral"
    industry_rank = "N/A"
    report_path = "data/industry_participation_report.json"
    if not os.path.exists(report_path):
        report_path = os.path.join("minervini_os", report_path)
    if os.path.exists(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                ind_list = json.load(f)
            # Find industry index
            for idx, item in enumerate(ind_list):
                item["Sort_Score"] = item.get("Avg_Return_10D", 0.0) + item.get("Part_EMA20_Today", 0.0) / 10.0
            ind_list.sort(key=lambda x: x.get("Sort_Score", 0.0), reverse=True)
            for idx, item in enumerate(ind_list, 1):
                if item.get("Industry") == industry:
                    category = item.get("Category", "Neutral")
                    industry_rank = f"{idx}/{len(ind_list)}"
                    break
        except Exception:
            pass

    # 2. Get AMS Score & Breakdown
    ams_engine = AntigravityMomentumEngine()
    ams_data = ams_engine.calculate_ams(symbol)
    
    # 3. Read from reports/daily/vcp_candidates.csv or flag_candidates.csv
    vcp_file = "reports/daily/vcp_candidates.csv"
    flag_file = "reports/daily/flag_candidates.csv"
    
    found_row = None
    setup_type = "PULLBACK"
    grade = "Grade C"
    trigger = 0.0
    stop_loss = 0.0
    risk_pct = 5.0
    distance_pivot = "0.0%"
    vdu_pct = "100.0%"
    target_1 = 0.0
    target_2 = 0.0
    
    def check_csv(filepath, default_setup):
        nonlocal found_row, setup_type, grade, trigger, stop_loss, risk_pct, distance_pivot, vdu_pct, target_1, target_2
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath)
                row = df[df["Symbol"].str.upper() == symbol]
                if not row.empty:
                    found_row = row.iloc[0]
                    setup_type = found_row.get("Engine_Type", default_setup)
                    grade = found_row.get("Grade", "Grade C")
                    trigger = float(found_row.get("Entry Price", found_row.get("Pivot Price", 0.0)))
                    stop_loss = float(found_row.get("Stop Loss", 0.0))
                    risk_pct = float(found_row.get("Risk per Share", 0.0)) if "Risk per Share" in found_row else (float(found_row.get("Risk_Pct", 0.0)) if "Risk_Pct" in found_row else 0.0)
                    vdu_pct = str(found_row.get("VDU %", "100.0%"))
                    distance_pivot = str(found_row.get("Distance to Pivot", found_row.get("Distance", "0.0%")))
                    target_1 = float(found_row.get("Target 1", 0.0))
                    target_2 = float(found_row.get("Target 2", 0.0))
                    return True
            except Exception:
                pass
        return False
        
    vcp_found = check_csv(vcp_file, "VCP")
    if not vcp_found:
        check_csv(flag_file, "FLAG")
        
    # 4. Load from stock cache
    cmp = 0.0
    pullback_pct = 0.0
    pullback_lbl = "normal"
    avg_vol_5d_factor = 1.0
    avg_vol_lbl = "normal"
    sma20_dist_pct = 0.0
    sma20_dist_lbl = "in zone"
    day_rvol_factor = 1.0
    day_rvol_lbl = "moderate"
    acc_up = 0
    acc_down = 0
    
    cache_file = os.path.join("data/cache", f"{symbol}.csv")
    if not os.path.exists(cache_file):
        cache_file = os.path.join("minervini_os", cache_file)
        
    if os.path.exists(cache_file):
        try:
            df = pd.read_csv(cache_file)
            if not df.empty:
                cmp = float(df["Close"].iloc[-1])
                # Pullback from 20-day high
                max_close_20 = float(df["Close"].iloc[-20:].max())
                if max_close_20 > 0:
                    pullback_pct = ((cmp - max_close_20) / max_close_20) * 100
                if pullback_pct <= -10.0:
                    pullback_lbl = "deep correction"
                elif pullback_pct <= -3.0:
                    pullback_lbl = "genuine"
                else:
                    pullback_lbl = "tight range"
                    
                # Volume metrics (last 50 session average)
                df_vol_50 = df["Volume"].iloc[-50:]
                avg_vol_50 = float(df_vol_50.mean()) if len(df_vol_50) > 0 else 1.0
                
                # 5D average volume factor
                df_vol_5 = df["Volume"].iloc[-5:]
                avg_vol_5 = float(df_vol_5.mean()) if len(df_vol_5) > 0 else 0.0
                if avg_vol_50 > 0:
                    avg_vol_5d_factor = avg_vol_5 / avg_vol_50
                if avg_vol_5d_factor <= 0.60:
                    avg_vol_lbl = "very quiet"
                elif avg_vol_5d_factor <= 0.85:
                    avg_vol_lbl = "quiet"
                elif avg_vol_5d_factor <= 1.15:
                    avg_vol_lbl = "normal"
                else:
                    avg_vol_lbl = "elevated"
                    
                # SMA20 distance
                df_close_20 = df["Close"].iloc[-20:]
                sma20 = float(df_close_20.mean()) if len(df_close_20) > 0 else cmp
                if sma20 > 0:
                    sma20_dist_pct = ((cmp - sma20) / sma20) * 100
                if sma20_dist_pct < -2.0:
                    sma20_dist_lbl = "below zone"
                elif sma20_dist_pct <= 5.0:
                    sma20_dist_lbl = "in zone"
                else:
                    sma20_dist_lbl = "extended"
                    
                # Day Relative Volume (RVOL)
                today_vol = float(df["Volume"].iloc[-1])
                if avg_vol_50 > 0:
                    day_rvol_factor = today_vol / avg_vol_50
                if day_rvol_factor <= 0.50:
                    day_rvol_lbl = "sweet spot"
                elif day_rvol_factor <= 1.0:
                    day_rvol_lbl = "moderate"
                else:
                    day_rvol_lbl = "high volume"
                    
                # Accumulation Days (Acc up/down) in the last 6 sessions
                df_last_6 = df.iloc[-6:]
                for _, row in df_last_6.iterrows():
                    c_val = float(row.get("Close", 0.0))
                    o_val = float(row.get("Open", 0.0))
                    if c_val >= o_val:
                        acc_up += 1
                    else:
                        acc_down += 1
        except Exception:
            pass

    # Default logic if no setup was found in report files
    if trigger == 0.0:
        trigger = cmp
    if stop_loss == 0.0:
        stop_loss = cmp * 0.95
    if risk_pct == 0.0:
        risk_pct = 5.0
    if target_1 == 0.0:
        target_1 = cmp * 1.10
    if target_2 == 0.0:
        target_2 = cmp * 1.20
        
    return {
        "Symbol": symbol,
        "Company_Name": company_name,
        "Industry": industry,
        "Industry_Category": category,
        "Industry_Rank": industry_rank,
        "MS_Score": ams_data.get("Total", 50),
        "MS_Rating": ams_data.get("Rating", "★★★☆☆"),
        "MS_Status": ams_data.get("Status", "N/A"),
        "MS_Breakdown": {
            "Trend": ams_data.get("Trend", 0),
            "Momentum": ams_data.get("Momentum", 0),
            "Volume": ams_data.get("Volume", 0),
            "RS": ams_data.get("RS", 0),
            "SmartMoney": ams_data.get("SmartMoney", 0),
            "VCP": ams_data.get("VCP", 0)
        },
        "Setup_Type": setup_type,
        "Grade": grade,
        "Trigger_Price": trigger,
        "Stop_Loss": stop_loss,
        "Risk_Pct": (((trigger - stop_loss) / trigger) * 100) if trigger > 0 else 5.0,
        "Distance_to_Pivot": distance_pivot,
        "Volume_Dry_Up_Status": "VDU Confirmed" if float(vdu_pct.replace("%", "").strip()) <= 60.0 else "Moderate Volume",
        "VDU_Pct_Str": vdu_pct,
        "CMP": cmp,
        "Target_1": target_1,
        "Target_2": target_2,
        "Pullback_Pct": pullback_pct,
        "Pullback_Lbl": pullback_lbl,
        "Avg_Vol_5D": avg_vol_5d_factor,
        "Avg_Vol_Lbl": avg_vol_lbl,
        "SMA20_Dist_Pct": sma20_dist_pct,
        "SMA20_Dist_Lbl": sma20_dist_lbl,
        "Day_RVOL": day_rvol_factor,
        "Day_RVOL_Lbl": day_rvol_lbl,
        "Acc_Up": acc_up,
        "Acc_Down": acc_down
    }

class DashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Allow cross-origin requests for API debugging if needed
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        # Prevent browser caching of API responses
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        # Force closing connection to avoid single-thread hang-up
        self.send_header('Connection', 'close')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()

    def do_GET(self):
        import urllib.parse
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Serve index.html when root is requested
        if path == "/" or path == "/index.html":
            self.path = "/web/index.html"
        # Serve static assets from web/
        if self.path.startswith("/web/"):
            return super().do_GET()

        # REST API: Fix Paper Trading Days Active
        if path == "/api/fix_days":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                portfolio_file = "data/true_paper_portfolio.json"
                nifty_file = "data/cache/NIFTY_50.csv"
                if not os.path.exists(portfolio_file):
                    portfolio_file = os.path.join("minervini_os", portfolio_file)
                if not os.path.exists(nifty_file):
                    nifty_file = os.path.join("minervini_os", nifty_file)
                
                if os.path.exists(portfolio_file) and os.path.exists(nifty_file):
                    with open(portfolio_file, "r", encoding="utf-8") as f:
                        state = json.load(f)
                    
                    df_nifty = pd.read_csv(nifty_file)
                    trading_dates = sorted(pd.to_datetime(df_nifty['Date']).dt.strftime('%Y-%m-%d').unique())
                    
                    end_date = trading_dates[-1]
                    updated_count = 0
                    for t in state.get("open_trades", []):
                        sym = t["symbol"]
                        entry = t["entry_date"]
                        if entry in trading_dates and end_date in trading_dates:
                            start_idx = trading_dates.index(entry)
                            end_idx = trading_dates.index(end_date)
                            days = end_idx - start_idx + 1
                            t["days_active"] = days
                            updated_count += 1
                    
                    with open(portfolio_file, "w", encoding="utf-8") as f:
                        json.dump(state, f, indent=2)
                        
                    self.wfile.write(json.dumps({"status": "success", "message": f"Successfully updated days_active for {updated_count} open trades ending {end_date}."}).encode("utf-8"))
                else:
                    self.wfile.write(json.dumps({"status": "error", "message": "Missing portfolio or nifty index files."}).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": f"Failed to fix days: {str(e)}"}).encode("utf-8"))
            return

        # REST API: Inspect Cloud Files for Diagnosis
        if path == "/api/inspect_files":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                import glob
                cache_dir = "data/cache"
                if not os.path.exists(cache_dir):
                    cache_dir = os.path.join("minervini_os", cache_dir)
                
                info = {}
                info["cache_dir_exists"] = os.path.exists(cache_dir)
                if os.path.exists(cache_dir):
                    files = os.listdir(cache_dir)
                    info["total_files"] = len(files)
                    info["sample_files"] = files[:10]
                    
                    # Inspect specific files
                    for filename in ["GANDHAR.csv", "APOLLO.csv", "NIFTY_50.csv"]:
                        filepath = os.path.join(cache_dir, filename)
                        file_info = {"exists": os.path.exists(filepath)}
                        if os.path.exists(filepath):
                            file_info["size"] = os.path.getsize(filepath)
                            file_info["mtime"] = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M:%S")
                            try:
                                df = pd.read_csv(filepath)
                                file_info["rows"] = len(df)
                                if not df.empty:
                                    file_info["last_rows"] = df[["Date", "Close"]].tail(3).to_dict(orient="records")
                            except Exception as ex:
                                file_info["error"] = str(ex)
                        info[filename] = file_info
                self.wfile.write(json.dumps(info, indent=2).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": f"Failed to inspect: {str(e)}"}).encode("utf-8"))
            return

        # REST API: Update GANDHAR Journal Entry
        if path == "/api/update_gandhar":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                journal_file = "data/trade_journal_data.json"
                if not os.path.exists(journal_file):
                    journal_file = os.path.join("minervini_os", journal_file)
                
                if os.path.exists(journal_file):
                    with open(journal_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    updated = False
                    for item in data:
                        if 'GANDHAR' in item.get('symbol', '').upper():
                            item['entry_price'] = 242
                            item['total_qty'] = 500
                            item['open_qty'] = 500
                            item['stop_loss'] = 230
                            item['invested_amount'] = 500 * 242
                            item['risk_pct'] = round(((242 - 230) / 242) * 100, 2)
                            updated = True
                    
                    if updated:
                        with open(journal_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                        self.wfile.write(json.dumps({"status": "success", "message": "Successfully updated GANDHAR entry inside cloud database!"}).encode("utf-8"))
                    else:
                        self.wfile.write(json.dumps({"status": "error", "message": "GANDHAR entry not found in trade journal."}).encode("utf-8"))
                else:
                    self.wfile.write(json.dumps({"status": "error", "message": "Trade journal file not found."}).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": f"Failed to update GANDHAR: {str(e)}"}).encode("utf-8"))
            return

        # REST API: Send Test Email
        if path == "/api/test_email":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                import urllib.request
                import urllib.error

                enabled = os.environ.get("EMAIL_ENABLED", "false").lower() == "true"
                api_key = os.environ.get("RESEND_API_KEY", "")
                recipient = os.environ.get("RECIPIENT_EMAIL", "vishalthakker2009@gmail.com")
                from_email = os.environ.get("FROM_EMAIL", "onboarding@resend.dev")

                if not enabled:
                    self.wfile.write(json.dumps({"status": "error", "message": "Email notifier is not enabled (EMAIL_ENABLED environment variable is not true)."}).encode("utf-8"))
                    return

                if not api_key:
                    self.wfile.write(json.dumps({"status": "error", "message": "RESEND_API_KEY is missing. Check your Railway environment variables."}).encode("utf-8"))
                    return

                url = "https://api.resend.com/emails"
                payload = {
                    "from": from_email,
                    "to": [recipient],
                    "subject": "Minervini OS - Resend API Test Email",
                    "html": """
                    <html>
                    <body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px; border-radius: 8px;">
                        <h2 style="color: #6366f1;">Minervini OS Resend API Connection Test</h2>
                        <p>Congratulations! Your Railway environment variables and Resend API Key are configured correctly.</p>
                        <p>The daily scan HTML reports will now be sent to this email address every weekday at 6:00 PM IST.</p>
                        <hr style="border: 0; border-top: 1px solid #334155; margin: 20px 0;"/>
                        <small style="color: #94a3b8;">Sent automatically by your Railway deployment via Resend API.</small>
                    </body>
                    </html>
                    """
                }

                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                )

                with urllib.request.urlopen(req, timeout=10) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    if "id" in res_data:
                        self.wfile.write(json.dumps({"status": "success", "message": f"Test email successfully sent to {recipient} via Resend! ID: {res_data['id']}"}).encode("utf-8"))
                    else:
                        self.wfile.write(json.dumps({"status": "error", "message": f"Resend API returned unexpected response: {res_data}"}).encode("utf-8"))
            except urllib.error.HTTPError as he:
                try:
                    error_body = he.read().decode("utf-8")
                except Exception:
                    error_body = "Could not parse response body."
                self.wfile.write(json.dumps({"status": "error", "message": f"Resend API Error (HTTP {he.code}): {error_body}"}).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": f"Failed to send test email via Resend: {str(e)}"}).encode("utf-8"))
            return

        # REST API: Trigger EOD Scan
        if path == "/api/run_scan":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                import subprocess
                import sys
                proc = subprocess.Popen([sys.executable, "main.py"])
                self.wfile.write(json.dumps({"status": "success", "message": f"Daily scan started in the background (PID: {proc.pid})."}).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": f"Failed to start scan: {str(e)}"}).encode("utf-8"))
            return

        # REST API: Get Portfolio Data
        if path == "/api/portfolio":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = get_active_portfolio()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # REST API: Get Portfolio Management Report
        if path == "/api/portfolio_management":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                from src.trade_manager import TradeManager
                cfg = load_config("config/config.yaml")
                trade_mgr = TradeManager(cfg)
                data = trade_mgr.evaluate_all_trades()
            except Exception as e:
                print("Error calculating trade management report:", e)
                data = {"trades": [], "summary": f"Error: {e}"}
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # REST API: Get Portfolio Management History Report
        if path == "/api/portfolio_management_history":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                from src.trade_manager import TradeManager
                cfg = load_config("config/config.yaml")
                trade_mgr = TradeManager(cfg)
                data = trade_mgr.evaluate_trades_history()
            except Exception as e:
                print("Error calculating trade management history:", e)
                data = {"positions": [], "summary": f"Error: {e}"}
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # REST API: Get Sector Rotation Data
        if path == "/api/sector_rotation":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            date_val = query_params.get("date", [None])[0]
            report_file = "data/industry_participation_report.json"
            if date_val:
                cleaned_date = date_val.replace("-", "")
                dated_file = f"data/industry_participation_report_{cleaned_date}.json"
                if os.path.exists(dated_file):
                    report_file = dated_file
                elif os.path.exists(os.path.join("minervini_os", dated_file)):
                    report_file = os.path.join("minervini_os", dated_file)
            
            if not os.path.exists(report_file):
                report_file = os.path.join("minervini_os", report_file)
                
            data = []
            if os.path.exists(report_file):
                try:
                    with open(report_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    print("Error reading industry participation report JSON:", e)
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # REST API: Get Sector Rotation History Log
        if path == "/api/sector_rotation_history":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = get_sector_rotation_history()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # REST API: Get RRG Sector Rotation Data
        if path == "/api/rrg_data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = get_rrg_data()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # REST API: Get Market Breadth History Log
        if path == "/api/market_breadth_history":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = get_market_breadth_history()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # REST API: Get Market Breadth Data
        if path == "/api/market_breadth":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            date_val = query_params.get("date", [None])[0]
            mb_file = "data/market_breadth.json"
            if date_val:
                cleaned_date = date_val.replace("-", "")
                dated_file = f"data/market_breadth_{cleaned_date}.json"
                if os.path.exists(dated_file):
                    mb_file = dated_file
                elif os.path.exists(os.path.join("minervini_os", dated_file)):
                    mb_file = os.path.join("minervini_os", dated_file)
            
            if not os.path.exists(mb_file):
                mb_file = os.path.join("minervini_os", mb_file)
                
            data = {}
            if os.path.exists(mb_file):
                try:
                    with open(mb_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    print("Error reading market breadth JSON:", e)
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # REST API: Get Earnings Calendar
        if path == "/api/earnings_calendar":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            cal_file = "data/earnings_calendar.json"
            if not os.path.exists(cal_file):
                cal_file = os.path.join("minervini_os", cal_file)
            data = {}
            if os.path.exists(cal_file):
                try:
                    with open(cal_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    print("Error reading earnings calendar JSON:", e)
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # REST API: Get True Paper Portfolio
        if path == "/api/true_paper_portfolio":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            pf_file = "data/true_paper_portfolio.json"
            data = {}
            if not os.path.exists(pf_file):
                try:
                    from src.true_paper_trader import TruePaperTrader
                    trader = TruePaperTrader()
                    data = trader.state
                except Exception as e:
                    print("Error initializing true paper trader:", e)
            else:
                try:
                    with open(pf_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    print("Error reading true paper portfolio:", e)
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # REST API: Get Closed Trades Data
        if path == "/api/closed_trades":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = get_closed_trades()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # REST API: Get Watchlist Data
        if path == "/api/watchlist":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            # Extract date query param
            date_val = query_params.get("date", [None])[0]
            data = get_latest_watchlist_data(date_val)
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # REST API: Get Stock Detail Data
        if path == "/api/stock_detail":
            symbol = query_params.get("symbol", [None])[0]
            if not symbol:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing symbol parameter")
                return
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = get_stock_detail(symbol)
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return
            
        # REST API: Get Scan Dates List
        if path == "/api/scan_dates":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            dates = get_available_scan_dates()
            self.wfile.write(json.dumps(dates).encode("utf-8"))
            return

        # REST API: Get Discipline History List
        if path == "/api/discipline_history":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = get_discipline_history_report()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # REST API: Get Scan Status
        if path == "/api/scan_status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            status_file = "data/last_scan_status.json"
            status_data = {"status": "none"}
            if os.path.exists(status_file):
                try:
                    with open(status_file, "r", encoding="utf-8") as f:
                        status_data = json.load(f)
                except Exception:
                    pass
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
            return

        # REST API: Get Gemini key configuration status
        if path == "/api/config/gemini_key":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            api_key = os.environ.get("GEMINI_API_KEY") or config.get("gemini_api_key") or config.get("system", {}).get("gemini_api_key")
            is_set = bool(api_key and len(api_key.strip()) > 5)
            self.wfile.write(json.dumps({"set": is_set}).encode("utf-8"))
            return
            
        # REST API: Get Feedback Data
        if path == "/api/feedback":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            feedback_file = "data/trade_feedback.json"
            feedback_data = []
            if os.path.exists(feedback_file):
                try:
                    with open(feedback_file, "r") as f:
                        feedback_data = json.load(f)
                except Exception:
                    pass
            self.wfile.write(json.dumps(feedback_data).encode("utf-8"))
            return

        # REST API: Get Trade Journal Data
        if path == "/api/trade_journal":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            journal_file = "data/trade_journal_data.json"
            journal_data = []
            if os.path.exists(journal_file):
                try:
                    with open(journal_file, "r", encoding="utf-8") as f:
                        journal_data = json.load(f)
                except Exception:
                    pass
            
            # Dynamic Antigravity Momentum Score for open journal trades
            ams_engine = AntigravityMomentumEngine()
            for t in journal_data:
                if t.get("status") == "OPEN":
                    sym = t.get("symbol", "")
                    ams_data = ams_engine.calculate_ams(sym)
                    t["MS_Score"] = ams_data["Total"]
                    t["Tier"] = calculate_watchlist_tier(ams_data["Total"], t.get("Industry_Category", "Neutral"))
                    t["MS_Rating"] = ams_data["RatingStars"]
                    t["MS_Status"] = ams_data["Status"]
                    t["MS_Breakdown"] = {
                        "Trend": ams_data["Trend"],
                        "Momentum": ams_data["Momentum"],
                        "Volume": ams_data["Volume"],
                        "RS": ams_data["RS"],
                        "SmartMoney": ams_data["SmartMoney"],
                        "VCP": ams_data["VCP"]
                    }
                    
            self.wfile.write(json.dumps(journal_data).encode("utf-8"))
            return
            
        # Fallback to default handler
        super().do_GET()

    def do_POST(self):
        # REST API: Log client errors for debugging
        if self.path == "/api/client_error":
            import sys
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            try:
                err_data = json.loads(post_data.decode("utf-8"))
                print(f"[CLIENT JS ERROR] Msg: {err_data.get('message')}, File: {err_data.get('source')}, Line: {err_data.get('lineno')}, Col: {err_data.get('colno')}", file=sys.stderr, flush=True)
                if err_data.get('stack'):
                    print(f"[CLIENT JS STACK] {err_data.get('stack')}", file=sys.stderr, flush=True)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "logged"}).encode("utf-8"))
            except Exception as e:
                print(f"Error logging client error: {e}", file=sys.stderr, flush=True)
                self.send_response(500)
                self.end_headers()
            return

        # REST API: Save Trade Feedback
        if self.path == "/api/feedback":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            
            try:
                new_entry = json.loads(post_data.decode("utf-8"))
                new_entry["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                feedback_file = "data/trade_feedback.json"
                feedback_data = []
                if os.path.exists(feedback_file):
                    try:
                        with open(feedback_file, "r") as f:
                            feedback_data = json.load(f)
                    except Exception:
                        pass
                
                # Append new entry
                feedback_data.append(new_entry)
                
                # Ensure data/ directory exists
                os.makedirs("data", exist_ok=True)
                with open(feedback_file, "w") as f:
                    json.dump(feedback_data, f, indent=2)
                    
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Feedback saved successfully"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        # REST API: Save Trade Journal Data
        if self.path == "/api/trade_journal":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            
            try:
                updated_journal = json.loads(post_data.decode("utf-8"))
                
                journal_file = "data/trade_journal_data.json"
                os.makedirs("data", exist_ok=True)
                with open(journal_file, "w", encoding="utf-8") as f:
                    json.dump(updated_journal, f, indent=2)
                    
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Trade journal saved successfully"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        # REST API: Update Gemini API Key
        if self.path == "/api/config/gemini_key":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
                new_key = payload.get("api_key", "").strip()
                
                # Update in memory
                global config
                config["gemini_api_key"] = new_key
                
                # Update config.yaml file
                config_path = "config/config.yaml"
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    if "gemini_api_key:" in content:
                        content = re.sub(r"gemini_api_key:\s*.*", f'gemini_api_key: "{new_key}"', content)
                    else:
                        if not content.endswith("\n"):
                            content += "\n"
                        content += f'\ngemini_api_key: "{new_key}"\n'
                        
                    with open(config_path, "w", encoding="utf-8") as f:
                        f.write(content)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "API key updated successfully"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        # REST API: Chat AI Assistant
        if self.path == "/api/chat":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            
            try:
                chat_req = json.loads(post_data.decode("utf-8"))
                msg = chat_req.get("message", "")
                
                response_str = process_chat_message(msg)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"response": response_str}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"response": f"Error processing query: {str(e)}"}).encode("utf-8"))
            return
            
        self.send_response(404)
        self.end_headers()

def run_server():
    # Make sure web directory exists
    os.makedirs(DIRECTORY, exist_ok=True)
    
    # Ensure feedback database exists
    feedback_file = "data/trade_feedback.json"
    if not os.path.exists(feedback_file):
        with open(feedback_file, "w") as f:
            json.dump([], f)
            
    # Pre-warm watchlist cache
    print("Pre-warming watchlist cache...")
    try:
        get_latest_watchlist_data()
        # Also pre-warm current date string format
        from datetime import datetime
        cur_date = datetime.now().strftime("%Y-%m-%d")
        get_latest_watchlist_data(cur_date)
        print("Watchlist cache pre-warmed successfully!")
    except Exception as e:
        print(f"Watchlist cache pre-warming failed: {e}")

    handler = DashboardRequestHandler
    # Bind to all interfaces with a Threading TCPServer to support concurrent requests
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), handler) as httpd:
        print(f"==================================================")
        print(f"Minervini Watchlist Dashboard Web Server Running")
        print(f"Access the Dashboard at: http://localhost:{PORT}")
        print(f"==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == "__main__":
    run_server()
