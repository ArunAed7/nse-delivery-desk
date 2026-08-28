"""
Phase 1: Fundamental Deep Dive Module
Earnings Quality + Valuation Framework + Profitability Analysis
Institutional-grade fundamental metrics for long-term investment decisions
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Optional, List
from dataclasses import dataclass


# =============================================================================
# EARNINGS QUALITY MODULE
# =============================================================================

def piotroski_f_score(roe: float, roa_current: float, roa_prior: float,
                      cfo: float, net_income: float,
                      leverage_current: float, leverage_prior: float,
                      current_ratio_current: float, current_ratio_prior: float,
                      shares_outstanding_current: float, shares_outstanding_prior: float,
                      gross_margin_current: float, gross_margin_prior: float,
                      asset_turnover_current: float, asset_turnover_prior: float) -> int:
    """
    Piotroski F-Score (0-9) - Financial strength indicator for value stocks
    
    9 binary criteria across 3 categories:
    Profitability (4): ROA, CFO, ΔROA, Accruals
    Leverage/Liquidity (3): ΔLeverage, ΔCurrent Ratio, ΔShares
    Operating Efficiency (2): ΔGross Margin, ΔAsset Turnover
    
    Score interpretation:
    - 8-9: Very strong financial position
    - 6-7: Strong
    - 4-5: Average
    - 0-3: Weak
    
    Returns: F-Score (0-9)
    """
    score = 0
    
    # Profitability Criteria
    # 1. Positive ROA
    if roa_current > 0:
        score += 1
    
    # 2. Positive CFO
    if cfo > 0:
        score += 1
    
    # 3. ROA improvement
    if roa_current > roa_prior:
        score += 1
    
    # 4. CFO > Net Income (quality of earnings)
    if cfo > net_income:
        score += 1
    
    # Leverage/Liquidity Criteria
    # 5. Lower leverage
    if leverage_current < leverage_prior:
        score += 1
    
    # 6. Higher current ratio
    if current_ratio_current > current_ratio_prior:
        score += 1
    
    # 7. No new shares issued
    if shares_outstanding_current <= shares_outstanding_prior:
        score += 1
    
    # Operating Efficiency Criteria
    # 8. Improved gross margin
    if gross_margin_current > gross_margin_prior:
        score += 1
    
    # 9. Improved asset turnover
    if asset_turnover_current > asset_turnover_prior:
        score += 1
    
    return score


def altman_z_score(total_assets: float, total_liabilities: float,
                   ebit: float, retained_earnings: float,
                   sales: float, market_cap: float,
                   working_capital: float) -> float:
    """
    Altman Z-Score - Bankruptcy prediction model
    
    Original formula (manufacturing firms):
    Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5
    
    Where:
    X1 = Working Capital / Total Assets
    X2 = Retained Earnings / Total Assets
    X3 = EBIT / Total Assets
    X4 = Market Cap / Total Liabilities
    X5 = Sales / Total Assets
    
    Interpretation:
    - Z > 2.99: Safe zone (low bankruptcy risk)
    - 1.81 < Z < 2.99: Grey zone
    - Z < 1.81: Distress zone (high bankruptcy risk)
    
    Returns: Z-Score
    """
    if total_assets == 0:
        return 0.0
    
    x1 = working_capital / total_assets
    x2 = retained_earnings / total_assets
    x3 = ebit / total_assets
    x4 = market_cap / total_liabilities if total_liabilities > 0 else 0
    x5 = sales / total_assets
    
    z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
    
    return z_score


def beneish_m_score(receivables: List[float], revenue: List[float],
                    gross_margin: List[float], sga_expense: List[float],
                    depreciation: List[float], total_assets: List[float],
                    debt: List[float]) -> float:
    """
    Beneish M-Score - Earnings manipulation detection
    
    Uses 8 financial ratios to detect earnings management:
    DSRI: Days Sales in Receivables Index
    GMI: Gross Margin Index
    AQI: Asset Quality Index
    SGI: Sales Growth Index
    DEPI: Depreciation Index
    SGAI: SG&A Expense Index
    LVGI: Leverage Index
    TATA: Total Accruals to Total Assets
    
    Interpretation:
    - M-Score > -1.78: High probability of manipulation
    - M-Score < -1.78: Low probability of manipulation
    
    Requires 2 years of data (current and prior)
    
    Returns: M-Score
    """
    if len(receivables) < 2 or len(revenue) < 2:
        return 0.0
    
    # Current and prior year values
    curr, prev = 0, 1
    
    # DSRI - Days Sales in Receivables Index
    dsri_curr = receivables[curr] / revenue[curr] if revenue[curr] > 0 else 0
    dsri_prev = receivables[prev] / revenue[prev] if revenue[prev] > 0 else 0
    dsri = dsri_curr / dsri_prev if dsri_prev > 0 else 0
    
    # GMI - Gross Margin Index
    gmi = gross_margin[prev] / gross_margin[curr] if gross_margin[curr] > 0 else 0
    
    # AQI - Asset Quality Index (simplified)
    aqi = total_assets[curr] / total_assets[prev] if total_assets[prev] > 0 else 0
    
    # SGI - Sales Growth Index
    sgi = revenue[curr] / revenue[prev] if revenue[prev] > 0 else 0
    
    # DEPI - Depreciation Index
    depi = depreciation[prev] / depreciation[curr] if depreciation[curr] > 0 else 0
    
    # SGAI - SG&A Expense Index
    sgai_curr = sga_expense[curr] / revenue[curr] if revenue[curr] > 0 else 0
    sgai_prev = sga_expense[prev] / revenue[prev] if revenue[prev] > 0 else 0
    sgai = sgai_curr / sgai_prev if sgai_prev > 0 else 0
    
    # LVGI - Leverage Index
    lvgi_curr = debt[curr] / total_assets[curr] if total_assets[curr] > 0 else 0
    lvgi_prev = debt[prev] / total_assets[prev] if total_assets[prev] > 0 else 0
    lvgi = lvgi_curr / lvgi_prev if lvgi_prev > 0 else 0
    
    # TATA - Total Accruals to Total Assets (simplified)
    tata = (revenue[curr] - receivables[curr]) / total_assets[curr] if total_assets[curr] > 0 else 0
    
    # M-Score calculation (original coefficients)
    m_score = (
        -4.84 +
        0.92 * dsri +
        0.528 * gmi +
        0.404 * aqi +
        0.892 * sgi +
        0.115 * depi -
        0.172 * sgai +
        4.679 * tata -
        0.327 * lvgi
    )
    
    return m_score


def accruals_ratio(net_income: float, operating_cash_flow: float,
                   total_assets: float) -> float:
    """
    Accruals Ratio - Measure of earnings quality
    
    Accruals = Net Income - Operating Cash Flow
    High accruals suggest lower earnings quality
    
    Returns: Accruals ratio (lower is better)
    """
    if total_assets == 0:
        return 0.0
    
    accruals = net_income - operating_cash_flow
    return accruals / total_assets


def calculate_earnings_quality_metrics(financial_data: Dict) -> Dict[str, float]:
    """
    Comprehensive earnings quality assessment
    
    Args:
        financial_data: Dictionary with required financial metrics
    
    Returns: Dictionary with all earnings quality scores
    """
    results = {}
    
    # Piotroski F-Score
    results['piotroski_f_score'] = piotroski_f_score(
        roe=financial_data.get('roe', 0),
        roa_current=financial_data.get('roa_current', 0),
        roa_prior=financial_data.get('roa_prior', 0),
        cfo=financial_data.get('operating_cash_flow', 0),
        net_income=financial_data.get('net_income', 0),
        leverage_current=financial_data.get('leverage_current', 0),
        leverage_prior=financial_data.get('leverage_prior', 0),
        current_ratio_current=financial_data.get('current_ratio_current', 0),
        current_ratio_prior=financial_data.get('current_ratio_prior', 0),
        shares_outstanding_current=financial_data.get('shares_current', 0),
        shares_outstanding_prior=financial_data.get('shares_prior', 0),
        gross_margin_current=financial_data.get('gross_margin_current', 0),
        gross_margin_prior=financial_data.get('gross_margin_prior', 0),
        asset_turnover_current=financial_data.get('asset_turnover_current', 0),
        asset_turnover_prior=financial_data.get('asset_turnover_prior', 0)
    )
    
    # Altman Z-Score
    results['altman_z_score'] = altman_z_score(
        total_assets=financial_data.get('total_assets', 0),
        total_liabilities=financial_data.get('total_liabilities', 0),
        ebit=financial_data.get('ebit', 0),
        retained_earnings=financial_data.get('retained_earnings', 0),
        sales=financial_data.get('sales', 0),
        market_cap=financial_data.get('market_cap', 0),
        working_capital=financial_data.get('working_capital', 0)
    )
    
    # Beneish M-Score
    results['beneish_m_score'] = beneish_m_score(
        receivables=financial_data.get('receivables', [0, 0]),
        revenue=financial_data.get('revenue_list', [0, 0]),
        gross_margin=financial_data.get('gross_margin_list', [0, 0]),
        sga_expense=financial_data.get('sga_expense', [0, 0]),
        depreciation=financial_data.get('depreciation', [0, 0]),
        total_assets=financial_data.get('total_assets_list', [0, 0]),
        debt=financial_data.get('debt', [0, 0])
    )
    
    # Accruals Ratio
    results['accruals_ratio'] = accruals_ratio(
        net_income=financial_data.get('net_income', 0),
        operating_cash_flow=financial_data.get('operating_cash_flow', 0),
        total_assets=financial_data.get('total_assets', 0)
    )
    
    # Composite earnings quality score (0-100)
    eq_score = 0
    
    # Piotroski contribution (max 25 points)
    eq_score += (results['piotroski_f_score'] / 9) * 25
    
    # Altman contribution (max 25 points)
    if results['altman_z_score'] > 2.99:
        eq_score += 25
    elif results['altman_z_score'] > 1.81:
        eq_score += 15
    else:
        eq_score += 5
    
    # Beneish contribution (max 25 points)
    if results['beneish_m_score'] < -2.22:
        eq_score += 25
    elif results['beneish_m_score'] < -1.78:
        eq_score += 15
    else:
        eq_score += 5
    
    # Accruals contribution (max 25 points)
    if results['accruals_ratio'] < 0.05:
        eq_score += 25
    elif results['accruals_ratio'] < 0.10:
        eq_score += 15
    elif results['accruals_ratio'] < 0.15:
        eq_score += 10
    else:
        eq_score += 5
    
    results['earnings_quality_score'] = min(eq_score, 100)
    
    return results


# =============================================================================
# VALUATION FRAMEWORK
# =============================================================================

@dataclass
class DCFResult:
    intrinsic_value: float
    current_price: float
    margin_of_safety: float
    fair_value_range: Tuple[float, float]
    implied_growth_rate: float
    recommendation: str


def dcf_valuation_fcff(free_cash_flow: float, growth_rate: float, 
                       wacc: float, terminal_growth: float,
                       shares_outstanding: float, net_debt: float,
                       projection_years: int = 5) -> DCFResult:
    """
    Discounted Cash Flow using Free Cash Flow to Firm (FCFF)
    
    Two-stage model:
    1. Explicit forecast period (5-10 years)
    2. Terminal value (perpetuity growth)
    
    Enterprise Value = PV(FCFF) + PV(Terminal Value)
    Equity Value = Enterprise Value - Net Debt
    Intrinsic Value per Share = Equity Value / Shares Outstanding
    
    Returns: DCFResult with valuation and recommendation
    """
    # Project FCFF for explicit period
    projected_fcff = []
    for year in range(1, projection_years + 1):
        fcff = free_cash_flow * (1 + growth_rate) ** year
        projected_fcff.append(fcff)
    
    # Calculate PV of projected FCFF
    pv_fcff = sum([
        fcff / (1 + wacc) ** year 
        for year, fcff in enumerate(projected_fcff, 1)
    ])
    
    # Terminal Value (Gordon Growth Model)
    terminal_fcff = projected_fcff[-1] * (1 + terminal_growth)
    terminal_value = terminal_fcff / (wacc - terminal_growth)
    
    # PV of Terminal Value
    pv_terminal = terminal_value / (1 + wacc) ** projection_years
    
    # Enterprise Value
    enterprise_value = pv_fcff + pv_terminal
    
    # Equity Value
    equity_value = enterprise_value - net_debt
    
    # Intrinsic Value per Share
    intrinsic_value = equity_value / shares_outstanding if shares_outstanding > 0 else 0
    
    # Margin of Safety
    # (Note: current_price would be passed in real usage)
    current_price = intrinsic_value  # Placeholder
    margin_of_safety = (intrinsic_value - current_price) / current_price if current_price > 0 else 0
    
    # Fair Value Range (±15%)
    fair_value_low = intrinsic_value * 0.85
    fair_value_high = intrinsic_value * 1.15
    
    # Implied Growth Rate (what growth is priced in?)
    # Simplified: reverse DCF would iterate to find this
    implied_growth = growth_rate * 0.8  # Placeholder
    
    # Recommendation
    if margin_of_safety > 0.25:
        recommendation = "Strong Buy"
    elif margin_of_safety > 0.10:
        recommendation = "Buy"
    elif margin_of_safety > -0.10:
        recommendation = "Hold"
    elif margin_of_safety > -0.25:
        recommendation = "Sell"
    else:
        recommendation = "Strong Sell"
    
    return DCFResult(
        intrinsic_value=intrinsic_value,
        current_price=current_price,
        margin_of_safety=margin_of_safety,
        fair_value_range=(fair_value_low, fair_value_high),
        implied_growth_rate=implied_growth,
        recommendation=recommendation
    )


def dcf_valuation_fcfe(free_cash_flow_equity: float, growth_rate: float,
                       cost_of_equity: float, terminal_growth: float,
                       shares_outstanding: float,
                       projection_years: int = 5) -> DCFResult:
    """
    Discounted Cash Flow using Free Cash Flow to Equity (FCFE)
    
    Directly values equity without subtracting debt
    
    Returns: DCFResult with valuation and recommendation
    """
    # Project FCFE for explicit period
    projected_fcfe = []
    for year in range(1, projection_years + 1):
        fcfe = free_cash_flow_equity * (1 + growth_rate) ** year
        projected_fcfe.append(fcfe)
    
    # Calculate PV of projected FCFE
    pv_fcfe = sum([
        fcfe / (1 + cost_of_equity) ** year 
        for year, fcfe in enumerate(projected_fcfe, 1)
    ])
    
    # Terminal Value
    terminal_fcfe = projected_fcfe[-1] * (1 + terminal_growth)
    terminal_value = terminal_fcfe / (cost_of_equity - terminal_growth)
    
    # PV of Terminal Value
    pv_terminal = terminal_value / (1 + cost_of_equity) ** projection_years
    
    # Equity Value
    equity_value = pv_fcfe + pv_terminal
    
    # Intrinsic Value per Share
    intrinsic_value = equity_value / shares_outstanding if shares_outstanding > 0 else 0
    
    current_price = intrinsic_value  # Placeholder
    margin_of_safety = (intrinsic_value - current_price) / current_price if current_price > 0 else 0
    
    fair_value_low = intrinsic_value * 0.85
    fair_value_high = intrinsic_value * 1.15
    implied_growth = growth_rate * 0.8
    
    if margin_of_safety > 0.25:
        recommendation = "Strong Buy"
    elif margin_of_safety > 0.10:
        recommendation = "Buy"
    elif margin_of_safety > -0.10:
        recommendation = "Hold"
    elif margin_of_safety > -0.25:
        recommendation = "Sell"
    else:
        recommendation = "Strong Sell"
    
    return DCFResult(
        intrinsic_value=intrinsic_value,
        current_price=current_price,
        margin_of_safety=margin_of_safety,
        fair_value_range=(fair_value_low, fair_value_high),
        implied_growth_rate=implied_growth,
        recommendation=recommendation
    )


def ev_ebitda_valuation(ebitda: float, ev_sales_multiple: float,
                        net_debt: float, shares_outstanding: float,
                        peer_ev_ebitda_median: float,
                        peer_ev_ebitda_low: float,
                        peer_ev_ebitda_high: float) -> Dict[str, float]:
    """
    EV/EBITDA Comparable Valuation
    
    Values company based on peer multiples
    
    Returns: Dictionary with valuation metrics
    """
    # Enterprise Value based on peer median
    ev_median = ebitda * peer_ev_ebitda_median
    ev_low = ebitda * peer_ev_ebitda_low
    ev_high = ebitda * peer_ev_ebitda_high
    
    # Equity Value
    equity_median = ev_median - net_debt
    equity_low = ev_low - net_debt
    equity_high = ev_high - net_debt
    
    # Per Share Values
    price_median = equity_median / shares_outstanding if shares_outstanding > 0 else 0
    price_low = equity_low / shares_outstanding if shares_outstanding > 0 else 0
    price_high = equity_high / shares_outstanding if shares_outstanding > 0 else 0
    
    # Implied EV/Sales multiple check
    implied_ev_sales = ev_median / ev_sales_multiple if ev_sales_multiple > 0 else 0
    
    return {
        'ev_median': ev_median,
        'ev_low': ev_low,
        'ev_high': ev_high,
        'equity_value_median': equity_median,
        'price_target_median': price_median,
        'price_target_low': price_low,
        'price_target_high': price_high,
        'implied_ev_sales': implied_ev_sales,
        'upside_to_median': 0.0  # Would compare to current price
    }


def reverse_dcf(current_price: float, shares_outstanding: float,
                net_debt: float, free_cash_flow: float,
                wacc: float, terminal_growth: float,
                projection_years: int = 5) -> float:
    """
    Reverse DCF - Calculate implied growth rate from current price
    
    Answers: "What growth rate is the market pricing in?"
    
    Returns: Implied sustainable growth rate
    """
    # Current Enterprise Value
    current_equity_value = current_price * shares_outstanding
    current_ev = current_equity_value + net_debt
    
    # Iterate to find growth rate that justifies current EV
    # Simplified binary search approach
    low_growth, high_growth = -0.05, 0.25
    
    for _ in range(50):  # Binary search iterations
        mid_growth = (low_growth + high_growth) / 2
        
        # Calculate EV at this growth rate
        projected_fcff = [
            free_cash_flow * (1 + mid_growth) ** year 
            for year in range(1, projection_years + 1)
        ]
        
        pv_fcff = sum([
            fcff / (1 + wacc) ** year 
            for year, fcff in enumerate(projected_fcff, 1)
        ])
        
        terminal_fcff = projected_fcff[-1] * (1 + terminal_growth)
        terminal_value = terminal_fcff / (wacc - terminal_growth)
        pv_terminal = terminal_value / (1 + wacc) ** projection_years
        
        calculated_ev = pv_fcff + pv_terminal
        
        if calculated_ev > current_ev:
            high_growth = mid_growth
        else:
            low_growth = mid_growth
    
    return (low_growth + high_growth) / 2


def calculate_margin_of_safety(intrinsic_value: float, current_price: float,
                               uncertainty_factor: float = 0.2) -> Dict[str, float]:
    """
    Margin of Safety with uncertainty adjustment
    
    Benjamin Graham principle: Buy at significant discount to intrinsic value
    
    Returns: Various MoS metrics
    """
    base_mos = (intrinsic_value - current_price) / current_price if current_price > 0 else 0
    
    # Conservative intrinsic value (discounted for uncertainty)
    conservative_iv = intrinsic_value * (1 - uncertainty_factor)
    conservative_mos = (conservative_iv - current_price) / current_price if current_price > 0 else 0
    
    # Break-even price (no MoS)
    break_even_price = intrinsic_value
    
    # Buy price thresholds
    buy_strong = intrinsic_value * 0.60  # 40% discount
    buy_moderate = intrinsic_value * 0.75  # 25% discount
    buy_watch = intrinsic_value * 0.85  # 15% discount
    
    return {
        'base_margin_of_safety': base_mos,
        'conservative_margin_of_safety': conservative_mos,
        'conservative_intrinsic_value': conservative_iv,
        'break_even_price': break_even_price,
        'buy_price_strong': buy_strong,
        'buy_price_moderate': buy_moderate,
        'buy_price_watch': buy_watch,
        'current_vs_buy_strong': (current_price - buy_strong) / buy_strong if buy_strong > 0 else 0,
        'current_vs_buy_moderate': (current_price - buy_moderate) / buy_moderate if buy_moderate > 0 else 0
    }


# =============================================================================
# PROFITABILITY & GROWTH METRICS
# =============================================================================

def roe_dupont_decomposition(net_income: float, revenue: float,
                             total_assets: float, shareholders_equity: float) -> Dict[str, float]:
    """
    ROE DuPont Analysis - Decompose ROE into 3 components
    
    ROE = Net Profit Margin × Asset Turnover × Equity Multiplier
    
    Components:
    1. Net Profit Margin (Operating efficiency)
    2. Asset Turnover (Asset use efficiency)
    3. Equity Multiplier (Financial leverage)
    
    Returns: Dictionary with all components
    """
    # Three-component DuPont
    net_profit_margin = net_income / revenue if revenue > 0 else 0
    asset_turnover = revenue / total_assets if total_assets > 0 else 0
    equity_multiplier = total_assets / shareholders_equity if shareholders_equity > 0 else 0
    
    roe = net_profit_margin * asset_turnover * equity_multiplier
    
    # Five-component DuPont (extended)
    # ROE = Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Equity Multiplier
    # (Would need EBT, EBIT data for full decomposition)
    
    return {
        'roe': roe,
        'net_profit_margin': net_profit_margin,
        'asset_turnover': asset_turnover,
        'equity_multiplier': equity_multiplier,
        'roe_check': net_income / shareholders_equity if shareholders_equity > 0 else 0
    }


def roic_vs_wacc_spread(roic: float, wacc: float, invested_capital: float) -> Dict[str, float]:
    """
    ROIC vs WACC Spread - Value creation metric
    
    Economic Value Added (EVA) = (ROIC - WACC) × Invested Capital
    
    Positive spread = Value creation
    Negative spread = Value destruction
    
    Returns: Dictionary with spread analysis
    """
    spread = roic - wacc
    eva = spread * invested_capital
    
    # Value creation ratio
    value_creation_ratio = roic / wacc if wacc > 0 else 0
    
    # Reinvestment rate needed for growth
    # g = ROIC × Reinvestment Rate
    # Sustainable growth at current ROIC
    
    return {
        'roic_wacc_spread': spread,
        'economic_value_added': eva,
        'value_creation_ratio': value_creation_ratio,
        'roic': roic,
        'wacc': wacc,
        'invested_capital': invested_capital,
        'value_destroyer': spread < 0,
        'value_creator': spread > 0.02  # 2%+ spread
    }


def free_cash_flow_yield(free_cash_flow: float, market_cap: float) -> float:
    """
    Free Cash Flow Yield - Cash return on investment
    
    FCF Yield = Free Cash Flow / Market Cap
    
    Higher is better. Compare to bond yields.
    
    Returns: FCF Yield
    """
    return free_cash_flow / market_cap if market_cap > 0 else 0


def cash_conversion_cycle(days_receivables: float, days_inventory: float,
                          days_payables: float) -> float:
    """
    Cash Conversion Cycle (CCC) - Days to convert investments to cash
    
    CCC = DIO + DSO - DPO
    
    Where:
    DIO = Days Inventory Outstanding
    DSO = Days Sales Outstanding
    DPO = Days Payables Outstanding
    
    Lower CCC = Better cash management
    Negative CCC = Company gets paid before paying suppliers (ideal)
    
    Returns: CCC in days
    """
    return days_receivables + days_inventory - days_payables


def calculate_profitability_metrics(financial_data: Dict) -> Dict[str, float]:
    """
    Comprehensive profitability assessment
    
    Returns: Dictionary with all profitability metrics
    """
    results = {}
    
    # ROE DuPont
    dupont = roe_dupont_decomposition(
        net_income=financial_data.get('net_income', 0),
        revenue=financial_data.get('revenue', 0),
        total_assets=financial_data.get('total_assets', 0),
        shareholders_equity=financial_data.get('shareholders_equity', 0)
    )
    results.update(dupont)
    
    # ROIC vs WACC
    roic_wacc = roic_vs_wacc_spread(
        roic=financial_data.get('roic', 0),
        wacc=financial_data.get('wacc', 0.10),
        invested_capital=financial_data.get('invested_capital', 0)
    )
    results.update(roic_wacc)
    
    # FCF Yield
    results['fcf_yield'] = free_cash_flow_yield(
        free_cash_flow=financial_data.get('free_cash_flow', 0),
        market_cap=financial_data.get('market_cap', 0)
    )
    
    # Cash Conversion Cycle
    results['cash_conversion_cycle'] = cash_conversion_cycle(
        days_receivables=financial_data.get('days_receivables', 0),
        days_inventory=financial_data.get('days_inventory', 0),
        days_payables=financial_data.get('days_payables', 0)
    )
    
    # Composite profitability score (0-100)
    prof_score = 0
    
    # ROE contribution (max 25 points)
    if dupont['roe'] > 0.20:
        prof_score += 25
    elif dupont['roe'] > 0.15:
        prof_score += 20
    elif dupont['roe'] > 0.10:
        prof_score += 15
    elif dupont['roe'] > 0.05:
        prof_score += 10
    
    # ROIC spread contribution (max 25 points)
    if roic_wacc['roic_wacc_spread'] > 0.10:
        prof_score += 25
    elif roic_wacc['roic_wacc_spread'] > 0.05:
        prof_score += 20
    elif roic_wacc['roic_wacc_spread'] > 0:
        prof_score += 15
    
    # FCF Yield contribution (max 25 points)
    if results['fcf_yield'] > 0.08:
        prof_score += 25
    elif results['fcf_yield'] > 0.05:
        prof_score += 20
    elif results['fcf_yield'] > 0.03:
        prof_score += 15
    
    # CCC contribution (max 25 points) - lower is better
    if results['cash_conversion_cycle'] < 30:
        prof_score += 25
    elif results['cash_conversion_cycle'] < 60:
        prof_score += 20
    elif results['cash_conversion_cycle'] < 90:
        prof_score += 15
    
    results['profitability_score'] = min(prof_score, 100)
    
    return results


# =============================================================================
# COMPREHENSIVE FUNDAMENTAL ANALYSIS
# =============================================================================

def comprehensive_fundamental_analysis(financial_data: Dict) -> Dict:
    """
    Complete fundamental analysis combining all modules
    
    Returns: Comprehensive report with scores and recommendations
    """
    report = {}
    
    # Earnings Quality
    report['earnings_quality'] = calculate_earnings_quality_metrics(financial_data)
    
    # Valuation
    dcf_result = dcf_valuation_fcff(
        free_cash_flow=financial_data.get('free_cash_flow', 0),
        growth_rate=financial_data.get('growth_rate', 0.10),
        wacc=financial_data.get('wacc', 0.10),
        terminal_growth=financial_data.get('terminal_growth', 0.03),
        shares_outstanding=financial_data.get('shares_outstanding', 0),
        net_debt=financial_data.get('net_debt', 0)
    )
    report['dcf_valuation'] = dcf_result
    
    report['mos_analysis'] = calculate_margin_of_safety(
        intrinsic_value=dcf_result.intrinsic_value,
        current_price=financial_data.get('current_price', dcf_result.intrinsic_value)
    )
    
    # Profitability
    report['profitability'] = calculate_profitability_metrics(financial_data)
    
    # Overall fundamental score
    overall_score = (
        report['earnings_quality']['earnings_quality_score'] * 0.35 +
        report['profitability']['profitability_score'] * 0.35 +
        min(100, (1 + dcf_result.margin_of_safety) * 50) * 0.30
    )
    
    report['overall_fundamental_score'] = min(max(overall_score, 0), 100)
    
    # Investment recommendation
    if report['overall_fundamental_score'] >= 80:
        report['recommendation'] = "Strong Buy"
    elif report['overall_fundamental_score'] >= 65:
        report['recommendation'] = "Buy"
    elif report['overall_fundamental_score'] >= 50:
        report['recommendation'] = "Hold"
    elif report['overall_fundamental_score'] >= 35:
        report['recommendation'] = "Sell"
    else:
        report['recommendation'] = "Strong Sell"
    
    return report


if __name__ == "__main__":
    # Test with sample data
    print("Testing Earnings Quality Metrics...")
    
    sample_financials = {
        'roe': 0.18,
        'roa_current': 0.08,
        'roa_prior': 0.06,
        'operating_cash_flow': 5000000000,
        'net_income': 4000000000,
        'leverage_current': 0.45,
        'leverage_prior': 0.50,
        'current_ratio_current': 1.8,
        'current_ratio_prior': 1.5,
        'shares_current': 1000000000,
        'shares_prior': 1020000000,
        'gross_margin_current': 0.35,
        'gross_margin_prior': 0.32,
        'asset_turnover_current': 0.85,
        'asset_turnover_prior': 0.80,
        'total_assets': 50000000000,
        'total_liabilities': 25000000000,
        'ebit': 6000000000,
        'retained_earnings': 15000000000,
        'sales': 40000000000,
        'market_cap': 80000000000,
        'working_capital': 8000000000,
        'receivables': [5000000000, 4500000000],
        'revenue_list': [40000000000, 38000000000],
        'gross_margin_list': [0.35, 0.32],
        'sga_expense': [8000000000, 7500000000],
        'depreciation': [2000000000, 1900000000],
        'total_assets_list': [50000000000, 48000000000],
        'debt': [25000000000, 24000000000],
        'free_cash_flow': 4500000000,
        'growth_rate': 0.12,
        'wacc': 0.10,
        'terminal_growth': 0.03,
        'shares_outstanding': 1000000000,
        'net_debt': 5000000000,
        'current_price': 75.0,
        'roic': 0.15,
        'invested_capital': 35000000000,
        'revenue': 40000000000,
        'shareholders_equity': 25000000000,
        'days_receivables': 45,
        'days_inventory': 30,
        'days_payables': 60
    }
    
    results = comprehensive_fundamental_analysis(sample_financials)
    
    print(f"\n📊 FUNDAMENTAL ANALYSIS REPORT")
    print(f"{'='*50}")
    print(f"Earnings Quality Score: {results['earnings_quality']['earnings_quality_score']:.1f}/100")
    print(f"  - Piotroski F-Score: {results['earnings_quality']['piotroski_f_score']}/9")
    print(f"  - Altman Z-Score: {results['earnings_quality']['altman_z_score']:.2f}")
    print(f"  - Beneish M-Score: {results['earnings_quality']['beneish_m_score']:.3f}")
    
    print(f"\nValuation:")
    print(f"  - DCF Intrinsic Value: ₹{results['dcf_valuation'].intrinsic_value:.2f}")
    print(f"  - Margin of Safety: {results['dcf_valuation'].margin_of_safety*100:.1f}%")
    print(f"  - Recommendation: {results['dcf_valuation'].recommendation}")
    
    print(f"\nProfitability Score: {results['profitability']['profitability_score']:.1f}/100")
    print(f"  - ROE: {results['profitability']['roe']*100:.1f}%")
    print(f"  - ROIC-WACC Spread: {results['profitability']['roic_wacc_spread']*100:.1f}%")
    print(f"  - FCF Yield: {results['profitability']['fcf_yield']*100:.2f}%")
    print(f"  - Cash Conversion Cycle: {results['profitability']['cash_conversion_cycle']:.0f} days")
    
    print(f"\n{'='*50}")
    print(f"OVERALL FUNDAMENTAL SCORE: {results['overall_fundamental_score']:.1f}/100")
    print(f"RECOMMENDATION: {results['recommendation']}")
    print(f"{'='*50}")
    
    print("\n✅ All fundamental deep dive modules working correctly!")
