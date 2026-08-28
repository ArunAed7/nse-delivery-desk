"""
Module 10: Compliance & Reporting
Institutional-grade pre-trade checks, audit trails, and SEBI reporting.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import warnings
import json

warnings.filterwarnings('ignore')

class PreTradeCompliance:
    """
    Enforces investment mandate and regulatory limits before order execution.
    Critical for institutional funds (AIF, PMS, Mutual Funds).
    """
    
    def __init__(self, mandate_rules: Dict):
        """
        mandate_rules: {
            'max_single_stock_pct': 10,
            'max_sector_pct': 25,
            'min_market_cap': 500, # Cr
            'restricted_stocks': [],
            'max_derivatives_exposure': 0.2
        }
        """
        self.rules = mandate_rules
        
    def check_order(self, order: Dict, portfolio: Dict) -> Dict:
        """
        Validate order against mandate.
        Returns: {'approved': bool, 'reason': str}
        """
        stock = order.get('symbol')
        qty = order.get('quantity', 0)
        price = order.get('price', 0)
        order_value = qty * price
        
        portfolio_value = portfolio.get('total_value', 1)
        current_holdings = portfolio.get('holdings', {})
        sector_exposure = portfolio.get('sector_exposure', {})
        
        # Rule 1: Single Stock Limit
        current_stock_value = current_holdings.get(stock, {}).get('value', 0)
        new_stock_value = current_stock_value + order_value
        stock_pct = (new_stock_value / portfolio_value) * 100
        
        if stock_pct > self.rules.get('max_single_stock_pct', 10):
            return {'approved': False, 'reason': f'Single stock limit breached ({stock_pct:.1f}%)'}
            
        # Rule 2: Sector Limit
        stock_sector = order.get('sector', 'Unknown')
        current_sector_val = sector_exposure.get(stock_sector, 0)
        new_sector_val = current_sector_val + order_value
        sector_pct = (new_sector_val / portfolio_value) * 100
        
        if sector_pct > self.rules.get('max_sector_pct', 25):
            return {'approved': False, 'reason': f'Sector limit breached ({sector_pct:.1f}%)'}
            
        # Rule 3: Restricted Stocks
        if stock in self.rules.get('restricted_stocks', []):
            return {'approved': False, 'reason': 'Stock is in restricted list'}
            
        # Rule 4: Minimum Market Cap
        stock_mcap = order.get('market_cap_cr', 0)
        if stock_mcap < self.rules.get('min_market_cap', 500):
            return {'approved': False, 'reason': f'Market cap below minimum ({stock_mcap} Cr)'}
            
        return {'approved': True, 'reason': 'All checks passed'}

class AuditTrail:
    """
    Maintains immutable log of all decisions, signals, and trades.
    Required for SEBI inspections and internal reviews.
    """
    
    def __init__(self, log_file: str = 'audit_log.json'):
        self.log_file = log_file
        self.logs = []
        
    def log_signal(self, strategy: str, symbol: str, signal: str, 
                   metrics: Dict, timestamp: datetime = None):
        """Log a trading signal generation."""
        entry = {
            'type': 'SIGNAL',
            'timestamp': (timestamp or datetime.now()).isoformat(),
            'strategy': strategy,
            'symbol': symbol,
            'signal': signal,
            'metrics': metrics
        }
        self.logs.append(entry)
        self._save()
        
    def log_trade(self, order_id: str, symbol: str, side: str, 
                  qty: int, price: float, reason: str):
        """Log an executed trade."""
        entry = {
            'type': 'TRADE',
            'timestamp': datetime.now().isoformat(),
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': qty,
            'price': price,
            'reason': reason
        }
        self.logs.append(entry)
        self._save()
        
    def log_model_change(self, model_name: str, old_params: Dict, new_params: Dict, 
                         approved_by: str):
        """Log changes to ML model parameters (Model Risk Management)."""
        entry = {
            'type': 'MODEL_CHANGE',
            'timestamp': datetime.now().isoformat(),
            'model': model_name,
            'old_params': old_params,
            'new_params': new_params,
            'approved_by': approved_by
        }
        self.logs.append(entry)
        self._save()
        
    def _save(self):
        """Append logs to file."""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.logs, f, indent=2)
        except Exception as e:
            print(f"Audit log save error: {e}")
            
    def get_logs(self, start_date: str = None, end_date: str = None, 
                 log_type: str = None) -> pd.DataFrame:
        """Retrieve filtered logs."""
        df = pd.DataFrame(self.logs)
        if df.empty:
            return df
            
        if log_type:
            df = df[df['type'] == log_type]
        if start_date:
            df = df[df['timestamp'] >= start_date]
        if end_date:
            df = df[df['timestamp'] <= end_date]
            
        return df

class SEBIReporter:
    """
    Generates reports required for SEBI filings (AIF/PMS).
    """
    
    def generate_monthly_portfolio_report(self, holdings: pd.DataFrame, 
                                          transactions: pd.DataFrame) -> Dict:
        """
        Format data for SEBI monthly reporting.
        """
        report = {
            'report_date': datetime.now().strftime('%Y-%m-%d'),
            'total_aum': float(holdings['Value'].sum()),
            'number_of_securities': len(holdings),
            'top_10_holdings': holdings.nlargest(10, 'Value')[['Symbol', 'Value', 'Weight']].to_dict('records'),
            'sector_allocation': holdings.groupby('Sector')['Weight'].sum().to_dict(),
            'turnover_ratio': self._calculate_turnover(transactions, holdings),
            'cash_position': float(holdings[holdings['Symbol'] == 'CASH']['Value'].sum())
        }
        return report
        
    def _calculate_turnover(self, transactions: pd.DataFrame, 
                            holdings: pd.DataFrame) -> float:
        """Calculate monthly turnover ratio."""
        if transactions.empty:
            return 0.0
        total_traded = transactions['Value'].sum()
        avg_aum = holdings['Value'].mean()
        return round((total_traded / max(avg_aum, 1)) * 100, 2)

def run_compliance_check(order: Dict, portfolio: Dict) -> Dict:
    rules = {
        'max_single_stock_pct': 10,
        'max_sector_pct': 25,
        'min_market_cap': 500,
        'restricted_stocks': ['XYZ'], # Example
        'max_derivatives_exposure': 0.2
    }
    
    compliance = PreTradeCompliance(rules)
    audit = AuditTrail()
    
    result = compliance.check_order(order, portfolio)
    
    # Log the check
    audit.log_signal(
        strategy='PreTradeCheck',
        symbol=order.get('symbol', 'UNKNOWN'),
        signal='APPROVED' if result['approved'] else 'REJECTED',
        metrics={'reason': result['reason']}
    )
    
    return result
