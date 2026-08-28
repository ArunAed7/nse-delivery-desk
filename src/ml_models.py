"""
Module 9: Machine Learning Models
Institutional-grade return prediction, NLP sentiment, and regime classification.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings('ignore')

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import TimeSeriesSplit
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

class ReturnPredictor:
    """
    Uses tree-based models to predict next-day/next-week returns.
    Features: Technical indicators, Fundamentals, Sentiment.
    """
    
    def __init__(self):
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required for ML models")
        self.model = GradientBoostingRegressor(n_estimators=100, max_depth=4)
        self.scaler = StandardScaler()
        self.is_fitted = False
        
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Feature engineering for return prediction.
        """
        feat = df.copy()
        
        # Lagged Returns
        for lag in [1, 2, 3, 5, 10]:
            feat[f'Ret_Lag{lag}'] = feat['Close'].pct_change(lag)
            
        # Moving Averages
        feat['MA_Ratio'] = feat['Close'] / feat['Close'].rolling(20).mean()
        feat['Vol_Ratio'] = feat['Volume'] / feat['Volume'].rolling(20).mean()
        
        # Volatility
        feat['Volatility'] = feat['Close'].pct_change().rolling(20).std()
        
        # RSI
        delta = feat['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        feat['RSI'] = 100 - (100 / (1 + rs))
        
        feat = feat.dropna()
        return feat
    
    def fit(self, X: pd.DataFrame, y: pd.Series):
        """Train the model."""
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict returns."""
        if not self.is_fitted:
            raise ValueError("Model not fitted yet")
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

class SentimentAnalyzer:
    """
    Simple rule-based sentiment scoring (FinBERT placeholder).
    In production, replace with HuggingFace FinBERT model.
    """
    
    def __init__(self):
        # Positive/Negative word lists for basic scoring
        self.positive_words = ['beat', 'growth', 'profit', 'upgrade', 'bullish', 'outperform', 'record', 'strong']
        self.negative_words = ['miss', 'loss', 'downgrade', 'bearish', 'underperform', 'weak', 'risk', 'fall']
        
    def score_text(self, text: str) -> float:
        """
        Returns sentiment score (-1 to 1).
        """
        text_lower = text.lower()
        words = text_lower.split()
        
        pos_count = sum(1 for w in words if w in self.positive_words)
        neg_count = sum(1 for w in words if w in self.negative_words)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
            
        score = (pos_count - neg_count) / total
        return round(score, 2)
    
    def analyze_news_batch(self, news_df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze sentiment for a batch of news headlines.
        """
        news_df['Sentiment_Score'] = news_df['Headline'].apply(self.score_text)
        news_df['Sentiment_Label'] = pd.cut(
            news_df['Sentiment_Score'], 
            bins=[-1, -0.2, 0.2, 1], 
            labels=['Negative', 'Neutral', 'Positive']
        )
        return news_df

class RegimeClassifier:
    """
    Hidden Markov Model-like regime detection using GMM or simple clustering.
    Classifies market into High Vol/Low Vol, Bull/Bear states.
    """
    
    def __init__(self, n_regimes: int = 3):
        self.n_regimes = n_regimes
        self.centers = None
        
    def fit_predict(self, returns: pd.Series, volatility: pd.Series) -> pd.Series:
        """
        Simple K-Means like regime assignment.
        State 0: Low Vol Bull
        State 1: High Vol Sideways
        State 2: Low Vol Bear
        """
        df = pd.DataFrame({'ret': returns, 'vol': volatility}).dropna()
        
        # Normalize
        df['ret_z'] = (df['ret'] - df['ret'].mean()) / df['ret'].std()
        df['vol_z'] = (df['vol'] - df['vol'].mean()) / df['vol'].std()
        
        # Simple rule-based clustering (replace with KMeans/GMM in prod)
        def assign_regime(row):
            if row['vol_z'] > 1:
                return 1 # High Vol
            elif row['ret_z'] > 0.5:
                return 0 # Bull
            else:
                return 2 # Bear
                
        df['regime'] = df.apply(assign_regime, axis=1)
        return df['regime']

def run_ml_pipeline(price_df: pd.DataFrame) -> Dict:
    if not SKLEARN_AVAILABLE:
        return {'error': 'scikit-learn not installed'}
        
    # Prepare data
    pred_model = ReturnPredictor()
    feat_df = pred_model.create_features(price_df)
    
    X = feat_df[['Ret_Lag1', 'Ret_Lag2', 'MA_Ratio', 'Vol_Ratio', 'RSI', 'Volatility']]
    y = feat_df['Close'].pct_change().shift(-1) # Next day return
    
    X = X.dropna()
    y = y.dropna()
    
    # Align
    min_len = min(len(X), len(y))
    X = X.iloc[-min_len:]
    y = y.iloc[-min_len:]
    
    # Train/Test split (simple)
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    
    # Fit
    pred_model.fit(X_train, y_train)
    preds = pred_model.predict(X_test)
    
    # Simple accuracy metric (directional)
    actual_dir = np.sign(y_test.values)
    pred_dir = np.sign(preds)
    accuracy = (actual_dir == pred_dir).sum() / len(actual_dir)
    
    return {
        'model_accuracy': round(accuracy * 100, 2),
        'feature_importance': dict(zip(X.columns, pred_model.model.feature_importances_)),
        'latest_prediction': preds[-1] if len(preds) > 0 else 0
    }
