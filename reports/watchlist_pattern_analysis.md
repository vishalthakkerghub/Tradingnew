# Watchlist Pattern & Correlation Analysis (June 15 - July 15, 2026)

This analysis is based on **761 triggered and completed swing trades** from the June 15 to July 15, 2026 watchlist period. It evaluates how various metrics correlate with trade success (hitting Target 1 or BOTH targets) vs failure (stopped out).

---

## 1. Industry Category: The Deciding Factor
The single most powerful predictor of success is the **Weekly Industry Category**.

| Industry Category | Completed Trades | Win Rate | Analysis & Takeaway |
| :--- | :---: | :---: | :--- |
| **Leading** | 11 | **90.91%** | **Golden Group**: Almost all breakouts in Leading groups hit their targets (10 out of 11). |
| **Emerging** | 17 | **64.71%** | **Strong Edge**: High success rate as capital rotates into these early-stage leaders. |
| **Neutral** | 242 | 35.12% | Standard baseline probability. |
| **Weak** | 445 | 35.06% | Standard baseline probability. |
| **Unscaled** (Small-scale) | 46 | **15.22%** | **High Danger**: Avoid. Small-scale sectors (< 5 stocks) lack institutional depth and fail easily. |

---

## 2. Setup Type: Mini & Flex VCPs Outperform
Different VCP engine calibrations show varying edge profiles:

| Setup/Engine Type | Completed Trades | Win Rate | Analysis & Takeaway |
| :--- | :---: | :---: | :--- |
| **MINI_VCP** | 9 | **66.67%** | **Excellent Edge**: Very tight, compact contraction structures yield explosive, clean breakouts. |
| **FLEX_VCP** | 62 | **51.61%** | **Solid Edge**: Moderate volatility contractions perform well above average. |
| **FLAG** (Setup/Pullback) | 665 | 33.68% | Highly populated setup, performing at standard market baseline. |
| **STRICT_VCP** | 25 | 28.00% | Underperformed during this period (often because strict entry criteria require clean macro tailwinds). |

---

## 3. The Delivery Paradox: High Beta vs Defensives
An interesting trend emerged when comparing Delivery % buckets:

*   **Low Delivery (<25%)**: Count: 626 | **Win Rate: 35.94%**
*   **High Delivery (>50%)**: Count: 40 | **Win Rate: 17.50%**

### Why this happens (Market Insight):
High-delivery stocks (>50%) are typically large-cap, high-float, defensive stocks (e.g. major banks, consumer goods). They have high institutional absorption but lack the beta/volatility to hit aggressive swing targets (Target 1: +15%, Target 2: +25%) before pulling back to hit stop losses. 
Conversely, low-delivery stocks are often high-beta mid/small caps that experience explosive, fast-momentum breakout surges, hitting targets rapidly.

---

## 4. Failure Correlations: The "Avoid" Setup
By combining negative metrics, we can create a clear filter for trades to avoid:

*   **Filter**: Stock is in a **Weak Sector** OR has a low **AMS Score (< 60)**.
*   **Result**: 654 completed trades met this criteria.
*   **Failure Rate**: **64.22%** (Over 64% of these setups resulted in a stopped-out loss).

---

## 5. Summary Actionable Rules for Trading
1.  **Strict Selection**: Focus first on VCP candidates in **Leading** and **Emerging** sectors.
2.  **Avoid Weak/Unscaled**: Filter out and skip any candidate in a **Weak** or **Unscaled** group.
3.  **Engine Preference**: Favor **MINI_VCP** and **FLEX_VCP** setups when they present clean triggers.
4.  **Sizing by Beta**: For high-delivery large caps, target smaller targets (e.g., exit half at +8% to +10%) rather than waiting for full swing targets.
