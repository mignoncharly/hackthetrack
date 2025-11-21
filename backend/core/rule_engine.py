# backend/core/rule_engine.py 

"""
Rule-Based Alert Engine - Immediate danger detection
"""
from typing import List, Dict, Tuple
from backend.core.config import ALERT_THRESHOLDS

class RuleEngine:
    """Rule-based alert system for immediate CLI warnings"""
    
    def __init__(self):
        self.thresholds = ALERT_THRESHOLDS
    
    def evaluate_alerts(self, 
                       features: Dict[str, float], 
                       predictions: Dict[str, float]) -> Tuple[int, List[str]]:
        """
        Evaluate all alert rules
        
        Args:
            features: Current lap telemetry features
            predictions: ML model predictions
            
        Returns:
            Tuple of (alert_level, alert_messages)
        """
        alerts = []
        alert_scores = []
        
        # Rule 1: High focus drop probability
        if predictions.get('focus_drop_probability', 0) > self.thresholds['focus_drop_prob']:
            alerts.append(f"⚠️ High focus drop risk: {predictions['focus_drop_probability']:.0%}")
            alert_scores.append(3)  # Critical
        
        # Rule 2: Critical focus score
        focus_score = features.get('FocusScore_smooth', 50)
        if focus_score < self.thresholds['focus_score_critical']:
            alerts.append(f"🚨 Critical focus level: {focus_score:.0f}/100")
            alert_scores.append(3)  # Critical
        elif focus_score < 30:
            alerts.append(f"⚠️ Low focus warning: {focus_score:.0f}/100")
            alert_scores.append(2)  # Warning
        
        # Rule 3: High error burst (brake + throttle)
        brake_spike = features.get('BrakeSpikeRate_5s_mean', 0)
        throttle_jerk = features.get('ThrottleJerk_1s_mean', 0)
        
        if brake_spike > self.thresholds['brake_spike_high'] and throttle_jerk > 20:
            alerts.append("🔴 Error burst detected - suggest 1-lap cooldown")
            alert_scores.append(2)
        
        # Rule 4: Steering indecision
        steer_entropy = features.get('SteerEntropy_10s_mean', 0)
        if steer_entropy > self.thresholds['steer_entropy_high']:
            alerts.append("🟡 Steering indecision - check driver confidence")
            alert_scores.append(1)
        
        # Rule 5: Anomaly detection
        if predictions.get('is_anomaly', False):
            alerts.append("🔵 Unusual driving pattern detected")
            alert_scores.append(1)
        
        # Rule 6: Degrading consistency
        if features.get('speed_std', 0) > 35:
            alerts.append("⚠️ Speed consistency degrading")
            alert_scores.append(1)
        
        # Determine overall alert level
        if not alerts:
            alert_level = 0
            alerts = ["✅ All systems nominal"]
        else:
            alert_level = max(alert_scores) if alert_scores else 0
        
        return alert_level, alerts
    
    def generate_action_recommendations(self, 
                                       alert_level: int, 
                                       features: Dict[str, float]) -> List[str]:
        """
        Generate actionable recommendations based on alert level
        
        Args:
            alert_level: Overall alert severity (0-3)
            features: Current lap features
            
        Returns:
            List of recommended actions
        """
        if alert_level == 0:
            return ["Continue current pace"]
        
        recommendations = []
        
        if alert_level >= 3:
            recommendations.append("🚨 IMMEDIATE ACTION: Radio check-in with driver")
            recommendations.append("Consider pit strategy adjustment")
        
        if alert_level >= 2:
            recommendations.append("Monitor next 2-3 laps closely")
            recommendations.append("Prepare alternate tire strategy")
        
        # Specific recommendations based on metrics
        if features.get('BrakeSpikeRate_5s_mean', 0) > 2.5:
            recommendations.append("Review brake sector performance")
        
        if features.get('SteerEntropy_10s_mean', 0) > 1.7:
            recommendations.append("Check track confidence / grip feedback")
        
        if features.get('ThrottleJerk_1s_mean', 0) > 25:
            recommendations.append("Advise smoother throttle application")
        
        return recommendations
