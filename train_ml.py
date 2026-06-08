"""
Generate synthetic training data for ML models
"""

import numpy as np
import pandas as pd
import os
import pickle
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error
from datetime import datetime, timezone

def generate_synthetic_trades(n=200):
    """Generate synthetic trade data for training ML models"""
    trades = []
    
    for i in range(n):
        # Generate realistic feature values
        confidence = np.random.uniform(30, 100)  # Base signal confidence
        rsi = np.random.uniform(10, 90)
        macd = np.random.uniform(-0.05, 0.05)
        bb_position = np.random.uniform(0, 1)  # Position within BBands
        atr_normalized = np.random.uniform(0.001, 0.05)
        volume_ratio = np.random.uniform(0.5, 2.0)
        price_vs_sma20 = np.random.uniform(-0.03, 0.03)
        price_vs_sma50 = np.random.uniform(-0.05, 0.05)
        hour_of_day = np.random.randint(0, 24)
        day_of_week = np.random.randint(0, 7)
        session = np.random.choice([0.0, 0.5, 1.0])  # Asian/European/London-NY
        volatility_regime = np.random.choice([0.0, 1.0])  # low/high
        trend_alignment = np.random.choice([0.0, 1.0])  # no/yes
        
        # Create trade outcome based on features (realistic logic)
        # Higher confidence + trend alignment + good RSI = better outcome
        score = (
            (confidence / 100) * 0.3 +
            (trend_alignment * 0.25) +
            ((rsi > 30 and rsi < 70) * 0.2) +  # RSI not overbought/oversold
            ((price_vs_sma20 * price_vs_sma50 > 0) * 0.15) +  # Price and SMA aligned
            (np.random.uniform(0, 1) * 0.1)  # Some randomness
        )
        
        win = score > 0.5
        pnl = np.random.uniform(50, 500) if win else -np.random.uniform(50, 500)
        
        trades.append({
            'confidence': confidence,
            'rsi': rsi,
            'macd': macd,
            'bb_position': bb_position,
            'atr_normalized': atr_normalized,
            'volume_ratio': volume_ratio,
            'price_vs_sma20': price_vs_sma20,
            'price_vs_sma50': price_vs_sma50,
            'hour_of_day': hour_of_day,
            'day_of_week': day_of_week,
            'session': session,
            'volatility_regime': volatility_regime,
            'trend_alignment': trend_alignment,
            'pnl': pnl,
            'signal_ml_confidence': confidence
        })
    
    return trades


def train_initial_models():
    """Train and save initial ML models"""
    trades = generate_synthetic_trades(500)
    
    feature_names = [
        'confidence', 'rsi', 'macd', 'bb_position', 'atr_normalized',
        'volume_ratio', 'price_vs_sma20', 'price_vs_sma50', 'hour_of_day',
        'day_of_week', 'session', 'volatility_regime', 'trend_alignment', 'signal_ml_confidence'
    ]
    
    # Prepare features
    X = []
    y_success = []
    y_profit = []
    
    for trade in trades:
        features = [
            trade['confidence'] / 100.0,
            trade['rsi'] / 100.0,
            (trade['macd'] + 0.05) / 0.1,  # Normalize
            trade['bb_position'],
            trade['atr_normalized'] / 0.05,
            trade['volume_ratio'] / 2.0,
            (trade['price_vs_sma20'] + 0.03) / 0.06,
            (trade['price_vs_sma50'] + 0.05) / 0.1,
            trade['hour_of_day'] / 24.0,
            trade['day_of_week'] / 7.0,
            trade['session'],
            trade['volatility_regime'],
            trade['trend_alignment'],
            trade['signal_ml_confidence'] / 100.0
        ]
        X.append(features)
        y_success.append(1 if trade['pnl'] > 0 else 0)
        y_profit.append(trade['pnl'])
    
    X = np.array(X)
    y_success = np.array(y_success)
    y_profit = np.array(y_profit)
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train models
    classifier = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    classifier.fit(X_scaled, y_success)
    
    regressor = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    regressor.fit(X_scaled, y_profit)
    
    # Create models directory
    model_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(model_dir, exist_ok=True)
    
    # Save models
    with open(os.path.join(model_dir, "signal_classifier.pkl"), 'wb') as f:
        pickle.dump(classifier, f)
    
    with open(os.path.join(model_dir, "profit_regressor.pkl"), 'wb') as f:
        pickle.dump(regressor, f)
    
    with open(os.path.join(model_dir, "feature_scaler.pkl"), 'wb') as f:
        pickle.dump(scaler, f)
    
    # Evaluate
    y_pred = classifier.predict(X_scaled)
    acc = accuracy_score(y_success, y_pred)
    profit_pred = regressor.predict(X_scaled)
    mse = mean_squared_error(y_profit, profit_pred)
    
    print(f"Models trained and saved to {model_dir}")
    print(f"Signal classifier accuracy: {acc:.3f}")
    print(f"Profit regressor MSE: {mse:.2f}")
    print(f"Trades generated: {len(trades)}")
    print(f"Feature importance: {dict(zip(feature_names, classifier.feature_importances_))}")
    
    return {
        "success": True,
        "signal_accuracy": acc,
        "profit_mse": mse,
        "trades_generated": len(trades),
        "feature_importance": dict(zip(feature_names, classifier.feature_importances_.tolist()))
    }


if __name__ == "__main__":
    train_initial_models()