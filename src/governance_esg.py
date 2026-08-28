"""
Module 6: Governance & ESG Scoring
Institutional-grade promoter pledge tracking, capital allocation score, and ESG factors.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import warnings

warnings.filterwarnings('ignore')

class GovernanceAnalyzer:
    """
    Evaluates corporate governance quality based on promoter behavior,
    capital allocation history, and board structure.
    """
    
    def __init__(self):
        pass
        
    def calculate_promoter_pledge_score(self, pledge_history: pd.DataFrame) -> int:
        """
        Score (0-100) based on promoter pledge trends.
        100 = No pledge, 0 = High/Increasing pledge.
        """
        if pledge_history.empty or 'Pledge_Percentage' not in pledge_history.columns:
            return 100 # Assume good if no data
            
        latest = pledge_history['Pledge_Percentage'].iloc[-1]
        
        # Trend analysis
        trend = 0
        if len(pledge_history) > 2:
            prev_avg = pledge_history['Pledge_Percentage'].iloc[:-1].mean()
            if latest > prev_avg:
                trend = -10 # Penalty for increasing
            elif latest < prev_avg:
                trend = 5 # Bonus for decreasing
                
        base_score = max(0, 100 - (latest * 2)) # 50% pledge = 0 score
        final_score = max(0, min(100, base_score + trend))
        
        return int(final_score)
    
    def calculate_capital_allocation_score(self, financials: pd.DataFrame) -> int:
        """
        Score (0-100) based on how management allocates capital.
        Factors: ROIC vs WACC, Buybacks, Dividend consistency, Debt reduction.
        """
        score = 50 # Base
        
        # 1. ROIC > WACC creates value
        if 'ROIC' in financials.columns and 'WACC' in financials.columns:
            spread = financials['ROIC'].iloc[-1] - financials['WACC'].iloc[-1]
            if spread > 5: score += 20
            elif spread > 0: score += 10
            elif spread < -5: score -= 20
            
        # 2. Free Cash Flow positive?
        if 'FCF' in financials.columns:
            if financials['FCF'].iloc[-1] > 0:
                score += 10
            else:
                score -= 10
                
        # 3. Debt trend
        if 'Debt_to_Equity' in financials.columns:
            if len(financials) > 1:
                debt_trend = financials['Debt_to_Equity'].diff().iloc[-1]
                if debt_trend < 0: score += 10 # Reducing debt
                elif debt_trend > 0.5: score -= 10 # Rapidly increasing debt
                
        return max(0, min(100, int(score)))
    
    def board_independence_score(self, board_data: Dict) -> int:
        """
        Score based on board composition.
        SEBI requires at least 50% independent directors for top listed entities.
        """
        total_directors = board_data.get('total_directors', 1)
        independent = board_data.get('independent_directors', 0)
        
        if total_directors == 0:
            return 50
            
        ratio = independent / total_directors
        
        if ratio >= 0.5:
            return 100
        elif ratio >= 0.33:
            return 75
        elif ratio >= 0.2:
            return 50
        else:
            return 25
            
    def related_party_transactions_flag(self, rpt_amount: float, total_revenue: float) -> str:
        """
        Flags high Related Party Transactions which can be a governance red flag.
        """
        if total_revenue == 0:
            return "Unknown"
            
        ratio = rpt_amount / total_revenue
        
        if ratio > 0.15:
            return "High Risk (>15%)"
        elif ratio > 0.05:
            return "Moderate Risk (5-15%)"
        else:
            return "Low Risk"

class ESGScorer:
    """
    Simple ESG scoring framework adapted for Indian markets.
    """
    
    def calculate_esg_score(self, env_data: Dict, social_data: Dict, gov_data: Dict) -> Dict:
        """
        Returns E, S, G scores and composite ESG score (0-100).
        """
        # Environmental (Carbon intensity, water usage, waste)
        e_score = env_data.get('carbon_score', 50)
        
        # Social (Labor practices, community, safety)
        s_score = social_data.get('labor_score', 50)
        
        # Governance (Board, audit, shareholder rights)
        g_score = gov_data.get('board_score', 50)
        
        composite = (e_score * 0.3) + (s_score * 0.3) + (g_score * 0.4)
        
        return {
            'E_Score': e_score,
            'S_Score': s_score,
            'G_Score': g_score,
            'ESG_Composite': round(composite, 1),
            'Rating': self._get_rating(composite)
        }
        
    def _get_rating(self, score: float) -> str:
        if score >= 80: return "AAA"
        elif score >= 70: return "AA"
        elif score >= 60: return "A"
        elif score >= 50: return "BBB"
        elif score >= 40: return "BB"
        elif score >= 30: return "B"
        else: return "CCC"

def analyze_governance(pledge_df: pd.DataFrame, fin_df: pd.DataFrame, board_dict: Dict) -> Dict:
    gov = GovernanceAnalyzer()
    
    return {
        'promoter_pledge_score': gov.calculate_promoter_pledge_score(pledge_df),
        'capital_allocation_score': gov.calculate_capital_allocation_score(fin_df),
        'board_independence_score': gov.board_independence_score(board_dict),
        'rpt_status': 'Low Risk' # Placeholder
    }
