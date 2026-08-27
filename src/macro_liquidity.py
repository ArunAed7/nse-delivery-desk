"""
Module 8: Macro Dashboard & Liquidity Flows
Institutional-grade regime detection, sector rotation, and FII/DII flow analysis.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import warnings

warnings.filterwarnings('ignore')

class MacroRegimeDetector:
    """
    Identifies market regimes (Bull, Bear, Sideways) using HMM-like logic.
    Helps in adjusting portfolio beta and sector exposure.
    """
    
    def __init__(self):
        pass
        
    def detect_regime(self, index_data: pd.DataFrame) -> str:
        """
        Uses Price vs 200DMA and 200DMA Slope to determine regime.
        """
        close = index_data['Close']
        ma_200 = close.rolling(200).mean()
        ma_50 = close.rolling(50).mean()
        
        current_price = close.iloc[-1]
        current_ma200 = ma_200.iloc[-1]
        
        # Calculate slope of 200DMA
        ma200_slope = ma_200.diff(20).iloc[-1]
        
        if current_price > current_ma200 and ma200_slope > 0:
            return "Bull Regime"
        elif current_price < current_ma200 and ma200_slope < 0:
            return "Bear Regime"
        elif abs(current_price - current_ma200) < (current_ma200 * 0.03):
            return "Sideways/Consolidation"
        else:
            return "Transitioning"
            
    def get_sector_rotation_signal(self, sector_perf: pd.DataFrame) -> List[str]:
        """
        Recommends sectors based on economic cycle phase.
        Input: DataFrame with sector returns (1M, 3M, 6M, 12M)
        """
        # Simple momentum ranking
        if sector_perf.empty:
            return []
            
        # Score based on 3M and 6M momentum
        sector_perf['Score'] = (sector_perf['3M'] * 0.4) + (sector_perf['6M'] * 0.6)
        top_sectors = sector_perf.nlargest(3, 'Score').index.tolist()
        
        return top_sectors

class LiquidityFlowAnalyzer:
    """
    Tracks FII/DII flows, SIP inflows, and Margin levels.
    Liquidity drives markets in the short term.
    """
    
    def __init__(self):
        self.flow_data = None
        
    def load_flow_data(self, df: pd.DataFrame):
        """Columns: Date, FII_Net, DII_Net, SIP_Inflow"""
        self.flow_data = df
        return self
        
    def calculate_flow_trend(self, window: int = 20) -> Dict[str, str]:
        """
        Determines if institutions are accumulating or distributing.
        """
        if self.flow_data is None:
            return {'FII': 'Neutral', 'DII': 'Neutral'}
            
        fii_avg = self.flow_data['FII_Net'].rolling(window).mean().iloc[-1]
        dii_avg = self.flow_data['DII_Net'].rolling(window).mean().iloc[-1]
        
        fii_trend = "Buying" if fii_avg > 0 else "Selling"
        dii_trend = "Buying" if dii_avg > 0 else "Selling"
        
        return {'FII': fii_trend, 'DII': dii_trend}
        
    def liquidity_score(self) -> int:
        """
        Composite score (0-100) of market liquidity conditions.
        High score = Easy money, supports higher valuations.
        """
        if self.flow_data is None:
            return 50
            
        score = 50
        
        # FII Flows (last 5 days net)
        recent_fii = self.flow_data['FII_Net'].tail(5).sum()
        if recent_fii > 5000: score += 20
        elif recent_fii > 0: score += 10
        elif recent_fii < -5000: score -= 20
        elif recent_fii < 0: score -= 10
        
        # DII Flows (counter balance)
        recent_dii = self.flow_data['DII_Net'].tail(5).sum()
        if recent_dii > 5000: score += 15 # DIIs buying supports market
        
        # SIP Inflows (steady money)
        avg_sip = self.flow_data['SIP_Inflow'].mean()
        if avg_sip > 15000: score += 15 # Record inflows
        
        return max(0, min(100, score))
        
    def bulk_deal_heatmap(self, deals_df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyzes bulk deals to spot institutional interest.
        """
        if deals_df.empty:
            return pd.DataFrame()
            
        # Group by stock and buyer/seller type
        heatmap = deals_df.groupby(['Stock', 'Client_Type'])['Value'].sum().unstack(fill_value=0)
        heatmap['Net_Institutional'] = heatmap.get('FII', 0) + heatmap.get('DII', 0) - heatmap.get('Promoter', 0)
        
        return heatmap.sort_values('Net_Institutional', ascending=False)

def analyze_macro_liquidity(index_df: pd.DataFrame, flow_df: pd.DataFrame) -> Dict:
    macro = MacroRegimeDetector()
    liq = LiquidityFlowAnalyzer().load_flow_data(flow_df)
    
    return {
        'regime': macro.detect_regime(index_df),
        'fii_trend': liq.calculate_flow_trend()['FII'],
        'liquidity_score': liq.liquidity_score(),
        'recommendation': 'Overweight Equities' if liq.liquidity_score() > 70 else 'Neutral'
    }
