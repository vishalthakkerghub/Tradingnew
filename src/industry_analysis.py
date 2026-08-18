import os
import json
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

def load_data():
    symbols_json = "config/symbols.json"
    xlsx_path = "data/industry stockname mapping.xlsx"
    
    # Fallbacks for paths if run from different cwd
    if not os.path.exists(symbols_json):
        symbols_json = os.path.join("minervini_os", symbols_json)
    if not os.path.exists(xlsx_path):
        xlsx_path = os.path.join("minervini_os", xlsx_path)
        
    with open(symbols_json, "r", encoding="utf-8") as f:
        symbols = json.load(f)
        
    df_excel = pd.read_excel(xlsx_path)
    df_excel['NSEcode_clean'] = df_excel['NSEcode'].astype(str).str.strip().str.upper()

    # Map Symbol -> {"industry": ..., "sector": ..., "name": ...}
    symbol_to_industry = {}
    for _, row in df_excel.iterrows():
        sym = str(row['NSEcode_clean']).strip()
        ind = row.get('Industry', row.get('Industry Name'))
        sec = row.get('Sector', 'Others')
        name = row['Stock Name']
        if pd.isna(ind) or str(ind).strip() == "":
            ind = None
        if pd.isna(sec) or str(sec).strip() == "":
            sec = 'Others'
        symbol_to_industry[sym] = {"industry": ind, "sector": sec, "name": name}
        
    unlinked = []
    linked_symbols = {}
    
    for s in symbols:
        s_upper = s.upper().strip()
        if s_upper not in symbol_to_industry or symbol_to_industry[s_upper]["industry"] is None:
            unlinked.append(s_upper)
        else:
            linked_symbols[s_upper] = symbol_to_industry[s_upper]
            
    return symbols, linked_symbols, unlinked

def process_single_stock(symbol, industry_name, sector_name, company_name, target_dates, index_indexed, mc_map):
    cache_dir = "data/cache"
    cache_file = os.path.join(cache_dir, f"{symbol}.csv")
    if not os.path.exists(cache_file):
        cache_file = os.path.join("minervini_os", cache_file)
        if not os.path.exists(cache_file):
            return None
            
    try:
        df = pd.read_csv(cache_file)
        if df.empty or len(df) < 10:
            return None
            
        # Get latest price and apply price and market cap filters
        p_latest = float(df['Close'].iloc[-1])
        if p_latest < 30.0:
            return None

        mc = mc_map.get(symbol, 0)
        if mc > 0:
            # 500 Cr = 5,000,000,000 Rupees
            # 50,000 Cr = 50,000,000,000,000 Rupees (50 Lakh Crores)
            if mc < 5000000000 or mc > 50000000000000:
                return None
            
        df.columns = [c.strip() for c in df.columns]
        df['Date'] = pd.to_datetime(df['Date'])
        df.sort_values('Date', inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        # Calculate indicators
        close_prices = df['Close']
        df['EMA20'] = close_prices.ewm(span=20, adjust=False).mean()
        df['SMA50'] = close_prices.rolling(window=50, min_periods=10).mean()
        df['SMA200'] = close_prices.rolling(window=200, min_periods=30).mean()
        
        df['High52W'] = df['High'].rolling(window=252, min_periods=60).max()
        df['High52W'] = df['High52W'].fillna(df['High'].cummax())
        
        # Calculate RS ratio metrics
        df['Index_Close'] = df['Date'].map(index_indexed)
        df['RS_Ratio'] = df['Close'] / df['Index_Close']
        df['RS_Ratio_EMA20'] = df['RS_Ratio'].ewm(span=20, adjust=False).mean()
        
        # 3M returns
        df['Stock_Perf_3M'] = df['Close'].pct_change(periods=min(60, len(df)-1))
        df['Index_Perf_3M'] = df['Index_Close'].pct_change(periods=min(60, len(df)-1))
        
        df_indexed = df.set_index('Date')
        
        daily_indicators = {}
        for d in target_dates:
            if d in df_indexed.index:
                row_data = df_indexed.loc[d]
                if isinstance(row_data, pd.DataFrame):
                    row_data = row_data.iloc[-1]
                    
                c = float(row_data['Close'])
                ema = float(row_data['EMA20'])
                sma50 = float(row_data['SMA50'])
                sma200 = float(row_data['SMA200'])
                h52 = float(row_data['High52W'])
                
                # Check stacked
                stacked = int(c > ema and ema > sma50 and sma50 > sma200) if (not pd.isna(ema) and not pd.isna(sma50) and not pd.isna(sma200)) else 0
                above_ema20 = int(c > ema) if not pd.isna(ema) else 0
                above_sma50 = int(c > sma50) if not pd.isna(sma50) else 0
                above_sma200 = int(c > sma200) if not pd.isna(sma200) else 0
                
                dist_52wh = float(((h52 - c) / h52) * 100.0) if (not pd.isna(h52) and h52 > 0) else 0.0
                near_52wh = int(dist_52wh <= 10.0)
                
                # Calculate RS points
                stock_perf = row_data['Stock_Perf_3M']
                index_perf = row_data['Index_Perf_3M']
                rs_ratio = row_data['RS_Ratio']
                rs_ratio_ema = row_data['RS_Ratio_EMA20']
                
                points = 0
                if not pd.isna(stock_perf) and not pd.isna(index_perf):
                    if stock_perf > index_perf + 0.10:
                        points += 5
                    elif stock_perf > index_perf:
                        points += 3
                    else:
                        points += 1
                else:
                    points += 2
                    
                if not pd.isna(rs_ratio) and not pd.isna(rs_ratio_ema):
                    if rs_ratio > rs_ratio_ema:
                        points += 5
                        
                high_rs = int(points >= 7)
                
                # Volume & Pocket Pivot Logic
                try:
                    idx = df[df['Date'] == d].index[0]
                except Exception:
                    idx = -1
                
                is_pocket_pivot = 0
                flow_val = 0.0
                vol_val = 0.0
                
                if idx != -1:
                    today_close = float(df.loc[idx, 'Close'])
                    prev_close = float(df.loc[idx-1, 'Close']) if idx > 0 else today_close
                    today_open = float(df.loc[idx, 'Open']) if 'Open' in df.columns else today_close
                    today_vol = float(df.loc[idx, 'Volume']) if 'Volume' in df.columns else 0.0
                    
                    is_up_day = (today_close > prev_close) or (today_close == prev_close and today_close > today_open)
                    is_down_day = (today_close < prev_close) or (today_close == prev_close and today_close < today_open)
                    
                    vol_val = today_vol * today_close
                    if is_up_day:
                        flow_val = vol_val
                    elif is_down_day:
                        flow_val = -vol_val
                        
                    # 10-day window check for pocket pivot (up day volume > max down volume of last 10 days)
                    if is_up_day and today_vol > 0.0:
                        window_start = max(0, idx - 9)
                        max_down_vol = 0.0
                        for j in range(window_start, idx):
                            j_close = float(df.loc[j, 'Close'])
                            j_prev = float(df.loc[j-1, 'Close']) if j > 0 else j_close
                            j_open = float(df.loc[j, 'Open']) if 'Open' in df.columns else j_close
                            is_j_down = (j_close < j_prev) or (j_close == j_prev and j_close < j_open)
                            if is_j_down:
                                j_vol = float(df.loc[j, 'Volume']) if 'Volume' in df.columns else 0.0
                                if j_vol > max_down_vol:
                                    max_down_vol = j_vol
                        if today_vol > max_down_vol:
                            is_pocket_pivot = 1
                
                # Calculate if SMA200 is rising
                sma200_rising = 0
                if idx != -1 and idx >= 20:
                    sma200_today = float(df.loc[idx, 'SMA200']) if 'SMA200' in df.columns else 0.0
                    sma200_prev = float(df.loc[idx-20, 'SMA200']) if 'SMA200' in df.columns else 0.0
                    if sma200_today > sma200_prev:
                        sma200_rising = 1

                daily_indicators[d] = {
                    "stacked": stacked,
                    "above_ema20": above_ema20,
                    "above_sma50": above_sma50,
                    "above_sma200": above_sma200,
                    "near_52wh": near_52wh,
                    "dist_52wh": dist_52wh,
                    "high_rs": high_rs,
                    "price": c,
                    "pocket_pivot": is_pocket_pivot,
                    "volume_flow": flow_val,
                    "volume_value": vol_val,
                    "perf_3m": float(stock_perf) if not pd.isna(stock_perf) else 0.0,
                    "sma200_rising": sma200_rising
                }
            else:
                daily_indicators[d] = {
                    "stacked": 0,
                    "above_ema20": 0,
                    "above_sma50": 0,
                    "above_sma200": 0,
                    "near_52wh": 0,
                    "dist_52wh": 99.0,
                    "high_rs": 0,
                    "price": 0.0,
                    "pocket_pivot": 0,
                    "volume_flow": 0.0,
                    "volume_value": 0.0,
                    "perf_3m": 0.0,
                    "sma200_rising": 0
                }
                
        # 10D return
        p_latest = float(df['Close'].iloc[-1])
        p_10d = float(df['Close'].iloc[-min(10, len(df))])
        ret_10d = ((p_latest - p_10d) / p_10d) * 100.0
        
        # Today's return
        p_yesterday = float(df['Close'].iloc[-2]) if len(df) >= 2 else p_latest
        ret_today = ((p_latest - p_yesterday) / p_yesterday) * 100.0
        
        return {
        "Symbol": symbol,
        "Industry": industry_name,
        "Sector": sector_name,
        "Company_Name": company_name,
        "Ret_Today": ret_today,
        "Ret_10D": ret_10d,
        "Daily_Indicators": daily_indicators
    }
    except Exception as e:
        print(f"Error processing stock {symbol}: {e}")
        return None

def analyze_participation(end_date=None):
    symbols, linked_symbols, unlinked = load_data()
    
    # Load NSE trading dates dynamically from NIFTY_50 cache
    index_file = "data/cache/NIFTY_50.csv"
    if not os.path.exists(index_file):
        index_file = os.path.join("minervini_os", index_file)
        
    if os.path.exists(index_file):
        try:
            df_idx = pd.read_csv(index_file)
            df_idx['Date'] = pd.to_datetime(df_idx['Date'])
            df_idx.sort_values('Date', inplace=True)
            trading_dates = df_idx['Date'].tolist()
            
            # Extract last 10 trading days for rolling calculations
            if end_date:
                end_dt = pd.to_datetime(end_date)
                if end_dt in trading_dates:
                    idx = trading_dates.index(end_dt)
                    target_dates = trading_dates[max(0, idx-9):idx+1]
                else:
                    filtered_dates = [d for d in trading_dates if d <= end_dt]
                    if filtered_dates:
                        idx = trading_dates.index(filtered_dates[-1])
                        target_dates = trading_dates[max(0, idx-9):idx+1]
                    else:
                        target_dates = trading_dates[-10:]
            else:
                target_dates = trading_dates[-10:]
                
            index_indexed = df_idx.set_index('Date')['Close']
            print(f"Resolving rolling daily scan ending: {target_dates[-1].strftime('%Y-%m-%d')}")
        except Exception as date_ex:
            print(f"Failed to parse index dates: {date_ex}")
            return
    else:
        print("Missing Nifty benchmark file. Cannot run daily scan.")
        return
        
    # Load market caps mapping
    mc_file = "data/market_caps.json"
    if not os.path.exists(mc_file):
        mc_file = os.path.join("minervini_os", mc_file)
        
    mc_map = {}
    if os.path.exists(mc_file):
        try:
            with open(mc_file, "r") as f:
                mc_map = json.load(f)
        except Exception as e:
            print(f"Failed to load market caps database: {e}")
            
    print(f"Loaded symbols. Processing histories for {len(linked_symbols)} linked stocks...")
    results = []
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(process_single_stock, s, info["industry"], info["sector"], info["name"], target_dates, index_indexed, mc_map): s 
            for s, info in linked_symbols.items()
        }
        for fut in futures:
            res = fut.result()
            if res is not None:
                results.append(res)
                
    df_stocks = pd.DataFrame(results)
    print(f"Processed {len(df_stocks)} valid stocks.")
    
    # Calculate RS percentiles across all stocks for each target date
    if not df_stocks.empty:
        for d in target_dates:
            perf_values = []
            for res in results:
                ind_val = res["Daily_Indicators"].get(d)
                if ind_val and ind_val.get("price", 0.0) > 0:
                    perf_values.append(ind_val.get("perf_3m", 0.0))
            
            if perf_values:
                sorted_perf = sorted(perf_values)
                n_perf = len(sorted_perf)
                for res in results:
                    ind_val = res["Daily_Indicators"].get(d)
                    if ind_val and ind_val.get("price", 0.0) > 0:
                        val = ind_val.get("perf_3m", 0.0)
                        r_idx = sorted_perf.index(val)
                        percentile = int(round((r_idx / n_perf) * 98)) + 1
                        ind_val["rs_rating"] = percentile
                    else:
                        if ind_val:
                            ind_val["rs_rating"] = 1
    
    # Load previous day's JSON report for state hysteresis
    # Target chronologically preceding day's report when available
    d_yesterday = target_dates[-2] if len(target_dates) >= 2 else None
    prev_report_file = None
    if d_yesterday:
        yesterday_clean = d_yesterday.strftime("%Y%m%d")
        prev_report_file = f"data/industry_participation_report_{yesterday_clean}.json"
        if not os.path.exists(prev_report_file):
            prev_report_file = os.path.join("minervini_os", prev_report_file)
            if not os.path.exists(prev_report_file):
                prev_report_file = None
                
    if not prev_report_file:
        prev_report_file = "data/industry_participation_report.json"
        if not os.path.exists(prev_report_file):
            prev_report_file = os.path.join("minervini_os", prev_report_file)
        
    prev_states = {}
    if os.path.exists(prev_report_file):
        try:
            with open(prev_report_file, "r", encoding="utf-8") as f_prev:
                prev_list = json.load(f_prev)
                for item in prev_list:
                    prev_states[item["Industry"]] = {
                        "Category": item.get("Category", "Avoid"),
                        "Streak_Days": item.get("Streak_Days", 0),
                        "Failure_Days": item.get("Failure_Days", 0),
                        "Last_Updated_Date": item.get("Last_Updated_Date", ""),
                        "Breadth": item.get("Breadth", 0.0),
                        "Flow_Val": item.get("Flow_Val", 0.0)
                    }
        except Exception as state_ex:
            print("Failed to read previous state report:", state_ex)
            
    industry_groups = df_stocks.groupby('Industry')
    industry_weekly = []
    
    d_today = target_dates[-1]
    d_yesterday = target_dates[-2]
    
    for ind_name, group in industry_groups:
        total_stocks = len(group)
        if total_stocks < 1:
            continue
            
        # Daily averages for above MA indicators
        def get_participation_percentage(d, indicator_key):
            above_count = sum(r['Daily_Indicators'].get(d, {}).get(indicator_key, 0) for _, r in group.iterrows())
            return (above_count / total_stocks) * 100.0
            
        # Calculate daily values for today vs yesterday for indicators
        part_ema20_today = get_participation_percentage(d_today, 'above_ema20')
        part_ema20_yesterday = get_participation_percentage(d_yesterday, 'above_ema20')
        part_change = part_ema20_today - part_ema20_yesterday
        
        part_sma50_today = get_participation_percentage(d_today, 'above_sma50')
        part_sma50_yesterday = get_participation_percentage(d_yesterday, 'above_sma50')
        part_sma50_change = part_sma50_today - part_sma50_yesterday
        
        part_sma200_today = get_participation_percentage(d_today, 'above_sma200')
        part_sma200_yesterday = get_participation_percentage(d_yesterday, 'above_sma200')
        part_sma200_change = part_sma200_today - part_sma200_yesterday
        
        stacked_today = get_participation_percentage(d_today, 'stacked')
        stacked_yesterday = get_participation_percentage(d_yesterday, 'stacked')
        stacked_change = stacked_today - stacked_yesterday
        
        part_rs_today = get_participation_percentage(d_today, 'high_rs')
        part_rs_yesterday = get_participation_percentage(d_yesterday, 'high_rs')
        part_rs_change = part_rs_today - part_rs_yesterday
        
        part_52wh_today = get_participation_percentage(d_today, 'near_52wh')
        part_52wh_yesterday = get_participation_percentage(d_yesterday, 'near_52wh')
        part_52wh_change = part_52wh_today - part_52wh_yesterday
        
        # Idea A: Net Money Flow %
        sum_flow_today = sum(r['Daily_Indicators'].get(d_today, {}).get('volume_flow', 0.0) for _, r in group.iterrows())
        sum_val_today = sum(r['Daily_Indicators'].get(d_today, {}).get('volume_value', 0.0) for _, r in group.iterrows())
        net_flow_pct_today = (sum_flow_today / sum_val_today) * 100.0 if sum_val_today > 0.0 else 0.0
        net_flow_score_scaled = (net_flow_pct_today + 100.0) / 2.0
        
        # Idea D: Pocket Pivot Group Breadth (last 5 sessions)
        last_5_dates = target_dates[-5:]
        pocket_pivot_count = 0
        for _, r in group.iterrows():
            has_pp = False
            for d_temp in last_5_dates:
                if r['Daily_Indicators'].get(d_temp, {}).get('pocket_pivot', 0):
                    has_pp = True
                    break
            if has_pp:
                pocket_pivot_count += 1
        pocket_pivot_pct = (pocket_pivot_count / total_stocks) * 100.0 if total_stocks > 0 else 0.0
        
        # Check if there is at least one stock within 10% of 52-week high
        has_leader = any(r['Daily_Indicators'].get(d_today, {}).get('dist_52wh', 99.0) <= 10.0 for _, r in group.iterrows())
        
        avg_ret_today = group['Ret_Today'].mean()
        avg_ret_10d = group['Ret_10D'].mean()
        
        # Identify stock candidates ranked by their setups
        stock_details_list = []
        d_weekly = target_dates[-6] if len(target_dates) >= 6 else target_dates[0]
        for _, r in group.iterrows():
            ind_today = r['Daily_Indicators'].get(d_today, {})
            ind_yesterday = r['Daily_Indicators'].get(d_yesterday, {})
            ind_weekly = r['Daily_Indicators'].get(d_weekly, {})
            
            # Rank score helper today
            rank_score = 0
            if ind_today.get("above_ema20", 0): rank_score += 2
            if ind_today.get("above_sma50", 0): rank_score += 2
            if ind_today.get("stacked", 0): rank_score += 3
            if ind_today.get("high_rs", 0): rank_score += 3
            if ind_today.get("near_52wh", 0): rank_score += 5
            rank_score -= (ind_today.get("dist_52wh", 0.0) / 10.0)
            
            # Rank score helper yesterday
            rank_score_yesterday = 0
            if ind_yesterday.get("above_ema20", 0): rank_score_yesterday += 2
            if ind_yesterday.get("above_sma50", 0): rank_score_yesterday += 2
            if ind_yesterday.get("stacked", 0): rank_score_yesterday += 3
            if ind_yesterday.get("high_rs", 0): rank_score_yesterday += 3
            if ind_yesterday.get("near_52wh", 0): rank_score_yesterday += 5
            rank_score_yesterday -= (ind_yesterday.get("dist_52wh", 0.0) / 10.0)
            
            # Determine if new or changed
            p_yesterday = ind_yesterday.get("price", 0.0)
            is_new = (p_yesterday < 30.0)
            reason = ""
            change = "constant"
            
            if is_new:
                change = "new"
                if p_yesterday == 0.0:
                    reason = "First time detected in scan database"
                elif p_yesterday < 30.0 and ind_today.get("price", 0.0) >= 30.0:
                    reason = "Price crossed above ₹30 floor threshold"
                elif not ind_yesterday.get("above_ema20", 0) and ind_today.get("above_ema20", 0):
                    reason = "Crossed above 20 EMA short-term pivot"
                elif not ind_yesterday.get("above_sma50", 0) and ind_today.get("above_sma50", 0):
                    reason = "Crossed above 50 SMA support line"
                elif not ind_yesterday.get("stacked", 0) and ind_today.get("stacked", 0):
                    reason = "Moving averages stacked (Stage 2 Uptrend)"
                elif not ind_yesterday.get("high_rs", 0) and ind_today.get("high_rs", 0):
                    reason = "Relative Strength (RS) score crossed above 70"
                elif not ind_yesterday.get("near_52wh", 0) and ind_today.get("near_52wh", 0):
                    reason = "Coiling tight within 10% of 52-Week High"
                else:
                    reason = "Fresh momentum and setup confirmation"
            else:
                if rank_score > rank_score_yesterday:
                    change = "up"
                elif rank_score < rank_score_yesterday:
                    change = "down"
                else:
                    change = "constant"
            
            # Stock detail dict
            stock_details_list.append({
                "Symbol": r['Symbol'],
                "Company_Name": r['Company_Name'],
                "Industry": ind_name,
                "Price": ind_today.get("price", 0.0),
                "Dist_52WH": ind_today.get("dist_52wh", 0.0),
                "Rank_Score": rank_score,
                "Is_New": bool(is_new),
                "New_Reason": reason,
                "Change": change,
                "Ret_Today": float(r['Ret_Today']),
                "Above_EMA20": int(ind_today.get("above_ema20", 0)),
                "Above_SMA50": int(ind_today.get("above_sma50", 0)),
                "Above_SMA200": int(ind_today.get("above_sma200", 0)),
                "Stacked": int(ind_today.get("stacked", 0)),
                "High_RS": int(ind_today.get("high_rs", 0)),
                "Pocket_Pivot": int(ind_today.get("pocket_pivot", 0)),
                "RS_D": int(ind_today.get("rs_rating", 50)),
                "RS_W": int(ind_weekly.get("rs_rating", 50)),
                "SMA200_Rising": int(ind_today.get("sma200_rising", 0))
            })
            
        # Sort candidates descending by Rank_Score
        stock_details_list.sort(key=lambda x: x["Rank_Score"], reverse=True)
        tickers_list = [item["Symbol"] for item in stock_details_list]
        
        # Load previous day's state parameters
        prev = prev_states.get(ind_name, {"Category": "Avoid", "Streak_Days": 0, "Failure_Days": 0, "Last_Updated_Date": "", "Breadth": 0.0, "Flow_Val": 0.0})
        prev_cat = prev["Category"]
        # Safe migration mapping for previous day categories if running first time on old logs
        if prev_cat in ["Running Hot", "The Sweet Spot"]:
            prev_cat = "Confirmed Uptrend"
        elif prev_cat == "Sector Waking Up":
            prev_cat = "Early Uptrend"
        elif prev_cat in ["Neutral", "Out of Favor"]:
            prev_cat = "Avoid"
            
        prev_streak = prev["Streak_Days"]
        prev_fail = prev["Failure_Days"]
        prev_date = prev.get("Last_Updated_Date", "")
        prev_breadth = prev.get("Breadth", 0.0)
        prev_flow = prev.get("Flow_Val", 0.0)
        
        # Override to force Movies & Entertainment (music) streak to start fresh on Thursday 2026-07-23
        if ind_name == "Movies & Entertainment" and str(d_today)[:10] == "2026-07-23":
            prev_cat = "Avoid"
            prev_streak = 0
            prev_fail = 0
            prev_date = ""
            
        d_today_str = d_today.strftime("%Y-%m-%d")
        is_repeat_run = (prev_date == d_today_str)
        
        # Calculate Breadth Trend (EXPANDING, CONTRACTING, FLAT)
        if stacked_today > prev_breadth:
            breadth_trend = "EXPANDING"
        elif stacked_today < prev_breadth:
            breadth_trend = "CONTRACTING"
        else:
            breadth_trend = "FLAT"

        # Calculate Flow Trend (UP, DOWN, FLAT)
        if net_flow_pct_today > prev_flow and net_flow_pct_today > -5.0:
            flow_trend = "UP"
        elif net_flow_pct_today < prev_flow and net_flow_pct_today < 5.0:
            flow_trend = "DOWN"
        else:
            flow_trend = "FLAT"

        # Quality Floor check
        passed_floor = (part_ema20_today >= 40.0 and has_leader)
        
        # Conviction check: at least 20% stacked breadth and at least 4 stocks total
        has_conviction = (stacked_today >= 20.0 and total_stocks >= 4)
        
        # Determine raw calculated stage today
        if passed_floor:
            if flow_trend == "UP" and breadth_trend in ["EXPANDING", "FLAT"] and has_conviction:
                raw_category = "Confirmed Uptrend"
            elif flow_trend == "UP" and (breadth_trend in ["CONTRACTING", "FLAT"] or not has_conviction):
                raw_category = "Early Uptrend"
            elif breadth_trend in ["FLAT", "EXPANDING"] and flow_trend == "FLAT":
                raw_category = "Consolidation"
            elif breadth_trend == "CONTRACTING" and flow_trend == "DOWN":
                raw_category = "Downtrend Warning"
            else:
                raw_category = "Avoid"
        else:
            if breadth_trend == "CONTRACTING" and flow_trend == "DOWN":
                raw_category = "Downtrend Warning"
            elif breadth_trend in ["FLAT", "EXPANDING"] and flow_trend == "FLAT":
                raw_category = "Consolidation"
            else:
                raw_category = "Avoid"

        # Stickiness Hysteresis state machine
        was_focus = prev_cat in ["Confirmed Uptrend", "Early Uptrend"]
        
        if was_focus:
            if raw_category == "Downtrend Warning":
                category = "Downtrend Warning"
                streak = 0
                fail_days = 0
                explanation = "Instant demotion to Downtrend Warning (fading breadth & flow)."
            elif raw_category in ["Confirmed Uptrend", "Early Uptrend"]:
                category = raw_category
                streak = prev_streak + 1
                fail_days = 0
                explanation = f"{category}, Streak Day {streak}."
            else:
                # Other drops (e.g. to Consolidation or Avoid) are subject to 2-day grace period
                if prev_fail < 1:
                    category = prev_cat
                    streak = prev_streak
                    fail_days = 1
                    explanation = "Focus state held on grace period (Failure Day 1)."
                else:
                    category = raw_category
                    streak = 0
                    fail_days = 0
                    explanation = f"Demoted to {category} after 2 consecutive days below quality floor."
        else:
            category = raw_category
            streak = 1 if category in ["Confirmed Uptrend", "Early Uptrend"] else 0
            fail_days = 0
            explanation = f"Stage: {category}."
            
        if is_repeat_run:
            category = prev_cat
            streak = prev_streak
            fail_days = prev_fail
            explanation = "Repeat run on same trading session date. State preserved."
            
        # Determine unique Sector and Zone for this group
        sector_name = group['Sector'].iloc[0] if 'Sector' in group.columns else "Others"
        zone_name = category

        industry_weekly.append({
            "Industry": ind_name,
            "Sector": sector_name,
            "Zone": zone_name,
            "Total_Stocks": total_stocks,
            "Category": category,
            "Streak_Days": streak,
            "Failure_Days": fail_days,
            
            "Breadth": stacked_today,
            "Breadth_Change": stacked_change,
            "Flow": net_flow_pct_today,
            "Flow_Val": net_flow_pct_today,
            "Part_Change": part_change,
            
            "EMA20_Participation_Today": part_ema20_today,
            "EMA20_Participation_Change": part_change,
            
            "SMA50_Participation_Today": part_sma50_today,
            "SMA50_Participation_Change": part_sma50_change,
            
            "SMA200_Participation_Today": part_sma200_today,
            "SMA200_Participation_Change": part_sma200_change,
            
            "RS_Participation_Today": part_rs_today,
            "RS_Participation_Change": part_rs_change,
            
            "Near52WH_Participation_Today": part_52wh_today,
            "Near52WH_Participation_Change": part_52wh_change,
            
            "Avg_Return_Today": avg_ret_today,
            "Avg_Return_10D": avg_ret_10d,
            
            "Net_Flow_Pct": net_flow_pct_today,
            "Net_Flow_Score_Scaled": net_flow_score_scaled,
            "Pocket_Pivot_Pct": pocket_pivot_pct,
            
            "Explanation": explanation,
            "Stocks": tickers_list,
            "Stock_Details": stock_details_list
        })
        
    df_industries = pd.DataFrame(industry_weekly)
    
    # Classify all industries (no minimum stock threshold)
    df_scaled = df_industries.copy()
    df_unscaled = pd.DataFrame(columns=df_industries.columns)
    
    # Sort within categories
    df_scaled['Sort_Score'] = df_scaled['Avg_Return_10D'] + df_scaled['EMA20_Participation_Today'] / 10.0
    df_scaled.sort_values(['Category', 'Sort_Score'], ascending=[True, False], inplace=True)
    
    # Calculate Market Breadth Index history across all processed stocks (results)
    market_breadth_history = {}
    for d in target_dates:
        total_valid = 0
        sum_ema20 = 0
        sum_sma50 = 0
        sum_sma200 = 0
        sum_stacked = 0
        sum_rs = 0
        sum_52wh = 0
        sum_adv = 0
        
        try:
            d_idx = trading_dates.index(d)
            d_prev = trading_dates[d_idx - 1] if d_idx > 0 else d
        except Exception:
            d_prev = d
            
        for r in results:
            ind = r['Daily_Indicators'].get(d, {})
            if ind.get("price", 0.0) > 0.0:
                total_valid += 1
                sum_ema20 += ind.get("above_ema20", 0)
                sum_sma50 += ind.get("above_sma50", 0)
                sum_sma200 += ind.get("above_sma200", 0)
                sum_stacked += ind.get("stacked", 0)
                sum_rs += ind.get("high_rs", 0)
                sum_52wh += ind.get("near_52wh", 0)
                
                ind_prev = r['Daily_Indicators'].get(d_prev, {})
                if ind_prev.get("price", 0.0) > 0.0:
                    if ind.get("price", 0.0) > ind_prev.get("price", 0.0):
                        sum_adv += 1
                        
        if total_valid > 0:
            p_ema20 = (sum_ema20 / total_valid) * 100.0
            p_sma50 = (sum_sma50 / total_valid) * 100.0
            p_sma200 = (sum_sma200 / total_valid) * 100.0
            p_stacked = (sum_stacked / total_valid) * 100.0
            p_rs = (sum_rs / total_valid) * 100.0
            p_52wh = (sum_52wh / total_valid) * 100.0
            p_adv = (sum_adv / total_valid) * 100.0
            
            # MBI is the average of 5 primary indicators (200-SMA, 50-SMA, A/D, Near 52WH, RS >= 70)
            breadth_index = (p_sma200 + p_sma50 + p_adv + p_52wh + p_rs) / 5.0
            
            market_breadth_history[d.strftime('%Y-%m-%d')] = {
                "Breadth_Index": breadth_index,
                "Above20EMA": p_ema20,
                "Above50SMA": p_sma50,
                "Above200SMA": p_sma200,
                "Stacked": p_stacked,
                "HighRS": p_rs,
                "Near52WH": p_52wh,
                "AdvancesDeclines": p_adv
            }
            
    today_str = target_dates[-1].strftime('%Y-%m-%d')
    yesterday_str = target_dates[-2].strftime('%Y-%m-%d') if len(target_dates) >= 2 else today_str
    d3_str = target_dates[-4].strftime('%Y-%m-%d') if len(target_dates) >= 4 else today_str
    d5_str = target_dates[-6].strftime('%Y-%m-%d') if len(target_dates) >= 6 else today_str
    
    t_data = market_breadth_history.get(today_str, {})
    y_data = market_breadth_history.get(yesterday_str, {})
    d3_data = market_breadth_history.get(d3_str, {})
    d5_data = market_breadth_history.get(d5_str, {})
    
    idx_today = t_data.get("Breadth_Index", 0.0)
    idx_yesterday = y_data.get("Breadth_Index", 0.0)
    idx_3d = d3_data.get("Breadth_Index", 0.0)
    idx_5d = d5_data.get("Breadth_Index", 0.0)
    
    change_1d = idx_today - idx_yesterday
    change_3d = idx_today - idx_3d
    change_5d = idx_today - idx_5d
    
    status = "Caution"
    status_color = "caution"
    if idx_today >= 60.0:
        status = "Strong"
        status_color = "strong"
    elif idx_today < 40.0:
        status = "Weak"
        status_color = "weak"
        
    breadth_report = {
        "AsOfDate": today_str,
        "Index": round(idx_today, 1),
        "Change_1D": round(change_1d, 1),
        "Change_3D": round(change_3d, 1),
        "Change_5D": round(change_5d, 1),
        "Status": status,
        "StatusColor": status_color,
        "Indicators": {
            "Above20EMA": round(t_data.get("Above20EMA", 0.0), 1),
            "Above50SMA": round(t_data.get("Above50SMA", 0.0), 1),
            "Above200SMA": round(t_data.get("Above200SMA", 0.0), 1),
            "Stacked": round(t_data.get("Stacked", 0.0), 1),
            "AdvancesDeclines": round(t_data.get("AdvancesDeclines", 0.0), 1),
            "Near52WH": round(t_data.get("Near52WH", 0.0), 1),
            "HighRS": round(t_data.get("HighRS", 0.0), 1)
        }
    }
    
    mb_path = "data/market_breadth.json"
    if not os.path.exists("data"):
        mb_path = os.path.join("minervini_os", mb_path)
    os.makedirs(os.path.dirname(mb_path), exist_ok=True)
    with open(mb_path, "w", encoding="utf-8") as f_mb:
        json.dump(breadth_report, f_mb, indent=2)
    # Also save dated copy
    cleaned_date = today_str.replace("-", "")
    dated_mb_path = os.path.join(os.path.dirname(mb_path), f"market_breadth_{cleaned_date}.json")
    with open(dated_mb_path, "w", encoding="utf-8") as f_mb_dated:
        json.dump(breadth_report, f_mb_dated, indent=2)
    print(f"Market breadth summary report written successfully (also saved to {dated_mb_path}).")
    
    # Save the reports
    write_reports(df_scaled, df_unscaled, unlinked, df_stocks, target_dates)

def write_reports(df_scaled, df_unscaled, unlinked, df_stocks, target_dates):
    local_reports_dir = "reports/daily"
    if not os.path.exists(local_reports_dir):
        local_reports_dir = os.path.join("minervini_os", local_reports_dir)
    os.makedirs(local_reports_dir, exist_ok=True)
    filepath_md = os.path.join(local_reports_dir, "industry_participation_report.md")
    
    conv_dir = "C:/Users/visha/.gemini/antigravity/brain/553a983d-9b7b-4e40-8933-3a4e4e5f9534"
    filepath_artifact = os.path.join(conv_dir, "industry_participation_report.md") if os.path.exists(conv_dir) else None
    
    d_latest = target_dates[-1]
    
    with open(filepath_md, "w", encoding="utf-8") as f:
        f.write("# 📈 Rolling Daily Industry Momentum & Rotation Report\n\n")
        f.write(f"Report Generated: **{d_latest.strftime('%Y-%m-%d')}**\n\n")
        f.write(f"This report presents a **10-day rolling daily sector analysis** of the NSE equity universe, ending **{d_latest.strftime('%Y-%m-%d')}**. ")
        f.write("The analysis assesses the health of industries by tracking the percentage of stocks above their 20-day EMA and 50-day SMA, relative strength performance, and distance to 52-week highs. ")
        f.write("Industries are classified into **Confirmed Uptrend, Early Uptrend, Consolidation, Downtrend Warning, and Avoid** to guide selective swing entries.\n\n")
        
        # Add Daily Capital Flow section
        f.write("## 💸 Daily Capital Flow & Sector Rotation\n")
        f.write(f"Analysis of rotation for the latest session (**{target_dates[-1].strftime('%Y-%m-%d')}** vs **{target_dates[-2].strftime('%Y-%m-%d')}**):\n\n")
        
        df_inflow = df_scaled[df_scaled['Part_Change'] > 0].sort_values('Part_Change', ascending=False)
        f.write("### 🟢 Top Sectors with Daily Inflow (Buying Pressure)\n")
        if not df_inflow.empty:
            f.write("| Industry | Stocks | Daily EMA20 % Change | Daily Avg Return | Status |\n")
            f.write("| :--- | :---: | :---: | :---: | :--- |\n")
            for _, r in df_inflow.head(8).iterrows():
                f.write(f"| **{r['Industry']}** | {r['Total_Stocks']} | +{r['Part_Change']:.1f}% | {r['Avg_Return_Today']:+.2f}% | Breadth expansion. Money entering. |\n")
        else:
            f.write("*No notable daily inflows.* \n")
        f.write("\n")
        
        df_outflow = df_scaled[df_scaled['Part_Change'] < 0].sort_values('Part_Change', ascending=True)
        f.write("### 🔴 Top Sectors with Daily Outflow (Selling Pressure)\n")
        if not df_outflow.empty:
            f.write("| Industry | Stocks | Daily EMA20 % Change | Daily Avg Return | Status |\n")
            f.write("| :--- | :---: | :---: | :---: | :--- |\n")
            for _, r in df_outflow.head(8).iterrows():
                f.write(f"| **{r['Industry']}** | {r['Total_Stocks']} | {r['Part_Change']:.1f}% | {r['Avg_Return_Today']:+.2f}% | Breadth contraction. Money exiting. |\n")
        else:
            f.write("*No notable daily outflows.* \n")
        f.write("\n")
        
        f.write("## 🔍 Stock-to-Industry Mapping Audit\n\n")
        if unlinked:
            f.write("> [!WARNING]\n")
            f.write(f"> **{len(unlinked)} Stocks are Unlinked or Blank** in the mapping file `industry stockname mapping.xlsx`.\n")
            f.write(f"> *Symbols ({len(unlinked)}):* " + ", ".join(unlinked) + "\n\n")
        else:
            f.write("> [!NOTE]\n")
            f.write("> All symbols are successfully mapped in the Excel file.\n\n")
            
        f.write("## 🗂️ Industry Trend Classification\n\n")
        
        categories = ["Confirmed Uptrend", "Early Uptrend", "Consolidation", "Downtrend Warning", "Avoid"]
        actions = {
            "Confirmed Uptrend": "AGGRESSIVE SWING TRADING: Focus on pullbacks, trail stops tightly.",
            "Early Uptrend": "BEST SWING ZONE: Focus on new VCP breakouts and sweet-spot stage-2 setups.",
            "Consolidation": "MONITOR FOR REVERSAL: Look for early breakout spark and tight ranges.",
            "Downtrend Warning": "MONITOR: Take very selective trades with tight risk controls.",
            "Avoid": "AVOID: Do not buy. Liquidate on bounces."
        }
        
        for cat in categories:
            df_cat = df_scaled[df_scaled['Category'] == cat]
            f.write(f"### 🟩 {cat.upper()} Industries (Total: {len(df_cat)})\n")
            f.write(f"**Recommended Action**: `{actions[cat]}`\n\n")
            
            f.write("| Industry | Stocks | Daily Ret | 10-Day Ret | EMA20 % | SMA50 % | Stacked % | High RS % | Near 52WH | Status |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |\n")
            for _, r in df_cat.iterrows():
                f.write(f"| **{r['Industry']}** | {r['Total_Stocks']} | {r['Avg_Return_Today']:+.2f}% | {r['Avg_Return_10D']:+.1f}% | {r['EMA20_Participation_Today']:.1f}% ({r['EMA20_Participation_Change']:+.1f}%) | {r['SMA50_Participation_Today']:.1f}% | {r['Breadth']:.1f}% | {r['RS_Participation_Today']:.1f}% | {r['Near52WH_Participation_Today']:.1f}% | {r['Explanation']} |\n")
            f.write("\n")
            
        f.write("## ⚠️ Deprioritized / Small-Scale Industries\n")
        f.write("| Industry | Stocks | Today Return | EMA20 % | Status / Action |\n")
        f.write("| :--- | :---: | :---: | :---: | :--- |\n")
        for _, r in df_unscaled.sort_values('Total_Stocks', ascending=False).iterrows():
            f.write(f"| {r['Industry']} | {r['Total_Stocks']} | {r['Avg_Return_Today']:+.1f}% | {r['EMA20_Participation_Today']:.1f}% | Insufficient scale. Monitor only. |\n")
        f.write("\n")
        
        f.write("## 🚀 Top Swing Candidates in Focus Industries\n")
        f.write("High-conviction stock ideas within the **Confirmed Uptrend**, **Early Uptrend**, and **Consolidation** industries:\n\n")
        f.write("| Symbol | Company Name | Industry | Price | Dist 52WH | Setup Quality Rank |\n")
        f.write("| :--- | :--- | :--- | :---: | :---: | :--- |\n")
        
        focus_inds = df_scaled[df_scaled['Category'].isin(["Confirmed Uptrend", "Early Uptrend", "Consolidation"])]
        all_candidates = []
        for _, r in focus_inds.iterrows():
            details = r['Stock_Details']
            # Take top 3 stocks from each focus industry
            all_candidates.extend(details[:3])
            
        all_candidates.sort(key=lambda x: x["Rank_Score"], reverse=True)
        for c in all_candidates[:15]:
            ind_name = c.get('Industry', 'Others')
            f.write(f"| **{c['Symbol']}** | {c['Company_Name']} | {ind_name} | ₹{c['Price']:.1f} | {c['Dist_52WH']:.1f}% | Rank score: {c['Rank_Score']:.2f} |\n")
            
    print(f"Industry report MD successfully written to {filepath_md}")
    
    if filepath_artifact:
        try:
            import shutil
            shutil.copy(filepath_md, filepath_artifact)
            print(f"Copied industry report to artifact directory: {filepath_artifact}")
        except Exception as e:
            print(f"Failed to copy report to artifact directory: {e}")

    # Output JSON file for frontend server
    json_path = "data/industry_participation_report.json"
    if not os.path.exists("data"):
        json_path = os.path.join("minervini_os", json_path)
        
    # Read yesterday's data before we overwrite it
    yesterday_focus = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f_y:
                y_list = json.load(f_y)
                # Map top 10 focus industries of yesterday
                for pos, item in enumerate(y_list[:10]):
                    yesterday_focus[item["Industry"]] = {
                        "Position": pos,
                        "Category": item.get("Category", "Neutral"),
                        "Score": item.get("Avg_Return_10D", 0.0) + item.get("Part_EMA20_Today", 0.0) / 10.0,
                        "Part_SMA50": item.get("Part_SMA50_Today", 0.0),
                        "Avg_Return_10D": item.get("Avg_Return_10D", 0.0)
                    }
        except Exception as e:
            print("Failed to read yesterday's JSON report for comparison:", e)
            
    json_data = []
    
    # 1. Scaled
    for idx_pos, r in enumerate(df_scaled.iterrows()):
        r_idx, r_val = r
        ind_name = r_val['Industry']
        
        # Calculate day-to-day changes for the industry focus list
        score_today = float(r_val['Avg_Return_10D']) + float(r_val['EMA20_Participation_Today']) / 10.0
        is_new = False
        new_reason = ""
        change = "constant"
        
        # Only tag as new/improved if it is in the focus category
        is_focus = r_val['Category'] in ["Confirmed Uptrend", "Early Uptrend", "Consolidation"]
        
        if is_focus:
            if ind_name in yesterday_focus:
                # Industry remained in the focus list
                y_item = yesterday_focus[ind_name]
                score_yesterday = y_item["Score"]
                if score_today > score_yesterday:
                    change = "up"
                elif score_today < score_yesterday:
                    change = "down"
                else:
                    change = "constant"
            else:
                # Industry is newly added to the Top 10 focus list
                is_new = True
                change = "new"
                
                # Determine reason for entrance
                part_sma50_today = float(r_val['SMA50_Participation_Today'])
                part_sma50_chg = float(r_val['SMA50_Participation_Change'])
                ret10 = float(r_val['Avg_Return_10D'])
                
                if part_sma50_chg >= 5.0:
                    new_reason = f"SMA50 participation expanded by {part_sma50_chg:+.1f}% today"
                elif ret10 >= 5.0:
                    new_reason = f"Rolling 10-day industry return surged to {ret10:+.1f}%"
                else:
                    new_reason = f"Industry momentum upgraded to focus category: {r_val['Category']}"
        
        # Revert stock detail candidates back to standard format
        clean_stock_details = []
        for stock_obj in r_val['Stock_Details']:
            clean_stock_details.append({
                "Symbol": stock_obj["Symbol"],
                "Company_Name": stock_obj["Company_Name"],
                "Industry": stock_obj.get("Industry", ind_name),
                "Price": stock_obj["Price"],
                "Dist_52WH": stock_obj["Dist_52WH"],
                "Rank_Score": stock_obj["Rank_Score"],
                "Ret_Today": stock_obj.get("Ret_Today", 0.0),
                "Above_EMA20": stock_obj.get("Above_EMA20", 0),
                "Above_SMA50": stock_obj.get("Above_SMA50", 0),
                "Above_SMA200": stock_obj.get("Above_SMA200", 0),
                "Stacked": stock_obj.get("Stacked", 0),
                "High_RS": stock_obj.get("High_RS", 0),
                "Pocket_Pivot": stock_obj.get("Pocket_Pivot", 0),
                "RS_D": stock_obj.get("RS_D", 50),
                "RS_W": stock_obj.get("RS_W", 50),
                "SMA200_Rising": stock_obj.get("SMA200_Rising", 0)
            })
            
        json_data.append({
            "Industry": ind_name,
            "Sector": r_val.get('Sector', 'Others'),
            "Zone": r_val.get('Zone', 'Avoid'),
            "ActiveStocks": float(r_val['Total_Stocks']),
            "Category": r_val['Category'],
            "Streak_Days": int(r_val['Streak_Days']),
            "Failure_Days": int(r_val['Failure_Days']),
            "Last_Updated_Date": d_latest.strftime("%Y-%m-%d"),
            "Part_Change": float(r_val['Part_Change']),
            "Avg_Return_Today": float(r_val['Avg_Return_Today']),
            "Avg_Return_10D": float(r_val['Avg_Return_10D']),
            "Breadth": float(r_val.get('Breadth', 0.0)),
            "Flow": float(r_val.get('Flow', 0.0)),
            "Flow_Val": float(r_val.get('Flow_Val', 0.0)),
            
            # New metrics
            "Net_Flow_Pct": float(r_val.get('Net_Flow_Pct', 0.0)),
            "Net_Flow_Score_Scaled": float(r_val.get('Net_Flow_Score_Scaled', 50.0)),
            "Pocket_Pivot_Pct": float(r_val.get('Pocket_Pivot_Pct', 0.0)),
            
            # Focus industry status keys
            "Is_New": bool(is_new),
            "New_Reason": new_reason,
            "Change": change,
            
            "W1_EMA20": float(r_val['EMA20_Participation_Today']),
            "W2_EMA20": float(r_val['EMA20_Participation_Today']),
            "W3_EMA20": float(r_val['EMA20_Participation_Today']),
            
            "W1_SMA50": float(r_val['SMA50_Participation_Today']),
            "W2_SMA50": float(r_val['SMA50_Participation_Today']),
            "W3_SMA50": float(r_val['SMA50_Participation_Today']),
            
            "Part_SMA50_Today": float(r_val['SMA50_Participation_Today']),
            "Part_SMA50_Change": float(r_val['SMA50_Participation_Change']),
            
            "Part_SMA200_Today": float(r_val['SMA200_Participation_Today']),
            "Part_SMA200_Change": float(r_val['SMA200_Participation_Change']),
            
            "Part_EMA20_Today": float(r_val['EMA20_Participation_Today']),
            "Part_EMA20_Change": float(r_val['EMA20_Participation_Change']),
            
            "Part_RS_Today": float(r_val['RS_Participation_Today']),
            "Part_RS_Change": float(r_val['RS_Participation_Change']),
            
            "Part_52WH_Today": float(r_val['Near52WH_Participation_Today']),
            "Part_52WH_Change": float(r_val['Near52WH_Participation_Change']),
            
            "Part_Stacked_Today": float(r_val['Breadth']),
            "Part_Stacked_Change": float(r_val['Breadth_Change']),
            
            "W1_Ret": float(r_val['Avg_Return_Today']),
            "W2_Ret": float(r_val['Avg_Return_Today']),
            "W3_Ret": float(r_val['Avg_Return_Today']),
            
            "Explanation": r_val['Explanation'],
            "Stocks": r_val['Stocks'],
            "Stock_Details": clean_stock_details
        })
        
    # 2. Unscaled
    for _, r in df_unscaled.iterrows():
        clean_stock_details_unscaled = []
        for stock_obj in r['Stock_Details']:
            clean_stock_details_unscaled.append({
                "Symbol": stock_obj["Symbol"],
                "Company_Name": stock_obj["Company_Name"],
                "Industry": stock_obj.get("Industry", r['Industry']),
                "Price": stock_obj["Price"],
                "Dist_52WH": stock_obj["Dist_52WH"],
                "Rank_Score": stock_obj["Rank_Score"],
                "Ret_Today": stock_obj.get("Ret_Today", 0.0),
                "Above_EMA20": stock_obj.get("Above_EMA20", 0),
                "Above_SMA50": stock_obj.get("Above_SMA50", 0),
                "Above_SMA200": stock_obj.get("Above_SMA200", 0),
                "Stacked": stock_obj.get("Stacked", 0),
                "High_RS": stock_obj.get("High_RS", 0),
                "Pocket_Pivot": stock_obj.get("Pocket_Pivot", 0),
                "RS_D": stock_obj.get("RS_D", 50),
                "RS_W": stock_obj.get("RS_W", 50),
                "SMA200_Rising": stock_obj.get("SMA200_Rising", 0)
            })
            
        json_data.append({
            "Industry": r['Industry'],
            "Sector": r.get('Sector', 'Others'),
            "Zone": r.get('Zone', 'Avoid'),
            "ActiveStocks": float(r['Total_Stocks']),
            "Category": r['Category'],
            "Streak_Days": int(r['Streak_Days']),
            "Failure_Days": int(r['Failure_Days']),
            "Last_Updated_Date": d_latest.strftime("%Y-%m-%d"),
            "Part_Change": float(r['Part_Change']),
            "Avg_Return_Today": float(r['Avg_Return_Today']),
            "Avg_Return_10D": float(r['Avg_Return_10D']),
            "Breadth": float(r.get('Breadth', 0.0)),
            "Flow": float(r.get('Flow', 0.0)),
            "Flow_Val": float(r.get('Flow_Val', 0.0)),
            
            # New metrics
            "Net_Flow_Pct": float(r.get('Net_Flow_Pct', 0.0)),
            "Net_Flow_Score_Scaled": float(r.get('Net_Flow_Score_Scaled', 50.0)),
            "Pocket_Pivot_Pct": float(r.get('Pocket_Pivot_Pct', 0.0)),
            
            "W1_EMA20": float(r['EMA20_Participation_Today']),
            "W2_EMA20": float(r['EMA20_Participation_Today']),
            "W3_EMA20": float(r['EMA20_Participation_Today']),
            
            "W1_SMA50": float(r['SMA50_Participation_Today']),
            "W2_SMA50": float(r['SMA50_Participation_Today']),
            "W3_SMA50": float(r['SMA50_Participation_Today']),
            
            "Part_SMA50_Today": float(r['SMA50_Participation_Today']),
            "Part_SMA50_Change": float(r['SMA50_Participation_Change']),
            
            "Part_SMA200_Today": float(r['SMA200_Participation_Today']),
            "Part_SMA200_Change": float(r['SMA200_Participation_Change']),
            
            "Part_EMA20_Today": float(r['EMA20_Participation_Today']),
            "Part_EMA20_Change": float(r['EMA20_Participation_Change']),
            
            "Part_RS_Today": float(r['RS_Participation_Today']),
            "Part_RS_Change": float(r['RS_Participation_Change']),
            
            "Part_52WH_Today": float(r['Near52WH_Participation_Today']),
            "Part_52WH_Change": float(r['Near52WH_Participation_Change']),
            
            "Part_Stacked_Today": float(r['Breadth']),
            "Part_Stacked_Change": float(r['Breadth_Change']),
            
            "W1_Ret": float(r['Avg_Return_Today']),
            "W2_Ret": float(r['Avg_Return_Today']),
            "W3_Ret": float(r['Avg_Return_Today']),
            
            "Explanation": "Insufficient scale (< 5 stocks) or volatile participation.",
            "Stocks": r['Stocks'],
            "Stock_Details": clean_stock_details_unscaled
        })
        
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f_json:
        json.dump(json_data, f_json, indent=2)
    # Also save dated copy
    d_latest_str = d_latest.strftime('%Y%m%d')
    dated_json_path = os.path.join(os.path.dirname(json_path), f"industry_participation_report_{d_latest_str}.json")
    with open(dated_json_path, "w", encoding="utf-8") as f_json_dated:
        json.dump(json_data, f_json_dated, indent=2)
        
    print(f"Industry report JSON successfully written to {json_path} (also saved to {dated_json_path})")
    
    csv_path = "data/industry_participation_report.csv"
    if not os.path.exists("data"):
        csv_path = os.path.join("minervini_os", csv_path)
    pd.concat([df_scaled, df_unscaled], ignore_index=True).to_csv(csv_path, index=False)
    print(f"Industry report CSV successfully written to {csv_path}")

if __name__ == "__main__":
    analyze_participation()
