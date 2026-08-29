"""
Module 4: Derivatives Intelligence
Institutional-grade options analysis, OI decoding, and FII positioning.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings('ignore')

class DerivativesIntelligence:
    """
    Analyzes Options Open Interest, Put-Call Ratios, and FII/DII derivatives positions.
    Identifies support/resistance via Max Pain and Change in OI.
    """
    
    def __init__(self):
        self.oi_data = None
        self.pcr_data = None
        
    def load_oi_data(self, df: pd.DataFrame):
        """Load raw OI data (Strike, CE_OI, PE_OI, CE_Chng, PE_Chng, LTP)"""
        self.oi_data = df
        return self
        
    def calculate_pcr(self, method: str = 'volume') -> float:
        """
        Calculate Put-Call Ratio.
        methods: 'volume', 'oi', 'weighted'
        """
        if self.oi_data is None:
            return 0.0
            
        if method == 'oi':
            total_put_oi = self.oi_data['PE_OI'].sum()
            total_call_oi = self.oi_data['CE_OI'].sum()
        else: # volume
            total_put_oi = self.oi_data.get('PE_Vol', self.oi_data['PE_OI']).sum()
            total_call_oi = self.oi_data.get('CE_Vol', self.oi_data['CE_OI']).sum()
            
        return round(total_put_oi / max(total_call_oi, 1), 2)
    
    def identify_max_pain(self, spot_price: float) -> float:
        from src.grade import max_pain_strike

        if self.oi_data is None:
            return spot_price
        pain = max_pain_strike(self.oi_data)
        return float(pain) if pd.notna(pain) else spot_price

    def detect_oi_buildup(self, threshold: float = 10.0) -> pd.DataFrame:
        from src.grade import oi_buildup

        if self.oi_data is None:
            return pd.DataFrame()
        return oi_buildup(self.oi_data, pct=max(threshold / 100.0, 0.05))
    
    def calculate_iv_rank(self, current_iv: float, iv_52w_high: float, iv_52w_low: float) -> float:
        """
        IV Rank: Where current IV sits relative to 52-week range (0-100).
        Critical for deciding to buy vs sell options.
        """
        if iv_52w_high == iv_52w_low:
            return 50.0
        rank = ((current_iv - iv_52w_low) / (iv_52w_high - iv_52w_low)) * 100
        return max(0, min(100, round(rank, 2)))
    
    def fii_derivatives_positioning(self, fii_data: pd.DataFrame) -> Dict[str, any]:
        """
        Analyze FII Long/Short ratios in Index Futures.
        Bullish if Long% > 60%, Bearish if < 40%.
        """
        if fii_data.empty:
            return {'signal': 'Neutral', 'long_pct': 50, 'trend': 'Flat'}
            
        latest = fii_data.iloc[-1]
        long_contracts = latest.get('Long_Contracts', 0)
        short_contracts = latest.get('Short_Contracts', 0)
        total = long_contracts + short_contracts
        
        if total == 0:
            return {'signal': 'Neutral', 'long_pct': 50, 'trend': 'Flat'}
            
        long_pct = (long_contracts / total) * 100
        
        signal = 'Neutral'
        if long_pct > 60: signal = 'Bullish'
        elif long_pct < 40: signal = 'Bearish'
        
        trend = 'Flat'
        if len(fii_data) > 1:
            prev_long_pct = (fii_data.iloc[-2]['Long_Contracts'] / (fii_data.iloc[-2]['Long_Contracts'] + fii_data.iloc[-2]['Short_Contracts'])) * 100
            if long_pct > prev_long_pct + 2: trend = 'Increasing Longs'
            elif long_pct < prev_long_pct - 2: trend = 'Increasing Shorts'
            
        return {
            'signal': signal,
            'long_pct': round(long_pct, 2),
            'trend': trend,
            'net_positions': long_contracts - short_contracts
        }

def analyze_options_chain(df: pd.DataFrame, spot: float) -> Dict:
    engine = DerivativesIntelligence()
    engine.load_oi_data(df)
    
    return {
        'pcr': engine.calculate_pcr('oi'),
        'max_pain': engine.identify_max_pain(spot),
        'oi_signals': engine.detect_oi_buildup(),
        'fii_signal': 'Pending Data' # Placeholder
    }
