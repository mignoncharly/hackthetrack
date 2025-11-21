/**
 * GR Cup CLI Monitor - Replay Controls
 * Handles Play/Pause/Stop/Speed controls and tab switching
 */

// ============================================================================
// REPLAY CONTROL FUNCTIONS
// ============================================================================

/**
 * Toggle play/pause
 */
function togglePlayback() {
    if (AppState.isPlaying) {
        pausePlayback();
    } else {
        startPlayback();
    }
}

/**
 * Start automatic playback
 */
function startPlayback() {
    AppState.isPlaying = true;
    AppState.lastUpdateTime = Date.now();

    // If at end, restart from beginning
    if (AppState.currentLap >= AppState.maxLap) {
        AppState.currentLap = AppState.minLap;
    }

    // Update UI
    updatePlaybackStatus();
    updateButtonStates();

    // Show live indicator
    const liveIndicator = document.getElementById('live-mode-indicator');
    if (liveIndicator) {
        liveIndicator.style.display = 'block';
    }

    // Hide lap slider during playback
    document.getElementById('lap-slider-group').style.opacity = '0.5';
    document.getElementById('lap-slider').disabled = true;

    // Start auto-advance
    startAutoAdvance();

    console.log('▶️ Playback started');
}

/**
 * Pause playback
 */
function pausePlayback() {
    AppState.isPlaying = false;

    // Stop auto-advance
    if (AppState.replayTimer) {
        clearInterval(AppState.replayTimer);
        AppState.replayTimer = null;
    }

    // Update UI
    updatePlaybackStatus();
    updateButtonStates();

    // Hide live indicator
    const liveIndicator = document.getElementById('live-mode-indicator');
    if (liveIndicator) {
        liveIndicator.style.display = 'none';
    }

    // Show lap slider
    document.getElementById('lap-slider-group').style.opacity = '1';
    document.getElementById('lap-slider').disabled = false;

    console.log('⏸️ Playback paused');
}

/**
 * Stop playback and reset to start
 */
function stopPlayback() {
    pausePlayback();
    setLap(AppState.minLap);
    console.log('⏹️ Playback stopped');
}

/**
 * Jump to first lap
 */
function jumpToStart() {
    pausePlayback();
    setLap(AppState.minLap);
}

/**
 * Jump to last lap
 */
function jumpToEnd() {
    pausePlayback();
    setLap(AppState.maxLap);
}

/**
 * Set specific lap
 */
function setLap(lap) {
    AppState.currentLap = lap;
    updateCurrentLapData();
    updateLapIndicators();
    updateButtonStates();
}

/**
 * Start auto-advance timer
 */
function startAutoAdvance() {
    const interval = 1000 / AppState.playbackSpeed; // milliseconds per lap

    AppState.replayTimer = setInterval(() => {
        AppState.currentLap++;

        // Loop back to start
        if (AppState.currentLap > AppState.maxLap) {
            AppState.currentLap = AppState.minLap;
        }

        // Update UI
        updateCurrentLapData();
        updateLapIndicators();

        // Broadcast to WebSocket if connected
        if (window.socket && window.socket.connected) {
            window.socket.emit('lap_change', {
                driver_id: AppState.selectedDriver,
                lap: AppState.currentLap
            });
        }

    }, interval);
}

/**
 * Change playback speed
 */
function changeSpeed(speedIndex) {
    AppState.playbackSpeed = SPEED_MAP[speedIndex];
    document.getElementById('speed-value').textContent = AppState.playbackSpeed + 'x';

    // Restart timer if playing
    if (AppState.isPlaying) {
        clearInterval(AppState.replayTimer);
        startAutoAdvance();
    }

    console.log(`⚡ Speed changed to ${AppState.playbackSpeed}x`);
}

/**
 * Update playback status badge
 */
function updatePlaybackStatus() {
    const statusDiv = document.getElementById('playback-status');
    const playBtn = document.getElementById('btn-play');

    if (AppState.isPlaying) {
        // Playing state
        statusDiv.className = 'playback-status playing';
        statusDiv.innerHTML = `
            <span class="status-emoji">▶️</span>
            <span class="status-text">PLAYING</span>
            <div class="status-details">
                Lap <span id="current-lap-sidebar">${AppState.currentLap}</span> /
                <span id="max-lap-sidebar">${AppState.maxLap}</span>
            </div>
        `;

        playBtn.innerHTML = '<span class="btn-icon">⏸️</span><span class="btn-text">Pause</span>';
        playBtn.className = 'btn btn-secondary';

    } else {
        // Paused state
        statusDiv.className = 'playback-status paused';
        statusDiv.innerHTML = `
            <span class="status-emoji">⏸️</span>
            <span class="status-text">PAUSED</span>
            <div class="status-details">
                Lap <span id="current-lap-sidebar">${AppState.currentLap}</span> /
                <span id="max-lap-sidebar">${AppState.maxLap}</span>
            </div>
        `;

        playBtn.innerHTML = '<span class="btn-icon">▶️</span><span class="btn-text">Play</span>';
        playBtn.className = 'btn btn-primary';
    }
}

/**
 * Update button states (enable/disable)
 */
function updateButtonStates() {
    const btnStart = document.getElementById('btn-start');
    const btnEnd = document.getElementById('btn-end');
    const btnStop = document.getElementById('btn-stop');

    // Start button - disabled if at first lap
    btnStart.disabled = AppState.currentLap === AppState.minLap;

    // End button - disabled if at last lap
    btnEnd.disabled = AppState.currentLap === AppState.maxLap;

    // Stop button - disabled if paused and at first lap
    btnStop.disabled = !AppState.isPlaying && AppState.currentLap === AppState.minLap;
}

// ============================================================================
// TAB SWITCHING
// ============================================================================

/**
 * Switch to a different tab
 */
function switchTab(tabId) {
    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');

    // Update tab panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.getElementById(tabId).classList.add('active');

    // Render tab-specific content
    renderTabContent(tabId);

    console.log(`📑 Switched to tab: ${tabId}`);
}

/**
 * Render content for specific tab
 */
function renderTabContent(tabId) {
    switch (tabId) {
        case 'tab-live':
            // Already rendered in main
            break;

        case 'tab-replay':
            renderTimelineChart();
            renderSessionSummary();
            break;

        case 'tab-timeline':
            renderFullTimelineChart();
            renderEventLog();
            break;

        case 'tab-analytics':
            renderHeatmapChart();
            renderStatisticsTable();
            renderPercentilesChart();
            break;

        case 'tab-compare':
            renderMultiDriverComparison();
            break;

        case 'tab-baseline':
            renderBaselineTab();
            break;
    }
}

// ============================================================================
// EVENT LISTENERS SETUP
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {

    // Play/Pause button
    document.getElementById('btn-play').addEventListener('click', togglePlayback);

    // Stop button
    document.getElementById('btn-stop').addEventListener('click', stopPlayback);

    // Start button
    document.getElementById('btn-start').addEventListener('click', jumpToStart);

    // End button
    document.getElementById('btn-end').addEventListener('click', jumpToEnd);

    // Speed slider
    document.getElementById('speed-slider').addEventListener('input', (e) => {
        changeSpeed(parseInt(e.target.value));
    });

    // Lap slider
    document.getElementById('lap-slider').addEventListener('input', (e) => {
        if (!AppState.isPlaying) {
            setLap(parseInt(e.target.value));
        }
    });

    // Tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', (e) => {
            const tabId = e.currentTarget.dataset.tab;
            switchTab(tabId);
        });
    });

    // Compare button
    document.getElementById('btn-compare').addEventListener('click', () => {
        switchTab('tab-compare');
    });

    console.log('✅ Control event listeners initialized');
});

// Export functions for external use
window.togglePlayback = togglePlayback;
window.startPlayback = startPlayback;
window.pausePlayback = pausePlayback;
window.stopPlayback = stopPlayback;
window.setLap = setLap;
window.switchTab = switchTab;
