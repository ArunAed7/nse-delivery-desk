#!/usr/bin/env python3
"""
Phase 1 Institutional Modules - Test Suite
Tests all 5 Phase 1 modules: Momentum, Volatility, Earnings Quality, Valuation, Relative Strength
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_mock_data():
    """Generate realistic mock market data"""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=504, freq='B')
    stocks = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']
    
    data = []
    for stock in stocks:
        base_price = np.random.uniform(500, 2500)
        prices = [base_price]
        volumes = []
        
        for i in range(1, len(dates)):
            drift = np.random.uniform(-0.0005, 0.0015)
            vol = np.random.uniform(0.015, 0.035)
            change = np.random.normal(drift, vol)
            prices.append(prices[-1] * (1 + change))
            volumes.append(np.random.randint(500000, 5000000))
        
        for i, date in enumerate(dates):
            data.append({
                'date': date,
                'symbol': stock,
                'open': prices[i] * (1 + np.random.uniform(-0.005, 0.005)),
                'high': prices[i] * (1 + np.random.uniform(0, 0.02)),
                'low': prices[i] * (1 - np.random.uniform(0, 0.02)),
                'close': prices[i],
                'volume': volumes[i] if i < len(volumes) else np.random.randint(500000, 5000000),
                'turnover': prices[i] * (volumes[i] if i < len(volumes) else np.random.randint(500000, 5000000))
            })
    
    return pd.DataFrame(data)

def test_technical_pro(df):
    """Test Technical Pro module (Momentum + Volatility)"""
    print("=" * 60)
    print("1. TESTING TECHNICAL PRO (Momentum + Volatility)")
    print("=" * 60)
    
    from src.technical_pro import add_momentum_indicators, add_volatility_indicators
    
    sample = df[df['symbol'] == 'RELIANCE'].copy().reset_index(drop=True)
    print(f"Input: {len(sample)} rows for RELIANCE")
    
    # Add indicators
    sample = add_momentum_indicators(sample)
    sample = add_volatility_indicators(sample)
    
    latest = sample.iloc[-1]
    
    print("\nLatest Indicator Values:")
    print(f"  Connors RSI:     {latest.get('mom_crsi', 'N/A')}")
    print(f"  MACD:            {latest.get('macd_macd_line', 'N/A')}")
    print(f"  MACD Signal:     {latest.get('macd_signal_line', 'N/A')}")
    print(f"  ADX:             {latest.get('adx_adx', 'N/A')}")
    print(f"  VaR (95%):       {latest.get('var_95', 'N/A')}")
    print(f"  ATR:             {latest.get('atr', 'N/A')}")
    print(f"  Vol Regime:      {latest.get('vol_regime', 'N/A')}")
    print(f"  Bollinger Upper: {latest.get('bb_upper', 'N/A')}")
    print(f"  Bollinger Lower: {latest.get('bb_lower', 'N/A')}")
    
    # Verify key columns exist (with correct prefixes)
    required_cols = ['mom_crsi', 'macd_macd_line', 'adx_adx', 'var_95', 'atr', 'vol_regime']
    missing = [c for c in required_cols if c not in sample.columns]
    
    if missing:
        print(f"\n❌ FAILED: Missing columns: {missing}")
        print(f"   Available columns: {[c for c in sample.columns if 'connors' in c.lower() or 'macd' in c.lower() or 'adx' in c.lower()]}")
        return False
    
    print("\n✅ TECHNICAL PRO: PASSED\n")
    return True

def test_fundamentals_deep():
    """Test Fundamentals Deep module (Earnings Quality + Valuation)"""
    print("=" * 60)
    print("2. TESTING FUNDAMENTALS DEEP (Earnings Quality + Valuation)")
    print("=" * 60)
    
    from src.fundamentals_deep import (
        piotroski_f_score, altman_z_score,
        beneish_m_score, dcf_valuation_fcff,
        roe_dupont_decomposition, roic_vs_wacc_spread
    )
    
    # Calculate all metrics with proper parameters
    fscore = piotroski_f_score(
        roe=0.12, roa_current=0.06, roa_prior=0.057, cfo=22000, net_income=15000,
        leverage_current=0.48, leverage_prior=0.51,
        current_ratio_current=1.6, current_ratio_prior=1.5,
        shares_outstanding_current=1000, shares_outstanding_prior=1000,
        gross_margin_current=0.40, gross_margin_prior=0.39,
        asset_turnover_current=0.72, asset_turnover_prior=0.70
    )
    
    fund_data = {
        'net_income': 15000, 'total_assets': 250000, 'total_liabilities': 120000,
        'current_assets': 80000, 'current_liabilities': 50000, 'revenue': 180000,
        'gross_profit': 72000, 'ebit': 25000, 'working_capital': 30000,
        'retained_earnings': 85000, 'market_cap': 320000, 'shares_outstanding': 1000,
        'free_cash_flow': 18000, 'book_value': 130000, 'debt': 60000,
        'cash': 25000, 'prev_revenue': 165000, 'prev_net_income': 13500,
        'prev_total_assets': 235000, 'prev_working_capital': 28000,
        'prev_roa': 0.057, 'operating_cash_flow': 22000, 'capex': 4000,
        'wacc': 0.095, 'growth_rate': 0.06, 'tax_rate': 0.25
    }
    
    zscore = altman_z_score(
        total_assets=250000, total_liabilities=120000, ebit=25000,
        retained_earnings=85000, sales=180000, market_cap=320000,
        working_capital=30000
    )
    mscore = beneish_m_score(
        receivables=[25000, 23000], revenue=[180000, 165000],
        gross_margin=[0.40, 0.39], sga_expense=[35000, 33000],
        depreciation=[8000, 7500], total_assets=[250000, 235000],
        debt=[60000, 58000]
    )
    dcf_result = dcf_valuation_fcff(
        free_cash_flow=18000, growth_rate=0.06, wacc=0.095,
        terminal_growth=0.03, shares_outstanding=1000, net_debt=35000
    )
    roe_dupont = roe_dupont_decomposition(
        net_income=15000, revenue=180000, total_assets=250000,
        shareholders_equity=130000
    )
    roic_spread = roic_vs_wacc_spread(
        roic=0.12, wacc=0.095, invested_capital=190000
    )
    
    print("\nEarnings Quality Metrics:")
    strength = 'Strong' if fscore >= 6 else 'Weak'
    print(f"  Piotroski F-Score:  {fscore}/9 ({strength})")
    
    if zscore > 2.99:
        zone = 'Safe'
    elif zscore > 1.81:
        zone = 'Grey'
    else:
        zone = 'Distress'
    print(f"  Altman Z-Score:     {zscore:.2f} ({zone})")
    
    manip = 'Unlikely Manipulator' if mscore < -1.78 else 'Likely Manipulator'
    print(f"  Beneish M-Score:    {mscore:.2f} ({manip})")
    
    print("\nValuation Metrics:")
    dcf_val = dcf_result.intrinsic_value if hasattr(dcf_result, 'intrinsic_value') else dcf_result
    print(f"  DCF Value:          Rs.{dcf_val:.2f}")
    print(f"  ROE DuPont:         {roe_dupont['roe']:.2%}")
    print(f"    - Net Margin:     {roe_dupont['net_profit_margin']:.2%}")
    print(f"    - Asset Turnover: {roe_dupont['asset_turnover']:.2f}")
    print(f"    - Equity Mult:    {roe_dupont['equity_multiplier']:.2f}")
    print(f"  ROIC vs WACC:       {roic_spread['spread']:.2%} spread")
    
    # Validate ranges
    if not (0 <= fscore <= 9):
        print(f"\n❌ FAILED: F-Score out of range: {fscore}")
        return False
    
    print("\n✅ FUNDAMENTALS DEEP: PASSED\n")
    return True

def test_relative_strength(df):
    """Test Relative Strength Pro module"""
    print("=" * 60)
    print("3. TESTING RELATIVE STRENGTH PRO")
    print("=" * 60)
    
    from src.relative_strength_pro import (
        calculate_rs_rating, stage_analysis, 
        peer_relative_strength, rs_vs_index
    )
    
    results = []
    for symbol in df['symbol'].unique():
        stock_df = df[df['symbol'] == symbol].copy().reset_index(drop=True)
        
        # Calculate RS rating
        rs_rating = calculate_rs_rating(stock_df['close'], df)
        
        # Stage analysis
        stage = stage_analysis(stock_df['close'])
        
        # RS vs Index
        rs_idx = rs_vs_index(stock_df['close'], df)
        
        results.append({
            'Symbol': symbol,
            'RS_Rating': rs_rating.iloc[-1] if hasattr(rs_rating, 'iloc') else rs_rating,
            'Stage': stage.iloc[-1] if hasattr(stage, 'iloc') else stage,
            'RS_vs_Index': rs_idx.iloc[-1] if hasattr(rs_idx, 'iloc') else rs_idx
        })
    
    rs_df = pd.DataFrame(results).sort_values('RS_Rating', ascending=False)
    
    print("\nRS Ratings (All Stocks):")
    for _, row in rs_df.iterrows():
        print(f"  {row['Symbol']:12} RS={row['RS_Rating']:5.1f}/99  Stage={row['Stage']}  vs Index={row['RS_vs_index']:.2%}")
    
    # Verify ratings are in valid range
    if not ((0 <= rs_df['RS_Rating'].min()) and (rs_df['RS_Rating'].max() <= 99)):
        print(f"\n❌ FAILED: RS Ratings out of 0-99 range")
        return False
    
    print("\n✅ RELATIVE STRENGTH PRO: PASSED\n")
    return True

def main():
    print("\n" + "=" * 60)
    print("PHASE 1 INSTITUTIONAL MODULES - TEST SUITE")
    print("=" * 60 + "\n")
    
    # Generate mock data
    print("Generating mock market data...")
    df = generate_mock_data()
    print(f"Generated {len(df)} rows for {df['symbol'].nunique()} stocks\n")
    
    # Run tests
    results = {
        'Technical Pro': test_technical_pro(df),
        'Fundamentals Deep': test_fundamentals_deep(),
        'Relative Strength Pro': test_relative_strength(df)
    }
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for module, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {module:25} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL PHASE 1 MODULES VERIFIED SUCCESSFULLY!")
        print("=" * 60)
        print("\nPhase 1 Complete:")
        print("  ✅ Momentum Suite")
        print("  ✅ Volatility Analytics")
        print("  ✅ Earnings Quality")
        print("  ✅ Valuation Framework")
        print("  ✅ Relative Strength")
        return 0
    else:
        print("SOME TESTS FAILED - REVIEW OUTPUT ABOVE")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    exit(main())
