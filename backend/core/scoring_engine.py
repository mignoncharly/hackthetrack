# backend/core/scoring-engine.py

"""
CLI Scoring Engine - Core logic for computing Cognitive Load Index
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple

class CLIScoringEngine:
    """Compute CLI scores from telemetry features"""
    
    def __init__(self):
        # Hybrid formula weights
        self.weights = {
            'throttle_jerk': 0.30,
            'steer_entropy': 0.25,
            'micro_var': 0.20,
            'brake_spike': 0.15,
            'speed_var': 0.10
        }
    
    def compute_cli_score(self, features: Dict[str, float]) -> Tuple[float, float]:
        """
        Compute CLI raw score and Focus score
        
        Args:
            features: Dictionary of telemetry features
            
        Returns:
            Tuple of (cli_raw, focus_score)
        """
        # Extract components
        throttle_jerk = features.get('ThrottleJerk_1s_mean', 0)
        steer_entropy = features.get('SteerEntropy_10s_mean', 0)
        micro_var = features.get('MicroVariability_mean', 0)
        brake_spike = features.get('BrakeSpikeRate_5s_mean', 0)
        speed_var = features.get('speed_std', 0)
        
        # Z-score normalization (simplified - use global stats)
        z_throttle = self._normalize(throttle_jerk, mean=15.0, std=10.0)
        z_steer = self._normalize(steer_entropy, mean=1.4, std=0.4)
        z_micro = self._normalize(micro_var, mean=0.0, std=0.01)
        z_brake = self._normalize(brake_spike, mean=0.8, std=0.9)
        z_speed = self._normalize(speed_var, mean=25.0, std=10.0)
        
        # Compute weighted CLI raw score
        cli_raw = (
            self.weights['throttle_jerk'] * z_throttle +
            self.weights['steer_entropy'] * z_steer +
            self.weights['micro_var'] * z_micro +
            self.weights['brake_spike'] * z_brake +
            self.weights['speed_var'] * z_speed
        )
        
        # Normalize to 0-100 scale (higher = worse)
        # Assuming cli_raw ranges from -3 to +3 typically
        cli_normalized = 50 + (cli_raw * 15)  # Maps -3 to 5, +3 to 95
        cli_normalized = np.clip(cli_normalized, 0, 100)
        
        # Focus score = inverse (higher = better)
        focus_score = 100 - cli_normalized
        
        return cli_raw, focus_score
    
    def _normalize(self, value: float, mean: float, std: float) -> float:
        """Z-score normalization"""
        if std == 0:
            return 0
        return (value - mean) / std
    
    def compute_component_scores(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        Compute individual CLI component scores
        
        Returns:
            Dictionary of component scores
        """
        throttle_jerk = features.get('ThrottleJerk_1s_mean', 0)
        steer_entropy = features.get('SteerEntropy_10s_mean', 0)
        micro_var = features.get('MicroVariability_mean', 0)
        brake_spike = features.get('BrakeSpikeRate_5s_mean', 0)
        speed_var = features.get('speed_std', 0)
        
        return {
            'throttle_control': self._score_to_percent(throttle_jerk, 0, 50),
            'steering_smoothness': self._score_to_percent(steer_entropy, 0, 2),
            'micro_variability': self._score_to_percent(micro_var, 0, 0.1),
            'brake_consistency': self._score_to_percent(brake_spike, 0, 3),
            'speed_consistency': self._score_to_percent(speed_var, 0, 40)
        }
    
    def _score_to_percent(self, value: float, min_val: float, max_val: float) -> float:
        """Convert value to 0-100 percentage (lower = better)"""
        normalized = (value - min_val) / (max_val - min_val)
        normalized = np.clip(normalized, 0, 1)
        return 100 - (normalized * 100)  # Invert so higher = better
