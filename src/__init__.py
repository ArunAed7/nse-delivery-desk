"""
NSE Delivery Desk - Institutional Grade Modules
================================================

This package provides institutional-grade analytical capabilities:

Technical Analysis (technical_institutional.py):
- Momentum Suite: Multi-timeframe RSI, MACD, Connors RSI, ADX, CMF, Aroon
- Volatility Analytics: Historical Vol, ATR, VaR, CVaR, Bollinger/Keltner Channels
- Portfolio Risk: Portfolio-level VaR calculations

Fundamental Analysis (fundamentals_institutional.py):
- Earnings Quality: Piotroski F-Score, Altman Z-Score, Beneish M-Score
- Valuation: DCF (FCFF/FCFE), EV/EBITDA, Reverse DCF
- Profitability: ROE DuPont, ROIC vs WACC, FCF Yield, Cash Conversion Cycle

Portfolio & Risk (portfolio_risk.py):
- Factor Analysis: Value, Momentum, Quality, Low Vol, Size exposures
- Optimization: Mean-Variance, Risk Parity, Hierarchical Risk Parity
- Risk Metrics: Sharpe, Sortino, Max DD, Stress Testing, Concentration Analysis
"""

from . import technical_institutional
from . import fundamentals_institutional  
from . import portfolio_risk

__version__ = '2.0.0'
__all__ = [
    'technical_institutional',
    'fundamentals_institutional',
    'portfolio_risk'
]

print("✓ NSE Delivery Desk Institutional Modules loaded")
print(f"  Version: {__version__}")
print(f"  Modules: Technical, Fundamental, Portfolio & Risk")
