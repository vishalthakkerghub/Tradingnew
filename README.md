# Minervini AI Trading Operating System (v1.0 Scaffold)

This repository contains the software scaffolding and project structure for the **Minervini AI Trading Operating System**, implementing the Phase 1 Project Scaffold (Sprint 1) based on the v1.0 Master Specification and Technical Build Specification.

---

## 📂 Project Directory Structure

```
minervini_os/
├── config/
│   ├── config.yaml          # System configurations (Liquidity, Risk, Notification tokens)
│   └── symbols.json         # Universe scanning list (NSE equity list)
├── data/
│   └── cache/               # Local data cache (historical CSV or binary data storage)
├── logs/
│   └── system.log           # Daily log files (with log rotation active)
├── reports/
│   └── daily/               # Generated daily scan reports (Markdown and HTML formats)
├── src/
│   ├── __init__.py
│   ├── data_ingestion.py    # Fetching historical daily/intraday price and volume bars
│   ├── trend_template.py    # Processing the 10 Trend Template daily filters
│   ├── vcp_engine.py        # Pivot detection, contraction math, and VDU logic
│   ├── risk_engine.py       # Dynamic position sizing and sector cap checks
│   ├── market_conditions.py # Distribution day tracking and market health scoring
│   ├── notifier.py          # Formatting and sending Telegram notifications
│   └── utils.py             # Date math, mathematical helpers, and formatters
├── tests/
│   ├── __init__.py
│   ├── test_trend.py        # Unit tests for the 10 Trend Template filters
│   ├── test_vcp.py          # Unit tests for pivot and contraction calculations
│   └── test_risk.py         # Unit tests for position sizing and stop calculations
└── main.py                  # CLI entrypoint and orchestrator (cron/scheduler target)
```

---

## ⚙️ Initial Setup

### Prerequisites
- **Python 3.10+**
- **pip** (Python package installer)

### Installation
1. Navigate to the project root directory:
   ```bash
   cd "d:/VCP Trading/minervini_os"
   ```
2. Install the required libraries:
   ```bash
   pip install pyyaml pandas
   ```

---

## 🚀 Execution Instructions

### Running the Scanner Orchestrator (Dry Run)
You can execute the main daily scan loop in dry-run mode using the following command:
```bash
python main.py
```
*Observe the console output or inspect the generated log file at `logs/system.log` to trace the execution path.*

### Running the Test Suite
To run all unit tests and verify the mathematical placeholders and skeletons:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 🛠️ Code and Design Standards

All future development must adhere to the following rules:

1. **Python Coding Standard:** PEP 8 compliance. All functions must contain descriptive docstrings detailing inputs, outputs, and purposes.
2. **Semi-Automated Nature:** No automated broker order execution is allowed. Scanner outputs must be restricted to watchlists and discretionary buy alerts.
3. **Logging Discipline:** Use the custom logger (`logging.getLogger("Module")`) in every class. Never use raw `print()` statements for system messages.
4. **Unit Testing:** Do not implement business logic in `src/` without accompanying unit tests in `tests/` to validate mathematical formulas against mock datasets.
