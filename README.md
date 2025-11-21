# Racing AI - Cognitive Load Monitoring for Motorsport

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-ML-green.svg)](https://xgboost.readthedocs.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **AI-powered driver cognitive load monitoring system for GR Cup racing series, enabling real-time focus prediction and performance optimization.**

---

## Overview

Racing AI is a machine learning system that analyzes high-frequency telemetry data to predict driver cognitive load, focus drops, and performance degradation in real-time. By combining control-signal analysis, micro-variability detection, and predictive modeling, the system helps racing teams optimize driver performance and prevent focus-related incidents.

### Key Features

- **Cognitive Load Index (CLI)**: Novel metric quantifying driver mental state from telemetry
- **Focus Drop Prediction**: 96.6% AUC classifier predicting attention lapses 1-2 laps ahead
- **Real-Time Monitoring**: Live dashboard with lap-by-lap focus scores and alerts
- **Anomaly Detection**: Identifies unusual driving patterns beyond lap time analysis
- **Explainable AI**: SHAP values provide interpretable model decisions

---

## Problem Statement

In endurance racing, driver cognitive load directly impacts performance and safety. Traditional telemetry analysis focuses on lap times and car setup, but ignores the **driver's mental state**. Key challenges:

1. **Focus degradation is invisible** until it manifests as mistakes or crashes
2. **Lap times lag behind cognitive state** (fatigue occurs before time loss)
3. **Human observation is subjective** and can't process high-frequency data
4. **No quantitative metric** exists for real-time cognitive load

**Racing AI solves this** by computing a Cognitive Load Index from control inputs (throttle, brake, steering) at 1Hz frequency, enabling predictive intervention before performance degrades.

---

## How It Works

### 1. Data Processing Pipeline

```
Raw Telemetry (5-15 kHz, 1-3 GB)
    ↓
Pivot to Wide Format (vehicle × time × channels)
    ↓
Downsample to 1Hz (cognitive timescale)
    ↓
Feature Engineering (27 CLI features)
    ↓
Lap-Level Aggregation
```

**Processed Features:**
- **Control-Signal Metrics**: ThrottleJerk, BrakeSpikeRate, SteerEntropy
- **Micro-Variability**: Throttle/Steer/LatAccel standard deviations
- **Performance Metrics**: Speed, acceleration, lap time deviations

### 2. Cognitive Load Index (CLI)

The CLI is a weighted composite of five components:

```python
CLI = 0.30 × ThrottleJerk_z
    + 0.25 × SteerEntropy_z
    + 0.20 × MicroVariability_z
    + 0.15 × BrakeSpike_z
    + 0.10 × SpeedVar_z
```

- Z-scores computed **per-driver** for within-subject normalization
- FocusScore = 100 - CLI (100 = perfect focus, 0 = high load)
- 3-lap smoothing reduces noise

### 3. Machine Learning Models

#### Focus Drop Classifier (XGBoost)
- **Task**: Predict if focus will drop >15 points in next 1-2 laps
- **Performance**: 96.6% AUC, 95.5% CV AUC
- **Use Case**: Early warning system for team radio intervention

#### Focus Score Regressor (XGBoost)
- **Task**: Predict next lap's focus score (0-100 continuous)
- **Performance**: R²=0.718, RMSE=5.69 points
- **Use Case**: Continuous monitoring and trend analysis

#### Anomaly Detector (Isolation Forest)
- **Task**: Flag unusual driving patterns
- **Performance**: 5.8% anomaly rate (37/640 laps)
- **Use Case**: Detect hidden issues (setup, track conditions, driver state)

All models optimized via **GridSearchCV** with 3-fold cross-validation.

---

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

1. **Clone the repository:**
```bash
git clone https://github.com/mignoncharly/racing-ai.git
cd racing-ai
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Download sample data** (optional):
```bash
# Place raw telemetry CSVs in:
# - Sonoma/Race 1/
# - Sonoma/Race 2/
# - Road America/Race 1/
# - Road America/Race 2/
```

---

## Quick Start

### Process Telemetry Data

```bash
python process_telemetry.py
```

**Output:**
- `processed_data/sonoma_r1_telemetry_1hz.csv` (1Hz time-series)
- `processed_data/sonoma_r1_lap_features.csv` (lap-level features)

### Compute CLI Scores

```bash
python step1_integrate_and_score.py
```

**Output:**
- `processed_data/cli_complete_dataset.csv` (CLI scores + alerts + labels)

### Train ML Models

```bash
python step2_train_models_with_gridsearch.py
```

**Output:**
- `models/focus_drop_classifier.pkl`
- `models/focus_score_regressor.pkl`
- `models/anomaly_detector.pkl`
- `models/MODEL_CARD.md` (performance documentation)

### Launch API Backend

```bash
cd backend
uvicorn app:app --reload
```

API available at `http://localhost:8000`

### Launch Web Dashboard

```bash
cd frontend_flask
python app.py
```

Dashboard available at `http://localhost:5000`

---

## Usage Examples

### 1. Process New Telemetry File

```python
from process_telemetry import process_telemetry_file

telemetry_1hz, lap_features = process_telemetry_file(
    file_path="path/to/telemetry.csv",
    track_name="Sonoma",
    race_name="R1"
)
```

### 2. Compute CLI Score for a Lap

```python
import pandas as pd
from step1_integrate_and_score import compute_cli_score

lap_data = pd.read_csv("processed_data/sonoma_r1_lap_features.csv")
cli_scores = compute_cli_score(lap_data)
```

### 3. Predict Focus Drop

```python
import pickle
import pandas as pd

# Load model
with open("models/focus_drop_classifier.pkl", "rb") as f:
    model = pickle.load(f)

# Load features
X = pd.read_csv("processed_data/cli_complete_dataset.csv")[feature_cols]

# Predict
focus_drop_prob = model.predict_proba(X)[:, 1]
```

### 4. API Request (Real-Time Prediction)

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "throttle_jerk": 0.45,
    "steer_entropy": 2.3,
    "micro_var": 0.12,
    "brake_spike": 3,
    "speed_var": 5.2
  }'
```

**Response:**
```json
{
  "focus_score": 72.4,
  "focus_drop_prob": 0.12,
  "is_anomaly": false,
  "alert_level": 1,
  "action": "Maintain current pace"
}
```

---

## Project Structure

```
racing-ai/
│
├── process_telemetry.py              # Data processing pipeline
├── script_samples.py                 # Data exploration utilities
├── step1_integrate_and_score.py     # CLI computation + labeling
├── step2_train_models_with_gridsearch.py  # Model training
│
├── processed_data/                   # Processed datasets
│   ├── sonoma_r1_telemetry_1hz.csv
│   ├── sonoma_r1_lap_features.csv
│   ├── cli_complete_dataset.csv
│   └── cli_complete_dataset_with_predictions.csv
│
├── models/                           # Trained models
│   ├── focus_drop_classifier.pkl
│   ├── focus_score_regressor.pkl
│   ├── anomaly_detector.pkl
│   └── MODEL_CARD.md
│
├── backend/                          # FastAPI application
│   ├── app.py
│   ├── api/
│   ├── core/
│   └── utils/
│
├── frontend_flask/                   # Web dashboard
│   ├── app.py
│   ├── templates/
│   └── static/
│
├── tests/                            # Unit tests
├── docs/                             # Documentation
├── requirements.txt                  # Dependencies
└── README.md                         # This file
```

---

## Performance Metrics

### Model Performance (640-lap Sonoma dataset)

| Model | Metric | Score |
|-------|--------|-------|
| **Focus Drop Classifier** | Test ROC-AUC | **96.6%** |
| | Cross-Val AUC | 95.5% |
| | Training Samples | 512 (2.7% positive) |
| **Focus Score Regressor** | Test R² | **0.718** |
| | RMSE | 5.69 points |
| | Cross-Val R² | 0.687 |
| **Anomaly Detector** | Contamination | 5% |
| | Anomalies Detected | 37/640 laps |

### Alert System (Rule-Based Engine)

| Alert Type | Trigger Condition | Action Recommended |
|------------|-------------------|-------------------|
| **Error Burst** | BrakeSpike + ThrottleJerk both >75th% | Suggest 1-lap cool down |
| **Steering Indecision** | SteerEntropy >90th% | Check driver fatigue |
| **Focus Drop** | FocusScore drops >10 pts in 2 laps | Radio reminder |
| **Degrading Consistency** | Speed std >80th% + MicroVar >0 | Review sector issues |

**Alert Statistics:**
- Total alerts: 156/640 laps (24.4%)
- Critical alerts (level 2+): 38 laps
- Focus drops: 17 events (2.7%)
- Mistake events: 58 laps (9.1%)

---

## Data Sources

This project uses telemetry data from the **GR Cup racing series**:
- **Tracks**: Sonoma Raceway, Road America
- **Format**: High-frequency CSV (5-15 kHz sampling)
- **Channels**: Throttle, brake, steering, speed, G-forces, GPS
- **Lap Times**: Semicolon-delimited CSV with sector splits

**Data not included** in repository due to size (1-3 GB per race). Contact repository owner for sample datasets.

---

## Technologies

### Data Processing
- **pandas** - Data manipulation
- **numpy** - Numerical computing
- **scipy** - Statistical functions (entropy, z-scores)

### Machine Learning
- **XGBoost** - Gradient boosting (classification/regression)
- **scikit-learn** - Model selection, preprocessing
- **SHAP** - Explainable AI

### Backend
- **FastAPI** - Modern async API framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation

### Frontend
- **Flask** - Web framework
- **Streamlit** - Interactive dashboards
- **plotly** - Visualization

---

## Roadmap

### ✅ Completed
- [x] Data processing pipeline (1-3 GB → 15 MB)
- [x] CLI metric development
- [x] 3 ML models (classifier, regressor, anomaly detector)
- [x] GridSearchCV hyperparameter optimization
- [x] FastAPI backend
- [x] Flask web dashboard

### 🚧 In Progress
- [ ] Multi-track training (Road America integration)
- [ ] Real-time telemetry streaming
- [ ] WebSocket live updates

### 🔮 Future
- [ ] Driver personalization (per-driver baselines)
- [ ] Track sector-specific CLI analysis
- [ ] Stint-level fatigue modeling
- [ ] Docker deployment
- [ ] Cloud deployment (AWS/GCP)
- [ ] Integration with team telemetry systems (RaceCapture, AIM)

---

## Contributing

Contributions welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

**Areas for contribution:**
- Additional track data processing
- Model improvements (new features, architectures)
- Frontend UI/UX enhancements
- Documentation and tutorials
- Unit tests and CI/CD

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Citation

If you use this project in your research or application, please cite:

```bibtex
@software{racing_ai_2025,
  title = {Racing AI: Cognitive Load Monitoring for Motorsport},
  author = {Your Name},
  year = {2025},
  url = {https://github.com/mignoncharly/racing-ai}
}
```

---

## Acknowledgments

- **GR Cup Series** for providing telemetry data
- **XGBoost Community** for the gradient boosting framework
- **FastAPI** for the excellent async API framework
- **scikit-learn** for machine learning utilities

---

## Contact

**Project Maintainer:** Charles Nguenkam
**Email:** charles.nguenkam@gmail.com
**GitHub:** [@mignoncharly](https://github.com/mignoncharly)

For questions, issues, or collaboration inquiries, please [open an issue](https://github.com/mignoncharly/racing-ai/issues) on GitHub.

---

## Screenshots

In Screenshots directory

---


[![Star on GitHub](https://img.shields.io/github/stars/mignoncharly/racing-ai?style=social)](https://github.com/mignoncharly/racing-ai)
