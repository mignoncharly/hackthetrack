/**
 * GR Cup CLI Monitor - Main Application Logic
 * Handles state management, data loading, and core functionality
 */

// ============================================================================
// GLOBAL STATE
// ============================================================================

const AppState = {
    // Driver and lap data
    selectedDriver: null,
    currentLap: 1,
    minLap: 1,
    maxLap: 100,
    driverData: [],
    allDrivers: [],
    lapData: null,

    // Playback control
    isPlaying: false,
    playbackSpeed: 1.0,
    replayTimer: null,
    lastUpdateTime: Date.now(),

    // Multi-driver comparison
    selectedDriversForComparison: [],

    // Driver baseline
    driverBaseline: null,

    // API status
    apiConnected: false,
    mlApiConnected: false
};

// Speed mapping for slider
const SPEED_MAP = [0.5, 1.0, 2.0, 5.0, 10.0];

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize the application
 */
async function initApp() {
    console.log('🚀 Initializing GR Cup CLI Monitor...');

    try {
        // Check API health
        await checkAPIHealth();

        // Load drivers
        await loadDrivers();

        // Setup event listeners
        setupEventListeners();

        // Hide loading screen
        hideLoadingScreen();

        console.log('✅ Application initialized successfully');

    } catch (error) {
        console.error('❌ Failed to initialize application:', error);
        showError('Failed to load application. Please refresh the page.');
    }
}

/**
 * Hide loading screen and show app
 */
function hideLoadingScreen() {
    const loadingScreen = document.getElementById('loading-screen');
    const appContainer = document.getElementById('app-container');

    setTimeout(() => {
        loadingScreen.style.display = 'none';
        appContainer.style.display = 'flex';
    }, 500);
}

// ============================================================================
// DATA LOADING
// ============================================================================

/**
 * Check API health status
 */
async function checkAPIHealth() {
    try {
        // Check Flask API
        const response = await fetch('/api/health');
        const health = await response.json();

        AppState.apiConnected = health.status === 'healthy';
        updateAPIStatus(AppState.apiConnected);

        // Check ML API
        try {
            const mlResponse = await fetch('/api/ml/health');
            const mlHealth = await mlResponse.json();
            AppState.mlApiConnected = mlHealth.status === 'healthy';
            updateMLAPIStatus(AppState.mlApiConnected);
        } catch (error) {
            AppState.mlApiConnected = false;
            updateMLAPIStatus(false);
        }

    } catch (error) {
        console.error('API health check failed:', error);
        AppState.apiConnected = false;
        updateAPIStatus(false);
    }
}

/**
 * Update API status badge
 */
function updateAPIStatus(isConnected) {
    const statusBadge = document.getElementById('api-status');
    const statusText = document.getElementById('status-text');

    if (isConnected) {
        statusBadge.className = 'status-badge connected';
        statusText.textContent = 'API Connected';
    } else {
        statusBadge.className = 'status-badge disconnected';
        statusText.textContent = 'API Disconnected';
    }
}

/**
 * Update ML API status badge
 */
function updateMLAPIStatus(isConnected) {
    const statusBadge = document.getElementById('ml-api-status');
    const statusText = document.getElementById('ml-status-text');

    if (isConnected) {
        statusBadge.className = 'status-badge-small connected';
        statusText.textContent = 'ML API: Connected';
    } else {
        statusBadge.className = 'status-badge-small disconnected';
        statusText.textContent = 'ML API: Offline';
    }
}

/**
 * Load available drivers
 */
async function loadDrivers() {
    try {
        const response = await fetch('/api/drivers');
        const drivers = await response.json();

        AppState.allDrivers = drivers;

        // Populate driver select dropdown
        const select = document.getElementById('driver-select');
        select.innerHTML = '';

        drivers.forEach(driver => {
            const option = document.createElement('option');
            option.value = driver;
            option.textContent = `Car #${driver}`;
            select.appendChild(option);
        });

        // Populate comparison checkboxes
        populateDriverComparisonList(drivers);

        // Select first driver by default
        if (drivers.length > 0) {
            await selectDriver(drivers[0]);
        }

    } catch (error) {
        console.error('Failed to load drivers:', error);
        showError('Failed to load driver data');
    }
}

/**
 * Populate driver comparison checkbox list
 */
function populateDriverComparisonList(drivers) {
    const container = document.getElementById('driver-comparison-list');
    container.innerHTML = '';

    drivers.forEach(driver => {
        const item = document.createElement('div');
        item.className = 'driver-checkbox-item';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `driver-compare-${driver}`;
        checkbox.value = driver;
        checkbox.addEventListener('change', handleComparisonDriverChange);

        const label = document.createElement('label');
        label.htmlFor = `driver-compare-${driver}`;
        label.textContent = `Car #${driver}`;
        label.style.cursor = 'pointer';

        item.appendChild(checkbox);
        item.appendChild(label);
        container.appendChild(item);
    });
}

/**
 * Select a driver and load their data
 */
async function selectDriver(driverId) {
    try {
        console.log(`Loading data for driver ${driverId}...`);

        AppState.selectedDriver = driverId;

        // Fetch driver data
        const response = await fetch(`/api/driver/${driverId}/data`);
        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Failed to load driver data');
        }

        // Update state
        AppState.driverData = result.data;
        AppState.minLap = result.min_lap;
        AppState.maxLap = result.max_lap;
        AppState.currentLap = result.min_lap;

        // Load driver baseline
        await loadDriverBaseline(driverId);

        // Update UI
        updateLapSlider();
        updateGlobalIndicator();
        await updateCurrentLapData();

        // Render all visualizations
        renderAllCharts();

        console.log(`✅ Loaded ${result.total_laps} laps for driver ${driverId}`);

    } catch (error) {
        console.error('Failed to select driver:', error);
        showError(`Failed to load data for driver ${driverId}`);
    }
}

/**
 * Load driver baseline data
 */
async function loadDriverBaseline(driverId) {
    try {
        const response = await fetch(`/api/driver/${driverId}/baseline`);
        const result = await response.json();

        if (result.success) {
            AppState.driverBaseline = result.baseline;
        } else {
            AppState.driverBaseline = null;
        }
    } catch (error) {
        console.error('Failed to load driver baseline:', error);
        AppState.driverBaseline = null;
    }
}

/**
 * Update current lap data and UI
 */
async function updateCurrentLapData() {
    // Find lap data
    const lapData = AppState.driverData.find(d => d.lap === AppState.currentLap);

    if (lapData) {
        AppState.lapData = lapData;

        // Update UI elements
        updateMetricsDisplay(lapData);
        updateAllCharts(lapData);
        updateLapIndicators();
    }
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Driver selection
    document.getElementById('driver-select').addEventListener('change', (e) => {
        selectDriver(parseInt(e.target.value));
    });

    // Note: Control button listeners are in controls.js
    // Note: Tab switching listeners are in controls.js
    // Note: Slider listeners are in controls.js
}

/**
 * Handle comparison driver checkbox change
 */
function handleComparisonDriverChange(event) {
    const driverId = parseInt(event.target.value);
    const isChecked = event.target.checked;

    if (isChecked) {
        if (!AppState.selectedDriversForComparison.includes(driverId)) {
            AppState.selectedDriversForComparison.push(driverId);
        }
    } else {
        AppState.selectedDriversForComparison = AppState.selectedDriversForComparison.filter(id => id !== driverId);
    }

    // Update compare button state
    const compareBtn = document.getElementById('btn-compare');
    compareBtn.disabled = AppState.selectedDriversForComparison.length < 1;

    // If on compare tab, update chart
    const compareTab = document.getElementById('tab-compare');
    if (compareTab.classList.contains('active')) {
        renderMultiDriverComparison();
    }
}

// ============================================================================
// UI UPDATE FUNCTIONS
// ============================================================================

/**
 * Update lap slider range and value
 */
function updateLapSlider() {
    const slider = document.getElementById('lap-slider');
    slider.min = AppState.minLap;
    slider.max = AppState.maxLap;
    slider.value = AppState.currentLap;
    document.getElementById('lap-slider-text').textContent = `Lap ${AppState.currentLap}`;
}

/**
 * Update global lap indicator
 */
function updateGlobalIndicator() {
    document.getElementById('current-lap-global').textContent = AppState.currentLap;
    document.getElementById('max-lap-global').textContent = AppState.maxLap;
    document.getElementById('driver-number-global').textContent = AppState.selectedDriver;
}

/**
 * Update lap indicators across the UI
 */
function updateLapIndicators() {
    // Sidebar
    document.getElementById('current-lap-sidebar').textContent = AppState.currentLap;
    document.getElementById('max-lap-sidebar').textContent = AppState.maxLap;

    // Global indicator
    updateGlobalIndicator();

    // Tab 2 - Replay progress
    document.getElementById('replay-current-lap').textContent = AppState.currentLap;
    document.getElementById('replay-max-lap').textContent = AppState.maxLap;

    const progress = ((AppState.currentLap - AppState.minLap) / (AppState.maxLap - AppState.minLap)) * 100;
    document.getElementById('replay-progress-pct').textContent = progress.toFixed(1) + '%';
    document.getElementById('replay-progress-bar').style.width = progress + '%';

    // Progress bar in sidebar
    document.getElementById('progress-bar').style.width = progress + '%';
    document.getElementById('progress-percentage').textContent = Math.round(progress) + '%';

    // Lap slider
    document.getElementById('lap-slider').value = AppState.currentLap;
    document.getElementById('lap-slider-text').textContent = `Lap ${AppState.currentLap}`;
}

/**
 * Update metrics display
 */
function updateMetricsDisplay(lapData) {
    // Focus Score
    const focusScore = lapData.FocusScore_smooth || 0;
    document.getElementById('metric-focus').textContent = focusScore.toFixed(1);

    const focusDelta = focusScore - 50;
    const focusDeltaEl = document.getElementById('metric-focus-delta');
    focusDeltaEl.textContent = (focusDelta >= 0 ? '+' : '') + focusDelta.toFixed(1);
    focusDeltaEl.className = 'metric-delta ' + (focusDelta >= 0 ? 'positive' : 'negative');

    // Drop Risk
    const dropRisk = (lapData.focus_drop_prob || 0) * 100;
    document.getElementById('metric-risk').textContent = dropRisk.toFixed(0) + '%';

    // Alert Level
    const alertLevel = lapData.alert_level || 0;
    document.getElementById('metric-alert').textContent = `${alertLevel}/3`;

    const alertIcon = document.getElementById('alert-icon');
    const alertEmojis = ['✅', '🔵', '🟡', '🔴'];
    alertIcon.textContent = alertEmojis[Math.min(alertLevel, 3)];

    // Anomaly
    const isAnomaly = lapData.is_anomaly === 1;
    document.getElementById('metric-anomaly').textContent = isAnomaly ? '⚠️ Yes' : '✅ No';
}

/**
 * Update last update time
 */
function updateLastUpdateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();

    document.getElementById('last-update-time').textContent = timeString;
    document.getElementById('footer-update-time').textContent = timeString;
}

// Auto-update time every second
setInterval(updateLastUpdateTime, 1000);

// ============================================================================
// ERROR HANDLING
// ============================================================================

/**
 * Show error message to user
 */
function showError(message) {
    console.error(message);
    // Could add a toast notification here
    alert(message);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', initApp);

// Export for use in other modules
window.AppState = AppState;
window.updateCurrentLapData = updateCurrentLapData;
window.updateLapIndicators = updateLapIndicators;
window.selectDriver = selectDriver;
