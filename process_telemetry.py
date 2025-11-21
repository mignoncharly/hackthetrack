# process_telemetry.py

import pandas as pd
import numpy as np
from scipy.stats import entropy
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')

print("="*100)
print("🚀 GR CUP CLI - COMPLETE TELEMETRY PROCESSING PIPELINE")
print("="*100)

# ============================================================================
# CONFIGURATION
# ============================================================================

# PATHS TO THE FILES
SONOMA_R1_TELEM = "C:/Racing AI/Sonoma/Race 1/sonoma_telemetry_R1.csv"
ROAD_AMERICA_R1_TELEM = "C:/Racing AI/Road America/Race 1/R1_road_america_telemetry_data.csv"

# Output folder
OUTPUT_FOLDER = "processed_data"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Processing parameters
RESAMPLE_FREQ = '1S'  # Resample to 1 Hz (from ~5-15 kHz raw data)
CHUNK_SIZE = 100000   # Process in chunks to handle large files

# ============================================================================
# STEP 1: PIVOT TELEMETRY FROM LONG TO WIDE FORMAT
# ============================================================================

def process_telemetry_file(file_path, track_name, race_name):
    """
    Transform telemetry from long format to wide format and resample to 1Hz
    """
    print(f"\n{'='*100}")
    print(f"📊 Processing: {track_name} - {race_name}")
    print(f"{'='*100}")
    
    start_time = datetime.now()
    
    # Read telemetry in chunks (files are huge: 1-3 GB)
    print(f"\n1️⃣  Loading telemetry data (this may take 2-5 minutes)...")
    
    telemetry_chunks = []
    chunk_count = 0
    
    for chunk in pd.read_csv(file_path, chunksize=CHUNK_SIZE):
        chunk_count += 1
        if chunk_count % 10 == 0:
            print(f"   Processed {chunk_count * CHUNK_SIZE:,} rows...")
        
        # Pivot: convert telemetry_name rows into columns
        pivoted = chunk.pivot_table(
            index=['timestamp', 'vehicle_id', 'vehicle_number', 'lap'],
            columns='telemetry_name',
            values='telemetry_value',
            aggfunc='first'  # Take first value if duplicates
        ).reset_index()
        
        telemetry_chunks.append(pivoted)
    
    # Combine all chunks
    print(f"\n2️⃣  Combining chunks...")
    telemetry_wide = pd.concat(telemetry_chunks, ignore_index=True)
    
    print(f"   ✅ Combined shape: {telemetry_wide.shape}")
    print(f"   ✅ Columns: {list(telemetry_wide.columns)}")
    
    # Convert timestamp to datetime
    telemetry_wide['timestamp'] = pd.to_datetime(telemetry_wide['timestamp'])
    
    # Sort by vehicle and timestamp
    telemetry_wide = telemetry_wide.sort_values(['vehicle_id', 'timestamp'])
    
    #  ============================================================================
    # STEP 2: RESAMPLE TO 1 HZ (from 5-15 kHz down to manageable 1Hz)
    # ============================================================================
    
    print(f"\n3️⃣  Resampling to {RESAMPLE_FREQ} frequency...")
    
    resampled_data = []
    
    for vehicle_id in telemetry_wide['vehicle_id'].unique():
        vehicle_data = telemetry_wide[telemetry_wide['vehicle_id'] == vehicle_id].copy()
        vehicle_data = vehicle_data.set_index('timestamp')
        
        # Resample numeric columns
        numeric_cols = vehicle_data.select_dtypes(include=[np.number]).columns
        resampled = vehicle_data[numeric_cols].resample(RESAMPLE_FREQ).mean()
        
        # Add back vehicle info
        resampled['vehicle_id'] = vehicle_id
        resampled['vehicle_number'] = vehicle_data['vehicle_number'].iloc[0]
        
        resampled_data.append(resampled)
    
    telemetry_1hz = pd.concat(resampled_data).reset_index()
    
    print(f"   ✅ Resampled shape: {telemetry_1hz.shape}")
    print(f"   ✅ Reduced from ~{len(telemetry_wide):,} to {len(telemetry_1hz):,} rows ({len(telemetry_wide)/len(telemetry_1hz):.1f}x smaller)")
    
    # ============================================================================
    # STEP 3: COMPUTE CLI FEATURES
    # ============================================================================
    
    print(f"\n4️⃣  Computing CLI features...")
    
    # Ensure required columns exist
    required_cols = ['ath', 'Steering_Angle', 'pbrake_f', 'accx_can', 'accy_can', 'speed']
    for col in required_cols:
        if col not in telemetry_1hz.columns:
            telemetry_1hz[col] = 0.0
    
    # Group by vehicle for rolling calculations
    telemetry_1hz = telemetry_1hz.sort_values(['vehicle_id', 'timestamp'])
    
    # A. CONTROL-SIGNAL METRICS
    print("   Computing Control-Signal Metrics...")
    
    # ThrottleJerk = mean(|d(throttle)/dt|)
    telemetry_1hz['throttle_diff'] = telemetry_1hz.groupby('vehicle_id')['ath'].diff().abs()
    telemetry_1hz['ThrottleJerk_1s'] = telemetry_1hz.groupby('vehicle_id')['throttle_diff'].rolling(
        window=1, min_periods=1).mean().reset_index(0, drop=True)
    
    # BrakeSpikeRate = count of abrupt brake events (threshold: >0.5 bar change)
    telemetry_1hz['brake_diff'] = telemetry_1hz.groupby('vehicle_id')['pbrake_f'].diff().abs()
    telemetry_1hz['BrakeSpike'] = (telemetry_1hz['brake_diff'] > 0.5).astype(int)
    telemetry_1hz['BrakeSpikeRate_5s'] = telemetry_1hz.groupby('vehicle_id')['BrakeSpike'].rolling(
        window=5, min_periods=1).sum().reset_index(0, drop=True)
    
    # SteerEntropy = Shannon entropy of steering angle bins (10-degree bins)
    def compute_steer_entropy(series):
        """Compute Shannon entropy of steering angles"""
        if len(series) < 2:
            return 0
        # Bin steering angles into 10-degree increments
        bins = np.arange(-180, 180, 10)
        hist, _ = np.histogram(series, bins=bins)
        hist = hist[hist > 0]  # Remove zero bins
        if len(hist) == 0:
            return 0
        probs = hist / hist.sum()
        return entropy(probs)
    
    telemetry_1hz['SteerEntropy_10s'] = telemetry_1hz.groupby('vehicle_id')['Steering_Angle'].rolling(
        window=10, min_periods=5).apply(compute_steer_entropy, raw=True).reset_index(0, drop=True)
    
    # B. MICRO-VARIABILITY METRICS
    print("   Computing MicroVariability Metrics...")
    
    # MicroVariability = std of throttle/steer/latAccel at 1s windows
    telemetry_1hz['ThrottleVar_1s'] = telemetry_1hz.groupby('vehicle_id')['ath'].rolling(
        window=1, min_periods=1).std().reset_index(0, drop=True)
    
    telemetry_1hz['SteerVar_1s'] = telemetry_1hz.groupby('vehicle_id')['Steering_Angle'].rolling(
        window=1, min_periods=1).std().reset_index(0, drop=True)
    
    telemetry_1hz['LatAccelVar_1s'] = telemetry_1hz.groupby('vehicle_id')['accy_can'].rolling(
        window=1, min_periods=1).std().reset_index(0, drop=True)
    
    # Combined MicroVariability score
    telemetry_1hz['MicroVariability'] = (
        telemetry_1hz['ThrottleVar_1s'].fillna(0) + 
        telemetry_1hz['SteerVar_1s'].fillna(0) + 
        telemetry_1hz['LatAccelVar_1s'].fillna(0)
    ) / 3
    
    # C. SPEED & ACCELERATION FEATURES
    print("   Computing Speed & Acceleration Features...")
    
    telemetry_1hz['speed_change'] = telemetry_1hz.groupby('vehicle_id')['speed'].diff()
    telemetry_1hz['speed_rolling_mean'] = telemetry_1hz.groupby('vehicle_id')['speed'].rolling(
        window=5, min_periods=1).mean().reset_index(0, drop=True)
    
    # ============================================================================
    # STEP 4: AGGREGATE TO LAP-LEVEL FEATURES
    # ============================================================================
    
    print(f"\n5️⃣  Aggregating to lap-level features...")
    
    # Group by vehicle and lap
    lap_features = telemetry_1hz.groupby(['vehicle_id', 'vehicle_number', 'lap']).agg({
        'ThrottleJerk_1s': ['mean', 'std', 'max'],
        'BrakeSpikeRate_5s': ['mean', 'max', 'sum'],
        'SteerEntropy_10s': ['mean', 'max'],
        'MicroVariability': ['mean', 'std'],
        'ath': ['mean', 'std', 'min', 'max'],
        'pbrake_f': ['mean', 'max', 'sum'],
        'Steering_Angle': ['mean', 'std'],
        'speed': ['mean', 'std', 'min', 'max'],
        'accx_can': ['mean', 'std'],
        'accy_can': ['mean', 'std'],
    }).reset_index()
    
    # Flatten multi-level columns
    lap_features.columns = ['_'.join(col).strip('_') for col in lap_features.columns.values]
    lap_features.columns = [col if col != 'vehicle_id_' else 'vehicle_id' for col in lap_features.columns]
    lap_features.columns = [col if col != 'vehicle_number_' else 'vehicle_number' for col in lap_features.columns]
    lap_features.columns = [col if col != 'lap_' else 'lap' for col in lap_features.columns]
    
    print(f"   ✅ Lap-level features shape: {lap_features.shape}")
    print(f"   ✅ Features per lap: {len(lap_features.columns) - 3}")
    
    # ============================================================================
    # STEP 5: SAVE PROCESSED DATA
    # ============================================================================
    
    print(f"\n6️⃣  Saving processed data...")
    
    # Save 1Hz telemetry (for detailed analysis)
    output_1hz = os.path.join(OUTPUT_FOLDER, f"{track_name.lower().replace(' ', '_')}_{race_name.lower()}_telemetry_1hz.csv")
    telemetry_1hz.to_csv(output_1hz, index=False)
    print(f"   ✅ Saved 1Hz telemetry: {output_1hz} ({os.path.getsize(output_1hz) / 1024 / 1024:.1f} MB)")
    
    # Save lap-level features
    output_lap = os.path.join(OUTPUT_FOLDER, f"{track_name.lower().replace(' ', '_')}_{race_name.lower()}_lap_features.csv")
    lap_features.to_csv(output_lap, index=False)
    print(f"   ✅ Saved lap features: {output_lap} ({os.path.getsize(output_lap) / 1024:.1f} KB)")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Processing complete in {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    
    return telemetry_1hz, lap_features

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    
    datasets = [
        (SONOMA_R1_TELEM, "Sonoma", "R1"),
        # (ROAD_AMERICA_R1_TELEM, "Road America", "R1"),
    ]
    
    all_lap_features = []
    
    for file_path, track, race in datasets:
        if os.path.exists(file_path):
            _, lap_feat = process_telemetry_file(file_path, track, race)
            all_lap_features.append(lap_feat)
        else:
            print(f"\n⚠️  File not found: {file_path}")
    
    # Combine all lap features
    if all_lap_features:
        combined_lap_features = pd.concat(all_lap_features, ignore_index=True)
        output_combined = os.path.join(OUTPUT_FOLDER, "all_tracks_lap_features_combined.csv")
        combined_lap_features.to_csv(output_combined, index=False)
        
        print(f"\n{'='*100}")
        print("🎉 ALL PROCESSING COMPLETE!")
        print(f"{'='*100}")
        print(f"\n📊 SUMMARY:")
        print(f"   Total laps processed: {len(combined_lap_features)}")
        print(f"   Total features per lap: {len(combined_lap_features.columns) - 3}")
        print(f"   Output folder: {OUTPUT_FOLDER}/")
        print(f"\n✅ Next step: Merge with lap times and compute final CLI scores")
