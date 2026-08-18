import logging
import math
import pandas as pd
import numpy as np

logger = logging.getLogger("ExecutionEngine")

class ExecutionEngine:
    """
    Computes position sizing, structural stop losses, and manages exits for VCP candidates.
    Exit rules implemented: Structural SL, 10% in 3 weeks rule, 20-25% partial profit, and 10 EMA trailing exit.
    """
    def __init__(self, config: dict = None):
        self.config = config or {}
        risk_params = self.config.get("risk_management", {})
        self.default_capital = float(self.config.get("system", {}).get("default_capital", 1000000.0))
        self.default_risk_pct = float(risk_params.get("risk_per_trade_pct", 0.01))
        self.max_allocation_pct = float(risk_params.get("max_allocation_per_stock_pct", 0.25))
        self.max_stop_pct = float(risk_params.get("max_stop_pct", 0.08))
        
        logger.info(
            f"ExecutionEngine initialized: Default Capital=₹{self.default_capital:,.2f} | "
            f"Risk Per Trade={self.default_risk_pct * 100:.1f}% | "
            f"Max Allocation={self.max_allocation_pct * 100:.1f}% | "
            f"Max Stop Cap={self.max_stop_pct * 100:.1f}%"
        )

    def calculate_trade_setup(
        self,
        symbol: str,
        pivot_price: float,
        contraction_low: float,
        capital_size: float = None,
        risk_pct: float = None
    ) -> dict:
        """
        Calculates trade parameters for entry planning:
        Entry Price, Stop Loss, Risk per Share, Position Size, R-Multiple, and Trade Status.
        """
        capital = float(capital_size) if capital_size is not None else self.default_capital
        r_pct = float(risk_pct) if risk_pct is not None else self.default_risk_pct

        entry_price = float(pivot_price)
        
        # Structural Stop Loss: Final Contraction Low, capped at self.max_stop_pct for capital preservation
        max_stop_loss_limit = entry_price * (1.0 - self.max_stop_pct)
        stop_loss = max(max_stop_loss_limit, float(contraction_low))

        risk_per_share = entry_price - stop_loss
        
        if risk_per_share > 0:
            shares = math.floor((capital * r_pct) / risk_per_share)
        else:
            shares = 0

        # Enforce Max Allocation Constraint
        max_allocation = capital * self.max_allocation_pct
        max_shares = math.floor(max_allocation / entry_price) if entry_price > 0 else 0
        shares = min(shares, max_shares)

        return {
            "Symbol": symbol,
            "Entry_Price": entry_price,
            "Stop_Loss": stop_loss,
            "Risk_Per_Share": risk_per_share,
            "Position_Size": shares,
            "R_Multiple": 0.0,
            "Trade_Status": "PENDING_BREAKOUT"
        }

    def simulate_trade(
        self,
        stock_df: pd.DataFrame,
        entry_idx: int,
        entry_price: float,
        stop_loss: float,
        capital_size: float = None,
        risk_pct: float = None
    ) -> dict:
        """
        Simulates the daily lifecycle of an active trade starting after entry_idx.
        Tracks the trade day-by-day and returns execution/exit details.
        """
        capital = float(capital_size) if capital_size is not None else self.default_capital
        r_pct = float(risk_pct) if risk_pct is not None else self.default_risk_pct
        
        setup = self.calculate_trade_setup(
            symbol="",
            pivot_price=entry_price,
            contraction_low=stop_loss,
            capital_size=capital,
            risk_pct=r_pct
        )
        shares = setup["Position_Size"]
        risk_per_share = setup["Risk_Per_Share"]
        current_stop = setup["Stop_Loss"]

        n = len(stock_df)
        if entry_idx < 0 or entry_idx >= n:
            return {
                "exit_date": None,
                "exit_price": 0.0,
                "trade_status": "PENDING_BREAKOUT",
                "days_active": 0,
                "final_r_multiple": 0.0,
                "reason": "Invalid entry index"
            }

        # Calculate 10 EMA
        closes = stock_df["Close"].values
        highs = stock_df["High"].values
        lows = stock_df["Low"].values
        opens = stock_df["Open"].values
        dates = stock_df.index

        # EWM calculation matching pandas standard
        ema10_series = stock_df["Close"].ewm(span=10, adjust=False).mean().values

        reached_10pct_in_3w = False
        partial_exit_taken = False
        days_active = 0
        current_shares = shares
        cash_balance = 0.0
        
        trade_status = "ACTIVE"
        exit_date = None
        exit_price = 0.0
        exit_reason = "No exit triggered"

        for i in range(entry_idx + 1, n):
            days_active += 1
            day_high = float(highs[i])
            day_low = float(lows[i])
            day_close = float(closes[i])
            day_open = float(opens[i])
            day_date = dates[i]
            day_ema10 = float(ema10_series[i])

            # 1. Check Stop Loss (Structural/Trailing Breakeven)
            if day_low <= current_stop:
                trade_status = "STOPPED_OUT"
                exit_date = day_date
                # If open gaps down below stop loss, exit at Open
                exit_price = min(current_stop, day_open)
                cash_balance += current_shares * exit_price
                current_shares = 0
                exit_reason = "Stop loss hit"
                break

            # 2. 10% in 3 Weeks Rule
            if days_active <= 15:
                if day_high >= 1.10 * entry_price:
                    if not reached_10pct_in_3w:
                        reached_10pct_in_3w = True
                        logger.debug(f"Power play triggered: 10% gain reached on day {days_active}. Stop moved to breakeven (₹{entry_price:.2f}).")
                        current_stop = entry_price # Raise stop to breakeven
            
            if days_active == 15 and not reached_10pct_in_3w:
                trade_status = "TIME_EXIT"
                exit_date = day_date
                exit_price = day_close
                cash_balance += current_shares * exit_price
                current_shares = 0
                exit_reason = "Sluggish breakout time stop (failed to reach 10% in 3 weeks)"
                break

            # 3. 20-25% Partial Profit Target (using 20% gain as target)
            if not partial_exit_taken and day_high >= 1.20 * entry_price:
                partial_exit_taken = True
                trade_status = "PARTIAL_EXIT"
                partial_sell_shares = current_shares // 2
                partial_sell_price = max(1.20 * entry_price, day_open)
                cash_balance += partial_sell_shares * partial_sell_price
                current_shares -= partial_sell_shares
                current_stop = entry_price # Move stop to breakeven for remaining shares
                logger.debug(f"Partial profit target hit on day {days_active}. Sold {partial_sell_shares} shares at ₹{partial_sell_price:.2f}. Stop moved to breakeven.")

            # 4. 10 EMA Trailing Exit (activated after 5 days of trade progress)
            if days_active > 5 and day_close < day_ema10:
                trade_status = "FULLY_EXITED"
                exit_date = day_date
                exit_price = day_close
                cash_balance += current_shares * exit_price
                current_shares = 0
                exit_reason = "Closed below 10 EMA trailing stop"
                break

        # Calculate results
        if current_shares > 0:
            latest_close = float(closes[-1])
            total_value = cash_balance + (current_shares * latest_close)
        else:
            total_value = cash_balance

        initial_cost = shares * entry_price
        total_pnl = total_value - initial_cost
        
        # Calculate R-Multiple: (Total Profit / Loss) / (Shares * Risk per Share)
        initial_risk = shares * risk_per_share
        final_r_multiple = total_pnl / initial_risk if initial_risk > 0 else 0.0

        return {
            "exit_date": exit_date,
            "exit_price": exit_price if current_shares == 0 else float(closes[-1]),
            "trade_status": trade_status,
            "days_active": days_active,
            "final_r_multiple": final_r_multiple,
            "reason": exit_reason,
            "cash_realized": cash_balance,
            "shares_remaining": current_shares,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "current_stop": current_stop
        }
