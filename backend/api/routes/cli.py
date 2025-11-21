# backend/api/routes/cli.py

"""
CLI API Routes - Main endpoints for CLI scoring and monitoring
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
import pickle
import pandas as pd
import numpy as np
import json
from pathlib import Path
import logging

from backend.api.models.schemas import (
    LapData, CLIScoreResponse, PredictionResponse, 
    ExplanationResponse, DriverHistoryResponse
)
from backend.core.scoring_engine import CLIScoringEngine
from backend.core.rule_engine import RuleEngine
from backend.core.config import (
    MODEL_FOCUS_DROP, MODEL_FOCUS_REGRESSOR, MODEL_ANOMALY,
    FEATURE_COLS, DATASET_PATH
)

# Setup logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cli", tags=["CLI"])

# Load driver baselines
DRIVER_BASELINES = {}
try:
    baseline_path = Path("processed_data/driver_baselines.json")
    if baseline_path.exists():
        with open(baseline_path, 'r') as f:
            DRIVER_BASELINES = json.load(f)
        logger.info(f"✅ Loaded baselines for {len(DRIVER_BASELINES)} drivers")
        print(f"✅ Loaded baselines for {len(DRIVER_BASELINES)} drivers")
    else:
        logger.warning("⚠️ Driver baselines not found - personalization disabled")
        print("⚠️ Driver baselines not found - personalization disabled")
except Exception as e:
    logger.error(f"Error loading baselines: {e}")
    print(f"⚠️ Error loading baselines: {e}")

# Load models at startup (singleton pattern)
_models = {}
_engines = {}

def get_models():
    """Load models once and cache"""
    if not _models:
        with open(MODEL_FOCUS_DROP, 'rb') as f:
            _models['focus_drop'] = pickle.load(f)
        with open(MODEL_FOCUS_REGRESSOR, 'rb') as f:
            _models['focus_regressor'] = pickle.load(f)
        with open(MODEL_ANOMALY, 'rb') as f:
            _models['anomaly'] = pickle.load(f)
    return _models

def get_engines():
    """Initialize scoring engines"""
    if not _engines:
        _engines['scoring'] = CLIScoringEngine()
        _engines['rules'] = RuleEngine()
    return _engines

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/score", response_model=CLIScoreResponse)
async def compute_cli_score(
    lap_data: LapData,
    models: Dict = Depends(get_models),
    engines: Dict = Depends(get_engines)
):
    """
    🎯 Compute CLI score for a lap
    
    Returns real-time focus score and alert status
    """
    try:
        # Convert to feature dict
        features = lap_data.model_dump(by_alias=True)
        
        # Compute CLI score
        scoring_engine = engines['scoring']
        cli_raw, focus_score = scoring_engine.compute_cli_score(features)
        
        # Get ML predictions
        X = pd.DataFrame([features])[FEATURE_COLS].fillna(0)
        focus_drop_prob = models['focus_drop'].predict_proba(X)[0, 1]
        is_anomaly = models['anomaly'].predict(X)[0] == -1
        
        predictions = {
            'focus_drop_probability': focus_drop_prob,
            'is_anomaly': is_anomaly
        }
        
        # Evaluate alerts
        rule_engine = engines['rules']
        alert_level, alerts = rule_engine.evaluate_alerts(features, predictions)
        
        return CLIScoreResponse(
            focus_score=focus_score,
            cli_raw=cli_raw,
            alert_level=alert_level,
            alerts=alerts
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CLI computation failed: {str(e)}")

@router.post("/predict", response_model=PredictionResponse)
async def predict_focus_drop(
    lap_data: LapData,
    models: Dict = Depends(get_models)
):
    """
    📊 Predict focus drop and next-lap focus score
    
    Uses ML models to predict driver state evolution
    """
    try:
        features = lap_data.model_dump(by_alias=True)
        X = pd.DataFrame([features])[FEATURE_COLS].fillna(0)
        
        # Predictions
        focus_drop_prob = models['focus_drop'].predict_proba(X)[0, 1]
        next_lap_focus = models['focus_regressor'].predict(X)[0]
        is_anomaly = models['anomaly'].predict(X)[0] == -1
        anomaly_score = models['anomaly'].score_samples(X)[0]
        
        # Confidence level
        if focus_drop_prob < 0.3:
            confidence = "High"
        elif focus_drop_prob < 0.7:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        return PredictionResponse(
            focus_drop_probability=float(focus_drop_prob),
            next_lap_focus_score=float(np.clip(next_lap_focus, 0, 100)),
            is_anomaly=bool(is_anomaly),
            anomaly_score=float(anomaly_score),
            confidence=confidence
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.post("/explain", response_model=ExplanationResponse)
async def explain_prediction(lap_data: LapData):
    """
    🔍 Get SHAP explanation for prediction
    
    Shows which features contributed most to the prediction
    """
    try:
        import shap
        from backend.core.config import MODEL_SHAP
        
        # Load SHAP explainer
        with open(MODEL_SHAP, 'rb') as f:
            explainer = pickle.load(f)
        
        features = lap_data.model_dump(by_alias=True)
        X = pd.DataFrame([features])[FEATURE_COLS].fillna(0)
        
        # Compute SHAP values
        shap_values = explainer.shap_values(X)
        base_value = explainer.expected_value
        
        # Get feature contributions
        shap_dict = {
            FEATURE_COLS[i]: float(shap_values[0][i])
            for i in range(len(FEATURE_COLS))
        }
        
        # Top features by absolute impact
        top_features = sorted(
            [{'feature': k, 'impact': v} for k, v in shap_dict.items()],
            key=lambda x: abs(x['impact']),
            reverse=True
        )[:10]
        
        # Interpret contributions
        contributions = {}
        for feat, val in shap_dict.items():
            if abs(val) > 0.1:
                direction = "increasing" if val > 0 else "decreasing"
                contributions[feat] = f"{direction} focus drop risk"
        
        return ExplanationResponse(
            base_value=float(base_value),
            shap_values=shap_dict,
            top_features=top_features,
            feature_contributions=contributions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")

@router.get("/driver/{vehicle_number}/history", response_model=DriverHistoryResponse)
async def get_driver_history(vehicle_number: int):
    """
    📈 Get driver historical performance
    
    Retrieve past CLI performance and trends
    """
    try:
        # Load dataset
        df = pd.read_csv(DATASET_PATH)
        driver_data = df[df['vehicle_number'] == vehicle_number]
        
        if len(driver_data) == 0:
            raise HTTPException(status_code=404, detail=f"Driver {vehicle_number} not found")
        
        # Compute statistics
        avg_focus = driver_data['FocusScore_smooth'].mean()
        focus_drops = driver_data['focus_drop_next'].sum()
        mistakes = driver_data['mistake_event'].sum()
        
        # Trend analysis
        recent_laps = driver_data.tail(10)
        if recent_laps['FocusScore_smooth'].iloc[-1] > recent_laps['FocusScore_smooth'].iloc[0]:
            trend = "Improving"
        else:
            trend = "Declining"
        
        # Lap history
        lap_history = driver_data[['lap', 'FocusScore_smooth', 'CLI_raw', 'alert_level']].tail(20).to_dict('records')
        
        return DriverHistoryResponse(
            driver_id=driver_data['vehicle_id'].iloc[0],
            total_laps=len(driver_data),
            avg_focus_score=float(avg_focus),
            focus_drops=int(focus_drops),
            mistakes=int(mistakes),
            recent_trend=trend,
            lap_history=lap_history
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History retrieval failed: {str(e)}")

# ============================================================================
# PERSONALIZATION ENDPOINTS
# ============================================================================

@router.get("/driver/{driver_id}/baseline")
async def get_driver_baseline(driver_id: int):
    """
    🎯 Get personalized baseline for a specific driver
    
    Returns driver's baseline statistics and personalized thresholds
    """
    try:
        driver_key = str(driver_id)
        
        if driver_key not in DRIVER_BASELINES:
            raise HTTPException(
                status_code=404,
                detail=f"No baseline found for driver {driver_id}"
            )
        
        baseline = DRIVER_BASELINES[driver_key]
        
        return {
            "driver_id": driver_id,
            "baseline": baseline,
            "personalization_enabled": True,
            "interpretation": {
                "focus_baseline": f"Driver's typical focus score: {baseline['focus_baseline']:.1f}",
                "critical_threshold": f"Alert if focus drops below {baseline['critical_threshold']:.1f}",
                "warning_threshold": f"Warning if focus drops below {baseline['warning_threshold']:.1f}",
                "excellent_threshold": f"Excellent if focus above {baseline['excellent_threshold']:.1f}"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting baseline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "models_loaded": len(_models) > 0,
        "personalization_enabled": len(DRIVER_BASELINES) > 0,
        "drivers_with_baselines": len(DRIVER_BASELINES),
        "version": "1.0.0"
    }
