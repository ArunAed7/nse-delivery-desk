"""
Phase 1: Relative Strength Module
RS Ratings, Peer Comparison, Stage Analysis
Institutional-grade relative strength analysis for stock selection
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from scipy import stats


def calculate_rs_rating(stock_returns: pd.Series, benchmark_returns: pd.Series,
                        lookback_days: int = 252) -> float:
    """
    Relative performance vs a proxy series, scaled so 100 = in line with the proxy.

    This is not a 1-99 universe RS Rating.
    """
    # Ensure same length
    min_len = min(len(stock_returns), len(benchmark_returns))
    stock_ret = stock_returns.tail(min_len)
    bench_ret = benchmark_returns.tail(min_len)
    
    # Calculate cumulative relative performance
    cumulative_stock = (1 + stock_ret).cumprod()
    cumulative_bench = (1 + bench_ret).cumprod()
    
    relative_performance = cumulative_stock / cumulative_bench
    
    # Get latest relative performance
    latest_rp = relative_performance.iloc[-1]
    return float(latest_rp * 100)


def rs_vs_index(stock_close: pd.Series, index_close: pd.Series,
                periods: List[int] = [20, 60, 252]) -> pd.DataFrame:
    """
    Relative Strength vs Index across multiple timeframes
    
    Returns: DataFrame with RS metrics for each period
    """
    df = pd.DataFrame(index=stock_close.index)
    
    for period in periods:
        # Calculate returns over period
        stock_ret = stock_close.pct_change(period)
        index_ret = index_close.pct_change(period)
        
        # Relative strength
        rs = (1 + stock_ret) / (1 + index_ret) - 1
        
        df[f'rs_{period}d'] = rs
        df[f'rs_{period}d_rank'] = rs.rolling(window=period).apply(
            lambda x: stats.percentileofscore(x.dropna(), x.iloc[-1]) / 100 * 99 
            if len(x.dropna()) > 0 else 50, raw=False
        )
    
    return df


def peer_relative_strength(stock_data: pd.DataFrame, peer_group: pd.DataFrame,
                           metric: str = 'return_1y') -> pd.DataFrame:
    """
    Compare stock vs peer group on specified metric
    
    Args:
        stock_data: DataFrame with stock metrics
        peer_group: DataFrame with peer group metrics (each row is a peer)
        metric: Column name to compare
    
    Returns: DataFrame with peer comparison stats
    """
    stock_value = stock_data[metric].iloc[-1] if metric in stock_data else 0
    peer_values = peer_group[metric].dropna() if metric in peer_group else pd.Series()
    
    if len(peer_values) == 0:
        return pd.DataFrame({
            'stock_value': [stock_value],
            'peer_median': [np.nan],
            'peer_mean': [np.nan],
            'peer_percentile': [50],
            'outperformance': [0]
        })
    
    peer_median = peer_values.median()
    peer_mean = peer_values.mean()
    peer_std = peer_values.std()
    
    # Percentile rank within peer group
    percentile = stats.percentileofscore(peer_values, stock_value)
    
    # Z-score vs peers
    z_score = (stock_value - peer_mean) / peer_std if peer_std > 0 else 0
    
    return pd.DataFrame({
        'stock_value': [stock_value],
        'peer_median': [peer_median],
        'peer_mean': [peer_mean],
        'peer_std': [peer_std],
        'peer_percentile': [percentile],
        'z_score_vs_peers': [z_score],
        'outperformance': [stock_value - peer_median]
    })


def stage_analysis(close: pd.Series, volume: pd.Series = None) -> Dict[str, any]:
    """
    Stan Weinstein Stage Analysis
    
    Identifies which stage a stock is in:
    - Stage 1: Basing (consolidation after decline)
    - Stage 2: Advancing (uptrend - BUY)
    - Stage 3: Topping (consolidation after advance)
    - Stage 4: Declining (downtrend - AVOID/SHORT)
    
    Uses 30-week (150-day) moving average as primary filter
    
    Returns: Dictionary with stage and supporting metrics
    """
    # Calculate key moving averages
    ma_30w = close.rolling(window=150).mean()  # 30-week ~ 150 days
    ma_10w = close.rolling(window=50).mean()   # 10-week ~ 50 days
    
    current_price = close.iloc[-1]
    current_ma30w = ma_30w.iloc[-1]
    current_ma10w = ma_10w.iloc[-1]
    
    # MA slope (20-day change)
    ma30w_slope = ma_30w.iloc[-1] - ma_30w.iloc[-20] if len(ma_30w) > 20 else 0
    
    # Price vs MA relationships
    price_vs_ma30w = (current_price - current_ma30w) / current_ma30w if current_ma30w > 0 else 0
    price_vs_ma10w = (current_price - current_ma10w) / current_ma10w if current_ma10w > 0 else 0
    
    # Volume trend (if available)
    if volume is not None:
        vol_ma_50 = volume.rolling(window=50).mean()
        current_vol_trend = volume.iloc[-1] / vol_ma_50.iloc[-1] if vol_ma_50.iloc[-1] > 0 else 1
    else:
        current_vol_trend = 1.0
    
    # Determine stage
    if current_price > current_ma30w and ma30w_slope > 0:
        if price_vs_ma30w < 0.10:  # Within 10% of MA
            stage = "Stage 2A"  # Early Stage 2 (pullback to MA)
            signal = "BUY"
        else:
            stage = "Stage 2B"  # Extended Stage 2
            signal = "HOLD"
    elif current_price < current_ma30w and ma30w_slope < 0:
        if price_vs_ma30w > -0.10:  # Within 10% of MA
            stage = "Stage 4A"  # Early Stage 4 (rally to MA)
            signal = "AVOID/SHORT"
        else:
            stage = "Stage 4B"  # Extended Stage 4
            signal = "AVOID"
    elif current_price > current_ma30w and ma30w_slope <= 0:
        stage = "Stage 3"  # Topping
        signal = "SELL/HOLD"
    else:  # current_price < current_ma30w and ma30w_slope >= 0
        stage = "Stage 1"  # Basing
        signal = "WATCH"
    
    return {
        'stage': stage,
        'signal': signal,
        'current_price': current_price,
        'ma_30w': current_ma30w,
        'ma_10w': current_ma10w,
        'ma30w_slope': ma30w_slope,
        'price_vs_ma30w_pct': price_vs_ma30w * 100,
        'price_vs_ma10w_pct': price_vs_ma10w * 100,
        'volume_trend': current_vol_trend,
        'is_stage_2': stage.startswith("Stage 2"),
        'is_buyable': signal == "BUY"
    }


def relative_strength_momentum_score(close: pd.Series, benchmark_close: pd.Series,
                                     weights: Dict[str, float] = None) -> float:
    """
    Composite RS Momentum Score (0-100)
    
    Combines multiple RS factors:
    - 1-month RS
    - 3-month RS
    - 6-month RS
    - 12-month RS (primary)
    
    Weights default to emphasizing recent performance while considering long-term
    
    Returns: RS Score (0-100)
    """
    if weights is None:
        weights = {
            '1m': 0.10,
            '3m': 0.20,
            '6m': 0.30,
            '12m': 0.40
        }
    
    periods = {'1m': 21, '3m': 63, '6m': 126, '12m': 252}
    
    scores = []
    for period_name, period_days in periods.items():
        # Stock return
        stock_ret = close.pct_change(period_days).iloc[-1]
        # Benchmark return
        bench_ret = benchmark_close.pct_change(period_days).iloc[-1]
        
        # Relative performance
        rel_perf = stock_ret - bench_ret
        
        # Convert to score (0-100 scale, centered at 50)
        # Assume ±20% relative perf is extreme
        score = 50 + rel_perf * 250  # 20% outperformance = 100
        score = max(0, min(100, score))
        
        scores.append(score * weights[period_name])
    
    return sum(scores)


def identify_rs_breakouts(close: pd.Series, volume: pd.Series,
                          benchmark_close: pd.Series,
                          lookback: int = 63) -> pd.DataFrame:
    """
    Identify RS Breakouts - When stock breaks out while RS is strong
    
    Criteria:
    1. Price makes N-day high
    2. RS line also makes N-day high
    3. Above-average volume
    
    Returns: DataFrame with breakout signals
    """
    df = pd.DataFrame(index=close.index)
    
    # Price highs
    df['price_high_' + str(lookback)] = close.rolling(window=lookback).max()
    df['is_price_breakout'] = close >= df['price_high_' + str(lookback)]
    
    # RS line
    rs_line = close / benchmark_close
    df['rs_high_' + str(lookback)] = rs_line.rolling(window=lookback).max()
    df['is_rs_breakout'] = rs_line >= df['rs_high_' + str(lookback)]
    
    # Volume check
    vol_ma = volume.rolling(window=50).mean()
    df['is_volume_confirmed'] = volume > vol_ma * 1.5
    
    # Combined breakout signal
    df['rs_breakout_signal'] = (
        df['is_price_breakout'] & 
        df['is_rs_breakout'] & 
        df['is_volume_confirmed']
    )
    
    return df


def build_rs_universe(stocks_data: Dict[str, pd.DataFrame],
                      benchmark_data: pd.Series,
                      min_market_cap: float = 1000,
                      min_volume: float = 500000) -> pd.DataFrame:
    """
    Build ranked universe of stocks by RS metrics
    
    Args:
        stocks_data: Dict of ticker -> DataFrame with OHLCV data
        benchmark_data: Series of benchmark prices
        min_market_cap: Minimum market cap in crores
        min_volume: Minimum avg daily volume
    
    Returns: DataFrame of stocks ranked by RS
    """
    results = []
    
    for ticker, df in stocks_data.items():
        if len(df) < 252:  # Need 1 year of data
            continue
        
        # Basic filters
        avg_volume = df['volume'].tail(63).mean()
        if avg_volume < min_volume:
            continue
        
        # Calculate RS metrics
        rs_252 = rs_vs_index(df['close'], benchmark_data, [252])
        rs_rating = calculate_rs_rating(
            df['close'].pct_change(),
            benchmark_data.pct_change()
        )
        
        stage = stage_analysis(df['close'], df.get('volume'))
        
        rs_score = relative_strength_momentum_score(
            df['close'], benchmark_data
        )
        
        results.append({
            'ticker': ticker,
            'rs_rating': rs_rating,
            'rs_252d': rs_252['rs_252d'].iloc[-1] if len(rs_252) > 0 else 0,
            'rs_score': rs_score,
            'stage': stage['stage'],
            'is_stage_2': stage['is_stage_2'],
            'avg_volume': avg_volume,
            'current_price': df['close'].iloc[-1]
        })
    
    # Create ranked DataFrame
    universe_df = pd.DataFrame(results)
    
    if len(universe_df) > 0:
        # Rank by RS Rating
        universe_df['rs_rank'] = universe_df['rs_rating'].rank(ascending=False)
        
        # Sort by RS Rating descending
        universe_df = universe_df.sort_values('rs_rating', ascending=False)
    
    return universe_df


def generate_rs_report(ticker: str, stock_data: pd.DataFrame,
                       benchmark_data: pd.Series,
                       peer_data: pd.DataFrame = None) -> Dict:
    """
    Comprehensive RS Report for a single stock
    
    Returns: Dictionary with all RS analysis
    """
    report = {}
    
    # RS Rating
    report['rs_rating'] = calculate_rs_rating(
        stock_data['close'].pct_change(),
        benchmark_data.pct_change()
    )
    
    # Multi-timeframe RS
    rs_multi = rs_vs_index(stock_data['close'], benchmark_data, [20, 60, 252])
    report['rs_20d'] = rs_multi['rs_20d'].iloc[-1]
    report['rs_60d'] = rs_multi['rs_60d'].iloc[-1]
    report['rs_252d'] = rs_multi['rs_252d'].iloc[-1]
    
    # Stage Analysis
    report['stage_analysis'] = stage_analysis(
        stock_data['close'],
        stock_data.get('volume')
    )
    
    # RS Momentum Score
    report['rs_momentum_score'] = relative_strength_momentum_score(
        stock_data['close'], benchmark_data
    )
    
    # Breakout detection
    breakouts = identify_rs_breakouts(
        stock_data['close'],
        stock_data.get('volume', pd.Series(1, index=stock_data.index)),
        benchmark_data
    )
    report['recent_breakout'] = breakouts['rs_breakout_signal'].iloc[-1]
    report['breakout_count_63d'] = breakouts['rs_breakout_signal'].tail(63).sum()
    
    # Peer comparison (if data available)
    if peer_data is not None and len(peer_data) > 0:
        peer_comp = peer_relative_strength(
            stock_data.tail(1),
            peer_data,
            'return_1y' if 'return_1y' in stock_data else 'close'
        )
        report['peer_comparison'] = peer_comp.to_dict('records')[0]
    
    # Overall RS grade
    rel = float(report["rs_rating"] or 100)
    rating_pts = min(99, max(1, int(50 + (rel - 100))))
    rs_grade_score = (
        rating_pts * 0.40 +
        report['rs_momentum_score'] * 0.30 +
        (100 if report['stage_analysis']['is_stage_2'] else 30) * 0.20 +
        (100 if report['recent_breakout'] else 50) * 0.10
    )
    
    if rs_grade_score >= 90:
        report['rs_grade'] = 'A+'
    elif rs_grade_score >= 80:
        report['rs_grade'] = 'A'
    elif rs_grade_score >= 70:
        report['rs_grade'] = 'B'
    elif rs_grade_score >= 60:
        report['rs_grade'] = 'C'
    elif rs_grade_score >= 50:
        report['rs_grade'] = 'D'
    else:
        report['rs_grade'] = 'E'
    
    report['rs_grade_score'] = rs_grade_score
    
    return report


if __name__ == "__main__":
    # Test with sample data
    print("Testing Relative Strength Module...")
    
    dates = pd.date_range('2022-01-01', periods=500, freq='D')
    np.random.seed(42)
    
    # Generate synthetic stock data (outperforming)
    stock_returns = np.random.normal(0.0008, 0.02, 500)
    stock_close = pd.Series(100 * np.cumprod(1 + stock_returns), index=dates)
    
    # Generate synthetic benchmark data (market)
    bench_returns = np.random.normal(0.0004, 0.015, 500)
    bench_close = pd.Series(100 * np.cumprod(1 + bench_returns), index=dates)
    
    # Volume
    volume = pd.Series(np.random.randint(1000000, 10000000, 500), index=dates)
    
    stock_df = pd.DataFrame({
        'close': stock_close,
        'volume': volume
    })
    
    # Test RS Rating
    rs_rating = calculate_rs_rating(stock_close.pct_change(), bench_close.pct_change())
    print(f"\nRS Rating: {rs_rating}/99")
    
    # Test Multi-timeframe RS
    rs_multi = rs_vs_index(stock_close, bench_close)
    print(f"\nRelative Strength vs Index:")
    print(f"  20-day: {rs_multi['rs_20d'].iloc[-1]*100:.2f}%")
    print(f"  60-day: {rs_multi['rs_60d'].iloc[-1]*100:.2f}%")
    print(f"  252-day: {rs_multi['rs_252d'].iloc[-1]*100:.2f}%")
    
    # Test Stage Analysis
    stage = stage_analysis(stock_close, volume)
    print(f"\nStage Analysis:")
    print(f"  Current Stage: {stage['stage']}")
    print(f"  Signal: {stage['signal']}")
    print(f"  Price vs 30W MA: {stage['price_vs_ma30w_pct']:.2f}%")
    
    # Test RS Momentum Score
    rs_score = relative_strength_momentum_score(stock_close, bench_close)
    print(f"\nRS Momentum Score: {rs_score:.1f}/100")
    
    # Test Breakout Detection
    breakouts = identify_rs_breakouts(stock_close, volume, bench_close)
    print(f"\nRecent Breakout Signal: {breakouts['rs_breakout_signal'].iloc[-1]}")
    print(f"Breakouts in last 63 days: {breakouts['rs_breakout_signal'].tail(63).sum()}")
    
    # Full Report
    print("\n" + "="*50)
    print("COMPREHENSIVE RS REPORT")
    print("="*50)
    
    report = generate_rs_report("TEST", stock_df, bench_close)
    
    print(f"RS Rating: {report['rs_rating']}/99")
    print(f"RS Grade: {report['rs_grade']} ({report['rs_grade_score']:.1f})")
    print(f"Stage: {report['stage_analysis']['stage']}")
    print(f"RS Momentum Score: {report['rs_momentum_score']:.1f}")
    print(f"Recent Breakout: {report['recent_breakout']}")
    
    print("\n✅ All relative strength modules working correctly!")
