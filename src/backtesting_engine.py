"""
Module 7: Backtesting Engine
Institutional-grade event studies, walk-forward analysis, and performance attribution.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional
import warnings

warnings.filterwarnings('ignore')

class BacktestEngine:
    """
    Vector-based backtesting engine for speed.
    Supports transaction costs, slippage, and position sizing.
    """
    
    def __init__(self, initial_capital: float = 1000000):
        self.initial_capital = initial_capital
        self.results = None
        
    def run(self, 
            data: pd.DataFrame, 
            strategy_func: Callable, 
            commission: float = 0.0005, 
            slippage: float = 0.0005) -> pd.DataFrame:
        """
        Run vector backtest.
        strategy_func must return a Series of signals (1=Long, -1=Short, 0=Flat).
        """
        df = data.copy()
        
        # Generate Signals
        df['signal'] = strategy_func(df)
        
        # Shift signal to avoid lookahead bias (signal generated at close, executed next open)
        df['position'] = df['signal'].shift(1).fillna(0)
        
        # Calculate Returns
        df['market_ret'] = df['Close'].pct_change()
        df['strategy_ret'] = df['position'] * df['market_ret']
        
        # Apply Costs
        turnover = df['position'].diff().abs().fillna(0)
        costs = turnover * (commission + slippage)
        df['net_strategy_ret'] = df['strategy_ret'] - costs
        
        # Cumulative Performance
        df['cum_market'] = (1 + df['market_ret']).cumprod()
        df['cum_strategy'] = (1 + df['net_strategy_ret']).cumprod()
        
        self.results = df
        return df
    
    def calculate_metrics(self) -> Dict[str, float]:
        """Calculate institutional performance metrics."""
        if self.results is None:
            return {}
            
        df = self.results
        strat_ret = df['net_strategy_ret'].dropna()
        bench_ret = df['market_ret'].dropna()
        
        # CAGR
        years = len(df) / 252
        cagr = (df['cum_strategy'].iloc[-1] ** (1/years)) - 1 if years > 0 else 0
        
        # Volatility
        vol = strat_ret.std() * np.sqrt(252)
        
        # Sharpe Ratio (Rf=0 for simplicity)
        sharpe = (strat_ret.mean() * 252) / vol if vol != 0 else 0
        
        # Drawdown
        cum_ret = df['cum_strategy']
        rolling_max = cum_ret.cummax()
        drawdown = (cum_ret - rolling_max) / rolling_max
        max_dd = drawdown.min()
        
        # Sortino Ratio (Downside deviation)
        downside = strat_ret[strat_ret < 0]
        downside_std = downside.std() * np.sqrt(252) if not downside.empty else 0
        sortino = (strat_ret.mean() * 252) / downside_std if downside_std != 0 else 0
        
        # Win Rate
        trades = df['strategy_ret'][df['position'] != 0]
        win_rate = (trades > 0).sum() / len(trades) if len(trades) > 0 else 0
        
        # Profit Factor
        gross_profit = trades[trades > 0].sum()
        gross_loss = abs(trades[trades < 0].sum())
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else 999
        
        return {
            'CAGR': round(cagr * 100, 2),
            'Volatility': round(vol * 100, 2),
            'Sharpe_Ratio': round(sharpe, 2),
            'Sortino_Ratio': round(sortino, 2),
            'Max_Drawdown': round(max_dd * 100, 2),
            'Win_Rate': round(win_rate * 100, 1),
            'Profit_Factor': round(profit_factor, 2),
            'Total_Trades': len(trades)
        }

class WalkForwardAnalyzer:
    """
    Walk-Forward Analysis to prevent overfitting.
    Optimizes on in-sample, validates on out-of-sample.
    """
    
    def __init__(self, train_months: int = 12, test_months: int = 3):
        self.train_months = train_months
        self.test_months = test_months
        
    def run(self, data: pd.DataFrame, strategy_class, param_grid: Dict) -> pd.DataFrame:
        """
        Iterate through time windows.
        """
        results = []
        dates = data.index
        
        # Simple splitting logic (can be improved)
        total_days = len(data)
        train_days = self.train_months * 21
        test_days = self.test_months * 21
        
        start_idx = 0
        while start_idx + train_days + test_days < total_days:
            train_end = start_idx + train_days
            test_end = train_end + test_days
            
            train_data = data.iloc[start_idx:train_end]
            test_data = data.iloc[train_end:test_end]
            
            # Find best params on train (simplified: just take first for now)
            # In production, use GridSearch here
            best_params = list(param_grid.values())[0][0] if param_grid else {}
            
            # Run on test
            engine = BacktestEngine()
            res_df = engine.run(test_data, lambda x: strategy_class(x, **best_params).generate_signals())
            metrics = engine.calculate_metrics()
            
            results.append({
                'period_start': test_data.index[0],
                'period_end': test_data.index[-1],
                'sharpe': metrics.get('Sharpe_Ratio', 0),
                'cagr': metrics.get('CAGR', 0)
            })
            
            start_idx += train_days # Rolling window
            
        return pd.DataFrame(results)

def simple_momentum_strategy(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """Example Strategy: Buy if price > MA(lookback)"""
    ma = df['Close'].rolling(lookback).mean()
    return np.where(df['Close'] > ma, 1, 0)

# Usage Example
if __name__ == "__main__":
    # Mock Data
    dates = pd.date_range(start='2020-01-01', periods=500)
    mock_prices = 100 + np.cumsum(np.random.randn(500))
    df = pd.DataFrame({'Close': mock_prices}, index=dates)
    
    engine = BacktestEngine()
    engine.run(df, lambda x: simple_momentum_strategy(x, 20))
    print(engine.calculate_metrics())
