# backed/api/models/schemas.py

"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class LapData(BaseModel):
    """Input lap telemetry features"""
    throttle_jerk_mean: float = Field(..., alias='ThrottleJerk_1s_mean')
    throttle_jerk_std: float = Field(..., alias='ThrottleJerk_1s_std')
    throttle_jerk_max: float = Field(..., alias='ThrottleJerk_1s_max')
    brake_spike_mean: float = Field(..., alias='BrakeSpikeRate_5s_mean')
    brake_spike_max: float = Field(..., alias='BrakeSpikeRate_5s_max')
    brake_spike_sum: float = Field(..., alias='BrakeSpikeRate_5s_sum')
    steer_entropy_mean: float = Field(..., alias='SteerEntropy_10s_mean')
    steer_entropy_max: float = Field(..., alias='SteerEntropy_10s_max')
    micro_var_mean: float = Field(..., alias='MicroVariability_mean')
    micro_var_std: float = Field(..., alias='MicroVariability_std')
    ath_mean: float
    ath_std: float
    speed_mean: float
    speed_std: float
    pbrake_f_mean: float
    pbrake_f_max: float
    steering_angle_mean: float = Field(..., alias='Steering_Angle_mean')
    steering_angle_std: float = Field(..., alias='Steering_Angle_std')
    accx_can_mean: float
    accx_can_std: float
    accy_can_mean: float
    accy_can_std: float
    cli_raw: float = Field(..., alias='CLI_raw')
    focus_score_smooth: float = Field(..., alias='FocusScore_smooth')
    lap: int
    air_temp: float = Field(25.0, alias='AIR_TEMP')
    track_temp: float = Field(35.0, alias='TRACK_TEMP')
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "ThrottleJerk_1s_mean": 15.5,
                "ThrottleJerk_1s_std": 8.2,
                "ThrottleJerk_1s_max": 45.0,
                "BrakeSpikeRate_5s_mean": 1.2,
                "BrakeSpikeRate_5s_max": 3.0,
                "BrakeSpikeRate_5s_sum": 6.0,
                "SteerEntropy_10s_mean": 1.5,
                "SteerEntropy_10s_max": 1.8,
                "MicroVariability_mean": 0.02,
                "MicroVariability_std": 0.01,
                "ath_mean": 70.0,
                "ath_std": 15.0,
                "speed_mean": 130.0,
                "speed_std": 25.0,
                "pbrake_f_mean": 0.5,
                "pbrake_f_max": 2.0,
                "Steering_Angle_mean": 5.0,
                "Steering_Angle_std": 10.0,
                "accx_can_mean": 0.1,
                "accx_can_std": 0.5,
                "accy_can_mean": -0.2,
                "accy_can_std": 0.4,
                "CLI_raw": 0.5,
                "FocusScore_smooth": 65.0,
                "lap": 15,
                "AIR_TEMP": 25.0,
                "TRACK_TEMP": 35.0
            }
        }

class CLIScoreResponse(BaseModel):
    """CLI score response"""
    focus_score: float = Field(..., description="Current focus score (0-100)")
    cli_raw: float = Field(..., description="Raw CLI score")
    alert_level: int = Field(..., description="Alert level (0-3)")
    alerts: List[str] = Field(..., description="Active alert messages")
    timestamp: datetime = Field(default_factory=datetime.now)

class PredictionResponse(BaseModel):
    """Focus drop prediction response"""
    focus_drop_probability: float = Field(..., description="Probability of focus drop (0-1)")
    next_lap_focus_score: float = Field(..., description="Predicted next lap focus score")
    is_anomaly: bool = Field(..., description="Whether lap is anomalous")
    anomaly_score: float = Field(..., description="Anomaly score")
    confidence: str = Field(..., description="Confidence level")
    
class ExplanationResponse(BaseModel):
    """SHAP explanation response"""
    base_value: float
    shap_values: Dict[str, float]
    top_features: List[Dict[str, float]]
    feature_contributions: Dict[str, str]

class DriverHistoryResponse(BaseModel):
    """Driver historical performance"""
    driver_id: str
    total_laps: int
    avg_focus_score: float
    focus_drops: int
    mistakes: int
    recent_trend: str
    lap_history: List[Dict]
