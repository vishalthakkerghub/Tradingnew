"""
Login/startup catch-up trigger for the daily scan.

The main daily automation fires at a fixed time (6:20 PM IST) via the
Windows Scheduled Task "MinerviniOS_DailyScan". If the machine was off,
asleep, or the user wasn't logged in at that exact time, that day's run
gets silently skipped. This script is bound to a second scheduled task
trigger ("At log on", see MinerviniOS_LoginCatchup) so the system checks
itself whenever the user actually starts using the machine.

Two distinct jobs, and it's important they stay distinct:

1. Backfill True Paper Trading's exit/entry evaluation for every
   individual missed trading day, in chronological order - not just
   "today". Safe to do now that get_cmp_from_cache() (src/true_paper_
   trader.py) does an exact date lookup instead of always reading the
   latest cached row (see memory: minervini-os-fix-plan for the incident
   this fixes - CYIENTDLM/SKYGOLD both missed a real T1-then-breakeven-
   stop sequence during a multi-day gap because of that exact bug, found
   during a system audit and hand-corrected once; this closes the gap so
   it can't happen silently again). Deliberately scoped to True Paper
   Trading ONLY - the VCP/Flag paper-trading engines (src/paper_trading_
   engine.py) are explicitly unused/closed per Vishal's decision
   (2026-09-22) and are not touched here even though they have the same
   missed-day exposure, for a different reason (no rollback mechanism +
   no entry-date guard makes replaying them unsafe, not just unwanted).

2. Run today's full scan (main.py) - new candidate discovery included,
   which fundamentally can't be backfilled for a past date (it scans
   CURRENT market data, there's no point-in-time historical scan
   capability), so this is only ever done for today, last, after every
   earlier missed day's True Paper Trading state is caught up.

Idempotent-safe: checks data/last_scan_status.json for today's date first
and exits immediately if today already completed successfully, so this
never causes a redundant duplicate run on a second login the same day.
"""
import json
import os
import sys
import subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(SCRIPT_DIR, "data", "last_scan_status.json")
SYMBOLS_FILE = os.path.join(SCRIPT_DIR, "config", "symbols.json")
NIFTY_CACHE = os.path.join(SCRIPT_DIR, "data", "cache", "NIFTY_50.csv")

# Safety valve: if more than this many trading days were missed, don't try
# to auto-backfill blindly - log it clearly and let it be handled by hand.
# A normal login-catchup gap should be 1-3 days; anything past this
# smells like something else is wrong (task disabled, machine off for
# weeks) and deserves a human look rather than a silent multi-week replay.
MAX_AUTO_BACKFILL_DAYS = 15


def already_ran_today():
    today = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(STATUS_FILE):
        return False, None
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        ts = d.get("timestamp", "")
        last_date = ts.split(" ")[0] if ts else None
        return (ts.startswith(today) and d.get("status") == "success"), last_date
    except Exception:
        return False, None


def get_missed_trading_days(last_success_date, today_date):
    """NSE trading days strictly between last_success_date (exclusive) and
    today_date (exclusive), read from the (now freshly-refreshed) NIFTY_50
    cache - the same source of truth the rest of the system already uses
    for "what counts as a trading day" (see get_previous_trading_date())."""
    if not last_success_date or not os.path.exists(NIFTY_CACHE):
        return []
    try:
        import pandas as pd
        df = pd.read_csv(NIFTY_CACHE)
        df["Date"] = pd.to_datetime(df["Date"])
        all_dates = sorted(df["Date"].dt.strftime("%Y-%m-%d").tolist())
        return [d for d in all_dates if last_success_date < d < today_date]
    except Exception as e:
        print(f"[catchup_scan] Could not determine missed trading days: {e}")
        return []


def refresh_price_cache():
    """Bulk-refreshes the price cache BEFORE any backfill, so every missed
    day's real historical OHLCV is actually available to replay against.
    A single yfinance fetch naturally brings back the whole date range, so
    this one call is enough to cover however many days were missed - no
    need to fetch once per missed day. main.py will see the cache is
    already fresh and skip re-fetching when it runs afterward for today."""
    sys.path.insert(0, os.path.join(SCRIPT_DIR, "src"))
    from data_ingestion import DataIngestionEngine
    with open(SYMBOLS_FILE, "r", encoding="utf-8") as f:
        symbols = json.load(f)
    print(f"[catchup_scan] Refreshing price cache for {len(symbols)} symbols before backfill...")
    de = DataIngestionEngine(cache_dir=os.path.join(SCRIPT_DIR, "data", "cache"))
    de.bulk_fetch_ohlcv(symbols)


def backfill_true_paper_trading(missed_days):
    """Replays True Paper Trading's exit/entry evaluation for each missed
    day in order, using ONE engine instance so each call's changes are
    visible to the next (run_daily_update() self-persists at the end of
    each call, no need to reload between iterations)."""
    sys.path.insert(0, os.path.join(SCRIPT_DIR, "src"))
    from true_paper_trader import TruePaperTrader
    trader = TruePaperTrader()
    for d in missed_days:
        print(f"[catchup_scan] Backfilling True Paper Trading for missed day {d}...")
        try:
            trader.run_daily_update(d)
        except Exception as e:
            print(f"[catchup_scan] Backfill for {d} failed: {e} - stopping backfill, will not attempt later days out of order.")
            break


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    done, last_success_date = already_ran_today()
    if done:
        print(f"[catchup_scan] Today's scan ({today}) already completed successfully - nothing to do.")
        return

    print(f"[catchup_scan] Today's scan ({today}) has not completed yet. Last known success: {last_success_date or 'none recorded'}.")

    if last_success_date:
        refresh_price_cache()
        missed_days = get_missed_trading_days(last_success_date, today)
        if len(missed_days) > MAX_AUTO_BACKFILL_DAYS:
            print(f"[catchup_scan] {len(missed_days)} missed trading days ({missed_days[0]} to {missed_days[-1]}) - "
                  f"exceeds the {MAX_AUTO_BACKFILL_DAYS}-day auto-backfill safety cap. Skipping automatic backfill; "
                  f"this needs a manual look rather than a silent multi-week replay. Proceeding straight to today's scan.")
        elif missed_days:
            print(f"[catchup_scan] {len(missed_days)} missed trading day(s) to backfill: {missed_days}")
            backfill_true_paper_trading(missed_days)
        else:
            print("[catchup_scan] No missed trading days to backfill (gap was only non-trading days).")

    print(f"[catchup_scan] Running today's full scan ({today})...")
    result = subprocess.run([sys.executable, "main.py"], cwd=SCRIPT_DIR)
    if result.returncode == 0:
        print("[catchup_scan] Catch-up run completed.")
    else:
        print(f"[catchup_scan] Catch-up run exited with code {result.returncode} - check logs/system.log.")


if __name__ == "__main__":
    main()
