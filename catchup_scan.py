"""
Login/startup catch-up trigger for the daily scan.

The main daily automation fires at a fixed time (6:20 PM IST) via the
Windows Scheduled Task "MinerviniOS_DailyScan". If the machine was off,
asleep, or the user wasn't logged in at that exact time, that day's run
gets silently skipped - this is exactly what caused the missed-exit
data-integrity issue found and fixed in True Paper Trading (see memory:
minervini-os-fix-plan, and the get_cmp_from_cache() date-lookup fix in
src/true_paper_trader.py).

This script is bound to a second scheduled task trigger ("At log on") so
that whenever the user actually starts using the machine, the system
checks whether today's scan already completed successfully - and if not,
runs it right then instead of silently waiting for tomorrow's 6:20 PM
trigger. Deliberately idempotent-safe to call even when today's scan HAS
already run: it just checks data/last_scan_status.json first and exits
immediately without doing anything if so, so logging in multiple times a
day (or logging in shortly after the normal 6:20 PM run) never triggers a
redundant duplicate run.
"""
import json
import os
import sys
import subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(SCRIPT_DIR, "data", "last_scan_status.json")


def already_ran_today():
    today = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(STATUS_FILE):
        return False
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        ts = d.get("timestamp", "")
        return ts.startswith(today) and d.get("status") == "success"
    except Exception:
        return False


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    if already_ran_today():
        print(f"[catchup_scan] Today's scan ({today}) already completed successfully - nothing to do.")
        return

    print(f"[catchup_scan] Today's scan ({today}) has not completed yet - running catch-up now...")
    result = subprocess.run([sys.executable, "main.py"], cwd=SCRIPT_DIR)
    if result.returncode == 0:
        print("[catchup_scan] Catch-up run completed.")
    else:
        print(f"[catchup_scan] Catch-up run exited with code {result.returncode} - check logs/system.log.")


if __name__ == "__main__":
    main()
