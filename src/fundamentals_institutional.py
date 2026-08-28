"""
Institutional-Grade Fundamental Analysis Module
===============================================
Phase 1: Earnings Quality + Advanced Valuation + Growth & Profitability

Features:
- Piotroski F-Score (9-point financial strength)
- Altman Z-Score (bankruptcy prediction)
- Beneish M-Score (earnings manipulation detection)
- DCF Valuation (FCFF/FCFE models)
- EV/EBITDA, SOTP valuation
- ROE DuPont analysis
- ROIC vs WACC
- Free Cash Flow yield
- Cash Conversion Cycle
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime


# ============================================================================
# EARNINGS QUALITY METRICS
# ============================================================================

def piotroski_f_score(financials: Dict) -> int:
    """
    Calculate Piotroski F-Score (0-9) measuring financial strength.
    
    Components:
    1. Positive Net Income
    2. Positive Operating Cash Flow
    3. Increasing ROA
    4. OCF > Net Income (quality of earnings)
    5. Decreasing Leverage
    6. Increasing Current Ratio
    7. No new shares issued
    8. Increasing Gross Margin
    9. Increasing Asset Turnover
    
    Score interpretation:
    - 8-9: High quality, strong financial position
    - 5-7: Average quality
    - 0-4: Low quality, weak financial position
    """
    score = 0
    
    # 1. Positive Net Income
    if financials.get('net_income', 0) > 0:
        score += 1
    
    # 2. Positive Operating Cash Flow
    if financials.get('operating_cash_flow', 0) > 0:
        score += 1
    
    # 3. Increasing ROA (current vs previous year)
    roa_current = financials.get('roa_current', 0)
    roa_prev = financials.get('roa_prev', 0)
    if roa_current > roa_prev:
        score += 1
    
    # 4. OCF > Net Income (accruals check)
    ocf = financials.get('operating_cash_flow', 0)
    ni = financials.get('net_income', 0)
    if ocf > ni:
        score += 1
    
    # 5. Decreasing Leverage (Debt/Assets)
    leverage_current = financials.get('leverage_current', 999)
    leverage_prev = financials.get('leverage_prev', 0)
    if leverage_current < leverage_prev:
        score += 1
    
    # 6. Increasing Current Ratio
    cr_current = financials.get('current_ratio_current', 0)
    cr_prev = financials.get('current_ratio_prev', 0)
    if cr_current > cr_prev:
        score += 1
    
    # 7. No new shares issued (shares outstanding decreased or stable)
    shares_current = financials.get('shares_current', float('inf'))
    shares_prev = financials.get('shares_prev', float('inf'))
    if shares_current <= shares_prev:
        score += 1
    
    # 8. Increasing Gross Margin
    gm_current = financials.get('gross_margin_current', 0)
    gm_prev = financials.get('gross_margin_prev', 0)
    if gm_current > gm_prev:
        score += 1
    
    # 9. Increasing Asset Turnover
    at_current = financials.get('asset_turnover_current', 0)
    at_prev = financials.get('asset_turnover_prev', 0)
    if at_current > at_prev:
        score += 1
    
    return score


def altman_z_score(financials: Dict) -> float:
    """
    Calculate Altman Z-Score for bankruptcy prediction.
    
    Formula (for public manufacturers):
    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
    
    Where:
    X1 = Working Capital / Total Assets
    X2 = Retained Earnings / Total Assets
    X3 = EBIT / Total Assets
    X4 = Market Value of Equity / Total Liabilities
    X5 = Sales / Total Assets
    
    Interpretation:
    - Z > 2.99: Safe zone (low bankruptcy risk)
    - 1.81 < Z < 2.99: Grey zone
    - Z < 1.81: Distress zone (high bankruptcy risk)
    """
    wc_ta = financials.get('working_capital', 0) / max(financials.get('total_assets', 1), 1)
    re_ta = financials.get('retained_earnings', 0) / max(financials.get('total_assets', 1), 1)
    ebit_ta = financials.get('ebit', 0) / max(financials.get('total_assets', 1), 1)
    mve_tl = financials.get('market_cap', 0) / max(financials.get('total_liabilities', 1), 1)
    sales_ta = financials.get('revenue', 0) / max(financials.get('total_assets', 1), 1)
    
    z_score = (1.2 * wc_ta + 
               1.4 * re_ta + 
               3.3 * ebit_ta + 
               0.6 * mve_tl + 
               1.0 * sales_ta)
    
    return z_score


def beneish_m_score(financials: Dict) -> float:
    """
    Calculate Beneish M-Score for detecting earnings manipulation.
    
    Eight variables:
    DSRI: Days Sales in Receivables Index
    GMI: Gross Margin Index
    AQI: Asset Quality Index
    SGI: Sales Growth Index
    DEPI: Depreciation Index
    SGAI: SG&A Expense Index
    LVGI: Leverage Index
    TATA: Total Accruals to Total Assets
    
    M-Score > -1.78 suggests high probability of manipulation
    """
    # DSRI - Days Sales in Receivables Index
    dsri_current = financials.get('receivables_current', 0) / max(financials.get('revenue_current', 1), 1)
    dsri_prev = financials.get('receivables_prev', 0) / max(financials.get('revenue_prev', 1), 1)
    dsri = dsri_current / max(dsri_prev, 0.001)
    
    # GMI - Gross Margin Index
    gmi = financials.get('gross_margin_prev', 0) / max(financials.get('gross_margin_current', 0.001), 0.001)
    
    # AQI - Asset Quality Index
    aqi_current = (financials.get('total_assets_current', 0) - 
                   financials.get('ppe_current', 0) - 
                   financials.get('ca_current', 0)) / max(financials.get('total_assets_current', 1), 1)
    aqi_prev = (financials.get('total_assets_prev', 0) - 
                financials.get('ppe_prev', 0) - 
                financials.get('ca_prev', 0)) / max(financials.get('total_assets_prev', 1), 1)
    aqi = aqi_current / max(aqi_prev, 0.001)
    
    # SGI - Sales Growth Index
    sgi = financials.get('revenue_current', 0) / max(financials.get('revenue_prev', 0.001), 0.001)
    
    # DEPI - Depreciation Index
    dep_current = financials.get('depreciation_current', 0) / max(
        financials.get('ppe_current', 1) + financials.get('depreciation_current', 1), 1)
    dep_prev = financials.get('depreciation_prev', 0) / max(
        financials.get('ppe_prev', 1) + financials.get('depreciation_prev', 1), 1)
    depi = dep_current / max(dep_prev, 0.001)
    
    # SGAI - SG&A Expense Index
    sgai_current = financials.get('sga_current', 0) / max(financials.get('revenue_current', 1), 1)
    sgai_prev = financials.get('sga_prev', 0) / max(financials.get('revenue_prev', 1), 1)
    sgai = sgai_current / max(sgai_prev, 0.001)
    
    # LVGI - Leverage Index
    lvgi_current = financials.get('debt_current', 0) / max(financials.get('total_assets_current', 1), 1)
    lvgi_prev = financials.get('debt_prev', 0) / max(financials.get('total_assets_prev', 1), 1)
    lvgi = lvgi_current / max(lvgi_prev, 0.001)
    
    # TATA - Total Accruals to Total Assets
    cfo = financials.get('operating_cash_flow', 0)
    ni = financials.get('net_income', 0)
    tata = (ni - cfo) / max(financials.get('total_assets_current', 1), 1)
    
    # M-Score calculation
    m_score = (-4.84 + 
               0.92 * dsri + 
               0.528 * gmi + 
               0.404 * aqi + 
               0.892 * sgi + 
               0.115 * depi + 
               -0.172 * sgai + 
               4.679 * tata + 
               -0.327 * lvgi)
    
    return m_score


def accruals_ratio(financials: Dict) -> float:
    """
    Calculate accruals ratio to detect earnings quality issues.
    Lower is better (more cash-based earnings).
    
    Accruals Ratio = (Net Income - Operating Cash Flow) / Total Assets
    """
    ni = financials.get('net_income', 0)
    ocf = financials.get('operating_cash_flow', 0)
    assets = financials.get('total_assets', 1)
    
    return (ni - ocf) / max(assets, 1)


# ============================================================================
# VALUATION MODELS
# ============================================================================

def dcf_fcff(valuation_inputs: Dict) -> Dict:
    """
    Discounted Cash Flow using Free Cash Flow to Firm (FCFF).
    
    Inputs required:
    - fcff_current: Current FCFF
    - growth_rates: List of growth rates for projection period
    - terminal_growth: Terminal growth rate
    - wacc: Weighted Average Cost of Capital
    - debt: Total debt
    - cash: Cash and equivalents
    - shares_outstanding: Number of shares
    
    Returns:
    - Enterprise value
    - Equity value
    - Intrinsic value per share
    - Margin of safety
    """
    fcff = valuation_inputs.get('fcff_current', 0)
    growth_rates = valuation_inputs.get('growth_rates', [0.10] * 5)
    terminal_growth = valuation_inputs.get('terminal_growth', 0.03)
    wacc = valuation_inputs.get('wacc', 0.10)
    debt = valuation_inputs.get('debt', 0)
    cash = valuation_inputs.get('cash', 0)
    shares = valuation_inputs.get('shares_outstanding', 1)
    current_price = valuation_inputs.get('current_price', 0)
    
    # Project FCFF
    projected_fcff = []
    for i, g in enumerate(growth_rates):
        fcff = fcff * (1 + g)
        projected_fcff.append(fcff)
    
    # Calculate terminal value (Gordon Growth Model)
    terminal_fcff = projected_fcff[-1] * (1 + terminal_growth)
    terminal_value = terminal_fcff / (wacc - terminal_growth)
    
    # Discount to present value
    pv_fcff = sum([fcff / ((1 + wacc) ** (i + 1)) for i, fcff in enumerate(projected_fcff)])
    pv_terminal = terminal_value / ((1 + wacc) ** len(growth_rates))
    
    # Enterprise Value
    enterprise_value = pv_fcff + pv_terminal
    
    # Equity Value
    equity_value = enterprise_value - debt + cash
    
    # Intrinsic value per share
    intrinsic_value = equity_value / max(shares, 1)
    
    # Margin of safety
    margin_of_safety = (intrinsic_value - current_price) / current_price if current_price > 0 else 0
    
    return {
        'enterprise_value': enterprise_value,
        'equity_value': equity_value,
        'intrinsic_value_per_share': intrinsic_value,
        'margin_of_safety': margin_of_safety,
        'pv_projected_fcff': pv_fcff,
        'pv_terminal_value': pv_terminal,
        'recommendation': 'BUY' if margin_of_safety > 0.2 else ('SELL' if margin_of_safety < -0.2 else 'HOLD')
    }


def dcf_fcfe(valuation_inputs: Dict) -> Dict:
    """
    Discounted Cash Flow using Free Cash Flow to Equity (FCFE).
    More appropriate for companies with stable capital structure.
    """
    fcfe = valuation_inputs.get('fcfe_current', 0)
    growth_rates = valuation_inputs.get('growth_rates', [0.10] * 5)
    terminal_growth = valuation_inputs.get('terminal_growth', 0.03)
    cost_of_equity = valuation_inputs.get('cost_of_equity', 0.12)
    shares = valuation_inputs.get('shares_outstanding', 1)
    current_price = valuation_inputs.get('current_price', 0)
    
    # Project FCFE
    projected_fcfe = []
    for i, g in enumerate(growth_rates):
        fcfe = fcfe * (1 + g)
        projected_fcfe.append(fcfe)
    
    # Terminal value
    terminal_fcfe = projected_fcfe[-1] * (1 + terminal_growth)
    terminal_value = terminal_fcfe / (cost_of_equity - terminal_growth)
    
    # Discount to present value
    pv_fcfe = sum([fcfe / ((1 + cost_of_equity) ** (i + 1)) for i, fcfe in enumerate(projected_fcfe)])
    pv_terminal = terminal_value / ((1 + cost_of_equity) ** len(growth_rates))
    
    # Equity value
    equity_value = pv_fcfe + pv_terminal
    
    # Intrinsic value per share
    intrinsic_value = equity_value / max(shares, 1)
    
    # Margin of safety
    margin_of_safety = (intrinsic_value - current_price) / current_price if current_price > 0 else 0
    
    return {
        'equity_value': equity_value,
        'intrinsic_value_per_share': intrinsic_value,
        'margin_of_safety': margin_of_safety,
        'recommendation': 'BUY' if margin_of_safety > 0.2 else ('SELL' if margin_of_safety < -0.2 else 'HOLD')
    }


def ev_ebitda_multiple(comparable_companies: List[Dict], target: Dict) -> Dict:
    """
    Valuation using EV/EBITDA multiple from comparable companies.
    """
    # Extract multiples from comparables
    multiples = [comp.get('ev_ebitda') for comp in comparable_companies if comp.get('ev_ebitda')]
    
    if not multiples:
        return {'error': 'No comparable company multiples available'}
    
    # Calculate median and mean multiples
    median_multiple = np.median(multiples)
    mean_multiple = np.mean(multiples)
    
    # Apply to target
    target_ebitda = target.get('ebitda', 0)
    target_debt = target.get('debt', 0)
    target_cash = target.get('cash', 0)
    target_shares = target.get('shares_outstanding', 1)
    target_price = target.get('current_price', 0)
    
    # Implied enterprise value
    implied_ev_median = median_multiple * target_ebitda
    implied_ev_mean = mean_multiple * target_ebitda
    
    # Implied equity value
    implied_equity_median = implied_ev_median - target_debt + target_cash
    implied_equity_mean = implied_ev_mean - target_debt + target_cash
    
    # Implied share price
    implied_price_median = implied_equity_median / max(target_shares, 1)
    implied_price_mean = implied_equity_mean / max(target_shares, 1)
    
    # Margin of safety
    mos_median = (implied_price_median - target_price) / target_price if target_price > 0 else 0
    mos_mean = (implied_price_mean - target_price) / target_price if target_price > 0 else 0
    
    return {
        'median_ev_ebitda': median_multiple,
        'mean_ev_ebitda': mean_multiple,
        'implied_price_median': implied_price_median,
        'implied_price_mean': implied_price_mean,
        'margin_of_safety_median': mos_median,
        'margin_of_safety_mean': mos_mean,
        'recommendation': 'BUY' if mos_median > 0.2 else ('SELL' if mos_median < -0.2 else 'HOLD')
    }


def reverse_dcf(current_price: float, shares: int, debt: float, cash: float,
                ebitda: float, tax_rate: float = 0.25, capex_percent: float = 0.05,
                nwc_percent: float = 0.05, wacc: float = 0.10, 
                terminal_growth: float = 0.03, years: int = 5) -> Dict:
    """
    Reverse DCF: Calculate implied growth rate given current market price.
    Useful for understanding market expectations.
    """
    # Current market data
    market_cap = current_price * shares
    enterprise_value = market_cap + debt - cash
    
    # Convert EBITDA to FCFF
    fcff_margin = (1 - tax_rate) * (1 - capex_percent - nwc_percent)
    current_fcff = ebitda * fcff_margin
    
    # Binary search for implied growth rate
    low_growth, high_growth = -0.10, 0.30
    
    for _ in range(50):  # Iterations
        mid_growth = (low_growth + high_growth) / 2
        
        # Project FCFF
        projected_fcff = [current_fcff * ((1 + mid_growth) ** i) for i in range(1, years + 1)]
        
        # Terminal value
        terminal_fcff = projected_fcff[-1] * (1 + terminal_growth)
        terminal_value = terminal_fcff / (wacc - terminal_growth)
        
        # Present value
        pv = sum([fcff / ((1 + wacc) ** i) for i, fcff in enumerate(projected_fcff, 1)])
        pv_terminal = terminal_value / ((1 + wacc) ** years)
        
        calculated_ev = pv + pv_terminal
        
        if calculated_ev > enterprise_value:
            high_growth = mid_growth
        else:
            low_growth = mid_growth
    
    implied_growth = (low_growth + high_growth) / 2
    
    return {
        'implied_growth_rate': implied_growth,
        'implied_growth_percent': implied_growth * 100,
        'current_fcff': current_fcff,
        'market_implied_assessment': 'Aggressive' if implied_growth > 0.15 else ('Conservative' if implied_growth < 0.05 else 'Moderate')
    }


# ============================================================================
# GROWTH & PROFITABILITY METRICS
# ============================================================================

def roe_dupont_analysis(financials: Dict) -> Dict:
    """
    DuPont Analysis: Decompose ROE into three components.
    
    ROE = Net Profit Margin × Asset Turnover × Equity Multiplier
    
    This helps identify the source of ROE:
    - High margin: Pricing power, cost control
    - High turnover: Operational efficiency
    - High multiplier: Financial leverage
    """
    net_income = financials.get('net_income', 0)
    revenue = financials.get('revenue', 0)
    avg_assets = financials.get('avg_total_assets', 1)
    avg_equity = financials.get('avg_shareholders_equity', 1)
    
    # Three components
    net_profit_margin = net_income / max(revenue, 1) * 100
    asset_turnover = revenue / max(avg_assets, 1)
    equity_multiplier = avg_assets / max(avg_equity, 1)
    
    # ROE
    roe = net_income / max(avg_equity, 1) * 100
    
    # Verify: ROE = NPM × AT × EM
    calculated_roe = net_profit_margin * asset_turnover * equity_multiplier / 100
    
    return {
        'roe_percent': roe,
        'net_profit_margin_percent': net_profit_margin,
        'asset_turnover': asset_turnover,
        'equity_multiplier': equity_multiplier,
        'calculated_roe_percent': calculated_roe,
        'roe_driver': 'Margin' if net_profit_margin > 15 else ('Turnover' if asset_turnover > 1 else 'Leverage')
    }


def roic_vs_wacc(financials: Dict) -> Dict:
    """
    Calculate ROIC and compare to WACC.
    ROIC > WACC indicates value creation.
    """
    # NOPAT (Net Operating Profit After Tax)
    ebit = financials.get('ebit', 0)
    tax_rate = financials.get('tax_rate', 0.25)
    nopat = ebit * (1 - tax_rate)
    
    # Invested Capital
    total_debt = financials.get('total_debt', 0)
    shareholders_equity = financials.get('shareholders_equity', 0)
    cash = financials.get('cash', 0)
    invested_capital = total_debt + shareholders_equity - cash
    
    # ROIC
    roic = nopat / max(invested_capital, 1) * 100
    
    # WACC (simplified calculation)
    cost_of_equity = financials.get('cost_of_equity', 0.12)
    cost_of_debt = financials.get('cost_of_debt', 0.08)
    debt_weight = total_debt / max(invested_capital + cash, 1)
    equity_weight = shareholders_equity / max(invested_capital + cash, 1)
    tax_rate = financials.get('tax_rate', 0.25)
    
    wacc = (equity_weight * cost_of_equity + 
            debt_weight * cost_of_debt * (1 - tax_rate))
    
    # Spread
    spread = roic / 100 - wacc
    
    return {
        'roic_percent': roic,
        'wacc_percent': wacc * 100,
        'spread_percent': spread * 100,
        'value_creation': 'Yes' if spread > 0 else 'No',
        'economic_profit': nopat - (invested_capital * wacc)
    }


def free_cash_flow_yield(financials: Dict, market_cap: float) -> Dict:
    """
    Calculate FCF Yield - measures cash return to shareholders.
    FCF Yield > 4% generally considered attractive.
    """
    operating_cash_flow = financials.get('operating_cash_flow', 0)
    capex = financials.get('capex', 0)
    
    fcf = operating_cash_flow - capex
    fcf_yield = fcf / max(market_cap, 1) * 100
    
    return {
        'free_cash_flow': fcf,
        'fcf_yield_percent': fcf_yield,
        'assessment': 'Attractive' if fcf_yield > 4 else ('Fair' if fcf_yield > 2 else 'Low')
    }


def cash_conversion_cycle(financials: Dict) -> Dict:
    """
    Calculate Cash Conversion Cycle (CCC).
    Measures how quickly a company converts investments into cash.
    Lower is better; negative CCC is excellent (company gets paid before paying suppliers).
    
    CCC = DIO + DSO - DPO
    """
    revenue = financials.get('revenue', 1)
    cogs = financials.get('cogs', revenue * 0.7)
    avg_inventory = financials.get('avg_inventory', 1)
    avg_receivables = financials.get('avg_receivables', 1)
    avg_payables = financials.get('avg_payables', 1)
    
    # Days Inventory Outstanding
    dio = (avg_inventory / max(cogs, 1)) * 365
    
    # Days Sales Outstanding
    dso = (avg_receivables / max(revenue, 1)) * 365
    
    # Days Payable Outstanding
    dpo = (avg_payables / max(cogs, 1)) * 365
    
    # Cash Conversion Cycle
    ccc = dio + dso - dpo
    
    return {
        'ccc_days': ccc,
        'dio_days': dio,
        'dso_days': dso,
        'dpo_days': dpo,
        'assessment': 'Excellent' if ccc < 0 else ('Good' if ccc < 30 else ('Average' if ccc < 60 else 'Poor'))
    }


# ============================================================================
# INTEGRATED FUNDAMENTAL ANALYSIS
# ============================================================================

def calculate_quality_scores(financials_history: List[Dict]) -> Dict:
    """
    Calculate comprehensive quality scores from historical financial data.
    """
    if not financials_history or len(financials_history) < 2:
        return {'error': 'Insufficient historical data'}
    
    latest = financials_history[-1]
    prev = financials_history[-2]
    
    # Build comparison dict
    financials = {
        'net_income': latest.get('net_income', 0),
        'operating_cash_flow': latest.get('operating_cash_flow', 0),
        'roa_current': latest.get('roa', 0),
        'roa_prev': prev.get('roa', 0),
        'leverage_current': latest.get('debt_to_assets', 0),
        'leverage_prev': prev.get('debt_to_assets', 0),
        'current_ratio_current': latest.get('current_ratio', 0),
        'current_ratio_prev': prev.get('current_ratio', 0),
        'shares_current': latest.get('shares_outstanding', 0),
        'shares_prev': prev.get('shares_outstanding', 0),
        'gross_margin_current': latest.get('gross_margin', 0),
        'gross_margin_prev': prev.get('gross_margin', 0),
        'asset_turnover_current': latest.get('asset_turnover', 0),
        'asset_turnover_prev': prev.get('asset_turnover', 0),
        'total_assets': latest.get('total_assets', 1),
        'working_capital': latest.get('working_capital', 0),
        'retained_earnings': latest.get('retained_earnings', 0),
        'ebit': latest.get('ebit', 0),
        'market_cap': latest.get('market_cap', 0),
        'total_liabilities': latest.get('total_liabilities', 0),
        'receivables_current': latest.get('receivables', 0),
        'receivables_prev': prev.get('receivables', 0),
        'revenue_current': latest.get('revenue', 0),
        'revenue_prev': prev.get('revenue', 0),
        'debt_current': latest.get('total_debt', 0),
        'debt_prev': prev.get('total_debt', 0),
    }
    
    # Calculate scores
    f_score = piotroski_f_score(financials)
    z_score = altman_z_score(financials)
    m_score = beneish_m_score(financials)
    accrual = accruals_ratio(financials)
    
    return {
        'piotroski_f_score': f_score,
        'f_score_rating': 'High' if f_score >= 7 else ('Medium' if f_score >= 4 else 'Low'),
        'altman_z_score': z_score,
        'z_score_risk': 'Safe' if z_score > 2.99 else ('Grey' if z_score > 1.81 else 'Distress'),
        'beneish_m_score': m_score,
        'manipulation_risk': 'High' if m_score > -1.78 else 'Low',
        'accruals_ratio': accrual,
        'earnings_quality': 'High' if accrual < 0.05 else ('Medium' if accrual < 0.10 else 'Low')
    }


def comprehensive_valuation(market_data: Dict, financials: Dict, 
                           comparable_companies: List[Dict] = None) -> Dict:
    """
    Run multiple valuation models and aggregate results.
    """
    results = {}
    
    # DCF FCFF
    dcf_inputs = {
        'fcff_current': financials.get('fcff', 0),
        'growth_rates': [0.12, 0.10, 0.08, 0.06, 0.05],
        'terminal_growth': 0.03,
        'wacc': 0.10,
        'debt': financials.get('total_debt', 0),
        'cash': financials.get('cash', 0),
        'shares_outstanding': financials.get('shares_outstanding', 1),
        'current_price': market_data.get('current_price', 0)
    }
    results['dcf_fcff'] = dcf_fcff(dcf_inputs)
    
    # Reverse DCF
    results['reverse_dcf'] = reverse_dcf(
        current_price=market_data.get('current_price', 0),
        shares=financials.get('shares_outstanding', 1),
        debt=financials.get('total_debt', 0),
        cash=financials.get('cash', 0),
        ebitda=financials.get('ebitda', 0)
    )
    
    # Comparable companies valuation
    if comparable_companies:
        target = {
            'ebitda': financials.get('ebitda', 0),
            'debt': financials.get('total_debt', 0),
            'cash': financials.get('cash', 0),
            'shares_outstanding': financials.get('shares_outstanding', 1),
            'current_price': market_data.get('current_price', 0)
        }
        results['comparable_valuation'] = ev_ebitda_multiple(comparable_companies, target)
    
    # Aggregate fair value estimate
    fair_values = []
    if 'dcf_fcff' in results:
        fair_values.append(results['dcf_fcff']['intrinsic_value_per_share'])
    if 'comparable_valuation' in results:
        fair_values.append(results['comparable_valuation']['implied_price_median'])
    
    avg_fair_value = np.mean(fair_values) if fair_values else 0
    current_price = market_data.get('current_price', 0)
    overall_mos = (avg_fair_value - current_price) / current_price if current_price > 0 else 0
    
    return {
        'models': results,
        'average_fair_value': avg_fair_value,
        'current_price': current_price,
        'overall_margin_of_safety': overall_mos,
        'consensus_recommendation': 'BUY' if overall_mos > 0.2 else ('SELL' if overall_mos < -0.2 else 'HOLD')
    }


if __name__ == '__main__':
    print("Institutional Fundamental Analysis Module loaded successfully")
    print("\nAvailable functions:")
    print("- Earnings Quality: piotroski_f_score(), altman_z_score(), beneish_m_score()")
    print("- Valuation: dcf_fcff(), dcf_fcfe(), ev_ebitda_multiple(), reverse_dcf()")
    print("- Profitability: roe_dupont_analysis(), roic_vs_wacc(), free_cash_flow_yield()")
    print("- Efficiency: cash_conversion_cycle()")
    print("- Integrated: calculate_quality_scores(), comprehensive_valuation()")
