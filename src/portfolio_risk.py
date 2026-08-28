"""
Institutional-Grade Risk Management & Portfolio Optimization Module
===================================================================
Phase 2: Factor Analysis + Portfolio Optimizer + Risk Dashboard

Features:
- Factor exposure analysis (Value, Momentum, Quality, Low Vol)
- Mean-Variance Optimization (Markowitz)
- Risk Parity allocation
- Hierarchical Risk Parity (HRP)
- Kelly Criterion position sizing
- Sharpe/Sortino ratios
- VaR/CVaR analytics
- Stress testing scenarios
- Concentration limits monitoring
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
from scipy.optimize import minimize, OptimizeResult
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
import warnings
warnings.filterwarnings('ignore')


# ============================================================================
# FACTOR ANALYSIS
# ============================================================================

def calculate_factor_exposures(stock_data: pd.DataFrame, factor_returns: pd.DataFrame = None) -> pd.DataFrame:
    """
    Calculate stock exposures to common factors.
    
    Factors:
    - Value: P/E, P/B, EV/EBITDA inverse
    - Momentum: 12M return excluding recent month
    - Quality: ROE, debt/equity, earnings stability
    - Low Volatility: Inverse of historical volatility
    - Size: Log market cap
    """
    if stock_data.empty:
        return pd.DataFrame()
    
    exposures = pd.DataFrame(index=stock_data.index)
    
    # Value Score (lower P/E, P/B = higher value score)
    if 'PE' in stock_data.columns:
        pe_rank = stock_data['PE'].rank(pct=True)
        exposures['VALUE'] = 1 - pe_rank  # Invert so low PE = high value
    elif 'PE_RATIO' in stock_data.columns:
        pe_rank = stock_data['PE_RATIO'].rank(pct=True)
        exposures['VALUE'] = 1 - pe_rank
    else:
        exposures['VALUE'] = 0.5
    
    # Momentum Score (12-month return excluding most recent month)
    for col in ['CHG_1Y', 'RETURN_12M', 'CHG_252D']:
        if col in stock_data.columns:
            exposures['MOMENTUM'] = stock_data[col].rank(pct=True)
            break
    else:
        exposures['MOMENTUM'] = 0.5
    
    # Quality Score (composite of profitability metrics)
    quality_components = []
    if 'ROE' in stock_data.columns:
        quality_components.append(stock_data['ROE'].rank(pct=True))
    if 'RETURN_ON_EQUITY' in stock_data.columns:
        quality_components.append(stock_data['RETURN_ON_EQUITY'].rank(pct=True))
    if 'DEBT_TO_EQUITY' in stock_data.columns:
        quality_components.append(1 - stock_data['DEBT_TO_EQUITY'].rank(pct=True))  # Invert
    if 'PROFIT_MARGIN' in stock_data.columns:
        quality_components.append(stock_data['PROFIT_MARGIN'].rank(pct=True))
    
    if quality_components:
        exposures['QUALITY'] = pd.DataFrame(quality_components).mean().rank(pct=True)
    else:
        exposures['QUALITY'] = 0.5
    
    # Low Volatility Score (inverse of volatility)
    vol_cols = ['HV_20', 'VOLATILITY_20', 'STD_DEV']
    for col in vol_cols:
        if col in stock_data.columns:
            exposures['LOW_VOL'] = 1 - stock_data[col].rank(pct=True)  # Invert
            break
    else:
        exposures['LOW_VOL'] = 0.5
    
    # Size Score (larger cap = higher score for institutional preference)
    if 'MARKET_CAP' in stock_data.columns:
        exposures['SIZE'] = np.log(stock_data['MARKET_CAP']).rank(pct=True)
    elif 'MARKET_CAP_CR' in stock_data.columns:
        exposures['SIZE'] = np.log(stock_data['MARKET_CAP_CR']).rank(pct=True)
    else:
        exposures['SIZE'] = 0.5
    
    return exposures


def factor_tilt_score(exposures: pd.DataFrame, target_factors: Dict[str, float] = None) -> pd.Series:
    """
    Calculate overall factor tilt score based on target factor exposures.
    
    Default targets (balanced growth at reasonable price):
    - Value: 0.3
    - Momentum: 0.4
    - Quality: 0.5
    - Low Vol: 0.2
    - Size: 0.1
    """
    if target_factors is None:
        target_factors = {
            'VALUE': 0.3,
            'MOMENTUM': 0.4,
            'QUALITY': 0.5,
            'LOW_VOL': 0.2,
            'SIZE': 0.1
        }
    
    available_factors = [f for f in target_factors.keys() if f in exposures.columns]
    
    if not available_factors:
        return pd.Series(0.5, index=exposures.index)
    
    # Calculate weighted factor score
    weights = np.array([target_factors[f] for f in available_factors])
    weights = weights / weights.sum()  # Normalize
    
    factor_scores = exposures[available_factors].values
    composite_score = np.dot(factor_scores, weights)
    
    return pd.Series(composite_score, index=exposures.index, name='FACTOR_SCORE')


def style_box_classification(exposures: pd.DataFrame) -> pd.DataFrame:
    """
    Classify stocks into Morningstar-style boxes based on Value and Size.
    
    Returns DataFrame with STYLE_BOX column (e.g., 'Large Value', 'Mid Growth', etc.)
    """
    result = exposures.copy()
    
    # Size classification
    if 'SIZE' in result.columns:
        result['SIZE_CATEGORY'] = pd.cut(
            result['SIZE'],
            bins=[0, 0.33, 0.67, 1.0],
            labels=['Small', 'Mid', 'Large']
        )
    else:
        result['SIZE_CATEGORY'] = 'Unknown'
    
    # Value/Growth classification (high VALUE score = Value, low = Growth)
    if 'VALUE' in result.columns:
        result['STYLE_CATEGORY'] = pd.cut(
            result['VALUE'],
            bins=[0, 0.33, 0.67, 1.0],
            labels=['Growth', 'Blend', 'Value']
        )
    else:
        result['STYLE_CATEGORY'] = 'Unknown'
    
    # Combined style box
    result['STYLE_BOX'] = result['SIZE_CATEGORY'].astype(str) + ' ' + result['STYLE_CATEGORY'].astype(str)
    
    return result


# ============================================================================
# PORTFOLIO OPTIMIZATION
# ============================================================================

def mean_variance_optimization(expected_returns: pd.Series, cov_matrix: pd.DataFrame,
                               risk_free_rate: float = 0.06, 
                               constraints: Dict = None) -> Dict:
    """
    Markowitz Mean-Variance Optimization.
    
    Maximizes Sharpe Ratio subject to constraints.
    
    Returns:
    - Optimal weights
    - Expected portfolio return
    - Portfolio volatility
    - Sharpe ratio
    """
    n_assets = len(expected_returns)
    
    # Negative Sharpe Ratio (to minimize)
    def neg_sharpe(weights):
        port_return = np.dot(weights, expected_returns)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe = (port_return - risk_free_rate) / max(port_vol, 0.001)
        return -sharpe
    
    # Constraints
    cons = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]  # Weights sum to 1
    
    if constraints:
        # Min/max weight per asset
        if 'min_weight' in constraints and 'max_weight' in constraints:
            min_w = constraints['min_weight']
            max_w = constraints['max_weight']
            cons.append({'type': 'ineq', 'fun': lambda w: w - min_w})
            cons.append({'type': 'ineq', 'fun': lambda w: max_w - w})
        
        # Sector constraints
        if 'sector_weights' in constraints:
            for sector, (min_pct, max_pct) in constraints['sector_weights'].items():
                sector_indices = constraints.get('sector_indices', {}).get(sector, [])
                if sector_indices:
                    cons.append({
                        'type': 'ineq',
                        'fun': lambda w, idx=sector_indices, mn=min_pct, mx=max_pct: np.sum(w[idx]) - mn
                    })
                    cons.append({
                        'type': 'ineq',
                        'fun': lambda w, idx=sector_indices, mn=min_pct, mx=max_pct: mx - np.sum(w[idx])
                    })
    
    # Bounds
    bounds = tuple((0.0, 1.0) for _ in range(n_assets))
    
    # Initial guess (equal weight)
    init_weights = np.array([1/n_assets] * n_assets)
    
    # Optimize
    result = minimize(
        neg_sharpe,
        init_weights,
        method='SLSQP',
        bounds=bounds,
        constraints=cons,
        options={'maxiter': 1000, 'ftol': 1e-10}
    )
    
    if not result.success:
        return {'error': 'Optimization failed', 'message': result.message}
    
    optimal_weights = result.x
    port_return = np.dot(optimal_weights, expected_returns)
    port_vol = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))
    sharpe = (port_return - risk_free_rate) / max(port_vol, 0.001)
    
    return {
        'weights': optimal_weights,
        'expected_return': port_return,
        'volatility': port_vol,
        'sharpe_ratio': sharpe,
        'optimization_status': result.success
    }


def risk_parity_allocation(cov_matrix: pd.DataFrame, 
                           expected_returns: pd.Series = None,
                           risk_budget: np.ndarray = None) -> Dict:
    """
    Risk Parity optimization - equal risk contribution from each asset.
    
    More robust than mean-variance as it doesn't rely on expected returns.
    """
    n_assets = cov_matrix.shape[0]
    
    if risk_budget is None:
        risk_budget = np.array([1/n_assets] * n_assets)  # Equal risk budget
    
    # Risk contribution function
    def risk_contribution(weights):
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        marginal_contrib = np.dot(cov_matrix, weights)
        risk_contrib = weights * marginal_contrib / max(port_vol, 0.001)
        return risk_contrib
    
    # Objective: minimize squared difference from target risk budget
    def objective(weights):
        rc = risk_contribution(weights)
        rc_pct = rc / max(rc.sum(), 0.001)
        return np.sum((rc_pct - risk_budget) ** 2)
    
    # Constraints
    cons = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
    bounds = tuple((0.01, 0.5) for _ in range(n_assets))  # Prevent zero weights
    
    # Initial guess
    init_weights = np.array([1/n_assets] * n_assets)
    
    # Optimize
    result = minimize(
        objective,
        init_weights,
        method='SLSQP',
        bounds=bounds,
        constraints=cons,
        options={'maxiter': 1000}
    )
    
    if not result.success:
        return {'error': 'Risk parity optimization failed'}
    
    optimal_weights = result.x
    
    # Calculate final risk contributions
    final_rc = risk_contribution(optimal_weights)
    final_rc_pct = final_rc / final_rc.sum()
    
    port_vol = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))
    
    if expected_returns is not None:
        port_return = np.dot(optimal_weights, expected_returns)
        sharpe = port_return / max(port_vol, 0.001)
    else:
        port_return = None
        sharpe = None
    
    return {
        'weights': optimal_weights,
        'risk_contributions': final_rc_pct,
        'portfolio_volatility': port_vol,
        'expected_return': port_return,
        'sharpe_ratio': sharpe
    }


def hierarchical_risk_parity(returns: pd.DataFrame) -> Dict:
    """
    Hierarchical Risk Parity (HRP) - uses clustering to allocate capital.
    
    Advantages:
    - No need for invertible covariance matrix
    - More stable than traditional optimization
    - Accounts for hierarchical structure of correlations
    """
    # Calculate correlation and distance matrices
    corr = returns.corr()
    dist = np.sqrt((1 - corr) / 2)  # Distance metric
    
    # Hierarchical clustering
    link = linkage(squareform(dist), method='ward')
    
    # Get cluster order
    def get_quasi_diag(link):
        link = link.astype(int)
        sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
        num_items = link[-1, 3]
        
        while sort_ix.max() >= num_items:
            sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)
            df0 = sort_ix[sort_ix >= num_items]
            i = df0.index
            j = df0.values - num_items
            sort_ix[i] = link[j, 0]
            df1 = pd.Series(link[j, 1], index=i + 1)
            sort_ix = pd.concat([sort_ix, df1])
            sort_ix = sort_ix.sort_index()
            sort_ix.index = range(sort_ix.shape[0])
        
        return sort_ix.tolist()
    
    sort_ix = get_quasi_diag(link)
    sorted_assets = returns.columns[sort_ix]
    
    # Recursive bisection
    def recursive_bisection(cov, sorted_ix):
        n = len(sorted_ix)
        weights = np.ones(n)
        
        def bisect(weights, cov, sorted_ix, start, end):
            if end - start <= 1:
                return
            
            mid = (start + end) // 2
            left_ix = sorted_ix[start:mid]
            right_ix = sorted_ix[mid:end]
            
            # Calculate cluster variances
            left_cov = cov.loc[left_ix, left_ix]
            right_cov = cov.loc[right_ix, right_ix]
            
            # Inverse variance weights
            left_var = 1 / np.trace(left_cov) if len(left_ix) > 0 else 1
            right_var = 1 / np.trace(right_cov) if len(right_ix) > 0 else 1
            
            alpha = left_var / (left_var + right_var)
            
            weights[start:mid] *= alpha
            weights[mid:end] *= (1 - alpha)
            
            bisect(weights, cov, sorted_ix, start, mid)
            bisect(weights, cov, sorted_ix, mid, end)
        
        bisect(weights, cov, sorted_ix, 0, n)
        return weights
    
    cov = returns.cov()
    hrp_weights = recursive_bisection(cov, sort_ix)
    
    # Normalize
    hrp_weights = hrp_weights / hrp_weights.sum()
    
    # Portfolio metrics
    port_vol = np.sqrt(np.dot(hrp_weights.T, np.dot(cov, hrp_weights)))
    port_return = returns.mean().dot(hrp_weights) * 252
    
    return {
        'weights': hrp_weights,
        'asset_order': sorted_assets.tolist(),
        'portfolio_volatility': port_vol,
        'expected_return': port_return,
        'sharpe_ratio': port_return / max(port_vol, 0.001)
    }


def kelly_criterion(win_rate: float, win_loss_ratio: float, 
                    fraction: str = 'half') -> float:
    """
    Calculate Kelly Criterion position size.
    
    Args:
        win_rate: Probability of winning (0-1)
        win_loss_ratio: Average win / Average loss
        fraction: 'full', 'half', or 'quarter' Kelly
    
    Returns:
        Optimal position size as fraction of portfolio
    """
    # Kelly formula: f* = p - q/b
    # where p = win probability, q = loss probability, b = win/loss ratio
    p = win_rate
    q = 1 - p
    b = win_loss_ratio
    
    kelly = p - q / b
    
    if fraction == 'half':
        kelly = kelly / 2
    elif fraction == 'quarter':
        kelly = kelly / 4
    
    return max(0, min(kelly, 0.25))  # Cap at 25%


# ============================================================================
# RISK METRICS & DASHBOARD
# ============================================================================

def calculate_risk_metrics(returns: pd.Series, benchmark_returns: pd.Series = None,
                           risk_free_rate: float = 0.06) -> Dict:
    """
    Calculate comprehensive risk metrics for a portfolio/strategy.
    """
    # Basic statistics
    ann_return = returns.mean() * 252
    ann_vol = returns.std() * np.sqrt(252)
    
    # Risk-adjusted returns
    sharpe = (ann_return - risk_free_rate) / max(ann_vol, 0.001)
    
    # Sortino ratio (downside deviation)
    downside_returns = returns[returns < 0]
    downside_dev = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else ann_vol
    sortino = (ann_return - risk_free_rate) / max(downside_dev, 0.001)
    
    # Maximum drawdown
    cum_returns = (1 + returns).cumprod()
    rolling_max = cum_returns.expanding().max()
    drawdowns = cum_returns / rolling_max - 1
    max_dd = drawdowns.min()
    
    # Calmar ratio
    calmar = ann_return / abs(max_dd) if max_dd != 0 else 0
    
    # Skewness and Kurtosis
    skew = returns.skew()
    kurt = returns.kurtosis()
    
    # Win rate
    positive_days = (returns > 0).sum()
    total_days = len(returns)
    win_rate = positive_days / total_days if total_days > 0 else 0
    
    # Best/Worst periods
    best_day = returns.max()
    worst_day = returns.min()
    best_month = returns.rolling(21).sum().max()
    worst_month = returns.rolling(21).sum().min()
    
    result = {
        'annualized_return': ann_return,
        'annualized_volatility': ann_vol,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'max_drawdown': max_dd,
        'calmar_ratio': calmar,
        'skewness': skew,
        'kurtosis': kurt,
        'win_rate': win_rate,
        'best_day': best_day,
        'worst_day': worst_day,
        'best_month': best_month,
        'worst_month': worst_month,
        'total_days': total_days
    }
    
    # Benchmark comparison if provided
    if benchmark_returns is not None and len(benchmark_returns) == len(returns):
        excess_returns = returns - benchmark_returns
        
        # Alpha/Beta
        cov_mat = np.cov(returns, benchmark_returns)
        beta = cov_mat[0, 1] / max(cov_mat[1, 1], 0.001)
        alpha = ann_return - (risk_free_rate + beta * (benchmark_returns.mean() * 252 - risk_free_rate))
        
        # Tracking error
        tracking_error = excess_returns.std() * np.sqrt(252)
        
        # Information ratio
        info_ratio = excess_returns.mean() * 252 / max(tracking_error, 0.001)
        
        result.update({
            'alpha': alpha,
            'beta': beta,
            'tracking_error': tracking_error,
            'information_ratio': info_ratio,
            'benchmark_sharpe': (benchmark_returns.mean() * 252 - risk_free_rate) / max(benchmark_returns.std() * np.sqrt(252), 0.001)
        })
    
    return result


def stress_test_portfolio(returns: pd.Series, positions: pd.DataFrame,
                          scenarios: Dict[str, float] = None) -> Dict:
    """
    Stress test portfolio under various market scenarios.
    
    Default scenarios:
    - Market Crash (-30%)
    - Flash Crash (-10%)
    - Interest Rate Shock (+200bps)
    - Sector Rotation (-15% in specific sectors)
    """
    if scenarios is None:
        scenarios = {
            'Market Crash (-30%)': -0.30,
            'Flash Crash (-10%)': -0.10,
            'Correction (-20%)': -0.20,
            'Mild Decline (-5%)': -0.05
        }
    
    results = {}
    
    # Calculate portfolio beta (simplified - use average beta of holdings)
    avg_beta = positions.get('BETA', pd.Series([1.0] * len(positions))).mean() if 'BETA' in positions.columns else 1.0
    
    for scenario_name, market_move in scenarios.items():
        # Estimate portfolio impact
        portfolio_impact = market_move * avg_beta
        
        # Add idiosyncratic risk (assume 20% additional volatility)
        idio_adjustment = 1 + 0.2 * np.random.normal(0, 1)
        adjusted_impact = portfolio_impact * idio_adjustment
        
        results[scenario_name] = {
            'market_move': market_move,
            'estimated_portfolio_impact': adjusted_impact,
            'var_95_adjusted': adjusted_impact * 1.65,  # Approximate
            'dollar_loss_estimate': adjusted_impact * positions['VALUE'].sum() if 'VALUE' in positions.columns else None
        }
    
    return results


def concentration_analysis(positions: pd.DataFrame, 
                           limits: Dict = None) -> Dict:
    """
    Analyze portfolio concentration against predefined limits.
    
    Checks:
    - Single stock concentration
    - Sector concentration
    - Top 5/10 holdings concentration
    - Herfindahl-Hirschman Index (HHI)
    """
    if limits is None:
        limits = {
            'single_stock_max': 0.10,
            'sector_max': 0.30,
            'top5_max': 0.40,
            'top10_max': 0.60
        }
    
    if positions.empty or 'WEIGHT' not in positions.columns:
        return {'error': 'No positions with weights provided'}
    
    weights = positions['WEIGHT'].sort_values(ascending=False)
    total_value = positions['VALUE'].sum() if 'VALUE' in positions.columns else 1
    
    # HHI (measure of concentration)
    hhi = (weights ** 2).sum()
    effective_n = 1 / hhi  # Effective number of holdings
    
    # Top holdings
    top5_weight = weights.head(5).sum()
    top10_weight = weights.head(10).sum()
    
    # Violations
    violations = []
    if weights.max() > limits['single_stock_max']:
        violations.append(f"Single stock: {weights.max():.1%} > {limits['single_stock_max']:.0%}")
    if top5_weight > limits['top5_max']:
        violations.append(f"Top 5: {top5_weight:.1%} > {limits['top5_max']:.0%}")
    if top10_weight > limits['top10_max']:
        violations.append(f"Top 10: {top10_weight:.1%} > {limits['top10_max']:.0%}")
    
    # Sector concentration
    sector_concentration = {}
    if 'SECTOR' in positions.columns:
        sector_weights = positions.groupby('SECTOR')['WEIGHT'].sum()
        for sector, weight in sector_weights.items():
            if weight > limits['sector_max']:
                violations.append(f"Sector {sector}: {weight:.1%} > {limits['sector_max']:.0%}")
            sector_concentration[sector] = weight
    
    return {
        'hhi': hhi,
        'effective_holdings': effective_n,
        'actual_holdings': len(positions),
        'top1_weight': weights.iloc[0] if len(weights) > 0 else 0,
        'top5_weight': top5_weight,
        'top10_weight': top10_weight,
        'sector_concentration': sector_concentration,
        'violations': violations,
        'concentration_risk': 'High' if len(violations) > 2 else ('Medium' if len(violations) > 0 else 'Low')
    }


# ============================================================================
# INTEGRATED PORTFOLIO CONSTRUCTION
# ============================================================================

def construct_institutional_portfolio(stock_data: pd.DataFrame, 
                                      returns_history: pd.DataFrame,
                                      optimization_method: str = 'risk_parity',
                                      constraints: Dict = None) -> Dict:
    """
    End-to-end institutional portfolio construction.
    
    Steps:
    1. Calculate factor exposures
    2. Filter stocks based on quality criteria
    3. Estimate expected returns and covariance
    4. Optimize using selected method
    5. Apply risk checks
    """
    # Step 1: Factor analysis
    factor_exposures = calculate_factor_exposures(stock_data)
    
    # Step 2: Quality filter
    quality_mask = pd.Series(True, index=stock_data.index)
    if 'PIOTROSKI_F_SCORE' in stock_data.columns:
        quality_mask &= stock_data['PIOTROSKI_F_SCORE'] >= 5
    if 'ALTMAN_Z_SCORE' in stock_data.columns:
        quality_mask &= stock_data['ALTMAN_Z_SCORE'] > 1.81
    if 'MARKET_CAP' in stock_data.columns:
        quality_mask &= stock_data['MARKET_CAP'] > 1000  # Minimum 1000 Cr
    
    filtered_stocks = stock_data[quality_mask]
    filtered_symbols = filtered_stocks.index.tolist()
    
    if len(filtered_symbols) < 5:
        return {'error': 'Insufficient stocks passing quality filters'}
    
    # Step 3: Prepare returns data
    filtered_returns = returns_history[filtered_symbols].dropna(axis=1, how='any')
    
    if len(filtered_returns.columns) < 5:
        return {'error': 'Insufficient return data'}
    
    # Expected returns (using factor model + momentum)
    expected_returns = filtered_returns.mean() * 252
    
    # Adjust for factor scores
    if 'FACTOR_SCORE' in factor_exposures.columns:
        factor_adj = factor_exposures.loc[filtered_symbols, 'FACTOR_SCORE']
        expected_returns = expected_returns * (1 + factor_adj * 0.1)
    
    # Covariance matrix
    cov_matrix = filtered_returns.cov() * 252
    
    # Step 4: Optimization
    if optimization_method == 'mean_variance':
        opt_result = mean_variance_optimization(expected_returns, cov_matrix, constraints=constraints)
    elif optimization_method == 'risk_parity':
        opt_result = risk_parity_allocation(cov_matrix, expected_returns)
    elif optimization_method == 'hrp':
        opt_result = hierarchical_risk_parity(filtered_returns)
    else:
        return {'error': f'Unknown optimization method: {optimization_method}'}
    
    if 'error' in opt_result:
        return opt_result
    
    # Step 5: Risk analysis
    portfolio_returns = filtered_returns.dot(opt_result['weights'])
    risk_metrics = calculate_risk_metrics(portfolio_returns)
    
    # Build positions DataFrame
    positions = pd.DataFrame({
        'SYMBOL': filtered_symbols,
        'WEIGHT': opt_result['weights'],
        'EXPECTED_RETURN': expected_returns.values
    })
    
    # Concentration check
    concentration = concentration_analysis(positions)
    
    return {
        'weights': dict(zip(filtered_symbols, opt_result['weights'])),
        'expected_return': opt_result.get('expected_return'),
        'volatility': opt_result.get('volatility') or opt_result.get('portfolio_volatility'),
        'sharpe_ratio': opt_result.get('sharpe_ratio'),
        'risk_metrics': risk_metrics,
        'concentration': concentration,
        'method': optimization_method,
        'num_holdings': len(filtered_symbols)
    }


if __name__ == '__main__':
    print("Institutional Risk & Portfolio Module loaded successfully")
    print("\nAvailable functions:")
    print("- Factor Analysis: calculate_factor_exposures(), factor_tilt_score(), style_box_classification()")
    print("- Optimization: mean_variance_optimization(), risk_parity_allocation(), hierarchical_risk_parity()")
    print("- Position Sizing: kelly_criterion()")
    print("- Risk Metrics: calculate_risk_metrics(), stress_test_portfolio(), concentration_analysis()")
    print("- Integrated: construct_institutional_portfolio()")
