# scripts.py

import pandas as pd
import os

# ============================================================================
# TELEMETRY DATA INSPECTION SCRIPT
# ============================================================================

# PATHS TO FOLDERS
sonoma_r1_folder = "C:/Racing AI/Sonoma/Race 1"
sonoma_r2_folder = "C:/Racing AI/Sonoma/Race 2"
road_america_r1_folder = "C:/Racing AI/Road America/Race 1"
road_america_r2_folder = "C:/Racing AI/Road America/Race 2"

# Number of rows to sample 
SAMPLE_ROWS = 20

# ============================================================================
# FUNCTION TO ANALYZE TELEMETRY FILE
# ============================================================================

def analyze_telemetry(file_path, track_name, race_name):
    """Analyze telemetry file and extract key info"""
    print("=" * 100)
    print(f"📊 {track_name} - {race_name} TELEMETRY")
    print("=" * 100)
    
    try:
        # Load first N rows
        df = pd.read_csv(file_path, nrows=SAMPLE_ROWS)
        
        # Basic info
        print(f"\n✅ File loaded successfully")
        print(f"   Total columns: {len(df.columns)}")
        
        # Show all column names
        print(f"\n📋 COLUMN NAMES ({len(df.columns)} total):")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i:2d}. {col}")
        
        # Show data types
        print(f"\n📊 DATA TYPES:")
        print(df.dtypes)
        
        # Show sample data
        print(f"\n🔍 FIRST {SAMPLE_ROWS} ROWS:")
        print(df.to_string())
        
        # Get file size and estimate total rows
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"\n📦 FILE INFO:")
        print(f"   Size: {file_size_mb:.2f} MB")
        
        # Count total rows 
        with open(file_path, 'r') as f:
            total_rows = sum(1 for line in f) - 1  # minus header
        print(f"   Total rows: {total_rows:,}")
        print(f"   Sampling frequency estimate: ~{total_rows / (30*60):.1f} Hz (assuming 30-min race)")
        
        # Check for key columns we need
        print(f"\n🔍 KEY COLUMN DETECTION:")
        key_columns = {
            'Throttle': ['throttle', 'tps', 'gas', 'accelerator'],
            'Brake': ['brake', 'brake_pressure', 'brk'],
            'Steering': ['steering', 'steer', 'wheel_angle'],
            'Lat Accel': ['lat_accel', 'lateral_accel', 'latg', 'ay'],
            'Long Accel': ['long_accel', 'longitudinal_accel', 'longg', 'ax'],
            'Speed': ['speed', 'velocity', 'kph', 'mph'],
            'Timestamp': ['time', 'timestamp', 'elapsed'],
            'Vehicle ID': ['vehicle', 'car', 'driver', 'number']
        }
        
        for key_name, possible_names in key_columns.items():
            found = [col for col in df.columns if any(pn.lower() in col.lower() for pn in possible_names)]
            if found:
                print(f"   ✅ {key_name:15s}: {found}")
            else:
                print(f"   ❌ {key_name:15s}: NOT FOUND")
        
        # Export sample to CSV
        output_filename = f"{track_name.lower().replace(' ', '_')}_{race_name.lower()}_telemetry_SAMPLE.csv"
        df.to_csv(output_filename, index=False)
        print(f"\n💾 Sample exported: {output_filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR loading file: {e}")
        return False

# ============================================================================
# ANALYZE ALL TELEMETRY FILES
# ============================================================================

print("\n" + "🚀" * 50)
print("GR CUP TELEMETRY DATA ANALYSIS")
print("🚀" * 50 + "\n")

# Define all telemetry files to check
telemetry_files = [
    (os.path.join(sonoma_r1_folder, "sonoma_telemetry_R1.csv"), "Sonoma", "R1"),
    (os.path.join(sonoma_r2_folder, "sonoma_telemetry_R2.csv"), "Sonoma", "R2"),
    (os.path.join(road_america_r1_folder, "R1_road_america_telemetry_data.csv"), "Road America", "R1"),
    (os.path.join(road_america_r2_folder, "R2_road_america_telemetry_data.csv"), "Road America", "R2"),
]

successful = 0
failed = 0

for file_path, track, race in telemetry_files:
    if os.path.exists(file_path):
        if analyze_telemetry(file_path, track, race):
            successful += 1
        else:
            failed += 1
        print("\n")
    else:
        print(f"⚠️  File not found: {file_path}")
        failed += 1

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 100)
print("📊 ANALYSIS SUMMARY")
print("=" * 100)
print(f"✅ Successfully analyzed: {successful} files")
print(f"❌ Failed/Not found: {failed} files")
print(f"\n💾 Sample CSV files created in current directory:")
print(f"   - sonoma_r1_telemetry_SAMPLE.csv")
print(f"   - sonoma_r2_telemetry_SAMPLE.csv")
print(f"   - road_america_r1_telemetry_SAMPLE.csv")
print(f"   - road_america_r2_telemetry_SAMPLE.csv")

