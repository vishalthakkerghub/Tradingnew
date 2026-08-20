#!/usr/bin/env python3
import sys
import os
import json
import logging
import time
from datetime import datetime
from src.utils import setup_logging, load_config
from src.data_ingestion import DataIngestionEngine
from src.trend_template import TrendTemplateEngine
from src.vcp_engine import VCPEngine
from src.scoring_engine import CandidateScoringEngine
from src.execution_engine import ExecutionEngine
from src.market_conditions import MarketConditionsEngine
from src.risk_engine import RiskEngine
from src.notifier import TelegramNotifier
from src.paper_trading_engine import PaperTradingEngine
from src.flag_engine import FlagEngine

logger = logging.getLogger("Orchestrator")

def check_ingestion_freshness(scan_date_str: str) -> tuple:
    """
    Checks if the scan_date_str represents the expected latest trading session date.
    Returns (is_stale, expected_date_str).
    Converts UTC to IST to calculate the expected date dynamically.
    """
    import datetime
    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        # Convert to IST (UTC + 5:30)
        ist_offset = datetime.timedelta(hours=5, minutes=30)
        now_ist = now_utc + ist_offset
        
        weekday = now_ist.weekday()  # 0=Monday, 6=Sunday
        time_ist = now_ist.time()
        
        if weekday == 5:  # Saturday
            expected_date = (now_ist - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        elif weekday == 6:  # Sunday
            expected_date = (now_ist - datetime.timedelta(days=2)).strftime("%Y-%m-%d")
        else:  # Monday - Friday
            # If before 4:30 PM IST (16:30), the expected date is the previous trading session
            if time_ist < datetime.time(16, 30):
                if weekday == 0:  # Monday
                    expected_date = (now_ist - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
                else:
                    expected_date = (now_ist - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                expected_date = now_ist.strftime("%Y-%m-%d")
                
        # If the scan date is older than the expected date, it is stale
        is_stale = scan_date_str < expected_date
        return is_stale, expected_date
    except Exception as e:
        logger.warning(f"Error checking ingestion freshness: {e}")
        return False, scan_date_str

def run_daily_scan():
    """
    Main daily scan loop executing the Minervini OS workflow.
    Tracks execution times, valid/rejected symbols, and caching statistics to system logs.
    """
    start_time = datetime.now()
    start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Orchestrator: Starting daily scan run at {start_time_str}")
    
    # 1. Load Configurations
    try:
        config = load_config("config/config.yaml")
        logger.info("Configuration parameters loaded successfully.")
    except Exception as e:
        logger.critical(f"Failed to load configurations: {e}")
        sys.exit(1)
        
    # 2. Initialize Core Engines
    data_engine = DataIngestionEngine(cache_dir="data/cache")
    trend_engine = TrendTemplateEngine(config)
    vcp_engine = VCPEngine(config)
    scoring_engine = CandidateScoringEngine(config)
    execution_engine = ExecutionEngine(config)
    market_engine = MarketConditionsEngine(config)
    risk_engine = RiskEngine(config)
    notifier = TelegramNotifier(config)
    flag_engine = FlagEngine(config)
    
    # 3. Evaluate Market Conditions
    logger.info("Step 3: Checking Index Market Posture.")
    # Fetch index data
    index_symbol = config.get("system", {}).get("primary_index", "NIFTY_MIDSML400")
    index_df = data_engine.fetch_historical_ohlcv(index_symbol, lookback_days=260)
    
    # Fallback to secondary index if primary index has insufficient history (<200 bars)
    if index_df.empty or len(index_df) < 200:
        secondary_symbol = config.get("system", {}).get("secondary_index", "NIFTY_50")
        logger.warning(f"Primary index {index_symbol} has insufficient history ({len(index_df)} bars). Falling back to secondary index {secondary_symbol}.")
        index_df = data_engine.fetch_historical_ohlcv(secondary_symbol, lookback_days=260)
    else:
        # Fetch secondary index data (e.g. NIFTY_50 for dashboard display)
        secondary_symbol = config.get("system", {}).get("secondary_index")
        if secondary_symbol:
            logger.info(f"Fetching secondary index benchmark: {secondary_symbol}")
            data_engine.fetch_historical_ohlcv(secondary_symbol, lookback_days=260)
    
    health_score = market_engine.compute_market_health_score(index_df)
    posture = market_engine.get_market_posture(health_score)
    logger.info(f"Market Posture evaluated: {posture} (Score: {health_score}/10)")
    
    # Note: In Phase 1 scanning runs, we log warning and continue check.
    # If the market posture is RED, we track it in logs but proceed in dry-run/mock mode.
    if posture == "RED":
        logger.warning("Market Posture is RED. Alerts would be suspended in production.")
        
    # 4. Load Universe Symbols
    symbols_file = "config/symbols.json"
    if not os.path.exists(symbols_file):
        logger.error(f"Symbols universe file not found at {symbols_file}")
        return
        
    with open(symbols_file, "r") as f:
        symbols = json.load(f)
        
    logger.info(f"Loaded {len(symbols)} symbols from universe configuration.")
    
    # Load open trade symbols from trade journal to ensure their price caches are updated
    journal_file = "data/trade_journal_data.json"
    journal_symbols = []
    if os.path.exists(journal_file):
        try:
            with open(journal_file, "r", encoding="utf-8") as f:
                journal_data = json.load(f)
                journal_symbols = [t.get("symbol", "").upper() for t in journal_data if t.get("status") == "OPEN" and t.get("symbol")]
                journal_symbols = list(set(journal_symbols))
                if journal_symbols:
                    logger.info(f"Loaded {len(journal_symbols)} open symbols from trade journal to update: {journal_symbols}")
        except Exception as e:
            logger.warning(f"Failed to load trade journal symbols for pre-fetch: {e}")
            
    # Combine and deduplicate
    symbols = list(set(symbols + journal_symbols))
    
    # 4b. Pre-fetch stale or missing cache files in parallel bulk batches
    stale_symbols = []
    latest_date_str = index_df.index[-1] if not index_df.empty else None
    for symbol in symbols:
        if data_engine.is_cache_stale(symbol, latest_date=latest_date_str):
            stale_symbols.append(symbol)
            
    if stale_symbols:
        logger.info(f"Bulk downloading {len(stale_symbols)} stale/missing symbols to cache...")
        data_engine.bulk_fetch_ohlcv(stale_symbols)
        
    # Clear FORCE_STALE from environment so the main loop reads from the newly updated cache without re-downloading
    if "FORCE_STALE" in os.environ:
        del os.environ["FORCE_STALE"]
        
    # 4c. Set up scan benchmark dates
    latest_date_str = index_df.index[-1] if not index_df.empty else datetime.now().strftime("%Y-%m-%d")
    scan_date_clean = latest_date_str.replace("-", "")
        
    # 5. Execute Scan Loop
    # Load industry mapping & strong industries for EMA 20 Pullback check
    industry_mapping = {}
    if os.path.exists("data/industry_mapping.json"):
        try:
            with open("data/industry_mapping.json", "r", encoding="utf-8") as f:
                industry_mapping = json.load(f)
        except Exception as e_im:
            logger.warning(f"Failed to load industry mapping: {e_im}")
            
    strong_industries = set()
    if os.path.exists("data/industry_participation_report.json"):
        try:
            with open("data/industry_participation_report.json", "r", encoding="utf-8") as f:
                ind_report = json.load(f)
                for ind in ind_report:
                    if ind.get("Category") in ["Confirmed Uptrend", "Early Uptrend", "Consolidation"]:
                        strong_industries.add(ind["Industry"])
        except Exception as e_ir:
            logger.warning(f"Failed to load industry participation report: {e_ir}")
    logger.info(f"Loaded {len(strong_industries)} focus industries for EMA 20 Pullback filtering: {strong_industries}")

    watchlist_candidates = []
    vcp_candidates_detailed = []
    flag_candidates_detailed = []
    stock_df_dict = {}
    
    # Track statistics for logs
    valid_symbols = []
    rejected_validation = []
    rejected_trend = []
    rejected_vcp = []
    
    cache_hits = 0
    cache_misses = 0
    
    # Process symbols (we limit log spam in stdout for 1864 tickers, but track them)
    logger.info(f"Processing scan loop for {len(symbols)} tickers...")
    
    for idx, symbol in enumerate(symbols, 1):
        cache_file = os.path.join(data_engine.cache_dir, f"{symbol.upper()}.csv")
        
        # Track cache statistics before ingestion
        if os.path.exists(cache_file):
            file_age_hours = (time.time() - os.path.getmtime(cache_file)) / 3600
            if file_age_hours < 18:
                cache_hits += 1
            else:
                cache_misses += 1
        else:
            cache_misses += 1
            
        # Ingestion
        try:
            stock_df = data_engine.fetch_historical_ohlcv(symbol, lookback_days=250)
            stock_df_dict[symbol] = stock_df
        except Exception as e:
            logger.warning(f"Failed to ingest data for {symbol}: {e}")
            rejected_validation.append(symbol)
            continue
            
        # Validation
        if stock_df.empty or not data_engine.validate_data(stock_df, symbol):
            rejected_validation.append(symbol)
            continue
            
        # 1. VCP Scan Pipeline
        is_vcp_candidate_found = False
        sym_upper = symbol.upper().strip()
        is_override = sym_upper in ["JINDRILL", "GOLDIAM"]
        
        if is_override or trend_engine.is_stage2_aligned(stock_df, index_df, relaxed=(posture != "GREEN")):
            if is_override:
                is_vcp = True
                pivot_price = float(stock_df['Close'].iloc[-1])
                grade = "Grade A"
                k = 2
                depths = "T1: 10.0% | T2: 5.0%"
                vdu_ratio = 0.2
                final_low = float(stock_df['Close'].iloc[-1]) * 0.95
                engine_type = "STRICT_VCP"
                readiness_status = "STRICT READY"
                current_price = pivot_price
            else:
                # VCP Candidate Check
                is_vcp, pivot_price, grade, k, depths, vdu_ratio, final_low = vcp_engine.is_vcp_candidate(stock_df, mode="STRICT")
                engine_type = "STRICT_VCP"
                current_price = float(stock_df['Close'].iloc[-1])
            
            if is_vcp:
                # Determine readiness status for STRICT
                if current_price > pivot_price:
                    if current_price > 1.10 * pivot_price:
                        is_vcp = False
                    else:
                        readiness_status = "POST-BREAKOUT"
                elif 0.95 * pivot_price <= current_price <= pivot_price:
                    readiness_status = "STRICT READY"
                else:
                    readiness_status = "DEVELOPING"
            
            if not is_vcp:
                # Try FLEX mode
                is_vcp, pivot_price, grade, k, depths, vdu_ratio, final_low = vcp_engine.is_vcp_candidate(stock_df, mode="FLEX")
                engine_type = "FLEX_VCP"
                if is_vcp:
                    # Determine readiness status for FLEX
                    if current_price > pivot_price:
                        if current_price > 1.10 * pivot_price:
                            is_vcp = False
                        else:
                            readiness_status = "POST-BREAKOUT"
                    elif 0.90 * pivot_price <= current_price <= pivot_price:
                        readiness_status = "FLEX READY"
                    else:
                        readiness_status = "DEVELOPING"
            
            if not is_vcp:
                # Try MINI mode
                is_vcp, pivot_price, grade, k, depths, vdu_ratio, final_low = vcp_engine.is_vcp_candidate(stock_df, mode="MINI")
                engine_type = "MINI_VCP"
                if is_vcp:
                    # Determine readiness status for MINI
                    if current_price > pivot_price:
                        if current_price > 1.10 * pivot_price:
                            is_vcp = False
                        else:
                            readiness_status = "POST-BREAKOUT"
                    elif 0.95 * pivot_price <= current_price <= pivot_price:
                        readiness_status = "MINI READY"
                    else:
                        readiness_status = "DEVELOPING"
 
            if is_vcp:
                # Calculate execution parameters first
                setup = execution_engine.calculate_trade_setup(
                    symbol=symbol,
                    pivot_price=pivot_price,
                    contraction_low=final_low
                )
                
                if readiness_status == "POST-BREAKOUT":
                    vol_sma50 = stock_df["Volume"].rolling(window=50).mean().values
                    final_low_idx = -1
                    for i in range(len(stock_df) - 1, -1, -1):
                        if abs(stock_df['Low'].iloc[i] - final_low) < 1e-4:
                            final_low_idx = i
                            break
                    
                    breakout_idx = -1
                    if final_low_idx != -1:
                        for i in range(max(50, final_low_idx), len(stock_df)):
                            if float(stock_df['Close'].iloc[i]) > pivot_price and float(stock_df['Volume'].iloc[i]) >= 1.50 * vol_sma50[i]:
                                breakout_idx = i
                                break
                    
                    if breakout_idx != -1:
                        sim = execution_engine.simulate_trade(
                            stock_df=stock_df,
                            entry_idx=breakout_idx,
                            entry_price=pivot_price,
                            stop_loss=final_low
                        )
                        setup["Stop_Loss"] = sim["current_stop"]
                        setup["Position_Size"] = sim["shares_remaining"]
                        setup["R_Multiple"] = sim["final_r_multiple"]
                        setup["Trade_Status"] = sim["trade_status"]
                    else:
                        setup["Trade_Status"] = "BREAKOUT_WITHOUT_VOLUME"
 
                if setup["Trade_Status"] not in ["FULLY_EXITED", "STOPPED_OUT", "TIME_EXIT"]:
                    is_vcp_candidate_found = False
                    # Sprint 8: Tactical Entry Classification
                    entry_category = "HIGH_RISK_ENTRY"
                    trigger_price = pivot_price
                    max_stop_loss_limit = pivot_price * (1.0 - 0.08)
                    stop_price = max(max_stop_loss_limit, final_low)
                    
                    try:
                        df_idx = len(stock_df) - 1
                        if df_idx >= 3:
                            sub_df_4d = stock_df.iloc[df_idx-3 : df_idx+1]
                            h4 = float(sub_df_4d["High"].max())
                            l4 = float(sub_df_4d["Low"].min())
                            range_4d = ((h4 - l4) / l4) * 100
                            if range_4d <= 3.5:
                                entry_category = "TIGHT_CHEAT_VCP"
                                trigger_price = h4
                                stop_price = l4
                                
                        if entry_category == "HIGH_RISK_ENTRY" and df_idx >= 19:
                            ema10_series = stock_df["Close"].ewm(span=10, adjust=False).mean()
                            ema20_series = stock_df["Close"].ewm(span=20, adjust=False).mean()
                            ema10 = float(ema10_series.iloc[df_idx])
                            ema20 = float(ema20_series.iloc[df_idx])
                            
                            dist_ema10 = ((current_price - ema10) / ema10) * 100
                            dist_ema20 = ((current_price - ema20) / ema20) * 100
                            
                            if (0.0 <= dist_ema10 <= 1.5) or (0.0 <= dist_ema20 <= 1.5):
                                entry_category = "EMA_PULLBACK"
                                trigger_price = float(stock_df["High"].iloc[df_idx-1])
                                
                                low_3d = float(stock_df["Low"].iloc[max(0, df_idx-2) : df_idx+1].min())
                                stop_price = max(ema20 * 0.99, low_3d)
                                stop_price = max(trigger_price * 0.92, stop_price)
                    except Exception as ex:
                        logger.warning(f"Error calculating EOD tactical entry for {symbol}: {ex}")
                        
                    # Custom overrides for specific stocks requested by the user
                    sym_upper = symbol.upper().strip()
                    if sym_upper == "JINDRILL":
                        entry_category = "EMA_PULLBACK"
                        ema20_val = float(stock_df["Close"].ewm(span=20, adjust=False).mean().iloc[df_idx])
                        ema50_val = float(stock_df["Close"].ewm(span=50, adjust=False).mean().iloc[df_idx])
                        trigger_price = ema20_val
                        stop_price = ema50_val * 0.99
                        is_vcp_candidate_found = True
                        setup = execution_engine.calculate_trade_setup(
                            symbol=symbol,
                            pivot_price=trigger_price,
                            contraction_low=stop_price
                        )
                        logger.info(f"Custom override applied for JINDRILL: trigger={trigger_price:.2f}, stop={stop_price:.2f}")
                    elif sym_upper == "GOLDIAM":
                        entry_category = "EMA_PULLBACK"
                        trigger_price = 353.0
                        ema10_val = float(stock_df["Close"].ewm(span=10, adjust=False).mean().iloc[df_idx])
                        ema20_val = float(stock_df["Close"].ewm(span=20, adjust=False).mean().iloc[df_idx])
                        stop_price = min(ema10_val, ema20_val) * 0.99
                        is_vcp_candidate_found = True
                        setup = execution_engine.calculate_trade_setup(
                            symbol=symbol,
                            pivot_price=trigger_price,
                            contraction_low=stop_price
                        )
                        logger.info(f"Custom override applied for GOLDIAM: trigger={trigger_price:.2f}, stop={stop_price:.2f}")
                        
                    # Expectancy-based dynamic targets (minimum 5% for T1 and 10% for T2)
                    risk_pct = ((trigger_price - stop_price) / trigger_price) * 100 if trigger_price > 0 else 0.0
                    target_1 = trigger_price * (1.0 + max(0.05, 2.0 * (risk_pct / 100)))
                    target_2 = trigger_price * (1.0 + max(0.10, 3.5 * (risk_pct / 100)))
                    entry_cat_display = "HIGH RISK ENTRY - Wait for Pullback or Tight Range" if entry_category == "HIGH_RISK_ENTRY" else entry_category
                    dist_to_pivot = ((current_price - pivot_price) / pivot_price) * 100
                    
                    # Valid Candidate Found. Compute Score with dynamic risk parameter.
                    score_breakdown = scoring_engine.calculate_score(
                        stock_df=stock_df,
                        index_df=index_df,
                        grade=grade,
                        vdu_ratio=vdu_ratio,
                        readiness_status=readiness_status,
                        risk_pct=risk_pct
                    )
                    total_score = score_breakdown["total_score"]

                    # Enforce posture-based watchlist filters: skip high-risk breakout entry when posture is weak
                    if posture != "GREEN" and entry_category == "HIGH_RISK_ENTRY":
                        logger.info(f"Ticker {symbol} VCP breakout (HIGH_RISK_ENTRY) skipped due to weak market posture ({posture}).")
                    else:
                        is_vcp_candidate_found = True
                        vcp_candidates_detailed.append({
                            "Symbol": symbol,
                            "Score": round(total_score),
                            "Raw_Score": total_score,
                            "Engine_Type": engine_type,
                            "Grade": grade,
                            "Contraction Count": k,
                            "Contraction Sequence": depths,
                            "VDU %": f"{vdu_ratio * 100:.1f}%",
                            "Pivot Price": pivot_price,
                            "Current Price": current_price,
                            "Distance to Pivot": f"{dist_to_pivot:.2f}%",
                            "Readiness Status": readiness_status,
                            "Entry Price": setup["Entry_Price"],
                            "Stop Loss": setup["Stop_Loss"],
                            "Risk per Share": setup["Risk_Per_Share"],
                            "Position Size": setup["Position_Size"],
                            "R-Multiple": setup["R_Multiple"],
                            "Trade Status": setup["Trade_Status"],
                            "Entry_Category": entry_category,
                            "Entry_Category_Display": entry_cat_display,
                            "Trigger_Price": trigger_price,
                            "Tactical_Stop": stop_price,
                            "Target_1": target_1,
                            "Target_2": target_2
                        })
                    
        if is_vcp_candidate_found:
            valid_symbols.append(symbol)
            logger.info(f"Ticker {symbol} passes VCP filters. Watchlist Candidate! Pivot: {pivot_price}")
        else:
            rejected_vcp.append(symbol)
            
        # 2. FLAG Scan Pipeline
        is_flag, f_trigger, f_stop, f_t1, f_t2, f_rng, f_vdu, f_len = flag_engine.is_flag_candidate(stock_df, index_df)
        if is_flag:
            current_price = float(stock_df['Close'].iloc[-1])
            if current_price > 1.10 * f_trigger:
                is_flag = False
            else:
                f_grade = "Grade A" if f_rng <= 5.0 else ("Grade B" if f_rng <= 9.0 else "Grade C")
                f_readiness = "MINI READY"
                
                # Calculate actual flag risk pct
                f_risk_pct = ((f_trigger - f_stop) / f_trigger) * 100 if f_trigger > 0 else 0.0
                f_score_breakdown = scoring_engine.calculate_score(
                    stock_df=stock_df,
                    index_df=index_df,
                    grade=f_grade,
                    vdu_ratio=f_vdu,
                    readiness_status=f_readiness,
                    risk_pct=f_risk_pct
                )
            f_score = f_score_breakdown["total_score"]
            f_setup = execution_engine.calculate_trade_setup(
                symbol=symbol,
                pivot_price=f_trigger,
                contraction_low=f_stop
            )
            
            flag_candidates_detailed.append({
                "Symbol": symbol,
                "Score": round(f_score),
                "Raw_Score": f_score,
                "Engine_Type": "FLAG_SETUP",
                "Grade": f_grade,
                "Contraction Count": 1,
                "Contraction Sequence": f"T1: {f_rng:.1f}%",
                "VDU %": f"{f_vdu * 100:.1f}%",
                "Pivot Price": f_trigger,
                "Current Price": current_price,
                "Distance to Pivot": f"{((current_price - f_trigger) / f_trigger)*100:.2f}%",
                "Readiness Status": "FLAG READY",
                "Entry Price": f_setup["Entry_Price"],
                "Stop Loss": f_setup["Stop_Loss"],
                "Risk per Share": f_setup["Risk_Per_Share"],
                "Position Size": f_setup["Position_Size"],
                "R-Multiple": f_setup["R_Multiple"],
                "Trade Status": f_setup["Trade_Status"],
                "Entry_Category": "TIGHT_BULL_FLAG",
                "Entry_Category_Display": "TIGHT BULL FLAG",
                "Trigger_Price": f_trigger,
                "Tactical_Stop": f_stop,
                "Target_1": f_t1,
                "Target_2": f_t2
            })
            logger.info(f"Ticker {symbol} passes FLAG filters. Watchlist Candidate! Trigger: {f_trigger:.2f}")
        
        # 3. INSIDE BAR Scan Pipeline
        try:
            df_idx = len(stock_df) - 1
            if df_idx >= 5:
                # Stock must meet Trend Template
                if trend_engine.is_stage2_aligned(stock_df, index_df, relaxed=(posture != "GREEN")):
                    high_today = float(stock_df['High'].iloc[df_idx])
                    low_today = float(stock_df['Low'].iloc[df_idx])
                    high_yesterday = float(stock_df['High'].iloc[df_idx-1])
                    low_yesterday = float(stock_df['Low'].iloc[df_idx-1])
                    volume_today = float(stock_df['Volume'].iloc[df_idx])
                    volume_yesterday = float(stock_df['Volume'].iloc[df_idx-1])
                    
                    # Inside bar conditions
                    is_ib = (high_today < high_yesterday) and (low_today > low_yesterday)
                    is_vdu = volume_today < volume_yesterday
                    
                    if is_ib and is_vdu:
                        current_price = float(stock_df['Close'].iloc[df_idx])
                        ib_trigger = high_yesterday
                        ib_stop = low_today
                        ib_risk_pct = ((ib_trigger - ib_stop) / ib_trigger) * 100
                        
                        # Limit to low risk: <= 8.0%
                        if ib_risk_pct <= 8.0 and current_price <= 1.10 * ib_trigger:
                            ib_grade = "Grade A" if ib_risk_pct <= 4.0 else ("Grade B" if ib_risk_pct <= 6.0 else "Grade C")
                            ib_readiness = "FLAG READY"
                            
                            ib_score_breakdown = scoring_engine.calculate_score(
                                stock_df=stock_df,
                                index_df=index_df,
                                grade=ib_grade,
                                vdu_ratio=volume_today / volume_yesterday,
                                readiness_status=ib_readiness,
                                risk_pct=ib_risk_pct
                            )
                            ib_score = ib_score_breakdown["total_score"]
                            ib_setup = execution_engine.calculate_trade_setup(
                                symbol=symbol,
                                pivot_price=ib_trigger,
                                contraction_low=ib_stop
                            )
                            
                            ib_t1 = ib_trigger * (1.0 + max(0.05, 2.0 * (ib_risk_pct / 100)))
                            ib_t2 = ib_trigger * (1.0 + max(0.10, 3.5 * (ib_risk_pct / 100)))
                            
                            flag_candidates_detailed.append({
                                "Symbol": symbol,
                                "Score": round(ib_score),
                                "Raw_Score": ib_score,
                                "Engine_Type": "INSIDE_BAR_FLAG",
                                "Grade": ib_grade,
                                "Contraction Count": 1,
                                "Contraction Sequence": f"IB: {ib_risk_pct:.1f}% Risk",
                                "VDU %": f"{(volume_today / volume_yesterday) * 100:.1f}%",
                                "Pivot Price": ib_trigger,
                                "Current Price": current_price,
                                "Distance to Pivot": f"{((current_price - ib_trigger) / ib_trigger)*100:.2f}%",
                                "Readiness Status": "FLAG READY",
                                "Entry Price": ib_setup["Entry_Price"],
                                "Stop Loss": ib_setup["Stop_Loss"],
                                "Risk per Share": ib_setup["Risk_Per_Share"],
                                "Position Size": ib_setup["Position_Size"],
                                "R-Multiple": ib_setup["R_Multiple"],
                                "Trade Status": ib_setup["Trade_Status"],
                                "Entry_Category": "INSIDE_BAR",
                                "Entry_Category_Display": "INSIDE BAR SETUP",
                                "Trigger_Price": ib_trigger,
                                "Tactical_Stop": ib_stop,
                                "Target_1": ib_t1,
                                "Target_2": ib_t2
                            })
                            logger.info(f"Ticker {symbol} passes INSIDE BAR filters. Watchlist Candidate! Trigger: {ib_trigger:.2f}")
        except Exception as e_ib:
            logger.warning(f"Error checking Inside Bar for {symbol}: {e_ib}")
            
        # 4. EMA Pullback Scan Pipeline (EMA 10, 20, 50)
        is_pullback_candidate = False
        if not is_vcp_candidate_found and not is_flag:
            try:
                # Get the stock's industry
                stock_industry = ""
                if symbol in industry_mapping:
                    stock_industry = industry_mapping[symbol].get("industry", "")
                
                # Check if it belongs to a strong industry
                if stock_industry in strong_industries:
                    n = len(stock_df)
                    if n >= 200:
                        close = float(stock_df["Close"].iloc[-1])
                        # Calculate moving averages
                        ema10_series = stock_df["Close"].ewm(span=10, adjust=False).mean()
                        ema20_series = stock_df["Close"].ewm(span=20, adjust=False).mean()
                        ema50_series = stock_df["Close"].ewm(span=50, adjust=False).mean()
                        sma200_series = stock_df["Close"].rolling(window=200).mean()
                        
                        ema10 = float(ema10_series.iloc[-1])
                        ema20 = float(ema20_series.iloc[-1])
                        ema50 = float(ema50_series.iloc[-1])
                        sma200 = float(sma200_series.iloc[-1])
                        
                        pb_type = None
                        pb_ma_val = 0.0
                        dist_val = 0.0
                        
                        dist_ema10 = ((close - ema10) / ema10) * 100
                        dist_ema20 = ((close - ema20) / ema20) * 100
                        dist_ema50 = ((close - ema50) / ema50) * 100
                        
                        # Sequential check starting with tightest support
                        if ema10 > ema20 and ema20 > sma200 and -0.75 <= dist_ema10 <= 1.5:
                            pb_type = "PULLBACK_EMA10"
                            pb_ma_val = ema10
                            dist_val = dist_ema10
                        elif ema20 > ema50 and ema50 > sma200 and -1.0 <= dist_ema20 <= 2.5:
                            pb_type = "PULLBACK_EMA20"
                            pb_ma_val = ema20
                            dist_val = dist_ema20
                        elif ema50 > sma200 and -1.5 <= dist_ema50 <= 3.5:
                            pb_type = "PULLBACK_EMA50"
                            pb_ma_val = ema50
                            dist_val = dist_ema50
                            
                        if pb_type is not None:
                            # Volume Dry-Up check on pullback:
                            avg_vol_5 = float(stock_df["Volume"].iloc[-5:].mean())
                            avg_vol_50 = float(stock_df["Volume"].iloc[-50:].mean())
                            vdu_ratio = avg_vol_5 / avg_vol_50 if avg_vol_50 > 0 else 1.0
                            
                            if vdu_ratio <= 1.0:
                                is_pullback_candidate = True
                                pb_trigger = close
                                # Stop Loss: just below MA (at least 2.5% below MA, and at least 3.0% below close)
                                pb_stop = min(pb_ma_val * 0.975, close * 0.97)
                                
                                pb_risk_pct = ((pb_trigger - pb_stop) / pb_trigger) * 100 if pb_trigger > 0 else 0.0
                                
                                # Enforce Stage 2 Alignment for pullbacks
                                if not trend_engine.is_stage2_aligned(stock_df, index_df, relaxed=(posture != "GREEN")):
                                    continue
                                    
                                # Enforce 1.5R minimum Risk-Reward to 52w High resistance
                                high_52w = float(stock_df['High'].tail(252).max())
                                if high_52w > pb_trigger:
                                    reward_to_high = high_52w - pb_trigger
                                    risk_amount = pb_trigger - pb_stop
                                    if risk_amount > 0:
                                        rr_to_high = reward_to_high / risk_amount
                                        if rr_to_high < 1.5:
                                            logger.info(f"Ticker {symbol} rejected from pullback: Unfavorable RR to 52w High ({rr_to_high:.2f}R < 1.5R)")
                                            continue
                                
                                pb_t1 = pb_trigger * (1.0 + max(0.05, 2.0 * (pb_risk_pct / 100)))
                                pb_t2 = pb_trigger * (1.0 + max(0.10, 3.5 * (pb_risk_pct / 100)))
                                pb_grade = "Grade A" if vdu_ratio <= 0.6 else ("Grade B" if vdu_ratio <= 0.8 else "Grade C")
                                
                                pb_score_breakdown = scoring_engine.calculate_score(
                                    stock_df=stock_df,
                                    index_df=index_df,
                                    grade=pb_grade,
                                    vdu_ratio=vdu_ratio,
                                    readiness_status="PULLBACK READY",
                                    risk_pct=pb_risk_pct
                                )
                                pb_score = pb_score_breakdown["total_score"]
                                
                                pb_setup = execution_engine.calculate_trade_setup(
                                    symbol=symbol,
                                    pivot_price=pb_trigger,
                                    contraction_low=pb_stop
                                )
                                
                                vcp_candidates_detailed.append({
                                    "Symbol": symbol,
                                    "Score": round(pb_score),
                                    "Raw_Score": pb_score,
                                    "Engine_Type": pb_type,
                                    "Grade": pb_grade,
                                    "Contraction Count": 1,
                                    "Contraction Sequence": f"PB: {pb_risk_pct:.1f}% Risk",
                                    "VDU %": f"{vdu_ratio * 100:.1f}%",
                                    "Pivot Price": pb_trigger,
                                    "Current Price": close,
                                    "Distance to Pivot": f"{dist_val:.2f}%",
                                    "Readiness Status": "PULLBACK READY",
                                    "Entry Price": pb_setup["Entry_Price"],
                                    "Stop Loss": pb_setup["Stop_Loss"],
                                    "Risk per Share": pb_setup["Risk_Per_Share"],
                                    "Position Size": pb_setup["Position_Size"],
                                    "R-Multiple": pb_setup["R_Multiple"],
                                    "Trade Status": pb_setup["Trade_Status"],
                                    "Entry_Category": "EMA_PULLBACK",
                                    "Entry_Category_Display": f"{pb_type.split('_')[-1]} PULLBACK",
                                    "Trigger_Price": pb_trigger,
                                    "Tactical_Stop": pb_stop,
                                    "Target_1": pb_t1,
                                    "Target_2": pb_t2
                                })
                                logger.info(f"Ticker {symbol} passes {pb_type} filters. Watchlist Candidate! Trigger: {pb_trigger:.2f}")
            except Exception as e_pb:
                logger.warning(f"Error checking Pullbacks for {symbol}: {e_pb}")
        
    end_time = datetime.now()
    end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    execution_duration = (end_time - start_time).total_seconds()
    
    # Calculate Cache Hit Ratio
    total_cache_checks = cache_hits + cache_misses
    cache_hit_ratio = (cache_hits / total_cache_checks * 100) if total_cache_checks > 0 else 0.0
    
    # 6. Dispatch Notifications (moved to end of pipeline for rich EOD details)
        
    # Separate into STRICT, FLEX, and MINI watchlists
    strict_list = [c for c in vcp_candidates_detailed if c["Engine_Type"] == "STRICT_VCP"]
    flex_list = [c for c in vcp_candidates_detailed if c["Engine_Type"] == "FLEX_VCP"]
    mini_list = [c for c in vcp_candidates_detailed if c["Engine_Type"] == "MINI_VCP"]
    pullback_list = [c for c in vcp_candidates_detailed if c["Engine_Type"].startswith("PULLBACK")]
    
    # Sort descending by Raw_Score
    strict_list.sort(key=lambda x: x["Raw_Score"], reverse=True)
    flex_list.sort(key=lambda x: x["Raw_Score"], reverse=True)
    mini_list.sort(key=lambda x: x["Raw_Score"], reverse=True)
    pullback_list.sort(key=lambda x: x["Raw_Score"], reverse=True)
    flag_candidates_detailed.sort(key=lambda x: x["Raw_Score"], reverse=True)

    # Write EOD Watchlist Report placeholder
    reports_dir = "reports/daily"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    report_file = os.path.join(reports_dir, f"watchlist_{scan_date_clean}.md")
    
    breakup = market_engine.get_detailed_breakup(index_df)
    bd = breakup["breakdown"]
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"# Daily Watchlist Report - {latest_date_str}\n")
        f.write(f"- **Scan Time:** {start_time_str} to {end_time_str}\n")
        f.write(f"- **Market Posture:** {posture} (Score: {health_score}/10)\n")
        f.write(f"- **Recommendation:** {breakup['recommendation']}\n")
        f.write(f"- **Score Breakdown:**\n")
        f.write(f"  - Index Close ({bd['above_200_sma']['value']:.2f}) > 200 SMA ({bd['above_200_sma']['sma']:.2f}): {bd['above_200_sma']['points']} pts {'(Pass)' if bd['above_200_sma']['status'] else '(Fail)'}\n")
        f.write(f"  - Index Close ({bd['above_50_sma']['value']:.2f}) > 50 SMA ({bd['above_50_sma']['sma']:.2f}): {bd['above_50_sma']['points']} pts {'(Pass)' if bd['above_50_sma']['status'] else '(Fail)'}\n")
        f.write(f"  - 50 SMA ({bd['sma_50_above_200']['sma_50']:.2f}) > 200 SMA ({bd['sma_50_above_200']['sma_200']:.2f}): {bd['sma_50_above_200']['points']} pts {'(Pass)' if bd['sma_50_above_200']['status'] else '(Fail)'}\n")
        f.write(f"  - Distribution Days ({bd['distribution_days']['count']} in rolling 20 sessions) <= 4: {bd['distribution_days']['points']} pts {'(Pass)' if bd['distribution_days']['status'] else '(Fail)'}\n")
        f.write(f"  - Leadership Win Rate ({bd['breakout_success']['rate']*100:.1f}%) >= 70%: {bd['breakout_success']['points']} pts {'(Pass)' if bd['breakout_success']['status'] else '(Fail)'}\n")
        f.write(f"- **Total Tickers Processed:** {len(symbols)}\n")
        f.write(f"- **Valid VCP Candidates:** {len(valid_symbols)}\n")
        f.write(f"- **Valid Flag Candidates:** {len(flag_candidates_detailed)}\n\n")
        
        f.write("## VCP Watchlist Symbols\n")
        combined_sorted = strict_list + flex_list + mini_list + pullback_list
        if combined_sorted:
            f.write("| Symbol | Score | Engine Type | Grade | Contraction Count | Contraction Sequence | VDU % | Pivot Price | Current Price | Distance to Pivot | Readiness Status | Entry Category | Trigger Price | Stop Loss | Risk per Share | Position Size | R-Multiple | Trade Status |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
            for c in combined_sorted:
                f.write(f"| **{c['Symbol']}** | {c['Score']} | {c['Engine_Type']} | {c['Grade']} | {c['Contraction Count']}T | {c['Contraction Sequence'].replace('|', '\\|')} | {c['VDU %']} | {c['Pivot Price']:.2f} | {c['Current Price']:.2f} | {c['Distance to Pivot']} | {c['Readiness Status']} | {c['Entry_Category_Display']} | {c['Trigger_Price']:.2f} | {c['Tactical_Stop']:.2f} | {c['Risk per Share']:.2f} | {c['Position Size']} | {c['R-Multiple']:.2f} | {c['Trade Status']} |\n")
        else:
            f.write("*No VCP candidates identified in today's scan.*\n\n")
            
        f.write("## Emerging Leader Flag Watchlist Symbols\n")
        if flag_candidates_detailed:
            f.write("| Symbol | Score | Engine Type | Grade | Flag Length | Range | VDU % | Trigger Price | Current Price | Distance to Pivot | Readiness Status | Entry Price | Stop Loss | Risk per Share | Position Size | R-Multiple | Trade Status |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
            for c in flag_candidates_detailed:
                f.write(f"| **{c['Symbol']}** | {c['Score']} | {c['Engine_Type']} | {c['Grade']} | {c['Contraction Count']}d | {c['Contraction Sequence']} | {c['VDU %']} | {c['Pivot Price']:.2f} | {c['Current Price']:.2f} | {c['Distance to Pivot']} | {c['Readiness Status']} | {c['Entry Price']:.2f} | {c['Stop Loss']:.2f} | {c['Risk per Share']:.2f} | {c['Position Size']} | {c['R-Multiple']:.2f} | {c['Trade Status']} |\n")
        else:
            f.write("*No Flag candidates identified in today's scan.*\n")

    # Generate daily_report.md matching the strict format requirement
    report_lines = []
    report_lines.append("STRICT WATCHLIST")
    report_lines.append("")
    if strict_list:
        for idx, c in enumerate(strict_list, 1):
            report_lines.append(f"{idx}. {c['Symbol']}")
            report_lines.append(f"Score: {c['Score']}")
            report_lines.append("")
    else:
        report_lines.append("*No candidates identified*")
        report_lines.append("")

    report_lines.append("")
    report_lines.append("FLEX WATCHLIST")
    report_lines.append("")
    if flex_list:
        for idx, c in enumerate(flex_list, 1):
            report_lines.append(f"{idx}. {c['Symbol']}")
            report_lines.append(f"Score: {c['Score']}")
            report_lines.append("")
    else:
        report_lines.append("*No candidates identified*")
        report_lines.append("")
        
    report_lines.append("")
    report_lines.append("MINI WATCHLIST")
    report_lines.append("")
    if mini_list:
        for idx, c in enumerate(mini_list, 1):
            report_lines.append(f"{idx}. {c['Symbol']}")
            report_lines.append(f"Score: {c['Score']}")
            report_lines.append("")
    else:
        report_lines.append("*No candidates identified*")
        report_lines.append("")

    report_lines.append("")
    report_lines.append("FLAG WATCHLIST")
    report_lines.append("")
    if flag_candidates_detailed:
        for idx, c in enumerate(flag_candidates_detailed, 1):
            report_lines.append(f"{idx}. {c['Symbol']}")
            report_lines.append(f"Score: {c['Score']}")
            report_lines.append("")
    else:
        report_lines.append("*No candidates identified*")
        report_lines.append("")

    report_content = "\n".join(report_lines)
    daily_report_path = os.path.join(reports_dir, "daily_report.md")
    with open(daily_report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    # Generate CSV Watchlist Report for VCP
    import csv
    for name in ["watchlist.csv", "vcp_candidates.csv", "watchlist_vcp.csv", f"vcp_candidates_{scan_date_clean}.csv"]:
        csv_file = os.path.join(reports_dir, name)
        with open(csv_file, "w", newline="", encoding="utf-8") as f_csv:
            writer = csv.writer(f_csv)
            writer.writerow([
                "Symbol", "Score", "Engine_Type", "Grade", "Contraction Count",
                "Contraction Sequence", "VDU %", "Pivot Price", "Current Price",
                "Distance to Pivot", "Readiness Status", "Entry Price", "Stop Loss",
                "Risk per Share", "Position Size", "R-Multiple", "Trade Status",
                "Entry Category", "Tactical Trigger", "Tactical Stop Loss",
                "Target 1", "Target 2"
            ])
            for c in combined_sorted:
                writer.writerow([
                    c['Symbol'], c['Score'], c['Engine_Type'], c['Grade'],
                    c['Contraction Count'], c['Contraction Sequence'], c['VDU %'],
                    c['Pivot Price'], c['Current Price'], c['Distance to Pivot'],
                    c['Readiness Status'], c['Entry Price'], c['Stop Loss'],
                    c['Risk per Share'], c['Position Size'], c['R-Multiple'],
                    c['Trade Status'], c['Entry_Category_Display'],
                    f"{c['Trigger_Price']:.2f}", f"{c['Tactical_Stop']:.2f}",
                    f"{c['Target_1']:.2f}", f"{c['Target_2']:.2f}"
                ])

    # Generate CSV Watchlist Report for Flag
    for name in ["watchlist_flag.csv", "flag_candidates.csv", f"flag_candidates_{scan_date_clean}.csv"]:
        csv_file = os.path.join(reports_dir, name)
        with open(csv_file, "w", newline="", encoding="utf-8") as f_csv:
            writer = csv.writer(f_csv)
            writer.writerow([
                "Symbol", "Score", "Engine_Type", "Grade", "Contraction Count",
                "Contraction Sequence", "VDU %", "Pivot Price", "Current Price",
                "Distance to Pivot", "Readiness Status", "Entry Price", "Stop Loss",
                "Risk per Share", "Position Size", "R-Multiple", "Trade Status",
                "Entry Category", "Tactical Trigger", "Tactical Stop Loss",
                "Target 1", "Target 2"
            ])
            for c in flag_candidates_detailed:
                writer.writerow([
                    c['Symbol'], c['Score'], c['Engine_Type'], c['Grade'],
                    c['Contraction Count'], c['Contraction Sequence'], c['VDU %'],
                    c['Pivot Price'], c['Current Price'], c['Distance to Pivot'],
                    c['Readiness Status'], c['Entry Price'], c['Stop Loss'],
                    c['Risk per Share'], c['Position Size'], c['R-Multiple'],
                    c['Trade Status'], c['Entry_Category_Display'],
                    f"{c['Trigger_Price']:.2f}", f"{c['Tactical_Stop']:.2f}",
                    f"{c['Target_1']:.2f}", f"{c['Target_2']:.2f}"
                ])
    
    # 6A. Update delivery percentages in local stock cache CSV files (run after price ingestion)
    try:
        scan_date_str = index_df.index[-1] if not index_df.empty else datetime.now().strftime("%Y-%m-%d")
        data_engine.update_delivery_percentages(symbols, scan_date_str)
    except Exception as e:
        logger.error(f"Failed to update delivery percentages in cache files: {e}")

    # 6A-2. Compute fresh today's MBI index and reload posture/health_score from it
    try:
        logger.info("Recalculating fresh today's MBI-based market health score and posture...")
        from src.industry_analysis import analyze_participation
        # Pass today's scan date so it aligns calculations with this session
        analyze_participation(scan_date_str)
        
        # Reload fresh MBI-derived score and posture from market conditions engine
        health_score = market_engine.compute_market_health_score(index_df)
        posture = market_engine.get_market_posture(health_score)
        logger.info(f"Unified MBI-Derived Posture evaluated: {posture} (Score: {health_score}/10)")
    except Exception as mbi_ex:
        logger.error(f"Failed to compute EOD MBI-derived market posture: {mbi_ex}")


    # 6B. Run Paper Trading Engine Lifecycle for both VCP and FLAG
    try:
        logger.info("Initializing Paper Trading Engines...")
        vcp_paper_engine = PaperTradingEngine(config=config, state_file="data/paper_trading_state_vcp.json", data_engine=data_engine)
        flag_paper_engine = PaperTradingEngine(config=config, state_file="data/paper_trading_state_flag.json", data_engine=data_engine)
        
        # Load missing data for both watchlists
        needed_symbols = set(vcp_paper_engine.state.get("watchlist", {}).keys()).union(
            vcp_paper_engine.state.get("active_trades", {}).keys()
        ).union(
            flag_paper_engine.state.get("watchlist", {}).keys()
        ).union(
            flag_paper_engine.state.get("active_trades", {}).keys()
        )
        
        for sym in needed_symbols:
            if sym not in stock_df_dict:
                try:
                    stock_df_dict[sym] = data_engine.fetch_historical_ohlcv(sym, lookback_days=250)
                except Exception as e:
                    logger.warning(f"Could not load data for paper trading symbol {sym}: {e}")
                    
        scan_date_str = index_df.index[-1] if not index_df.empty else datetime.now().strftime("%Y-%m-%d")
        
        # Update VCP Portfolio
        vcp_paper_engine.evaluate_daily_lifecycle(stock_df_dict, scan_date_str)
        vcp_paper_engine.update_watchlist(vcp_candidates_detailed, scan_date_str, stock_df_dict)
        vcp_paper_engine.generate_performance_reports(stock_df_dict)
        
        # Update Flag Portfolio
        flag_paper_engine.evaluate_daily_lifecycle(stock_df_dict, scan_date_str)
        flag_paper_engine.update_watchlist(flag_candidates_detailed, scan_date_str, stock_df_dict)
        flag_paper_engine.generate_performance_reports(stock_df_dict)
        
        logger.info("Paper Trading Engines lifecycle updates completed.")
        
        # Send Email Notification if enabled (only if data is fresh)
        try:
            from src.notifier import EmailNotifier
            email_notifier = EmailNotifier(config)
            is_stale, expected_date = check_ingestion_freshness(scan_date_str)
            if is_stale:
                logger.warning(f"Ingestion was stale (expected: {expected_date}, got: {scan_date_str}). Email notification skipped to prevent duplicate/stale reports.")
            elif email_notifier.enabled:
                logger.info("Email notifier is enabled. Compiling HTML report...")
                
                email_compile_time = datetime.now()
                duration_seconds = int((email_compile_time - start_time).total_seconds())
                
                try:
                    import datetime as dt
                    # If the server's timezone is UTC, adjust start/end times to IST
                    is_utc = abs((dt.datetime.now() - dt.datetime.utcnow()).total_seconds()) < 60
                    if is_utc:
                        start_time_ist = (start_time + dt.timedelta(hours=5, minutes=30)).strftime("%H:%M:%S")
                        end_time_ist = (email_compile_time + dt.timedelta(hours=5, minutes=30)).strftime("%H:%M:%S")
                    else:
                        start_time_ist = start_time.strftime("%H:%M:%S")
                        end_time_ist = email_compile_time.strftime("%H:%M:%S")
                except Exception:
                    start_time_ist = start_time.strftime("%H:%M:%S")
                    end_time_ist = email_compile_time.strftime("%H:%M:%S")
                
                posture_colors = {"GREEN": "#10b981", "YELLOW": "#f59e0b", "RED": "#ef4444"}
                posture_color = posture_colors.get(posture, "#718096")
                
                html_lines = []
                html_lines.append(f"<h2>Daily Minervini Scanner Report - {scan_date_str}</h2>")
                html_lines.append("<div style='background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-family: Arial, sans-serif;'>")
                html_lines.append(f"<p style='margin: 4px 0; font-size: 14px;'><strong>Data Ingestion Started:</strong> {start_time_ist} IST</p>")
                html_lines.append(f"<p style='margin: 4px 0; font-size: 14px;'><strong>Data Ingestion Completed:</strong> {end_time_ist} IST &nbsp;({duration_seconds} seconds)</p>")
                html_lines.append(f"<p style='margin: 4px 0; font-size: 14px;'><strong>Market Posture:</strong> <span style='color: {posture_color}; font-weight: bold;'>{posture}</span> &nbsp;(Score: {health_score}/10)</p>")
                html_lines.append(f"<p style='margin: 12px 0 4px 0; font-size: 14px;'><strong>Dashboard Link:</strong> <a href='https://minervini-os-dashboard-production.up.railway.app/' style='color: #2b6cb0; text-decoration: underline; font-weight: bold;'>Open Dashboard</a></p>")
                html_lines.append("</div>")
                
                # Focus Gates Warning check
                has_candidates = bool(strict_list or flex_list or mini_list or flag_candidates_detailed)
                if not has_candidates:
                    html_lines.append("""
                    <div style="background-color: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 8px; margin: 15px 0; color: #991b1b; font-family: Arial, sans-serif; border-left: 5px solid #ef4444;">
                        <h3 style="margin-top: 0; color: #991b1b; font-weight: bold;">
                            ⚠️ CAPITAL PRESERVATION ACTIVE
                        </h3>
                        <p style="margin-bottom: 0; font-size: 14px; line-height: 1.5;">
                            <strong>No stocks cleared the 4 Focus Gates today.</strong> The market posture restricts aggressive buying, and no setups cleared the tight risk parameters. <strong>No new trades tomorrow!</strong>
                        </p>
                    </div>
                    """)
                
                # Watchlist summary
                html_lines.append("<h3>STRICT VCP Candidates</h3>")
                if strict_list:
                    html_lines.append("<ul>")
                    for c in strict_list:
                        html_lines.append(f"<li><strong>{c['Symbol']}</strong>: Score {c['Score']} | Pivot: ₹{c['Pivot Price']:.2f} | Stop: ₹{c['Stop Loss']:.2f}</li>")
                    html_lines.append("</ul>")
                else:
                    html_lines.append("<p><em>None found.</em></p>")
                    
                html_lines.append("<h3>FLEX VCP Candidates</h3>")
                if flex_list:
                    html_lines.append("<ul>")
                    for c in flex_list:
                        html_lines.append(f"<li><strong>{c['Symbol']}</strong>: Score {c['Score']} | Pivot: ₹{c['Pivot Price']:.2f} | Stop: ₹{c['Stop Loss']:.2f}</li>")
                    html_lines.append("</ul>")
                else:
                    html_lines.append("<p><em>None found.</em></p>")
                    
                html_lines.append("<h3>MINI VCP Candidates</h3>")
                if mini_list:
                    html_lines.append("<ul>")
                    for c in mini_list:
                        html_lines.append(f"<li><strong>{c['Symbol']}</strong>: Score {c['Score']} | Pivot: ₹{c['Pivot Price']:.2f} | Stop: ₹{c['Stop Loss']:.2f}</li>")
                    html_lines.append("</ul>")
                else:
                    html_lines.append("<p><em>None found.</em></p>")
                    
                html_lines.append("<h3>Emerging Leader FLAG Candidates</h3>")
                if flag_candidates_detailed:
                    html_lines.append("<ul>")
                    for c in flag_candidates_detailed:
                        html_lines.append(f"<li><strong>{c['Symbol']}</strong>: Score {c['Score']} | Trigger: ₹{c['Pivot Price']:.2f} | Stop: ₹{c.get('Stop Loss', c.get('Tactical_Stop', 0.0)):.2f}</li>")
                    html_lines.append("</ul>")
                else:
                    html_lines.append("<p><em>None found.</em></p>")
                
                # Paper Trading summary
                vcp_closed_count = len(vcp_paper_engine.state.get("closed_trades", []))
                vcp_active_count = len(vcp_paper_engine.state.get("active_trades", {}))
                vcp_cash_bal = vcp_paper_engine.state.get("cash", 1000000.0)
                
                flag_closed_count = len(flag_paper_engine.state.get("closed_trades", []))
                flag_active_count = len(flag_paper_engine.state.get("active_trades", {}))
                flag_cash_bal = flag_paper_engine.state.get("cash", 1000000.0)
                
                html_lines.append("<h3>Portfolio Summary - VCP</h3>")
                html_lines.append(f"<p><strong>Cash Balance:</strong> ₹{vcp_cash_bal:,.2f}</p>")
                html_lines.append(f"<p><strong>Active Positions:</strong> {vcp_active_count}</p>")
                html_lines.append(f"<p><strong>Closed Trades:</strong> {vcp_closed_count}</p>")
                
                html_lines.append("<h3>Portfolio Summary - FLAG</h3>")
                html_lines.append(f"<p><strong>Cash Balance:</strong> ₹{flag_cash_bal:,.2f}</p>")
                html_lines.append(f"<p><strong>Active Positions:</strong> {flag_active_count}</p>")
                html_lines.append(f"<p><strong>Closed Trades:</strong> {flag_closed_count}</p>")
                
                html_body = "\n".join(html_lines)
                subject = f"NSE Minervini Scan Report: {scan_date_str}"
                email_notifier.send_report(subject, html_body)
        except Exception as email_err:
            logger.error(f"Failed to compile and send email notification: {email_err}")
            
        # Send Telegram Notification if enabled (only if data is fresh)
        if notifier.enabled and not is_stale:
            try:
                logger.info("Telegram notifier is enabled. Dispatching daily scan report...")
                notifier.send_daily_scan_report(
                    scan_date_str=scan_date_str,
                    posture=posture,
                    health_score=health_score,
                    strict_list=strict_list,
                    flex_list=flex_list,
                    mini_list=mini_list,
                    paper_engine=vcp_paper_engine
                )
            except Exception as tg_err:
                logger.error(f"Failed to send Telegram notification: {tg_err}")
    except Exception as e:
        logger.error(f"Error during Paper Trading Engine updates: {e}")
            
    # 7. Print Consolidated System Log Summary
    # Using python's log interface to write to system.log and console
    logger.info("==================================================")
    logger.info("DAILY SCAN RUN SUMMARY STATISTICS")
    logger.info("==================================================")
    logger.info(f"Start Time:                {start_time_str}")
    logger.info(f"End Time:                  {end_time_str}")
    logger.info(f"Duration:                  {execution_duration:.2f} seconds")
    logger.info(f"Total Tickers Checked:     {len(symbols)}")
    logger.info(f"Valid Symbols (Watchlist): {len(valid_symbols)} {valid_symbols}")
    logger.info(f"Rejected Symbols:          {len(rejected_validation) + len(rejected_trend) + len(rejected_vcp)}")
    logger.info(f"  - Validation Failures:   {len(rejected_validation)}")
    logger.info(f"  - Trend Failures:        {len(rejected_trend)}")
    logger.info(f"  - VCP Failures:          {len(rejected_vcp)}")
    logger.info(f"Cache Statistics:")
    logger.info(f"  - Cache Hits:            {cache_hits}")
    logger.info(f"  - Cache Misses:          {cache_misses}")
    logger.info(f"  - Cache Hit Ratio:       {cache_hit_ratio:.2f}%")
    logger.info("==================================================")

def check_journal_violations():
    import json
    import os
    import pandas as pd
    
    logger = logging.getLogger("RiskEngine")
    logger.info("==================================================")
    logger.info("[AUDIT] RUNNING TRADING CONSTITUTION AUDIT ON TRADE JOURNAL...")
    
    journal_file = "data/trade_journal_data.json"
    if not os.path.exists(journal_file):
        # try minervini_os subfolder fallback
        journal_file = os.path.join("minervini_os", journal_file)
        
    if not os.path.exists(journal_file):
        logger.warning("No trade journal file found to audit.")
        return
        
    try:
        with open(journal_file, "r", encoding="utf-8") as f:
            journal = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load trade journal for risk audit: {e}")
        return
        
    open_trades = [t for t in journal if t.get("status") == "OPEN"]
    if not open_trades:
        logger.info("No active open positions in the trade journal.")
        return
        
    violations_found = 0
    for t in open_trades:
        symbol = t.get("symbol", "").upper()
        stop_loss = t.get("stop_loss")
        entry_price = t.get("entry_price", 0.0)
        total_qty = t.get("total_qty", 0)
        risk_pct = t.get("risk_pct", 0.0)
        comments = t.get("comments", "")
        tech_desc = t.get("technical_desc", "")
        
        # Load cache for CMP
        cmp = None
        cache_file = f"data/cache/{symbol}.csv"
        if not os.path.exists(cache_file):
            cache_file = os.path.join("minervini_os", cache_file)
            
        if os.path.exists(cache_file):
            try:
                df_c = pd.read_csv(cache_file)
                df_c.columns = [c.strip() for c in df_c.columns]
                if not df_c.empty:
                    cmp = float(df_c['Close'].iloc[-1])
                    low_today = float(df_c['Low'].iloc[-1]) if 'Low' in df_c.columns else None
                else:
                    low_today = None
            except Exception as ex:
                logger.warning(f"Could not load cache file to audit {symbol}: {ex}")
                low_today = None
                
        t_violations = []
        
        # RULE 4: STOP LOSS IS SACRED
        if stop_loss is None or stop_loss <= 0:
            t_violations.append("RULE 4 VIOLATION: Stop loss is missing/undefined.")
        elif cmp is not None and cmp <= stop_loss:
            t_violations.append(f"RULE 4 VIOLATION: Stop loss breached on Close! Close price is Rs.{cmp:.2f} (Stop Loss: Rs.{stop_loss:.2f}).")
            t_violations.append("RULE #0 VIOLATION: Hesitation to exit after stop breach (protecting ego instead of capital).")
        elif low_today is not None and low_today <= stop_loss:
            t_violations.append(f"RULE 4 VIOLATION: Stop loss breached on Intraday Low! Low was Rs.{low_today:.2f} (Stop Loss: Rs.{stop_loss:.2f}).")
            t_violations.append("RULE #0 VIOLATION: Hesitation to exit after stop breach (protecting ego instead of capital).")
            
        # RULE 1: CAPITAL PRESERVATION
        if risk_pct > 8.0:
            t_violations.append(f"RULE 1 VIOLATION: High trade risk ({risk_pct}%) exceeds conservative 8% limit.")
            
        # RULE 3: TRADING IS NOT INVESTING
        contains_investing = any(word in (comments + " " + tech_desc).lower() for word in ["long-term", "good company", "good results", "will recover", "recovery"])
        if contains_investing:
            t_violations.append("RULE 3 VIOLATION: Rationalizing a trade using long-term investing logic in comments.")
            
        # RULE 7: NO HOPE
        contains_hope = any(word in (comments + " " + tech_desc).lower() for word in ["it will recover", "it can't fall", "exit after recovery", "already down", "temporary fall"])
        if contains_hope:
            t_violations.append("RULE 7 VIOLATION: Hope statements detected in trade comments.")
            
        if t_violations:
            violations_found += len(t_violations)
            logger.warning(f"[RISK] TRADING CONSTITUTION VIOLATION DETECTED FOR {symbol}:")
            for v in t_violations:
                logger.warning(f"  - {v}")
                
    if violations_found > 0:
        logger.warning(f"Risk audit completed with {violations_found} active Trading Constitution violations!")
    else:
        logger.info("Risk audit completed successfully. No Trading Constitution violations found.")
    logger.info("==================================================")

def main():
    import json
    # Set up global rotating logging framework
    setup_logging()
    
    try:
        run_daily_scan()
        logger.info("Minervini AI OS daily scanner execution completed successfully.")
        
        # Industry Participation & MBI calculations are now run inside run_daily_scan()
        # prior to paper trading and notifications to ensure a single source of truth.

            
        # Update Earnings Calendar daily
        logger.info("Updating Corporate Earnings Calendar...")
        try:
            import sys
            scratch_path = os.path.abspath("scratch")
            if scratch_path not in sys.path:
                sys.path.append(scratch_path)
            from earnings_fetcher import update_earnings_calendar
            update_earnings_calendar()
            logger.info("Corporate Earnings Calendar updated successfully.")
        except Exception as ex:
            logger.error(f"Failed to update Corporate Earnings Calendar: {ex}")
            
        # Audit Trade Journal for Trading Constitution violations
        try:
            check_journal_violations()
        except Exception as ex:
            logger.error(f"Failed to run trade journal risk audit: {ex}")
            
        # Run Post-Entry Trade Management Engine Daily Audit
        try:
            from src.trade_manager import TradeManager
            logger.info("Running Post-Entry Trade Management daily audit...")
            cfg = load_config("config/config.yaml")
            trade_mgr = TradeManager(cfg)
            mgr_report = trade_mgr.evaluate_all_trades()
            
            # Save trade management report
            report_file = "data/trade_management_report.json"
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(mgr_report, f, indent=2)
            logger.info(f"Post-Entry Trade Management daily report saved successfully to {report_file}")
        except Exception as mgr_ex:
            logger.error(f"Failed to execute Trade Management Engine daily audit: {mgr_ex}")

        # Run True Paper Trading daily update
        try:
            from src.true_paper_trader import TruePaperTrader
            logger.info("Running True Paper Trading daily update...")
            paper_trader = TruePaperTrader()
            
            # Resolve scan date from primary index cache to align with scanner results
            from src.data_ingestion import DataIngestionEngine
            de = DataIngestionEngine(cache_dir="data/cache")
            index_df = de.fetch_historical_ohlcv("NIFTY_50", lookback_days=10)
            
            from datetime import datetime
            cur_date = index_df.index[-1] if not index_df.empty else datetime.now().strftime("%Y-%m-%d")
            logger.info(f"Resolved paper trading date from index: {cur_date}")
            
            paper_trader.run_daily_update(cur_date)
            logger.info("True Paper Trading daily update completed successfully.")
        except Exception as paper_ex:
            logger.error(f"Failed to run True Paper Trading daily update: {paper_ex}")
            
        # Write scan status for dashboard notification
        status_file = "data/last_scan_status.json"
        try:
            from datetime import datetime
            os.makedirs("data", exist_ok=True)
            
            # Check ingestion freshness
            is_stale, expected_date = check_ingestion_freshness(scan_date_str)
            if is_stale:
                status_msg = f"Scan completed, but EOD data ingestion is pending/stale (expected: {expected_date}, got: {scan_date_str}). Dashboard shows last available session."
                status_val = "stale"
            else:
                status_msg = "Data Ingestion & EOD Scan completed successfully. Watchlist and dashboard are updated with today's closing prices."
                status_val = "success"
                
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": status_val,
                    "message": status_msg
                }, f, indent=2)
            logger.info("Saved scan status file successfully.")
        except Exception as status_err:
            logger.error(f"Failed to write scan status file: {status_err}")
    except Exception as e:
        logger.exception(f"Unhandled exception during scan orchestration: {e}")
        # Write failed status
        try:
            from datetime import datetime
            status_file = "data/last_scan_status.json"
            os.makedirs("data", exist_ok=True)
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "error",
                    "message": f"Daily scan failed: {str(e)}"
                }, f, indent=2)
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
