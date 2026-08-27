"""
Module 5: Relative Strength & Peer Analysis
Institutional-grade RS ratings, stage analysis, and sector comparison.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings('ignore')

class RelativeStrengthAnalyzer:
    """
    Calculates Mansfield Relative Strength, Stage Analysis, and Peer Rankings.
    Differentiates from RSI (momentum) by measuring performance AGAINST a benchmark.
    """
    
    def __init__(self, benchmark_returns: pd.Series):
        """
        benchmark_returns: Daily returns series of Nifty 50 or Sector Index
        """
        self.benchmark_returns = benchmark_returns
        
    def calculate_mansfield_rs(self, stock_prices: pd.Series, window: int = 252) -> pd.Series:
        """
        Mansfield RS = (Stock Price / Benchmark Price) * 100
        Then smoothed with MA. Rising line = Outperformance.
        """
        # Align indices
        df = pd.DataFrame({'stock': stock_prices, 'bench': self.benchmark_returns.cumprod()})
        df = df.dropna()
        
        if df.empty:
            return pd.Series()
            
        rs_ratio = df['stock'] / df['bench']
        rs_line = rs_ratio * 100
        
        # Smooth with 50-day MA for trend
        rs_smooth = rs_line.rolling(window=50).mean()
        return rs_smooth
    
    def assign_rs_rating(self, rs_series: pd.Series) -> int:
        """
        Assign RS Rating (1-99) based on percentile rank vs universe.
        99 = Top 1% performer, 1 = Bottom 1%.
        Used by CAN SLIM investors.
        """
        if rs_series.empty:
            return 50
            
        current_rs = rs_series.iloc[-1]
        historical_rs = rs_series.dropna()
        
        if historical_rs.empty:
            return 50
            
        percentile = (historical_rs < current_rs).sum() / len(historical_rs)
        rating = int(percentile * 99)
        return max(1, min(99, rating))
    
    def determine_stage(self, price: pd.Series, rs_line: pd.Series) -> str:
        """
        Stan Weinstein Stage Analysis:
        Stage 1: Basing (Sideways)
        Stage 2: Advancing (Price > MA, RS Rising) - BUY
        Stage 3: Topping (Sideways at high)
        Stage 4: Declining (Price < MA, RS Falling) - SELL/SHORT
        """
        ma_30 = price.rolling(30).mean().iloc[-1]
        ma_150 = price.rolling(150).mean().iloc[-1]
        current_price = price.iloc[-1]
        
        rs_slope = rs_line.diff(50).iloc[-1] if len(rs_line) > 50 else 0
        
        if current_price > ma_30 and current_price > ma_150 and rs_slope > 0:
            return "Stage 2 (Advancing)"
        elif current_price < ma_30 and current_price < ma_150 and rs_slope < 0:
            return "Stage 4 (Declining)"
        elif rs_slope > 0 and abs(current_price - ma_150) < (ma_150 * 0.05):
            return "Stage 1 (Basing)"
        else:
            return "Stage 3 (Topping)"
    
    def peer_comparison(self, stock_metrics: Dict, peer_group: pd.DataFrame) -> Dict:
        """
        Compare stock against sector peers on key metrics.
        Returns percentile ranks for PE, PB, ROE, Growth.
        """
        if peer_group.empty:
            return {}
            
        results = {}
        for metric in ['PE', 'PB', 'ROE', 'Sales_Growth', 'Profit_Margin']:
            if metric in stock_metrics and metric in peer_group.columns:
                value = stock_metrics[metric]
                peers = peer_group[metric].dropna()
                
                if len(peers) == 0:
                    continue
                    
                percentile = (peers < value).sum() / len(peers)
                
                # For valuation (PE, PB), lower is often better, so invert logic if needed
                if metric in ['PE', 'PB']:
                    results[f'{metric}_Percentile'] = round((1 - percentile) * 100, 1) # Lower PE = Higher Rank
                else:
                    results[f'{metric}_Percentile'] = round(percentile * 100, 1) # Higher ROE = Higher Rank
                    
        return results

def analyze_relative_strength(stock_data: pd.DataFrame, benchmark_data: pd.Series) -> Dict:
    analyzer = RelativeStrengthAnalyzer(benchmark_data)
    
    rs_line = analyzer.calculate_mansfield_rs(stock_data['Close'])
    rating = analyzer.assign_rs_rating(rs_line)
    stage = analyzer.determine_stage(stock_data['Close'], rs_line)
    
    return {
        'rs_line': rs_line,
        'rs_rating': rating,
        'stage': stage,
        'current_rs_value': rs_line.iloc[-1] if not rs_line.empty else 0
    }
