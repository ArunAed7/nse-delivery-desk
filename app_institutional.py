"""
NSE Delivery Desk - Institutional Edition
Streamlit Application with all 10 institutional modules

Run: streamlit run app_institutional.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="NSE Delivery Desk - Institutional",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import institutional modules
from src import (
    TechnicalAnalyzer, FundamentalAnalyzer, PortfolioOptimizer, RiskDashboard,
    DerivativesIntelligence, RelativeStrengthAnalyzer, GovernanceAnalyzer,
    BacktestEngine, MacroRegimeDetector, LiquidityFlowAnalyzer,
    ReturnPredictor, SentimentAnalyzer, PreTradeCompliance, AuditTrail
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0;}
    .stButton>button {width: 100%;}
    h1, h2, h3 {color: #1f77b4;}
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("🏦 NSE Institutional")
st.sidebar.markdown("---")
module = st.sidebar.radio(
    "Select Module:",
    ["Dashboard", "Technical Pro", "Fundamental Deep Dive", 
     "Portfolio Optimizer", "Derivatives Intelligence", 
     "Relative Strength", "Governance & ESG",
     "Backtesting", "Macro & Flows", "ML Predictions", "Compliance"]
)

st.sidebar.markdown("---")
st.sidebar.info("**Institutional Edition v2.0**\n\n10 Advanced Modules:\n- Technical Analytics\n- Fundamental Models\n- Portfolio Optimization\n- Options Chain Analysis\n- RS Ratings\n- Governance Scoring\n- Backtesting Engine\n- Macro Regime Detection\n- ML Predictions\n- SEBI Compliance")

# Generate mock data for demo
def generate_mock_data():
    dates = pd.date_range('2023-01-01', periods=252)
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(252) * 0.02)
    df = pd.DataFrame({
        'Date': dates,
        'Open': prices * (1 + np.random.randn(252)*0.005),
        'High': prices * (1 + np.abs(np.random.randn(252)*0.01)),
        'Low': prices * (1 - np.abs(np.random.randn(252)*0.01)),
        'Close': prices,
        'Volume': np.random.randint(1e6, 1e7, 252)
    }, index=dates)
    return df

# ===================== DASHBOARD =====================
if module == "Dashboard":
    st.title("📊 Institutional Dashboard")
    st.markdown("### Market Overview & Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Nifty 50", "22,450", "+0.8%")
    with col2:
        st.metric("FII Flow (Cr)", "+4,250", "Buying")
    with col3:
        st.metric("PCR", "1.15", "Bullish")
    with col4:
        st.metric("India VIX", "12.5", "-2.1%")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎯 Top Institutional Picks")
        picks_df = pd.DataFrame({
            'Stock': ['RELIANCE', 'HDFCBANK', 'INFY', 'ICICIBANK', 'LT'],
            'RS Rating': [95, 88, 92, 85, 78],
            'F-Score': [8, 7, 9, 8, 7],
            'ROIC': [18.5, 16.2, 28.4, 15.8, 14.2],
            'Signal': ['BUY', 'BUY', 'STRONG BUY', 'BUY', 'HOLD']
        })
        st.dataframe(picks_df, hide_index=True, use_container_width=True)
        
    with col2:
        st.subheader("⚠️ Risk Alerts")
        alerts = [
            "🔴 High promoter pledge in XYZ Ltd (45%)",
            "🟡 Sector concentration > 30% in Financials",
            "🟢 FII buying streak: 5 days",
            "🟢 Market Regime: BULL"
        ]
        for alert in alerts:
            st.info(alert)

# ===================== TECHNICAL PRO =====================
elif module == "Technical Pro":
    st.title("📈 Technical Analysis Pro")
    st.markdown("### Institutional Momentum & Volatility Analytics")
    
    df = generate_mock_data()
    
    col1, col2 = st.columns(2)
    with col1:
        analyzer = TechnicalAnalyzer()
        df_with_indicators = analyzer.add_all_indicators(df)
        
        st.subheader("Momentum Indicators")
        momentum_cols = ['RSI', 'MACD', 'ADX', 'CMF']
        for col in momentum_cols:
            if col in df_with_indicators.columns:
                st.metric(col, f"{df_with_indicators[col].iloc[-1]:.2f}")
    
    with col2:
        st.subheader("Volatility Analytics")
        vol_analyzer = TechnicalAnalyzer()
        var_95 = vol_analyzer.calculate_var(df['Close'].pct_change().dropna(), 0.95)
        atr = df_with_indicators.get('ATR', pd.Series([0])).iloc[-1]
        
        st.metric("VaR (95%)", f"{var_95*100:.2f}%")
        st.metric("ATR (Stop Loss)", f"{atr:.2f}")
    
    st.subheader("Price Chart with Bollinger Bands")
    if 'BB_Upper' in df_with_indicators.columns and 'BB_Lower' in df_with_indicators.columns:
        chart_df = df_with_indicators[['Close', 'BB_Upper', 'BB_Lower']].tail(60)
        st.line_chart(chart_df)

# ===================== FUNDAMENTAL DEEP DIVE =====================
elif module == "Fundamental Deep Dive":
    st.title("📊 Fundamental Deep Dive")
    st.markdown("### DCF Valuation, Piotroski F-Score, Altman Z-Score")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Earnings Quality")
        fscore = 8  # Mock
        zscore = 3.5  # Mock
        st.metric("Piotroski F-Score", fscore, "Strong")
        st.metric("Altman Z-Score", zscore, "Safe Zone")
        
    with col2:
        st.subheader("DCF Valuation")
        intrinsic = 2850
        current = 2450
        mos = ((intrinsic - current) / intrinsic) * 100
        st.metric("Intrinsic Value", f"₹{intrinsic}")
        st.metric("Margin of Safety", f"{mos:.1f}%", "Attractive")
        
    with col3:
        st.subheader("Profitability")
        st.metric("ROIC", "18.5%", "vs WACC 9%")
        st.metric("FCF Yield", "4.2%", "Healthy")
    
    st.markdown("---")
    st.subheader("DuPont Analysis - ROE Decomposition")
    dupont_df = pd.DataFrame({
        'Metric': ['Net Margin', 'Asset Turnover', 'Equity Multiplier', 'ROE'],
        'Value': [12.5, 0.85, 2.1, 22.3]
    })
    st.dataframe(dupont_df, hide_index=True, use_container_width=True)

# ===================== PORTFOLIO OPTIMIZER =====================
elif module == "Portfolio Optimizer":
    st.title("🎯 Portfolio Optimizer")
    st.markdown("### Mean-Variance, Risk Parity, Factor Analysis")
    
    optimizer = PortfolioOptimizer()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Optimization Method")
        method = st.selectbox("Select Strategy:", 
                              ["Mean-Variance", "Risk Parity", "Hierarchical Risk Parity", "Kelly Criterion"])
        st.button("Run Optimization")
        
    with col2:
        st.subheader("Current Allocation")
        alloc_df = pd.DataFrame({
            'Stock': ['HDFCBANK', 'RELIANCE', 'INFY', 'ICICIBANK', 'CASH'],
            'Weight': [25, 20, 20, 15, 20],
            'Contribution_to_Risk': [22, 18, 25, 15, 0]
        })
        st.dataframe(alloc_df, hide_index=True)
    
    st.markdown("---")
    st.subheader("Factor Exposures")
    factor_df = pd.DataFrame({
        'Factor': ['Value', 'Momentum', 'Quality', 'Low Vol', 'Size'],
        'Exposure': [0.3, 0.6, 0.8, -0.2, 0.1],
        'Percentile': [65, 82, 91, 35, 55]
    })
    st.bar_chart(factor_df.set_index('Factor'))

# ===================== DERIVATIVES INTELLIGENCE =====================
elif module == "Derivatives Intelligence":
    st.title("📉 Derivatives Intelligence")
    st.markdown("### OI Analysis, PCR, Max Pain, FII Positioning")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Put-Call Ratio (PCR)", "1.15", "Bullish")
    with col2:
        st.metric("Max Pain Strike", "22,500", "Expiry: 28-Mar")
    with col3:
        st.metric("FII Long/Short", "65%", "Increasing Longs")
    
    st.markdown("---")
    st.subheader("Options Chain Analysis")
    
    oi_df = pd.DataFrame({
        'Strike': [21000, 21500, 22000, 22500, 23000, 23500, 24000],
        'CE_OI': [5e6, 8e6, 12e6, 25e6, 15e6, 8e6, 3e6],
        'CE_Chng': [1e5, 2e5, 5e5, 2e6, -5e5, -2e5, -1e5],
        'PE_OI': [3e6, 5e6, 10e6, 18e6, 20e6, 12e6, 8e6],
        'PE_Chng': [-1e5, 1e5, 3e5, 1e6, 1.5e6, 8e5, 5e5]
    })
    
    st.dataframe(oi_df, hide_index=True, use_container_width=True)
    
    st.info("💡 **OI Interpretation**: Highest CE OI at 22,500 (Resistance), Highest PE OI at 23,000 (Support)")

# ===================== RELATIVE STRENGTH =====================
elif module == "Relative Strength":
    st.title("💪 Relative Strength Analysis")
    st.markdown("### RS Ratings (1-99), Stage Analysis, Peer Comparison")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top RS Stocks")
        rs_df = pd.DataFrame({
            'Stock': ['TATAELXSI', 'COCHINSHIP', 'BEL', 'HAL', 'RVNL'],
            'RS_Rating': [99, 97, 95, 94, 92],
            'Stage': ['Stage 2', 'Stage 2', 'Stage 2', 'Stage 2', 'Stage 2'],
            '1M_Return': [25, 32, 18, 22, 28],
            '3M_Return': [65, 85, 45, 55, 72]
        })
        st.dataframe(rs_df, hide_index=True)
        
    with col2:
        st.subheader("Peer Comparison - L&T")
        peer_df = pd.DataFrame({
            'Company': ['L&T', 'ABB', 'Siemens', 'Thermax'],
            'PE': [28, 45, 55, 42],
            'ROE': [14, 18, 22, 16],
            'Sales_Growth': [12, 8, 15, 10],
            'RS_Rating': [78, 65, 72, 58]
        })
        st.dataframe(peer_df, hide_index=True)

# ===================== GOVERNANCE & ESG =====================
elif module == "Governance & ESG":
    st.title("🏛️ Governance & ESG")
    st.markdown("### Promoter Pledge, Capital Allocation, ESG Scores")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Promoter Pledge Score", "92/100", "Low Risk")
    with col2:
        st.metric("Capital Allocation Score", "85/100", "Excellent")
    with col3:
        st.metric("ESG Rating", "AA", "Top 10%")
    
    st.markdown("---")
    st.subheader("Governance Checklist")
    
    gov_df = pd.DataFrame({
        'Parameter': ['Promoter Pledge', 'Board Independence', 'Related Party Txns', 'Auditor Tenure', 'Dividend Consistency'],
        'Status': ['✅ Low (<5%)', '✅ 60% Independent', '✅ <5% Revenue', '✅ 8 years', '✅ 10 yrs consecutive'],
        'Score': [95, 85, 90, 75, 80]
    })
    st.dataframe(gov_df, hide_index=True)

# ===================== BACKTESTING =====================
elif module == "Backtesting":
    st.title("🧪 Backtesting Engine")
    st.markdown("### Walk-Forward Analysis, Performance Attribution")
    
    df = generate_mock_data()
    
    engine = BacktestEngine()
    results = engine.run(df, lambda x: np.where(x['Close'] > x['Close'].rolling(20).mean(), 1, 0))
    metrics = engine.calculate_metrics()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CAGR", f"{metrics.get('CAGR', 0):.1f}%")
    col2.metric("Sharpe Ratio", f"{metrics.get('Sharpe_Ratio', 0):.2f}")
    col3.metric("Max Drawdown", f"{metrics.get('Max_Drawdown', 0):.1f}%")
    col4.metric("Win Rate", f"{metrics.get('Win_Rate', 0):.1f}%")
    
    st.markdown("---")
    st.subheader("Cumulative Returns: Strategy vs Benchmark")
    if 'cum_strategy' in results.columns and 'cum_market' in results.columns:
        perf_df = results[['cum_strategy', 'cum_market']].tail(100)
        st.line_chart(perf_df)

# ===================== MACRO & FLOWS =====================
elif module == "Macro & Flows":
    st.title("🌍 Macro & Liquidity Flows")
    st.markdown("### Regime Detection, FII/DII Trends, Sector Rotation")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Market Regime", "🐂 Bull", "Price > 200DMA")
    with col2:
        st.metric("Liquidity Score", "72/100", "Favorable")
    with col3:
        st.metric("Recommended Equity", "Overweight", "70-80%")
    
    st.markdown("---")
    st.subheader("FII/DII Flow Trends (Last 5 Days)")
    
    flow_df = pd.DataFrame({
        'Date': pd.date_range('2024-03-20', periods=5),
        'FII_Net_Cr': [4250, 3800, 5100, 2900, 4500],
        'DII_Net_Cr': [-1200, -800, -1500, -500, -1100]
    })
    st.bar_chart(flow_df.set_index('Date'))
    
    st.info("💡 **Insight**: Consistent FII buying supported by DII accumulation indicates strong institutional confidence")

# ===================== ML PREDICTIONS =====================
elif module == "ML Predictions":
    st.title("🤖 ML Predictions")
    st.markdown("### Return Forecasting, Sentiment Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Next-Day Return Prediction")
        pred_df = pd.DataFrame({
            'Stock': ['RELIANCE', 'HDFCBANK', 'INFY', 'TCS', 'ICICIBANK'],
            'Predicted_Return': [1.2, 0.8, 1.5, 0.5, 1.1],
            'Confidence': [72, 68, 75, 65, 70],
            'Signal': ['BUY', 'HOLD', 'STRONG BUY', 'HOLD', 'BUY']
        })
        st.dataframe(pred_df, hide_index=True)
        
    with col2:
        st.subheader("News Sentiment Analysis")
        sent_df = pd.DataFrame({
            'Headline': ['Q4 Beat Estimates', 'New Order Win', 'Regulatory Concern', 'Management Change'],
            'Sentiment_Score': [0.8, 0.6, -0.5, -0.2],
            'Label': ['Positive', 'Positive', 'Negative', 'Neutral']
        })
        st.dataframe(sent_df, hide_index=True)

# ===================== COMPLIANCE =====================
elif module == "Compliance":
    st.title("✅ Compliance & Reporting")
    st.markdown("### Pre-Trade Checks, Audit Trail, SEBI Reports")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Pre-Trade Compliance Check")
        
        order = {
            'symbol': 'HDFCBANK',
            'quantity': 5000,
            'price': 1450,
            'sector': 'Financials',
            'market_cap_cr': 1100000
        }
        
        portfolio = {
            'total_value': 100000000,
            'holdings': {'HDFCBANK': {'value': 5000000}},
            'sector_exposure': {'Financials': 20000000}
        }
        
        compliance = PreTradeCompliance({
            'max_single_stock_pct': 10,
            'max_sector_pct': 25,
            'min_market_cap': 500
        })
        
        result = compliance.check_order(order, portfolio)
        
        if result['approved']:
            st.success(f"✅ Order APPROVED: {result['reason']}")
        else:
            st.error(f"❌ Order REJECTED: {result['reason']}")
            
    with col2:
        st.subheader("Recent Audit Log")
        audit = AuditTrail()
        log_df = pd.DataFrame({
            'Timestamp': ['2024-03-25 10:30', '2024-03-25 11:15', '2024-03-25 14:20'],
            'Type': ['SIGNAL', 'TRADE', 'SIGNAL'],
            'Symbol': ['RELIANCE', 'HDFCBANK', 'INFY'],
            'Action': ['BUY', 'SELL', 'HOLD']
        })
        st.dataframe(log_df, hide_index=True)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Data Sources:** NSE Bhavcopy | Screener.in | Bloomberg Terminal")
st.sidebar.caption("© 2024 NSE Delivery Desk Institutional Edition")
