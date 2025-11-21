"""
Flask Backend for GR Cup CLI Monitor
Modern web dashboard with real-time replay controls
"""
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import pandas as pd
import requests
import json
from pathlib import Path
import logging
import numpy as np
import pandas as pd


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'racing-ai-dashboard-secret-key-2025'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Load data at startup
DATA_PATH = Path(__file__).parent.parent / 'processed_data'
df = None
driver_baselines = {}

def load_data():
    """Load processed data and driver baselines"""
    global df, driver_baselines

    try:
        df = pd.read_csv(DATA_PATH / 'cli_complete_dataset_with_predictions.csv')
        logger.info(f"✅ Loaded dataset: {len(df)} rows")

        with open(DATA_PATH / 'driver_baselines.json', 'r') as f:
            driver_baselines = json.load(f)
        logger.info(f"✅ Loaded baselines for {len(driver_baselines)} drivers")

        return True
    except Exception as e:
        logger.error(f"❌ Failed to load data: {e}")
        return False

# Load data on startup
load_data()

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'data_loaded': df is not None,
        'drivers_count': len(df['vehicle_number'].unique()) if df is not None else 0, 
        'baselines_count': len(driver_baselines)
    })

@app.route('/api/drivers')
def get_drivers():
    """Get list of available drivers"""
    if df is None:
        return jsonify({'error': 'Data not loaded'}), 500

    drivers = sorted(df['vehicle_number'].unique().tolist())
    return jsonify(drivers)

@app.route('/api/driver/<int:driver_id>/data')
def get_driver_data(driver_id):
    """Get all lap data for a specific driver - WITH NaN HANDLING"""
    if df is None:
        return jsonify({'error': 'Data not loaded'}), 500

    driver_data = df[df['vehicle_number'] == driver_id].sort_values('lap')

    if len(driver_data) == 0:
        return jsonify({'error': f'No data found for driver {driver_id}'}), 404

    # Convert DataFrame to records and handle NaN values
    records = driver_data.replace({np.nan: None}).to_dict(orient='records')
    
    # Ensure all numeric values are JSON serializable
    for record in records:
        for key, value in record.items():
            if isinstance(value, (np.integer, np.int64)):
                record[key] = int(value)
            elif isinstance(value, (np.floating, np.float64)):
                record[key] = float(value) if not np.isnan(value) else None
            elif isinstance(value, np.bool_):
                record[key] = bool(value)

    return jsonify({
        'success': True,
        'data': records,
        'min_lap': int(driver_data['lap'].min()),
        'max_lap': int(driver_data['lap'].max()),
        'total_laps': len(driver_data)
    })

@app.route('/api/driver/<int:driver_id>/lap/<int:lap_number>')
def get_lap_data(driver_id, lap_number):
    """Get data for a specific lap - WITH NaN HANDLING"""
    if df is None:
        return jsonify({'error': 'Data not loaded'}), 500

    lap_data = df[(df['vehicle_number'] == driver_id) & (df['lap'] == lap_number)]

    if len(lap_data) == 0:
        return jsonify({'error': f'No data found for driver {driver_id}, lap {lap_number}'}), 404

    # Handle NaN values in the single record
    record = lap_data.iloc[0].replace({np.nan: None}).to_dict()
    
    # Ensure JSON serializability
    for key, value in record.items():
        if isinstance(value, (np.integer, np.int64)):
            record[key] = int(value)
        elif isinstance(value, (np.floating, np.float64)):
            record[key] = float(value) if value is not None and not np.isnan(value) else None
        elif isinstance(value, np.bool_):
            record[key] = bool(value)

    return jsonify({
        'success': True,
        'data': record
    })

@app.route('/api/driver/<int:driver_id>/baseline')
def get_driver_baseline(driver_id):
    """Get personalized baseline for driver"""
    baseline = driver_baselines.get(str(driver_id), None)

    if baseline:
        return jsonify({
            'success': True,
            'baseline': baseline,
            'driver_id': driver_id
        })

    return jsonify({
        'success': False,
        'message': f'No baseline found for driver {driver_id}'
    }), 404

@app.route('/api/drivers/compare', methods=['POST'])
def compare_drivers():
    """Get comparison data for multiple drivers"""
    if df is None:
        return jsonify({'error': 'Data not loaded'}), 500

    driver_ids = request.json.get('driver_ids', [])

    if not driver_ids:
        return jsonify({'error': 'No driver IDs provided'}), 400

    comparison_data = {}
    for driver_id in driver_ids:
        driver_data = df[df['vehicle_number'] == driver_id].sort_values('lap')
        if len(driver_data) > 0:
            comparison_data[driver_id] = {
                'laps': driver_data['lap'].tolist(),
                'focus_scores': driver_data['FocusScore_smooth'].tolist(),
                'avg_focus': float(driver_data['FocusScore_smooth'].mean()),
                'focus_drops': int(driver_data['focus_drop_next'].sum()),
                'mistakes': int(driver_data['mistake_event'].sum())
            }

    return jsonify({
        'success': True,
        'data': comparison_data
    })

@app.route('/api/ml/health')
def ml_health():
    """Check ML API health"""
    try:
        response = requests.get('http://localhost:8001/api/v1/cli/health', timeout=2)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 503

@app.route('/api/ml/predict', methods=['POST'])
def ml_predict():
    """Proxy ML predictions to FastAPI backend"""
    try:
        response = requests.post(
            'http://localhost:8001/api/v1/cli/score',
            json=request.json,
            timeout=5
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({
            'error': 'ML API unavailable',
            'message': str(e)
        }), 503

# ============================================================================
# WEBSOCKET EVENTS (for real-time sync - optional)
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected')
    emit('connected', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')

@socketio.on('replay_start')
def handle_replay_start(data):
    """Broadcast replay start to all clients"""
    emit('replay_started', data, broadcast=True, include_self=False)

@socketio.on('lap_change')
def handle_lap_change(data):
    """Broadcast lap change to all clients"""
    emit('lap_changed', data, broadcast=True, include_self=False)

@socketio.on('playback_state')
def handle_playback_state(data):
    """Broadcast playback state change"""
    emit('playback_updated', data, broadcast=True, include_self=False)

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🏎️  GR Cup CLI Monitor - Flask Edition")
    print("="*60)
    print(f"📊 Dashboard: http://localhost:5000")
    print(f"🔗 API Docs:  http://localhost:5000/api/health")
    print(f"🚀 Status:    Flask + SocketIO + Plotly.js")
    print("="*60 + "\n")

    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True  # For development only
    )
