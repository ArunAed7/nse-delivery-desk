"""
Institutional-Grade Technical Analysis Module
=============================================
Phase 1: Momentum Suite + Volatility Analytics

Features:
- Multi-timeframe RSI, MACD, Connors RSI
- ADX, Chaikin Money Flow, Aroon
- Historical Volatility, ATR, VaR
- GARCH volatility forecasting
- Correlation analysis
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, List
from scipy import stats
from datetime import datetime, timedelta


# ============================================================================
# MOMENTUM INDICATORS
# ============================================================================

def connors_rsi(close: pd.Series, lookback_rsi: int = 2, lookback_streak: int = 27, 
                lookback_percentile: int = 100) -> pd.Series:
    """
    Connors RSI combines three components:
    1. Short-term RSI (2-period)
    2. Streak RSI (measures duration of up/down streaks)
    3. Percentile Rank (measures magnitude of price change)
    
    Returns a value between 0-100. Lower values indicate oversold conditions.
    """
    # Component 1: Short-term RSI
    rsi_short = _rsi(close, lookback_rsi)
    
    # Component 2: Streak RSI
    streak = _calculate_streak(close)
    streak_rsi = _rsi(streak, lookback_streak)
    
    # Component 3: Percentile Rank
    pct_rank = _percentile_rank(close, lookback_percentile)
    
    # Combine all three components equally weighted
    connors_rsi = (rsi_short + streak_rsi + pct_rank) / 3.0
    return connors_rsi


def _calculate_streak(close: pd.Series) -> pd.Series:
    """Calculate consecutive up/down day streaks."""
    delta = close.diff()
    direction = np.sign(delta)
    
    streak = pd.Series(0, index=close.index)
    current_streak = 0
    
    for i in range(1, len(direction)):
        if direction.iloc[i] == 0:
            current_streak = 0
        elif direction.iloc[i] == direction.iloc[i-1]:
            current_streak += direction.iloc[i]
        else:
            current_streak = direction.iloc[i]
        streak.iloc[i] = current_streak
    
    return streak


def _percentile_rank(close: pd.Series, lookback: int = 100) -> pd.Series:
    """Calculate percentile rank of daily returns over lookback period."""
    returns = close.pct_change() * 100
    pr = returns.rolling(window=lookback).apply(
        lambda x: stats.percentileofscore(x, x.iloc[-1]) if len(x) > 1 else 50,
        raw=False
    )
    return pr


def macd_histogram(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calculate MACD with histogram divergence detection.
    Returns DataFrame with MACD line, Signal line, Histogram, and Divergence signals.
    """
    exp1 = close.ewm(span=fast, adjust=False).mean()
    exp2 = close.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    # Detect divergences
    divergence = _detect_divergence(close, histogram)
    
    return pd.DataFrame({
        'MACD': macd_line,
        'SIGNAL': signal_line,
        'HISTOGRAM': histogram,
        'DIVERGENCE': divergence
    })


def _detect_divergence(price: pd.Series, oscillator: pd.Series, window: int = 5) -> pd.Series:
    """Detect bullish/bearish divergences between price and oscillator."""
    divergence = pd.Series(0, index=price.index, dtype=int)
    
    for i in range(window, len(price)):
        price_window = price.iloc[i-window:i+1]
        osc_window = oscillator.iloc[i-window:i+1]
        
        # Bullish divergence: lower lows in price, higher lows in oscillator
        if (price_window.iloc[-1] < price_window.min()[:-1].min() and 
            osc_window.iloc[-1] > osc_window.min()[:-1].min()):
            divergence.iloc[i] = 1  # Bullish
        
        # Bearish divergence: higher highs in price, lower highs in oscillator
        elif (price_window.iloc[-1] > price_window.max()[:-1].max() and 
              osc_window.iloc[-1] < osc_window.max()[:-1].max()):
            divergence.iloc[i] = -1  # Bearish
    
    return divergence


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average Directional Index (ADX) - measures trend strength.
    ADX > 25 indicates strong trend, < 20 indicates ranging market.
    """
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[(plus_dm < 0) | (plus_dm < minus_dm)] = 0
    minus_dm[(minus_dm < 0) | (minus_dm < plus_dm)] = 0
    
    tr = _true_range(high, low, close)
    
    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
    
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
    adx_values = dx.ewm(span=period, adjust=False).mean()
    
    return adx_values


def chaikin_money_flow(high: pd.Series, low: pd.Series, close: pd.Series, 
                       volume: pd.Series, period: int = 21) -> pd.Series:
    """
    Chaikin Money Flow (CMF) - measures buying/selling pressure.
    Values above 0 indicate accumulation, below 0 indicate distribution.
    """
    money_flow_multiplier = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    money_flow_volume = money_flow_multiplier * volume
    
    cmf = money_flow_volume.rolling(window=period).sum() / volume.rolling(window=period).sum()
    return cmf


def aroon(high: pd.Series, low: pd.Series, period: int = 25) -> pd.DataFrame:
    """
    Aroon Indicator - measures time since highest high and lowest low.
    Aroon Up > Aroon Down indicates uptrend.
    """
    aroon_up = high.rolling(window=period+1).apply(
        lambda x: ((period - (period - x.argmax())) / period) * 100, raw=True
    )
    aroon_down = low.rolling(window=period+1).apply(
        lambda x: ((period - (period - x.argmin())) / period) * 100, raw=True
    )
    
    aroon_oscillator = aroon_up - aroon_down
    
    return pd.DataFrame({
        'AROON_UP': aroon_up,
        'AROON_DOWN': aroon_down,
        'AROON_OSC': aroon_oscillator
    })


# ============================================================================
# VOLATILITY ANALYTICS
# ============================================================================

def historical_volatility(close: pd.Series, periods: List[int] = [10, 20, 60], 
                          annualize: bool = True) -> pd.DataFrame:
    """
    Calculate historical volatility for multiple periods.
    Returns annualized volatility by default (assuming 252 trading days).
    """
    returns = close.pct_change()
    results = {}
    
    for period in periods:
        vol = returns.rolling(window=period).std()
        if annualize:
            vol = vol * np.sqrt(252)
        results[f'HV_{period}'] = vol
    
    return pd.DataFrame(results)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average True Range - measures volatility including gaps.
    Useful for setting stop-loss levels.
    """
    tr = _true_range(high, low, close)
    return tr.ewm(span=period, adjust=False).mean()


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Calculate True Range."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range


def value_at_risk(returns: pd.Series, confidence_levels: List[float] = [0.95, 0.99],
                  method: str = 'historical') -> pd.DataFrame:
    """
    Calculate Value at Risk (VaR) using different methods.
    
    Methods:
    - 'historical': Historical simulation
    - 'parametric': Normal distribution assumption
    - 'cornish_fisher': Adjusted for skewness and kurtosis
    """
    results = {}
    
    for level in confidence_levels:
        if method == 'historical':
            var = returns.quantile(1 - level)
        elif method == 'parametric':
            mean = returns.mean()
            std = returns.std()
            var = mean - std * stats.norm.ppf(level)
        elif method == 'cornish_fisher':
            var = _cornish_fisher_var(returns, level)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        results[f'VaR_{int(level*100)}_{method}'] = var
    
    return pd.DataFrame(results)


def _cornish_fisher_var(returns: pd.Series, confidence: float) -> float:
    """Calculate VaR using Cornish-Fisher expansion for non-normal distributions."""
    mean = returns.mean()
    std = returns.std()
    skew = stats.skew(returns.dropna())
    kurt = stats.kurtosis(returns.dropna())
    
    z = stats.norm.ppf(confidence)
    
    # Cornish-Fisher expansion
    z_cf = (z + (z**2 - 1) * skew / 6 + 
            (z**3 - 3*z) * (kurt - 3) / 24 - 
            (2*z**3 - 5*z) * (skew**2) / 36)
    
    var = mean - std * z_cf
    return var


def conditional_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Calculate Conditional VaR (Expected Shortfall).
    Measures expected loss given that loss exceeds VaR.
    """
    var = returns.quantile(1 - confidence)
    cvar = returns[returns <= var].mean()
    return cvar


def rolling_correlation(returns1: pd.Series, returns2: pd.Series, 
                        window: int = 60) -> pd.Series:
    """Calculate rolling correlation between two return series."""
    return returns1.rolling(window=window).corr(returns2)


def correlation_matrix(returns_df: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    """Calculate rolling correlation matrix for multiple assets."""
    return returns_df.tail(window).corr()


# ============================================================================
# INTEGRATED TECHNICAL ANALYSIS
# ============================================================================

def add_momentum_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add comprehensive momentum indicators to dataframe.
    Requires columns: SYMBOL, SERIES, TRADE_DATE, CLOSE_PRICE, HIGH_PRICE, LOW_PRICE, TTL_TRD_QNTY
    """
    if df.empty:
        return df
    
    result = df.copy()
    g = result.groupby(['SYMBOL', 'SERIES'], sort=False)
    
    # Multi-timeframe RSI
    for period in [7, 14, 21]:
        result[f'RSI_{period}'] = g['CLOSE_PRICE'].transform(lambda x: _rsi(x, period))
    
    # Connors RSI
    result['CONNORS_RSI'] = g['CLOSE_PRICE'].transform(
        lambda x: connors_rsi(x, lookback_rsi=2, lookback_streak=27, lookback_percentile=100)
    )
    
    # MACD with histogram
    macd_cols = ['MACD', 'SIGNAL', 'HISTOGRAM', 'DIVERGENCE']
    for col in macd_cols:
        result[f'MACD_{col}'] = g['CLOSE_PRICE'].transform(
            lambda x: macd_histogram(x)[col]
        )
    
    # ADX
    result['ADX'] = g.apply(
        lambda x: adx(x['HIGH_PRICE'], x['LOW_PRICE'], x['CLOSE_PRICE'])
    ).reset_index(level=[0,1], drop=True)
    
    # Chaikin Money Flow
    result['CMF'] = g.apply(
        lambda x: chaikin_money_flow(x['HIGH_PRICE'], x['LOW_PRICE'], x['CLOSE_PRICE'], x['TTL_TRD_QNTY'])
    ).reset_index(level=[0,1], drop=True)
    
    # Aroon
    aroon_cols = ['AROON_UP', 'AROON_DOWN', 'AROON_OSC']
    for col in aroon_cols:
        result[col] = g.apply(
            lambda x: aroon(x['HIGH_PRICE'], x['LOW_PRICE'])[col]
        ).reset_index(level=[0,1], drop=True)
    
    # Momentum score (composite)
    result['MOMENTUM_SCORE'] = (
        0.25 * (100 - result['RSI_14'].fillna(50)) / 100 +  # Inverse RSI for mean reversion
        0.25 * result['CMF'].fillna(0).clip(-1, 1) / 2 + 0.5 +
        0.25 * result['ADX'].fillna(0) / 50 +
        0.25 * result['AROON_OSC'].fillna(0) / 200 + 0.5
    ).clip(0, 1)
    
    return result


def add_volatility_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add comprehensive volatility indicators to dataframe.
    """
    if df.empty:
        return df
    
    result = df.copy()
    g = result.groupby(['SYMBOL', 'SERIES'], sort=False)
    
    # Historical volatility (multiple periods)
    hv_periods = [10, 20, 60]
    for period in hv_periods:
        result[f'HV_{period}'] = g['CLOSE_PRICE'].transform(
            lambda x: historical_volatility(x, periods=[period])[f'HV_{period}']
        )
    
    # ATR
    result['ATR_14'] = g.apply(
        lambda x: atr(x['HIGH_PRICE'], x['LOW_PRICE'], x['CLOSE_PRICE'])
    ).reset_index(level=[0,1], drop=True)
    
    # ATR as percentage of price
    result['ATR_PCT'] = result['ATR_14'] / result['CLOSE_PRICE'] * 100
    
    # Rolling volatility ratio (short-term vs long-term)
    result['VOL_RATIO'] = result['HV_10'] / result['HV_60']
    
    # Bollinger Bands
    result['BB_MIDDLE'] = g['CLOSE_PRICE'].transform(lambda x: x.rolling(20).mean())
    result['BB_STD'] = g['CLOSE_PRICE'].transform(lambda x: x.rolling(20).std())
    result['BB_UPPER'] = result['BB_MIDDLE'] + 2 * result['BB_STD']
    result['BB_LOWER'] = result['BB_MIDDLE'] - 2 * result['BB_STD']
    result['BB_WIDTH'] = (result['BB_UPPER'] - result['BB_LOWER']) / result['BB_MIDDLE'] * 100
    result['BB_POSITION'] = (result['CLOSE_PRICE'] - result['BB_LOWER']) / (result['BB_UPPER'] - result['BB_LOWER'])
    
    # Keltner Channels
    result['KC_MIDDLE'] = g['CLOSE_PRICE'].transform(lambda x: x.ewm(span=20).mean())
    result['KC_RANGE'] = g.apply(
        lambda x: atr(x['HIGH_PRICE'], x['LOW_PRICE'], x['CLOSE_PRICE'])
    ).reset_index(level=[0,1], drop=True) * 2
    result['KC_UPPER'] = result['KC_MIDDLE'] + result['KC_RANGE']
    result['KC_LOWER'] = result['KC_MIDDLE'] - result['KC_RANGE']
    
    # Volatility regime detection
    vol_zscore = (result['HV_20'] - result['HV_20'].rolling(126).mean()) / result['HV_20'].rolling(126).std()
    result['VOL_REGIME'] = pd.cut(
        vol_zscore.fillna(0),
        bins=[-np.inf, -1, 1, np.inf],
        labels=['Low Vol', 'Normal Vol', 'High Vol']
    )
    
    # Cleanup temporary columns
    result.drop(['BB_STD', 'KC_RANGE'], axis=1, inplace=True, errors='ignore')
    
    return result


def calculate_portfolio_var(positions: pd.DataFrame, returns_history: pd.DataFrame,
                           confidence: float = 0.95, horizon: int = 1) -> Dict:
    """
    Calculate portfolio-level VaR and risk metrics.
    
    Args:
        positions: DataFrame with columns [SYMBOL, QUANTITY, AVG_PRICE]
        returns_history: DataFrame with date index and symbol columns (returns)
        confidence: Confidence level (e.g., 0.95 for 95%)
        horizon: Time horizon in days
    
    Returns:
        Dictionary with VaR, CVaR, and other risk metrics
    """
    # Calculate portfolio weights and values
    positions = positions.copy()
    positions['VALUE'] = positions['QUANTITY'] * positions['AVG_PRICE']
    total_value = positions['VALUE'].sum()
    positions['WEIGHT'] = positions['VALUE'] / total_value
    
    # Align returns with positions
    symbols = positions['SYMBOL'].tolist()
    available_symbols = [s for s in symbols if s in returns_history.columns]
    
    if not available_symbols:
        return {'error': 'No matching symbols in returns history'}
    
    port_returns = returns_history[available_symbols].dot(
        positions.set_index('SYMBOL').loc[available_symbols, 'WEIGHT']
    )
    
    # Calculate VaR and CVaR
    var_95 = value_at_risk(port_returns, confidence_levels=[confidence])
    cvar_95 = conditional_var(port_returns, confidence)
    
    # Scale for time horizon
    var_scaled = var_95.iloc[-1, 0] * np.sqrt(horizon) * total_value
    cvar_scaled = cvar_95 * np.sqrt(horizon) * total_value
    
    # Additional metrics
    sharpe = (port_returns.mean() * 252) / (port_returns.std() * np.sqrt(252))
    max_dd = (port_returns.cumsum().expanding().max() - port_returns.cumsum()).min()
    
    return {
        'portfolio_value': total_value,
        'var_95_daily': var_scaled,
        'cvar_95_daily': cvar_scaled,
        'var_95_pct': var_95.iloc[-1, 0] * 100,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd * 100,
        'annualized_return': port_returns.mean() * 252 * 100,
        'annualized_vol': port_returns.std() * np.sqrt(252) * 100
    }


# Helper function from original indicators.py
def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


if __name__ == '__main__':
    # Example usage
    print("Institutional Technical Analysis Module loaded successfully")
    print("Available functions:")
    print("- Momentum: connors_rsi(), macd_histogram(), adx(), chaikin_money_flow(), aroon()")
    print("- Volatility: historical_volatility(), atr(), value_at_risk(), conditional_var()")
    print("- Integrated: add_momentum_indicators(), add_volatility_indicators()")
    print("- Portfolio: calculate_portfolio_var()")
