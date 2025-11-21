# scripts/compute-driver_baselines.py

"""
Compute per-driver baselines for personalized CLI normalization
This enables driver-specific alert thresholds and performance tracking
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path

def compute_driver_baselines(df):
    """
    Compute comprehensive per-driver baselines
    
    Returns:
    - driver_baselines: dict with per-driver statistics
    """
    
    baselines = {}
    
    for driver in df['vehicle_number'].unique():
        driver_data = df[df['vehicle_number'] == driver]
        
        # Focus Score Statistics
        focus_mean = driver_data['FocusScore_smooth'].mean()
        focus_std = driver_data['FocusScore_smooth'].std()
        focus_median = driver_data['FocusScore_smooth'].median()
        focus_p10 = driver_data['FocusScore_smooth'].quantile(0.10)
        focus_p90 = driver_data['FocusScore_smooth'].quantile(0.90)
        
        # CLI Component Baselines
        throttle_mean = driver_data['ThrottleJerk_1s_mean'].mean()
        throttle_std = driver_data['ThrottleJerk_1s_mean'].std()
        
        brake_mean = driver_data['BrakeSpikeRate_5s_mean'].mean()
        brake_std = driver_data['BrakeSpikeRate_5s_mean'].std()
        
        steer_mean = driver_data['SteerEntropy_10s_mean'].mean()
        steer_std = driver_data['SteerEntropy_10s_mean'].std()
        
        # Performance Metrics
        speed_mean = driver_data['speed_mean'].mean()
        speed_std_avg = driver_data['speed_std'].mean()
        
        # Behavioral Patterns
        focus_drop_rate = driver_data['focus_drop_next'].mean()
        mistake_rate = driver_data['mistake_event'].mean()
        
        # Store baseline
        baselines[int(driver)] = {
            'driver_id': int(driver),
            'total_laps': len(driver_data),
            
            # Focus Score Profile
            'focus_baseline': float(focus_mean),
            'focus_std': float(focus_std),
            'focus_median': float(focus_median),
            'focus_p10': float(focus_p10),
            'focus_p90': float(focus_p90),
            
            # CLI Components
            'throttle_baseline': float(throttle_mean),
            'throttle_std': float(throttle_std),
            'brake_baseline': float(brake_mean),
            'brake_std': float(brake_std),
            'steer_baseline': float(steer_mean),
            'steer_std': float(steer_std),
            
            # Performance
            'speed_baseline': float(speed_mean),
            'speed_stability': float(speed_std_avg),
            
            # Risk Profile
            'focus_drop_rate': float(focus_drop_rate),
            'mistake_rate': float(mistake_rate),
            
            # Personalized Thresholds
            'critical_threshold': float(focus_mean - 2 * focus_std),  # 2 std below mean
            'warning_threshold': float(focus_mean - 1 * focus_std),   # 1 std below mean
            'excellent_threshold': float(focus_mean + 1 * focus_std)  # 1 std above mean
        }
    
    return baselines

def compute_normalized_scores(df, baselines):
    """
    Add normalized (z-score) versions of key metrics per driver
    """
    
    df_normalized = df.copy()
    
    # Initialize columns
    df_normalized['focus_z_score'] = 0.0
    df_normalized['focus_percentile'] = 0.0
    df_normalized['performance_vs_baseline'] = 0.0
    df_normalized['personalized_alert_level'] = 0
    
    for driver in df['vehicle_number'].unique():
        mask = df_normalized['vehicle_number'] == driver
        baseline = baselines[int(driver)]
        
        # Z-score normalization
        driver_data = df_normalized[mask]['FocusScore_smooth']
        z_scores = (driver_data - baseline['focus_baseline']) / baseline['focus_std']
        df_normalized.loc[mask, 'focus_z_score'] = z_scores
        
        # Percentile within driver's own distribution
        percentiles = driver_data.rank(pct=True) * 100
        df_normalized.loc[mask, 'focus_percentile'] = percentiles
        
        # Performance vs baseline (% deviation)
        perf_vs_baseline = ((driver_data - baseline['focus_baseline']) / baseline['focus_baseline']) * 100
        df_normalized.loc[mask, 'performance_vs_baseline'] = perf_vs_baseline
        
        # Personalized alert levels based on driver's own thresholds
        df_normalized.loc[mask, 'personalized_alert_level'] = df_normalized[mask].apply(
            lambda row: compute_personalized_alert(row['FocusScore_smooth'], baseline),
            axis=1
        )
    
    return df_normalized

def compute_personalized_alert(focus_score, baseline):
    """
    Compute alert level based on driver's personal baseline
    """
    if focus_score < baseline['critical_threshold']:
        return 3  # Critical
    elif focus_score < baseline['warning_threshold']:
        return 2  # Warning
    elif focus_score > baseline['excellent_threshold']:
        return -1  # Excellent performance
    else:
        return 0  # Normal

def main():
    """Main execution"""
    
    print("🏎️  Computing Driver Baselines for Personalization...")
    print("=" * 60)
    
    # Load data
    print("\n📂 Loading dataset...")
    df = pd.read_csv('processed_data/cli_complete_dataset_with_predictions.csv')
    print(f"✅ Loaded {len(df)} laps from {df['vehicle_number'].nunique()} drivers")
    
    # Compute baselines
    print("\n📊 Computing per-driver baselines...")
    baselines = compute_driver_baselines(df)
    print(f"✅ Computed baselines for {len(baselines)} drivers")
    
    # Show sample baseline
    sample_driver = list(baselines.keys())[0]
    print(f"\n📋 Sample Baseline (Driver {sample_driver}):")
    print(f"   Focus Baseline: {baselines[sample_driver]['focus_baseline']:.2f} ± {baselines[sample_driver]['focus_std']:.2f}")
    print(f"   Critical Threshold: {baselines[sample_driver]['critical_threshold']:.2f}")
    print(f"   Warning Threshold: {baselines[sample_driver]['warning_threshold']:.2f}")
    print(f"   Excellent Threshold: {baselines[sample_driver]['excellent_threshold']:.2f}")
    
    # Save baselines
    print("\n💾 Saving baselines...")
    Path('processed_data').mkdir(exist_ok=True)
    
    with open('processed_data/driver_baselines.json', 'w') as f:
        json.dump(baselines, f, indent=2)
    print("✅ Saved to: processed_data/driver_baselines.json")
    
    # Compute normalized scores
    print("\n🔢 Computing normalized scores...")
    df_normalized = compute_normalized_scores(df, baselines)
    
    # Save normalized dataset
    output_path = 'processed_data/cli_dataset_with_personalization.csv'
    df_normalized.to_csv(output_path, index=False)
    print(f"✅ Saved normalized dataset to: {output_path}")
    
    # Statistics
    print("\n📈 Personalization Statistics:")
    print(f"   Mean Z-Score Range: [{df_normalized['focus_z_score'].min():.2f}, {df_normalized['focus_z_score'].max():.2f}]")
    print(f"   Drivers with custom thresholds: {len(baselines)}")
    
    personalized_alerts = df_normalized['personalized_alert_level'].value_counts().sort_index()
    print(f"\n⚠️  Personalized Alert Distribution:")
    for level, count in personalized_alerts.items():
        level_name = {-1: "Excellent", 0: "Normal", 2: "Warning", 3: "Critical"}.get(level, "Unknown")
        print(f"   {level_name}: {count} laps ({count/len(df_normalized)*100:.1f}%)")
    
    print("\n" + "=" * 60)
    print("✅ Driver Baseline Personalization Complete!")
    print(f"📊 {len(baselines)} driver profiles ready for use")

if __name__ == "__main__":
    main()
