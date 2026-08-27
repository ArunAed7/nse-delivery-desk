"""
NSE Delivery Desk - Institutional Edition
Version 2.0: Complete institutional-grade analytics platform

Modules:
- Technical Analysis (Momentum, Volatility, VaR)
- Fundamental Analysis (DCF, Piotroski, Altman Z-Score)
- Portfolio & Risk (Factor Analysis, Optimization, Sharpe/Sortino)
- Derivatives Intelligence (OI, PCR, Max Pain, FII positioning)
- Relative Strength (RS Ratings, Stage Analysis, Peer Comparison)
- Governance & ESG (Promoter Pledge, Capital Allocation Score)
- Backtesting Engine (Walk-Forward, Event Studies)
- Macro & Liquidity (Regime Detection, FII/DII Flows)
- ML Models (Return Prediction, Sentiment Analysis)
- Compliance & Reporting (Pre-trade checks, SEBI reports)
"""

from .technical_institutional import *
from .fundamentals_institutional import *
from .portfolio_risk import *
from .derivatives_intelligence import *
from .relative_strength import *
from .governance_esg import *
from .backtesting_engine import *
from .macro_liquidity import *
from .ml_models import *
from .compliance_reporting import *

__version__ = "2.0.0"
__all__ = [
    # Technical
    'TechnicalAnalyzer', 'add_momentum_indicators', 'calculate_var',
    # Fundamental
    'FundamentalAnalyzer', 'calculate_piotroski_fscore', 'calculate_altman_zscore',
    'run_dcf_valuation', 'calculate_roic_spread',
    # Portfolio & Risk
    'PortfolioOptimizer', 'RiskDashboard', 'FactorAnalyzer',
    'optimize_mean_variance', 'optimize_risk_parity',
    # Derivatives
    'DerivativesIntelligence', 'analyze_options_chain',
    # Relative Strength
    'RelativeStrengthAnalyzer', 'analyze_relative_strength',
    # Governance
    'GovernanceAnalyzer', 'ESGScorer', 'analyze_governance',
    # Backtesting
    'BacktestEngine', 'WalkForwardAnalyzer',
    # Macro
    'MacroRegimeDetector', 'LiquidityFlowAnalyzer', 'analyze_macro_liquidity',
    # ML
    'ReturnPredictor', 'SentimentAnalyzer', 'RegimeClassifier', 'run_ml_pipeline',
    # Compliance
    'PreTradeCompliance', 'AuditTrail', 'SEBIReporter', 'run_compliance_check'
]

print(f"✓ NSE Delivery Desk Institutional v{__version__} loaded")
print("  Modules: Technical | Fundamental | Portfolio | Derivatives | RS | Governance | Backtest | Macro | ML | Compliance")
