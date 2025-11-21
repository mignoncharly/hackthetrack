# step1_integrate_and_score.py

import pandas as pd
import numpy as np
from scipy import stats
import os
import warnings
warnings.filterwarnings('ignore')

print("="*100)
print("🚀 PHASE 1: DATA INTEGRATION & CLI SCORING")
print("="*100)

# ============================================================================
# CONFIGURATION - 
# ============================================================================

LAP_FEATURES_FILE = "processed_data/sonoma_r1_lap_features.csv"
LAP_TIMES_FILE = "sonoma/Race 1/23_AnalysisEnduranceWithSections_Race 1_Anonymized.CSV"
WEATHER_FILE = "sonoma/Race 1/26_Weather_Race 1_Anonymized.CSV"
OUTPUT_FOLDER = "processed_data"

# ============================================================================
# UTILITY FUNCTION: Convert lap time string to seconds
# ============================================================================

def laptime_to_seconds(laptime_str):
    """Convert lap time from 'M:SS.mmm' format to seconds"""
    try:
        if pd.isna(laptime_str) or laptime_str == '':
            return np.nan
        # Handle formats like '1:52.039' or '2:42.005'
        parts = str(laptime_str).split(':')
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        elif len(parts) == 1:
            # Already in seconds format
            return float(parts[0])
        else:
            return np.nan
    except:
        return np.nan

# ============================================================================
# STEP 1.1: MERGE TELEMETRY FEATURES + LAP TIMES
# ============================================================================

print(f"\n{'='*100}")
print("📊 STEP 1.1: Merging Telemetry Features + Lap Times")
print("="*100)

# Load telemetry features
print(f"\n1️⃣  Loading telemetry features...")
telem_features = pd.read_csv(LAP_FEATURES_FILE)
print(f"   ✅ Loaded {len(telem_features)} laps with telemetry features")

# Load lap times & sectors (semicolon-delimited!)
print(f"\n2️⃣  Loading lap times...")
lap_times = pd.read_csv(LAP_TIMES_FILE, sep=';')
lap_times.columns = lap_times.columns.str.strip()  # Remove leading/trailing spaces
print(f"   ✅ Loaded {len(lap_times)} lap records")
print(f"   Columns: {list(lap_times.columns[:10])}...")

# Clean and prepare lap times data
lap_times['NUMBER'] = lap_times['NUMBER'].astype(int) if 'NUMBER' in lap_times.columns else None

# Merge on vehicle_number and lap number
print(f"\n3️⃣  Merging datasets...")
merged = pd.merge(
    telem_features,
    lap_times,
    left_on=['vehicle_number', 'lap'],
    right_on=['NUMBER', 'LAP_NUMBER'],
    how='inner'
)

print(f"   ✅ Merged dataset: {len(merged)} laps")
print(f"   Total features: {len(merged.columns)}")

# Load weather (for contextual features)
if os.path.exists(WEATHER_FILE):
    weather = pd.read_csv(WEATHER_FILE, sep=';')
    weather.columns = weather.columns.str.strip()
    if len(weather) > 0:
        merged['AIR_TEMP'] = weather['AIR_TEMP'].iloc[0] if 'AIR_TEMP' in weather.columns else 25.0
        merged['TRACK_TEMP'] = weather['TRACK_TEMP'].iloc[0] if 'TRACK_TEMP' in weather.columns else 35.0
        merged['HUMIDITY'] = weather['HUMIDITY'].iloc[0] if 'HUMIDITY' in weather.columns else 50.0
        print(f"   ✅ Added weather context")

# ============================================================================
# STEP 1.2: COMPUTE RAW CLI SCORES (HYBRID FORMULA)
# ============================================================================

print(f"\n{'='*100}")
print("📊 STEP 1.2: Computing Raw CLI Scores")
print("="*100)

# Z-score normalization function
def zscore_normalize(series):
    """Compute z-scores, handling NaN and infinite values"""
    mean = series.mean()
    std = series.std()
    if std == 0 or pd.isna(std):
        return pd.Series(0, index=series.index)
    z = (series - mean) / std
    z = z.replace([np.inf, -np.inf], 0)
    return z.fillna(0)

print(f"\n1️⃣  Normalizing CLI component features...")

# Compute z-scores for each CLI component (per-driver normalization)
merged['z_ThrottleJerk'] = merged.groupby('vehicle_number')['ThrottleJerk_1s_mean'].transform(zscore_normalize)
merged['z_SteerEntropy'] = merged.groupby('vehicle_number')['SteerEntropy_10s_mean'].transform(zscore_normalize)
merged['z_MicroVar'] = merged.groupby('vehicle_number')['MicroVariability_mean'].transform(zscore_normalize)
merged['z_BrakeSpike'] = merged.groupby('vehicle_number')['BrakeSpikeRate_5s_mean'].transform(zscore_normalize)

# Speed variability (use std of speed as proxy)
merged['z_SpeedVar'] = merged.groupby('vehicle_number')['speed_std'].transform(zscore_normalize)

print(f"   ✅ Normalized 5 CLI components")

# Compute raw CLI score using your hybrid formula
print(f"\n2️⃣  Computing raw CLI scores...")

merged['CLI_raw'] = (
    0.30 * merged['z_ThrottleJerk'] +
    0.25 * merged['z_SteerEntropy'] +
    0.20 * merged['z_MicroVar'] +
    0.15 * merged['z_BrakeSpike'] +
    0.10 * merged['z_SpeedVar']
)

# Normalize CLI_raw to 0-100 scale (higher CLI = worse performance)
cli_min = merged['CLI_raw'].min()
cli_max = merged['CLI_raw'].max()
merged['CLI_normalized'] = 100 * (merged['CLI_raw'] - cli_min) / (cli_max - cli_min + 1e-6)

# Focus Score = inverse of CLI (100 = perfect focus, 0 = no focus)
merged['FocusScore'] = 100 - merged['CLI_normalized']

# Smooth focus score (rolling 3-lap average)
merged['FocusScore_smooth'] = merged.groupby('vehicle_number')['FocusScore'].transform(
    lambda x: x.rolling(window=3, min_periods=1, center=True).mean()
)

print(f"   ✅ CLI_raw: mean={merged['CLI_raw'].mean():.2f}, std={merged['CLI_raw'].std():.2f}")
print(f"   ✅ FocusScore: mean={merged['FocusScore_smooth'].mean():.1f}, range=[{merged['FocusScore_smooth'].min():.1f}, {merged['FocusScore_smooth'].max():.1f}]")

# ============================================================================
# STEP 1.3: RULE-BASED ALERT ENGINE
# ============================================================================

print(f"\n{'='*100}")
print("📊 STEP 1.3: Rule-Based Alert Engine")
print("="*100)

print(f"\n1️⃣  Defining alert rules...")

# Rule 1: High error burst (BrakeSpike + ThrottleJerk both high)
merged['alert_error_burst'] = (
    (merged['BrakeSpikeRate_5s_mean'] > merged['BrakeSpikeRate_5s_mean'].quantile(0.75)) &
    (merged['ThrottleJerk_1s_mean'] > merged['ThrottleJerk_1s_mean'].quantile(0.75))
).astype(int)

# Rule 2: Steering indecision (high entropy)
merged['alert_steer_indecision'] = (
    merged['SteerEntropy_10s_mean'] > merged['SteerEntropy_10s_mean'].quantile(0.90)
).astype(int)

# Rule 3: Focus drop (sudden 10+ point decrease in 2 laps)
merged['focus_change_2lap'] = merged.groupby('vehicle_number')['FocusScore_smooth'].diff(periods=2)
merged['alert_focus_drop'] = (merged['focus_change_2lap'] < -10).astype(int)

# Rule 4: Degrading consistency (increasing lap time variance)
merged['alert_degrading'] = (
    (merged['speed_std'] > merged['speed_std'].quantile(0.80)) &
    (merged['MicroVariability_mean'] > 0)
).astype(int)

# Aggregate alert level (0 = no alert, 1 = warning, 2 = critical)
merged['alert_level'] = (
    merged['alert_error_burst'] +
    merged['alert_steer_indecision'] +
    merged['alert_focus_drop'] +
    merged['alert_degrading']
).clip(0, 3)

# Generate action recommendations
def generate_action_card(row):
    """Generate action recommendation based on alerts"""
    if row['alert_level'] == 0:
        return "Maintain current pace"
    
    actions = []
    
    if row['alert_error_burst'] == 1:
        actions.append("High error bursts detected - suggest 1-lap cool down")
    
    if row['alert_steer_indecision'] == 1:
        actions.append("Steering indecision - check driver fatigue or track confidence")
    
    if row['alert_focus_drop'] == 1:
        actions.append(f"Focus dropped {abs(row['focus_change_2lap']):.0f} points - consider radio reminder")
    
    if row['alert_degrading'] == 1:
        actions.append("Consistency degrading - review sector-specific issues")
    
    return " | ".join(actions)

merged['action_card'] = merged.apply(generate_action_card, axis=1)

alert_count = (merged['alert_level'] > 0).sum()
print(f"   ✅ Alert rules defined")
print(f"   ✅ Alerts triggered: {alert_count} / {len(merged)} laps ({100*alert_count/len(merged):.1f}%)")

# ============================================================================
# STEP 1.4: LABEL GENERATION FOR ML TRAINING
# ============================================================================

print(f"\n{'='*100}")
print("📊 STEP 1.4: Label Generation for ML Training")
print("="*100)

print(f"\n1️⃣  Creating proxy labels...")

# Label 1: FocusDrop (binary) - significant drop in next 1-2 laps
merged['FocusScore_next'] = merged.groupby('vehicle_number')['FocusScore_smooth'].shift(-1)
merged['focus_drop_next'] = ((merged['FocusScore_smooth'] - merged['FocusScore_next']) > 15).astype(int)

# Label 2: MistakeEvent (binary) - extreme deviation in lap time or speed
# Convert lap time from string to seconds
if 'LAP_TIME' in merged.columns:
    print(f"   Converting lap times to seconds...")
    merged['lap_time_seconds'] = merged['LAP_TIME'].apply(laptime_to_seconds)
    merged['lap_time_baseline'] = merged.groupby('vehicle_number')['lap_time_seconds'].transform('median')
    merged['lap_time_deviation'] = abs(merged['lap_time_seconds'] - merged['lap_time_baseline'])
    merged['mistake_event'] = (
        merged['lap_time_deviation'] > merged.groupby('vehicle_number')['lap_time_deviation'].transform(lambda x: x.quantile(0.95))
    ).astype(int)
else:
    # Fallback: use speed anomalies
    merged['mistake_event'] = (
        (merged['speed_min'] < merged.groupby('vehicle_number')['speed_min'].transform(lambda x: x.quantile(0.05))) |
        (merged['BrakeSpikeRate_5s_max'] > 3)
    ).astype(int)

# Label 3: HighLoad (multi-class) - Low/Medium/High cognitive load
merged['load_level'] = pd.cut(
    merged['CLI_normalized'],
    bins=[0, 33, 66, 100],
    labels=['Low', 'Medium', 'High']
)

focus_drop_count = merged['focus_drop_next'].sum()
mistake_count = merged['mistake_event'].sum()

print(f"   ✅ Focus drop events (next lap): {focus_drop_count} ({100*focus_drop_count/len(merged):.1f}%)")
print(f"   ✅ Mistake events: {mistake_count} ({100*mistake_count/len(merged):.1f}%)")
print(f"   ✅ Load distribution: {merged['load_level'].value_counts().to_dict()}")

# ============================================================================
# SAVE INTEGRATED DATASET
# ============================================================================

print(f"\n{'='*100}")
print("💾 Saving Integrated Dataset")
print("="*100)

output_file = os.path.join(OUTPUT_FOLDER, "cli_complete_dataset.csv")
merged.to_csv(output_file, index=False)

print(f"\n✅ Saved complete dataset: {output_file}")
print(f"   Rows: {len(merged)}")
print(f"   Columns: {len(merged.columns)}")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================

print(f"\n{'='*100}")
print("📊 PHASE 1 COMPLETE - SUMMARY")
print("="*100)

print(f"\n🎯 CLI Scores:")
print(f"   Mean Focus Score: {merged['FocusScore_smooth'].mean():.1f}/100")
print(f"   Focus Score Range: {merged['FocusScore_smooth'].min():.1f} - {merged['FocusScore_smooth'].max():.1f}")
print(f"   CLI Raw Range: {merged['CLI_raw'].min():.2f} - {merged['CLI_raw'].max():.2f}")

print(f"\n🚨 Alerts:")
print(f"   Total alerts: {alert_count} ({100*alert_count/len(merged):.1f}% of laps)")
print(f"   Critical alerts (level 2+): {(merged['alert_level'] >= 2).sum()}")

print(f"\n🏷️  ML Labels:")
print(f"   Focus drops (next lap): {focus_drop_count}")
print(f"   Mistake events: {mistake_count}")
print(f"   Usable training samples: {len(merged[merged['focus_drop_next'].notna()])}")

print(f"\n✅ OUTPUT FILE: {output_file}")

print(f"\n{'='*100}")
