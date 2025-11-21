
# GR Cup CLI Model Card (GridSearch Optimized)

## Model Summary
**Created:** 2025-10-17 18:12:32
**Framework:** XGBoost + Scikit-learn + GridSearchCV
**Purpose:** Driver Cognitive Load monitoring and focus drop prediction
**Optimization:** Hyperparameter tuning via 3-fold cross-validation

---

## Model 1: Focus Drop Classifier (OPTIMIZED)
**Type:** Binary Classification (XGBoost)
**Task:** Predict if driver's focus will drop significantly in next lap

**GridSearch Results:**
- Total combinations tested: 108
- Best CV ROC-AUC: 0.955
- Test ROC-AUC: 0.966

**Optimal Hyperparameters:**
- colsample_bytree: 1.0
- learning_rate: 0.01
- max_depth: 3
- n_estimators: 50
- scale_pos_weight: 35.57142857142857
- subsample: 0.8

**Performance:**
- Training samples: 512 (positive class: 2.7%)
- Test samples: 128
- Improvement: GridSearch selected optimal params for class imbalance

**Top 5 Features:**
               feature  importance
     FocusScore_smooth    0.447459
BrakeSpikeRate_5s_mean    0.075177
 SteerEntropy_10s_mean    0.074432
               CLI_raw    0.065287
   ThrottleJerk_1s_max    0.046309

**File:** `models\focus_drop_classifier.pkl`
**GridSearch Log:** `models\gridsearch_results_classifier.csv`

---

## Model 2: Focus Score Regressor (OPTIMIZED)
**Type:** Regression (XGBoost)
**Task:** Predict next lap's focus score (0-100)

**GridSearch Results:**
- Total combinations tested: 108
- Best CV R²: 0.687
- Test R²: 0.718
- Test RMSE: 5.69 points

**Optimal Hyperparameters:**
- colsample_bytree: 0.8
- learning_rate: 0.1
- max_depth: 3
- n_estimators: 50
- subsample: 0.8

**Performance:**
- Training samples: 512
- Test samples: 128

**File:** `models\focus_score_regressor.pkl`
**GridSearch Log:** `models\gridsearch_results_regressor.csv`

---

## Model 3: Anomaly Detector (TUNED)
**Type:** Isolation Forest
**Task:** Detect unusual driving patterns

**Parameter Tuning Results:**
- Optimal contamination: 0.05
- Optimal n_estimators: 50
- Anomalies detected: 37 / 640 (5.8%)

**File:** `models\anomaly_detector.pkl`

---

## Features Used (27 total)
ThrottleJerk_1s_mean, ThrottleJerk_1s_std, ThrottleJerk_1s_max, BrakeSpikeRate_5s_mean, BrakeSpikeRate_5s_max, BrakeSpikeRate_5s_sum, SteerEntropy_10s_mean, SteerEntropy_10s_max, MicroVariability_mean, MicroVariability_std, ath_mean, ath_std, speed_mean, speed_std, pbrake_f_mean, pbrake_f_max, Steering_Angle_mean, Steering_Angle_std, accx_can_mean, accx_can_std, accy_can_mean, accy_can_std, CLI_raw, FocusScore_smooth, lap, AIR_TEMP, TRACK_TEMP

---

## Deployment Notes
- All models hyperparameter-optimized via GridSearchCV
- 3-fold cross-validation for robust generalization
- Class imbalance handled in classifier
- Models ready for production deployment

**Dataset:** cli_complete_dataset.csv (640 laps)
**Optimization Time:** ~5-10 minutes
**Cross-validation:** 3-fold stratified
