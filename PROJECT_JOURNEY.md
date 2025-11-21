# Racing AI - Project Journey Documentation

**From Raw Telemetry Data to Production-Ready ML System**

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Starting Point](#starting-point)
3. [Phase 1: Data Exploration & Understanding](#phase-1-data-exploration--understanding)
4. [Phase 2: Data Processing Pipeline](#phase-2-data-processing-pipeline)
5. [Phase 3: CLI Scoring System](#phase-3-cli-scoring-system)
6. [Phase 4: Machine Learning Models](#phase-4-machine-learning-models)
7. [Phase 5: Application Development](#phase-5-application-development)
8. [Current Status & Achievements](#current-status--achievements)
9. [Technologies Used](#technologies-used)
10. [Next Steps](#next-steps)

---

## Project Overview

**Goal:** Build an AI-powered system to monitor and predict driver cognitive load in real-time for GR Cup racing series, enabling teams to optimize driver performance and prevent focus-related incidents.

**Core Innovation:** Cognitive Load Index (CLI) - a composite metric combining throttle jerk, steering entropy, micro-variability, brake spikes, and speed variance to quantify driver mental state.

---

## Starting Point

### Initial Data Assets
- **4 Race Datasets** (2 tracks × 2 races):
  - Sonoma Raceway: Race 1 & Race 2
  - Road America: Race 1 & Race 2

- **Data Types per Race:**
  - High-frequency telemetry data (~5-15 kHz sampling rate)
  - CSV files ranging 1-3 GB each
  - Lap time analysis with sector breakdowns
  - Weather data

### Initial Challenges
1. **Massive data volume**: Multi-gigabyte files with millions of rows
2. **Long format structure**: Telemetry stored as name-value pairs (not analysis-ready)
3. **Unknown column structures**: Different naming conventions across tracks
4. **High sampling frequency**: 5-15 kHz data too granular for cognitive load analysis
5. **No established CLI metric**: Had to develop scoring methodology from scratch

---

## Phase 1: Data Exploration & Understanding

### Script: `script_samples.py`

**Purpose:** Understand data structure before processing

**Key Actions:**
- Inspected all 4 telemetry files
- Identified column naming conventions
- Detected key telemetry channels:
  - Throttle position (`ath`)
  - Brake pressure (`pbrake_f`)
  - Steering angle (`Steering_Angle`)
  - Lateral/longitudinal acceleration (`accy_can`, `accx_can`)
  - Speed (`speed`)
  - Vehicle identifiers and timestamps
- Generated sample CSVs for quick reference
- Calculated file sizes and estimated sampling rates

**Output:**
- `sonoma_r1_telemetry_SAMPLE.csv`
- `sonoma_r2_telemetry_SAMPLE.csv`
- `road_america_r1_telemetry_SAMPLE.csv`
- `road_america_r2_telemetry_SAMPLE.csv`

**Key Insights:**
- Data is in "long format" (telemetry_name, telemetry_value pairs)
- Timestamps allow per-vehicle time-series reconstruction
- Need to pivot to "wide format" for feature engineering
- ~30-minute races with millions of samples per vehicle

---

## Phase 2: Data Processing Pipeline

### Script: `process_telemetry.py`

**Purpose:** Transform raw telemetry into analysis-ready features

### Processing Steps

#### 2.1 Data Loading & Pivoting
- **Challenge:** 1-3 GB files, long format with duplicates
- **Solution:** Chunk-based processing (100,000 rows/chunk)
- **Transformation:** Pivoted from long to wide format
  - Before: `[timestamp, vehicle_id, telemetry_name, telemetry_value]`
  - After: `[timestamp, vehicle_id, ath, pbrake_f, Steering_Angle, speed, ...]`

#### 2.2 Downsampling (5-15 kHz → 1 Hz)
- **Why:** Human cognitive processes operate on ~1-second timescales
- **Method:** Per-vehicle resampling with mean aggregation
- **Benefit:** Reduced data by 5,000-15,000× while preserving cognitive patterns

#### 2.3 CLI Feature Engineering

**Control-Signal Metrics:**
1. **ThrottleJerk** = mean(|Δthrottle/Δt|)
   - Measures throttle control smoothness
   - Higher jerk = more erratic inputs

2. **BrakeSpikeRate** = count(|Δbrake| > 0.5 bar) per 5s window
   - Detects abrupt braking events
   - Proxy for surprise reactions

3. **SteerEntropy** = Shannon entropy of steering bins (10° increments)
   - Quantifies steering indecision
   - Higher entropy = less decisive corrections

**Micro-Variability Metrics:**
4. **MicroVariability** = mean(std[throttle, steer, latAccel] @ 1s windows)
   - Captures micro-corrections
   - High variability = less smooth control

5. **Speed Features:**
   - `speed_change`: First derivative of speed
   - `speed_rolling_mean`: 5-second average

#### 2.4 Lap-Level Aggregation
- Grouped all 1Hz features by `(vehicle_id, vehicle_number, lap)`
- Computed statistics: mean, std, min, max for each feature
- Generated **27 features per lap**

### Output Files
- `sonoma_r1_telemetry_1hz.csv` (1Hz time-series data)
- `sonoma_r1_lap_features.csv` (lap-aggregated features)
- `all_tracks_lap_features_combined.csv` (multi-track dataset)

**Processing Stats:**
- Reduced Sonoma R1 from ~1.2 GB to ~15 MB (80× compression)
- Processing time: ~2-5 minutes per race
- Generated features for 640 total laps

---

## Phase 3: CLI Scoring System

### Script: `step1_integrate_and_score.py`

**Purpose:** Merge telemetry features with lap times and compute Cognitive Load Index scores

### Data Integration

#### 3.1 Multi-Source Merging
- **Lap Features** (from Phase 2) + **Lap Times** (semicolon-delimited CSV)
- **Weather Data** (air temp, track temp, humidity)
- Merged on `(vehicle_number, lap)` keys
- Result: 640 laps with complete feature set

#### 3.2 CLI Score Computation

**Formula:** Hybrid weighted z-score approach

```python
CLI_raw = 0.30 × z_ThrottleJerk
        + 0.25 × z_SteerEntropy
        + 0.20 × z_MicroVar
        + 0.15 × z_BrakeSpike
        + 0.10 × z_SpeedVar
```

**Normalization:**
- Z-scores computed **per-driver** (within-subject normalization)
- CLI_raw scaled to 0-100 range
- **FocusScore** = 100 - CLI (inverted: 100 = perfect focus)
- Smoothed via 3-lap rolling average

**Key Insight:** Per-driver normalization accounts for individual driving styles

#### 3.3 Rule-Based Alert Engine

**Alert Triggers:**
1. **Error Burst** (HIGH): BrakeSpike + ThrottleJerk both >75th percentile
   - Action: "Suggest 1-lap cool down"

2. **Steering Indecision** (CRITICAL): SteerEntropy >90th percentile
   - Action: "Check driver fatigue or track confidence"

3. **Focus Drop** (WARNING): FocusScore drops >10 points in 2 laps
   - Action: "Consider radio reminder"

4. **Degrading Consistency**: Speed std >80th percentile + MicroVar >0
   - Action: "Review sector-specific issues"

**Alert Levels:** 0 (none) → 3 (critical)

#### 3.4 ML Training Label Generation

**3 Target Variables Created:**

1. **`focus_drop_next`** (binary):
   - 1 if FocusScore drops >15 points in next lap
   - 2.7% positive class (17/640 laps)
   - For classification model

2. **`mistake_event`** (binary):
   - 1 if lap time deviates >95th percentile from baseline
   - OR speed_min <5th percentile
   - OR extreme brake spikes
   - Proxy for driver errors

3. **`load_level`** (categorical):
   - Low / Medium / High (33%/33%/33% split)
   - Based on CLI_normalized bins

### Output
- `cli_complete_dataset.csv` (640 laps, 50+ features)

**Summary Stats:**
- Mean Focus Score: 67.3/100
- Focus drops: 17 events (2.7%)
- Mistakes: 58 events (9.1%)
- Alerts triggered: 156 (24.4% of laps)

---

## Phase 4: Machine Learning Models

### Script: `step2_train_models_with_gridsearch.py`

**Purpose:** Train optimized ML models to predict focus drops and score cognitive load

### Model Architecture

#### 4.1 Focus Drop Classifier (XGBoost)
**Task:** Predict if driver's focus will drop significantly in next lap

**GridSearchCV Configuration:**
- **Parameter Grid:**
  - `n_estimators`: [50, 100, 200]
  - `max_depth`: [3, 5, 7]
  - `learning_rate`: [0.01, 0.1, 0.3]
  - `subsample`: [0.8, 1.0]
  - `colsample_bytree`: [0.8, 1.0]
  - `scale_pos_weight`: [35.57] (class imbalance handling)
- **Total combinations:** 108
- **Cross-validation:** 3-fold stratified

**Optimal Hyperparameters:**
- `n_estimators`: 50
- `max_depth`: 3
- `learning_rate`: 0.01
- `subsample`: 0.8
- `colsample_bytree`: 1.0

**Performance:**
- **Training:** 512 samples (2.7% positive)
- **Test:** 128 samples
- **CV ROC-AUC:** 0.955
- **Test ROC-AUC:** 0.966 ⭐

**Top 5 Predictive Features:**
1. `FocusScore_smooth` (44.7%)
2. `BrakeSpikeRate_5s_mean` (7.5%)
3. `SteerEntropy_10s_mean` (7.4%)
4. `CLI_raw` (6.5%)
5. `ThrottleJerk_1s_max` (4.6%)

#### 4.2 Focus Score Regressor (XGBoost)
**Task:** Predict next lap's focus score (0-100 continuous)

**GridSearchCV Configuration:**
- Same parameter space as classifier (108 combinations)
- Scoring metric: R²

**Optimal Hyperparameters:**
- `n_estimators`: 50
- `max_depth`: 3
- `learning_rate`: 0.1
- `subsample`: 0.8
- `colsample_bytree`: 0.8

**Performance:**
- **CV R²:** 0.687
- **Test R²:** 0.718
- **Test RMSE:** 5.69 points
- Can predict focus within ±5.7 points on average

#### 4.3 Anomaly Detector (Isolation Forest)
**Task:** Detect unusual driving patterns that deviate from driver baseline

**Parameter Tuning:**
- Tested 12 combinations (contamination × n_estimators)
- Trained on "good" laps (FocusScore >50th percentile, no mistakes)
- 320 good laps used for training

**Optimal Parameters:**
- `contamination`: 0.05
- `n_estimators`: 50

**Results:**
- Detected 37 anomalous laps (5.8% of dataset)
- Flags laps with unusual control patterns even if lap time is acceptable

#### 4.4 Explainability (SHAP)
- Generated SHAP TreeExplainer for classifier
- Computed SHAP values for 50-sample test set
- Saved for future model interpretation

### Model Artifacts
**Saved to `models/` folder:**
- `focus_drop_classifier.pkl`
- `focus_score_regressor.pkl`
- `anomaly_detector.pkl`
- `gridsearch_results_classifier.csv`
- `gridsearch_results_regressor.csv`
- `shap_explainer.pkl`
- `shap_sample_values.pkl`
- `MODEL_CARD.md` (detailed documentation)

---

## Phase 5: Application Development

### Backend (FastAPI)
**Location:** `backend/`

**Components:**
- `app.py`: FastAPI application entry point
- `api/`: REST API endpoints
- `core/`: Core business logic
- `utils/`: Utility functions

**Capabilities:**
- Load trained models
- Process telemetry uploads
- Run real-time predictions
- Generate alerts and recommendations

### Frontend (Flask + Streamlit)
**Location:** `frontend_flask/`

**Components:**
- `app.py`: Flask application
- `templates/`: HTML templates
- `static/`: CSS, JS, images
- `requirements.txt`: Frontend dependencies

**Features:**
- Dashboard for live monitoring
- Lap-by-lap focus score visualization
- Alert notifications
- Driver performance analytics

---

## Current Status & Achievements

### What's Been Built

#### Data Pipeline ✅
- Automated processing for multi-gigabyte telemetry files
- Chunk-based loading prevents memory overflow
- Downsampling to 1Hz preserves cognitive patterns
- 27 engineered features per lap

#### CLI Metric System ✅
- Novel Cognitive Load Index formula
- Per-driver z-score normalization
- 3-lap smoothing for stability
- Rule-based alert engine with 4 trigger types

#### Machine Learning ✅
- **3 Production Models:**
  1. Focus Drop Classifier (96.6% AUC)
  2. Focus Score Regressor (R²=0.718, RMSE=5.69)
  3. Anomaly Detector (5% contamination)
- Hyperparameter optimization via GridSearchCV
- 3-fold cross-validation
- SHAP explainability support

#### Processed Datasets ✅
- `sonoma_r1_telemetry_1hz.csv` (1Hz time-series)
- `sonoma_r1_lap_features.csv` (lap aggregates)
- `cli_complete_dataset.csv` (640 laps, 50+ features)
- `cli_complete_dataset_with_predictions.csv` (with ML outputs)

#### Application Infrastructure ✅
- FastAPI backend
- Flask frontend
- Model serving pipeline
- REST API endpoints

---

## Technologies Used

### Data Processing
- **pandas** - Data manipulation and CSV handling
- **numpy** - Numerical computations
- **scipy** - Statistical functions (entropy, z-scores)

### Machine Learning
- **scikit-learn** - Train/test splits, GridSearchCV, preprocessing
- **XGBoost** - Gradient boosting for classification & regression
- **SHAP** - Model explainability

### Application Stack
- **FastAPI** - High-performance async API backend
- **Flask** - Web application framework
- **Streamlit** - Interactive dashboards
- **Uvicorn** - ASGI server

### Visualization
- **plotly** - Interactive charts

---

## Next Steps

### Short-Term (1-2 weeks)
1. **Multi-Track Training:**
   - Process Road America data (R1 & R2)
   - Combine with Sonoma for 4-track dataset
   - Retrain models on ~2,500 laps

2. **Real-Time Integration:**
   - Test live telemetry ingestion
   - Implement streaming predictions (lap-by-lap)
   - Add WebSocket support for live dashboard updates

3. **Alert Refinement:**
   - A/B test alert thresholds
   - Reduce false positive rate
   - Add driver-specific baselines

### Medium-Term (1-2 months)
4. **Driver Personalization:**
   - Per-driver model fine-tuning
   - Baseline drift detection (track learning curve)
   - Customizable alert sensitivity

5. **Advanced Features:**
   - Track sector-specific CLI (Turn 1, Turn 2, etc.)
   - Stint-level fatigue modeling
   - Weather impact quantification

6. **Deployment:**
   - Dockerize application
   - Set up CI/CD pipeline
   - Deploy to cloud (AWS/GCP)

### Long-Term (3-6 months)
7. **Expand to Other Series:**
   - IMSA, Formula Regional, GT World Challenge
   - Cross-series model transfer learning

8. **Integrate with Team Systems:**
   - Live timing integration (RaceCapture, AIM)
   - Pit-to-car radio triggers
   - Post-race debrief automation

9. **Research Extensions:**
   - EEG/biometric data fusion (if available)
   - Predictive maintenance (tire/brake wear correlation)
   - Optimal strategy recommendations

---

## File Structure Summary

```
Racing AI/
│
├── process_telemetry.py              # Phase 2: Raw → 1Hz + lap features
├── script_samples.py                 # Phase 1: Data exploration
├── step1_integrate_and_score.py     # Phase 3: CLI scoring + labels
├── step2_train_models_with_gridsearch.py  # Phase 4: ML models
│
├── processed_data/                   # Intermediate datasets
│   ├── sonoma_r1_telemetry_1hz.csv
│   ├── sonoma_r1_lap_features.csv
│   ├── cli_complete_dataset.csv
│   └── cli_complete_dataset_with_predictions.csv
│
├── models/                           # Trained models + docs
│   ├── focus_drop_classifier.pkl
│   ├── focus_score_regressor.pkl
│   ├── anomaly_detector.pkl
│   ├── gridsearch_results_*.csv
│   ├── shap_explainer.pkl
│   └── MODEL_CARD.md
│
├── backend/                          # FastAPI application
│   ├── app.py
│   ├── api/
│   ├── core/
│   └── utils/
│
├── frontend_flask/                   # Flask web interface
│   ├── app.py
│   ├── templates/
│   └── static/
│
├── Sonoma/                           # Raw data (Race 1 & 2)
├── Road America/                     # Raw data (Race 1 & 2)
│
└── requirements.txt                  # Python dependencies
```

---

## Key Achievements Recap

1. **Processed 1-3 GB raw files** → Manageable 15 MB datasets (80× compression)
2. **Engineered 27 cognitive load features** from high-frequency telemetry
3. **Developed novel CLI metric** with proven discriminative power
4. **Trained 3 models with 96.6% AUC** for focus drop prediction
5. **Built end-to-end ML pipeline** from data → models → API → UI
6. **Created production-ready system** for real-time driver monitoring

---

**Project Status:** ✅ **MVP Complete** - Ready for pilot deployment

**Next Milestone:** Integrate real-time telemetry stream for live race monitoring

---

*Document Version: 1.0*
*Last Updated: November 20, 2025*
