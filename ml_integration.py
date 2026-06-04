"""
Machine Learning Integration Module
Implements feedback loop for strategy optimization
"""

import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error
import pickle
import os
from trade_logger import TradeLogger
from config import *

logger = logging.getLogger(__name__)


class MLIntegration:
    """Machine learning integration for strategy optimization"""
    
    def __init__(self, trade_logger: TradeLogger = None, model_dir: str = None):
        self.trade_logger = trade_logger or TradeLogger()
        
        if model_dir is None:
            model_dir = os.path.join(os.path.dirname(__file__), "models")
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Model files
        self.signal_classifier_path = os.path.join(self.model_dir, "signal_classifier.pkl")
        self.profit_regressor_path = os.path.join(self.model_dir, "profit_regressor.pkl")
        self.scaler_path = os.path.join(self.model_dir, "feature_scaler.pkl")
        
        # Models
        self.signal_classifier = None
        self.profit_regressor = None
        self.feature_scaler = None
        
        # Feature names
        self.feature_names = [
            'confidence', 'rsi', 'macd', 'bb_position', 'atr_normalized',
            'volume_ratio', 'price_vs_sma20', 'price_vs_sma50', 'hour_of_day',
            'day_of_week', 'session', 'volatility_regime', 'trend_alignment',
            'signal_ml_confidence'
        ]
        
        # Load existing models if available
        self._load_models()
        
        logger.info("ML Integration initialized")
    
    def _load_models(self) -> None:
        """Load pre-trained models if they exist"""
        try:
            if os.path.exists(self.signal_classifier_path):
                with open(self.signal_classifier_path, 'rb') as f:
                    self.signal_classifier = pickle.load(f)
                logger.info("Loaded signal classifier model")
            
            if os.path.exists(self.profit_regressor_path):
                with open(self.profit_regressor_path, 'rb') as f:
                    self.profit_regressor = pickle.load(f)
                logger.info("Loaded profit regressor model")
            
            if os.path.exists(self.scaler_path):
                with open(self.scaler_path, 'rb') as f:
                    self.feature_scaler = pickle.load(f)
                logger.info("Loaded feature scaler")
                
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            self.signal_classifier = None
            self.profit_regressor = None
            self.feature_scaler = None
    
    def _save_models(self) -> None:
        """Save trained models to disk"""
        try:
            if self.signal_classifier is not None:
                with open(self.signal_classifier_path, 'wb') as f:
                    pickle.dump(self.signal_classifier, f)
                logger.info("Saved signal classifier model")
            
            if self.profit_regressor is not None:
                with open(self.profit_regressor_path, 'wb') as f:
                    pickle.dump(self.profit_regressor, f)
                logger.info("Saved profit regressor model")
            
            if self.feature_scaler is not None:
                with open(self.scaler_path, 'wb') as f:
                    pickle.dump(self.feature_scaler, f)
                logger.info("Saved feature scaler")
                
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def extract_features(self, signal: Dict[str, Any], market_data: Dict[str, Any] = None) -> np.ndarray:
        """Extract features for ML model from signal and market data"""
        try:
            features = []
            
            # Basic signal features
            features.append(signal.get('confidence', 50) / 100.0)  # Normalize to 0-1
            
            # Market data features (if available)
            if market_data:
                # These would be calculated from actual market data
                # For now, we'll use placeholder values or calculate from available data
                rsi = market_data.get('rsi', 50.0) / 100.0  # Normalize
                macd = market_data.get('macd', 0.0)  # Would need normalization
                bb_position = market_data.get('bb_position', 0.5)  # 0-1 range
                atr_normalized = market_data.get('atr_normalized', 0.01)  # Already normalized-ish
                volume_ratio = market_data.get('volume_ratio', 1.0)
                price_vs_sma20 = market_data.get('price_vs_sma20', 0.0)  # Percentage difference
                price_vs_sma50 = market_data.get('price_vs_sma50', 0.0)
                hour_of_day = market_data.get('hour_of_day', 12) / 24.0  # Normalize
                day_of_week = market_data.get('day_of_week', 3) / 7.0  # Normalize (0-6)
                session = market_data.get('session', 0.5)  # 0-1 encoded
                volatility_regime = market_data.get('volatility_regime', 0.5)  # 0-1
                trend_alignment = market_data.get('trend_alignment', 0.5)  # 0-1
                ml_confidence = signal.get('ml_confidence', 0.0) / 100.0  # Normalize
                
                features.extend([
                    rsi, macd, bb_position, atr_normalized, volume_ratio,
                    price_vs_sma20, price_vs_sma50, hour_of_day, day_of_week,
                    session, volatility_regime, trend_alignment, ml_confidence
                ])
            else:
                # Use default values if no market data
                features.extend([0.5, 0.0, 0.5, 0.01, 1.0, 0.0, 0.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.0])
            
            return np.array(features).reshape(1, -1)
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            # Return default feature vector
            return np.array([0.5] * len(self.feature_names)).reshape(1, -1)
    
    def predict_signal_success(self, signal: Dict[str, Any], market_data: Dict[str, Any] = None) -> float:
        """Predict the probability of signal success"""
        try:
            if self.signal_classifier is None or self.feature_scaler is None:
                # Return base confidence if no model available
                return signal.get('confidence', 50) / 100.0
            
            # Extract features
            features = self.extract_features(signal, market_data)
            
            # Scale features
            features_scaled = self.feature_scaler.transform(features)
            
            # Get probability prediction
            probabilities = self.signal_classifier.predict_proba(features_scaled)
            # Probability of class 1 (success)
            success_probability = probabilities[0][1] if len(probabilities[0]) > 1 else 0.5
            
            return success_probability
            
        except Exception as e:
            logger.error(f"Error predicting signal success: {e}")
            return signal.get('confidence', 50) / 100.0
    
    def predict_expected_profit(self, signal: Dict[str, Any], market_data: Dict[str, Any] = None) -> float:
        """Predict expected profit/loss for a signal"""
        try:
            if self.profit_regressor is None or self.feature_scaler is None:
                # Return 0 if no model available
                return 0.0
            
            # Extract features
            features = self.extract_features(signal, market_data)
            
            # Scale features
            features_scaled = self.feature_scaler.transform(features)
            
            # Get prediction
            predicted_profit = self.profit_regressor.predict(features_scaled)[0]
            
            return predicted_profit
            
        except Exception as e:
            logger.error(f"Error predicting expected profit: {e}")
            return 0.0
    
    def train_models(self) -> Dict[str, Any]:
        """Train ML models using historical trade data"""
        try:
            # Get training data from trade logger
            trades = self.trade_logger.get_closed_trades(limit=5000)  # Get sufficient data
            
            if len(trades) < 50:
                return {"success": False, "reason": "Insufficient training data"}
            
            # Prepare features and labels
            features_list = []
            success_labels = []  # 1 for winning trade, 0 for losing
            profit_labels = []   # Actual P&L for regression
            
            for trade in trades:
                try:
                    # Create a mock signal from trade data
                    signal = {
                        'confidence': trade.get('confidence', 50),
                        'ml_confidence': trade.get('ml_confidence', 0.0),
                        'action': 'BUY' if trade.get('side') == 'buy' else 'SELL'
                    }
                    
                    # Create mock market data (in practice, we'd reconstruct this)
                    market_data = {
                        'rsi': trade.get('rsi', 50.0),
                        'macd': trade.get('macd', 0.0),
                        'bb_position': trade.get('bb_position', 0.5),
                        'atr_normalized': trade.get('atr_normalized', 0.01),
                        'volume_ratio': trade.get('volume_ratio', 1.0),
                        'price_vs_sma20': trade.get('price_vs_sma20', 0.0),
                        'price_vs_sma50': trade.get('price_vs_sma50', 0.0),
                        'hour_of_day': trade.get('hour_of_day', 12),
                        'day_of_week': trade.get('day_of_week', 3),
                        'session': trade.get('session', 0.5),
                        'volatility_regime': trade.get('volatility_regime', 0.5),
                        'trend_alignment': trade.get('trend_alignment', 0.5)
                    }
                    
                    # Extract features
                    features = self.extract_features(signal, market_data)
                    features_list.append(features.flatten())
                    
                    # Labels
                    pnl = trade.get('pnl', 0.0)
                    success_labels.append(1 if pnl > 0 else 0)
                    profit_labels.append(pnl)
                    
                except Exception as e:
                    self.logger.error(f"Error processing trade for training: {e}")
                    continue
            
            if len(features_list) < 20:
                return {"success": False, "reason": "Insufficient valid training samples"}
            
            # Convert to numpy arrays
            X = np.array(features_list)
            y_success = np.array(success_labels)
            y_profit = np.array(profit_labels)
            
            # Split data
            X_train, X_test, y_success_train, y_success_test, y_profit_train, y_profit_test = train_test_split(
                X, y_success, y_profit, test_size=0.2, random_state=42
            )
            
            # Scale features
            self.feature_scaler = StandardScaler()
            X_train_scaled = self.feature_scaler.fit_transform(X_train)
            X_test_scaled = self.feature_scaler.transform(X_test)
            
            # Train signal classifier (predict win/loss)
            self.signal_classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            self.signal_classifier.fit(X_train_scaled, y_success_train)
            
            # Train profit regressor (predict P&L magnitude)
            self.profit_regressor = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            self.profit_regressor.fit(X_train_scaled, y_profit_train)
            
            # Evaluate models
            success_pred = self.signal_classifier.predict(X_test_scaled)
            success_accuracy = accuracy_score(y_success_test, success_pred)
            
            profit_pred = self.profit_regressor.predict(X_test_scaled)
            profit_mse = mean_squared_error(y_profit_test, profit_pred)
            
            # Save models
            self._save_models()
            
            # Feature importance
            signal_importance = dict(zip(self.feature_names, self.signal_classifier.feature_importances_))
            profit_importance = dict(zip(self.feature_names, self.profit_regressor.feature_importances_))
            
            result = {
                "success": True,
                "samples_used": len(features_list),
                "signal_accuracy": round(success_accuracy, 3),
                "profit_mse": round(profit_mse, 3),
                "signal_feature_importance": signal_importance,
                "profit_feature_importance": profit_importance,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Models trained successfully: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error training ML models: {e}")
            return {"success": False, "error": str(e)}
    
    def enhance_signal(self, signal: Dict[str, Any], market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhance a signal with ML predictions"""
        try:
            enhanced_signal = signal.copy()
            
            # Get ML predictions
            ml_success_prob = self.predict_signal_success(signal, market_data)
            ml_expected_profit = self.predict_expected_profit(signal, market_data)
            
            # Calculate enhanced confidence
            base_confidence = signal.get('confidence', 50) / 100.0
            # Weighted average: 70% base confidence, 30% ML prediction
            enhanced_confidence = (base_confidence * 0.7) + (ml_success_prob * 0.3)
            enhanced_confidence = max(0.0, min(1.0, enhanced_confidence)) * 100  # Back to percentage
            
            # Add ML insights
            enhanced_signal['ml_confidence'] = round(ml_success_prob * 100, 1)
            enhanced_signal['ml_expected_profit'] = round(ml_expected_profit, 2)
            enhanced_signal['original_confidence'] = signal.get('confidence', 50)
            enhanced_signal['enhanced_confidence'] = round(enhanced_confidence, 1)
            
            # Adjust reasoning to include ML insights
            ml_reason = f"ML Enhancement: Success probability {ml_success_prob:.1%}, Expected P&L: {ml_expected_profit:.2f}"
            original_reason = signal.get('reason', '')
            if original_reason:
                enhanced_signal['reason'] = f"{original_reason}. {ml_reason}"
            else:
                enhanced_signal['reason'] = ml_reason
            
            return enhanced_signal
            
        except Exception as e:
            logger.error(f"Error enhancing signal: {e}")
            return signal  # Return original signal on error