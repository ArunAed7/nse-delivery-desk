"""
Phase 1: Technical Pro Module
Momentum Suite + Volatility Analytics
Institutional-grade technical indicators for short-term trading decisions
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Optional, List
from scipy import stats


# =============================================================================
# MOMENTUM SUITE
# =============================================================================

def connors_rsi(close: pd.Series, lookback_rsi: int = 3, lookback_streak: int = 2, 
                lookback_rank: int = 100) -> pd.DataFrame:
    """
    Connors RSI - 3-component mean reversion indicator
    
    Components:
    1. RSI of close (lookback_rsi periods)
    2. RSI of streak duration (consecutive up/down days)
    3. Percentile rank of close over lookback_rank periods
    
    Returns: DataFrame with individual components and composite CRSI
    """
    df = pd.DataFrame(index=close.index)
    
    # Component 1: Standard RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=lookback_rsi).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=lookback_rsi).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_close'] = 100 - (100 / (1 + rs))
    
    # Component 2: Streak RSI
    streak = np.zeros(len(close))
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            streak[i] = streak[i-1] + 1 if streak[i-1] >= 0 else 1
        elif close.iloc[i] < close.iloc[i-1]:
            streak[i] = streak[i-1] - 1 if streak[i-1] <= 0 else -1
        else:
            streak[i] = 0
    
    streak_series = pd.Series(streak, index=close.index)
    delta_streak = streak_series.diff()
    gain_streak = delta_streak.where(delta_streak > 0, 0).rolling(window=lookback_streak).mean()
    loss_streak = (-delta_streak.where(delta_streak < 0, 0)).rolling(window=lookback_streak).mean()
    rs_streak = gain_streak / loss_streak.replace(0, np.nan)
    df['rsi_streak'] = 100 - (100 / (1 + rs_streak))
    
    # Component 3: Percentile Rank
    df['rank_pct'] = close.rolling(window=lookback_rank).apply(
        lambda x: stats.percentileofscore(x, x.iloc[-1]) / 100.0, raw=False
    )
    
    # Composite CRSI
    df['crsi'] = (df['rsi_close'] + df['rsi_streak'] + (df['rank_pct'] * 100)) / 3
    
    return df


def macd_with_divergence(close: pd.Series, fast: int = 12, slow: int = 26, 
                         signal: int = 9) -> pd.DataFrame:
    """
    MACD with automatic divergence detection
    
    Detects:
    - Regular Bullish/Bearish Divergence
    - Hidden Bullish/Bearish Divergence
    
    Returns: DataFrame with MACD line, signal, histogram, and divergence signals
    """
    df = pd.DataFrame(index=close.index)
    
    # Calculate MACD
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    df['macd_line'] = ema_fast - ema_slow
    df['signal_line'] = df['macd_line'].ewm(span=signal, adjust=False).mean()
    df['macd_hist'] = df['macd_line'] - df['signal_line']
    
    # Detect divergences (simplified - production would use pivot detection)
    df['bullish_div'] = False
    df['bearish_div'] = False
    
    # Look for price making lower lows while MACD makes higher lows
    for i in range(20, len(close)):
        # Regular Bullish Divergence
        if (close.iloc[i] < close.iloc[i-10] and 
            df['macd_line'].iloc[i] > df['macd_line'].iloc[i-10] and
            df['macd_line'].iloc[i-1] < 0):
            df.loc[df.index[i], 'bullish_div'] = True
        
        # Regular Bearish Divergence
        if (close.iloc[i] > close.iloc[i-10] and 
            df['macd_line'].iloc[i] < df['macd_line'].iloc[i-10] and
            df['macd_line'].iloc[i-1] > 0):
            df.loc[df.index[i], 'bearish_div'] = True
    
    return df


def adx_trend_strength(high: pd.Series, low: pd.Series, close: pd.Series, 
                       period: int = 14) -> pd.DataFrame:
    """
    Average Directional Index (ADX) - Measures trend strength
    
    Interpretation:
    - ADX < 20: Weak trend / Range-bound
    - ADX 20-40: Strong trend
    - ADX > 40: Very strong trend
    
    Returns: DataFrame with +DI, -DI, ADX, ADXR
    """
    df = pd.DataFrame(index=close.index)
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    # Directional Movement
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    # Smoothed DM
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    # DX and ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.rolling(window=period).mean()
    
    df['plus_di'] = plus_di
    df['minus_di'] = minus_di
    df['adx'] = adx
    df['adxr'] = (adx + adx.shift(period)).rolling(window=period).mean()
    
    # Trend strength classification
    df['trend_strength'] = pd.cut(
        df['adx'], 
        bins=[0, 20, 40, 100], 
        labels=['Weak', 'Strong', 'Very Strong']
    )
    
    return df


def chaikin_money_flow(high: pd.Series, low: pd.Series, close: pd.Series, 
                       volume: pd.Series, period: int = 20) -> pd.Series:
    """
    Chaikin Money Flow (CMF) - Volume-weighted momentum
    
    Measures buying/selling pressure over specified period
    - CMF > 0: Buying pressure
    - CMF < 0: Selling pressure
    
    Returns: CMF series
    """
    money_flow_multiplier = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    money_flow_volume = money_flow_multiplier * volume
    
    cmf = money_flow_volume.rolling(window=period).sum() / volume.rolling(window=period).sum()
    
    return cmf


def aroon_oscillator(high: pd.Series, low: pd.Series, period: int = 25) -> pd.DataFrame:
    """
    Aroon Indicator - Identifies trend changes and strength
    
    Returns: DataFrame with Aroon Up, Aroon Down, and Aroon Oscillator
    """
    df = pd.DataFrame(index=high.index)
    
    # Aroon Up: How many periods since highest high
    df['aroon_up'] = 100 * (period - high.rolling(window=period+1).apply(
        lambda x: period - x.argmax(), raw=False
    )) / period
    
    # Aroon Down: How many periods since lowest low
    df['aroon_down'] = 100 * (period - low.rolling(window=period+1).apply(
        lambda x: period - x.argmin(), raw=False
    )) / period
    
    # Aroon Oscillator
    df['aroon_osc'] = df['aroon_up'] - df['aroon_down']
    
    return df


def add_momentum_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Batch add all momentum indicators to dataframe
    
    Requires columns: 'high', 'low', 'close', 'volume'
    """
    result = df.copy()
    
    # Connors RSI
    crsi = connors_rsi(result['close'])
    result = pd.concat([result, crsi.add_prefix('mom_')], axis=1)
    
    # MACD with divergence
    macd = macd_with_divergence(result['close'])
    result = pd.concat([result, macd.add_prefix('macd_')], axis=1)
    
    # ADX
    adx = adx_trend_strength(result['high'], result['low'], result['close'])
    result = pd.concat([result, adx.add_prefix('adx_')], axis=1)
    
    # CMF
    result['cmf'] = chaikin_money_flow(
        result['high'], result['low'], result['close'], result['volume']
    )
    
    # Aroon
    aroon = aroon_oscillator(result['high'], result['low'])
    result = pd.concat([result, aroon.add_prefix('aroon_')], axis=1)
    
    return result


# =============================================================================
# VOLATILITY ANALYTICS
# =============================================================================

def historical_volatility(close: pd.Series, window: int = 20, 
                          annualize: bool = True, trading_days: int = 252) -> pd.Series:
    """
    Historical Volatility - Standard deviation of returns
    
    Returns: Annualized or raw volatility series
    """
    returns = close.pct_change()
    vol = returns.rolling(window=window).std()
    
    if annualize:
        vol = vol * np.sqrt(trading_days)
    
    return vol


def value_at_risk(returns: pd.Series, confidence: float = 0.95, 
                  method: str = 'historical', window: int = 252) -> float:
    """
    Value at Risk (VaR) - Maximum expected loss at confidence level
    
    Methods:
    - 'historical': Historical simulation
    - 'parametric': Normal distribution assumption
    - 'cornish_fisher': Adjusted for skewness/kurtosis
    
    Returns: VaR as positive number (loss)
    """
    if len(returns) < window:
        window = len(returns)
    
    recent_returns = returns.tail(window).dropna()
    
    if method == 'historical':
        var = -np.percentile(recent_returns, (1 - confidence) * 100)
    
    elif method == 'parametric':
        mu = recent_returns.mean()
        sigma = recent_returns.std()
        z_score = stats.norm.ppf(1 - confidence)
        var = -(mu + z_score * sigma)
    
    elif method == 'cornish_fisher':
        mu = recent_returns.mean()
        sigma = recent_returns.std()
        skew = stats.skew(recent_returns)
        kurt = stats.kurtosis(recent_returns)
        
        z = stats.norm.ppf(1 - confidence)
        z_cf = (z + (z**2 - 1) * skew / 6 + 
                (z**3 - 3*z) * (kurt - 3) / 24 - 
                (2*z**3 - 5*z) * skew**2 / 36)
        
        var = -(mu + z_cf * sigma)
    
    else:
        raise ValueError(f"Unknown method: {method}")
    
    return max(var, 0)


def conditional_var(returns: pd.Series, confidence: float = 0.95, 
                    window: int = 252) -> float:
    """
    Conditional VaR (Expected Shortfall) - Average loss beyond VaR
    
    More conservative than VaR, captures tail risk
    """
    if len(returns) < window:
        window = len(returns)
    
    recent_returns = returns.tail(window).dropna()
    var_threshold = np.percentile(recent_returns, (1 - confidence) * 100)
    
    cvar = -recent_returns[recent_returns <= var_threshold].mean()
    
    return max(cvar, 0) if not np.isnan(cvar) else 0


def atr_stops(high: pd.Series, low: pd.Series, close: pd.Series, 
              period: int = 14, multiplier: float = 2.0) -> pd.DataFrame:
    """
    Average True Range (ATR) based stop-loss levels
    
    Returns: DataFrame with ATR, long stop, short stop
    """
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period).mean()
    
    df = pd.DataFrame(index=close.index)
    df['atr'] = atr
    df['long_stop'] = close - (multiplier * atr)
    df['short_stop'] = close + (multiplier * atr)
    
    return df


def bollinger_bands(close: pd.Series, period: int = 20, 
                    std_dev: float = 2.0) -> pd.DataFrame:
    """
    Bollinger Bands - Volatility bands around moving average
    
    Returns: DataFrame with middle, upper, lower bands and %B
    """
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    
    # %B - Position within bands
    pct_b = (close - lower) / (upper - lower).replace(0, np.nan)
    
    # Bandwidth
    bandwidth = (upper - lower) / middle
    
    df = pd.DataFrame({
        'bb_middle': middle,
        'bb_upper': upper,
        'bb_lower': lower,
        'bb_pct_b': pct_b,
        'bb_bandwidth': bandwidth
    })
    
    return df


def keltner_channels(high: pd.Series, low: pd.Series, close: pd.Series, 
                     ema_period: int = 20, atr_period: int = 10, 
                     multiplier: float = 2.0) -> pd.DataFrame:
    """
    Keltner Channels - ATR-based volatility channels
    
    Often used with Bollinger Bands for squeeze detection
    """
    ema = close.ewm(span=ema_period, adjust=False).mean()
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=atr_period).mean()
    
    upper = ema + (multiplier * atr)
    lower = ema - (multiplier * atr)
    
    return pd.DataFrame({
        'kc_middle': ema,
        'kc_upper': upper,
        'kc_lower': lower
    })


def volatility_regime_detector(close: pd.Series, short_window: int = 20, 
                               long_window: int = 60) -> pd.Series:
    """
    Detect volatility regimes: Low, Normal, High, Extreme
    
    Based on ratio of short-term to long-term volatility
    """
    short_vol = historical_volatility(close, short_window)
    long_vol = historical_volatility(close, long_window)
    
    vol_ratio = short_vol / long_vol
    
    def classify_regime(ratio):
        if pd.isna(ratio):
            return 'Unknown'
        elif ratio < 0.7:
            return 'Low'
        elif ratio < 1.0:
            return 'Normal'
        elif ratio < 1.5:
            return 'High'
        else:
            return 'Extreme'
    
    regime = vol_ratio.apply(classify_regime)
    
    return regime


def portfolio_var(returns_matrix: pd.DataFrame, weights: np.ndarray, 
                  confidence: float = 0.95, method: str = 'historical') -> float:
    """
    Portfolio-level VaR using correlation structure
    
    Args:
        returns_matrix: DataFrame of asset returns
        weights: Array of portfolio weights
        confidence: Confidence level (e.g., 0.95 for 95%)
        method: VaR calculation method
    
    Returns: Portfolio VaR
    """
    portfolio_returns = (returns_matrix * weights).sum(axis=1)
    return value_at_risk(portfolio_returns, confidence, method)


def garch_volatility_forecast(returns: pd.Series, forecast_horizon: int = 10) -> Tuple[float, pd.Series]:
    """
    Simplified GARCH(1,1) volatility forecast
    
    Note: For production, use arch package. This is a simplified implementation.
    
    Returns: Current vol estimate and forecast series
    """
    # Simplified GARCH(1,1) estimation
    omega = 0.00001
    alpha = 0.1
    beta = 0.85
    
    n = len(returns)
    sigma2 = np.zeros(n)
    sigma2[0] = returns.var()
    
    for i in range(1, n):
        sigma2[i] = omega + alpha * returns.iloc[i-1]**2 + beta * sigma2[i-1]
    
    current_vol = np.sqrt(sigma2[-1])
    
    # Forecast
    forecasts = []
    for h in range(1, forecast_horizon + 1):
        forecast_vol = current_vol * np.sqrt((alpha + beta)**h)
        forecasts.append(forecast_vol)
    
    return current_vol, pd.Series(forecasts, index=range(1, forecast_horizon + 1))


def add_volatility_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Batch add all volatility indicators to dataframe
    
    Requires columns: 'high', 'low', 'close'
    """
    result = df.copy()
    
    # Historical volatility
    result['vol_hist_20'] = historical_volatility(result['close'], 20)
    result['vol_hist_60'] = historical_volatility(result['close'], 60)
    
    # ATR stops
    atr_df = atr_stops(result['high'], result['low'], result['close'])
    result = pd.concat([result, atr_df], axis=1)
    
    # Bollinger Bands
    bb_df = bollinger_bands(result['close'])
    result = pd.concat([result, bb_df], axis=1)
    
    # Keltner Channels
    kc_df = keltner_channels(result['high'], result['low'], result['close'])
    result = pd.concat([result, kc_df], axis=1)
    
    # Volatility regime
    result['vol_regime'] = volatility_regime_detector(result['close'])
    
    # VaR (rolling 252-day)
    result['var_95'] = result['close'].pct_change().rolling(252).apply(
        lambda x: value_at_risk(x, 0.95, 'historical'), raw=False
    )
    
    result['cvar_95'] = result['close'].pct_change().rolling(252).apply(
        lambda x: conditional_var(x, 0.95, 252), raw=False
    )
    
    return result


# =============================================================================
# SIGNAL GENERATION
# =============================================================================

def generate_momentum_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate composite momentum signals from all indicators
    
    Returns: DataFrame with individual signals and composite score
    """
    result = pd.DataFrame(index=df.index)
    
    # CRSI signals
    result['signal_crsi_oversold'] = df.get('mom_crsi', pd.Series(index=df.index)) < 30
    result['signal_crsi_overbought'] = df.get('mom_crsi', pd.Series(index=df.index)) > 70
    
    # MACD signals
    result['signal_macd_bull_cross'] = (
        (df.get('macd_macd_line', pd.Series(index=df.index)) > 
         df.get('macd_signal_line', pd.Series(index=df.index))) &
        (df.get('macd_macd_line', pd.Series(index=df.index)).shift(1) <= 
         df.get('macd_signal_line', pd.Series(index=df.index)).shift(1))
    )
    
    result['signal_macd_bear_cross'] = (
        (df.get('macd_macd_line', pd.Series(index=df.index)) < 
         df.get('macd_signal_line', pd.Series(index=df.index))) &
        (df.get('macd_macd_line', pd.Series(index=df.index)).shift(1) >= 
         df.get('macd_signal_line', pd.Series(index=df.index)).shift(1))
    )
    
    # ADX trend strength
    result['signal_strong_trend'] = df.get('adx_adx', pd.Series(index=df.index)) > 25
    
    # CMF money flow
    result['signal_buying_pressure'] = df.get('cmf', pd.Series(index=df.index)) > 0.1
    result['signal_selling_pressure'] = df.get('cmf', pd.Series(index=df.index)) < -0.1
    
    # Composite momentum score (-5 to +5)
    result['momentum_score'] = (
        result['signal_crsi_oversold'].astype(int) - 
        result['signal_crsi_overbought'].astype(int) +
        result['signal_macd_bull_cross'].astype(int) - 
        result['signal_macd_bear_cross'].astype(int) +
        result['signal_buying_pressure'].astype(int) - 
        result['signal_selling_pressure'].astype(int) +
        result['signal_strong_trend'].astype(int)
    )
    
    return result


if __name__ == "__main__":
    # Test with sample data
    dates = pd.date_range('2023-01-01', periods=300, freq='D')
    np.random.seed(42)
    
    # Generate synthetic price data
    returns = np.random.normal(0.0005, 0.02, 300)
    close = pd.Series(100 * np.cumprod(1 + returns), index=dates)
    high = close * (1 + np.abs(np.random.normal(0.01, 0.005, 300)))
    low = close * (1 - np.abs(np.random.normal(0.01, 0.005, 300)))
    volume = pd.Series(np.random.randint(1000000, 10000000, 300), index=dates)
    
    df = pd.DataFrame({'high': high, 'low': low, 'close': close, 'volume': volume})
    
    print("Testing Momentum Suite...")
    mom_df = add_momentum_indicators(df)
    print(f"Momentum indicators added: {mom_df.shape}")
    
    print("\nTesting Volatility Analytics...")
    vol_df = add_volatility_indicators(df)
    print(f"Volatility indicators added: {vol_df.shape}")
    
    print("\nGenerating signals...")
    signals = generate_momentum_signals(vol_df)
    print(f"Signals generated: {signals.shape}")
    print(f"\nLatest momentum score: {signals['momentum_score'].iloc[-1]}")
    
    print("\n✅ All technical pro modules working correctly!")
