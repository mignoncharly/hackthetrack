 
"""
Configuration settings for GR Cup CLI API
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Model paths
MODELS_DIR = BASE_DIR / "models"
MODEL_FOCUS_DROP = MODELS_DIR / "focus_drop_classifier.pkl"
MODEL_FOCUS_REGRESSOR = MODELS_DIR / "focus_score_regressor.pkl"
MODEL_ANOMALY = MODELS_DIR / "anomaly_detector.pkl"
MODEL_SHAP = MODELS_DIR / "shap_explainer.pkl"

# Data paths
DATA_DIR = BASE_DIR / "processed_data"
DATASET_PATH = DATA_DIR / "cli_complete_dataset_with_predictions.csv"

# API settings
API_VERSION = "v1"
API_TITLE = "GR Cup CLI API"
API_DESCRIPTION = """
🏎️ **Driver Cognitive Load Index (CLI) API**

Real-time monitoring and prediction system for driver focus and performance.

## Features:
- 🎯 Real-time CLI scoring
- 📊 Focus drop prediction
- 🔍 SHAP explainability
- 🚨 Rule-based alerts
- 📈 Historical analysis
"""

# Feature columns (must match training)
FEATURE_COLS = [
    'ThrottleJerk_1s_mean', 'ThrottleJerk_1s_std', 'ThrottleJerk_1s_max',
    'BrakeSpikeRate_5s_mean', 'BrakeSpikeRate_5s_max', 'BrakeSpikeRate_5s_sum',
    'SteerEntropy_10s_mean', 'SteerEntropy_10s_max',
    'MicroVariability_mean', 'MicroVariability_std',
    'ath_mean', 'ath_std',
    'speed_mean', 'speed_std',
    'pbrake_f_mean', 'pbrake_f_max',
    'Steering_Angle_mean', 'Steering_Angle_std',
    'accx_can_mean', 'accx_can_std',
    'accy_can_mean', 'accy_can_std',
    'CLI_raw', 'FocusScore_smooth',
    'lap', 'AIR_TEMP', 'TRACK_TEMP'
]

# Alert thresholds
ALERT_THRESHOLDS = {
    'focus_drop_prob': 0.7,      # 70% probability
    'focus_score_critical': 20,   # Below 20/100
    'brake_spike_high': 3.0,      # >3 spike events/5s
    'steer_entropy_high': 1.8     # High steering indecision
}
