/**
 * GR Cup CLI Monitor - Visualizations
 * All Plotly.js chart rendering functions
 */

// ============================================================================
// ERROR HANDLING FOR MISSING PLOTLY
// ============================================================================

if (typeof Plotly === 'undefined') {
    console.error('❌ Plotly.js failed to load! Charts will be disabled.');
    
    // Create a mock Plotly object to prevent errors
    window.Plotly = {
        newPlot: function(divId, data, layout, config) {
            console.warn(`📊 Plotly not available - chart "${divId}" disabled`);
            const div = document.getElementById(divId);
            if (div) {
                div.innerHTML = `
                    <div style="text-align: center; padding: 2rem; color: #ff6b6b;">
                        <h3>📊 Chart Unavailable</h3>
                        <p>Plotly.js failed to load. Please check your internet connection.</p>
                        <p><small>Chart: ${divId}</small></p>
                    </div>
                `;
            }
        }
    };
}

// Common Plotly layout settings
const COMMON_LAYOUT = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: '#ffffff', family: 'Segoe UI, sans-serif' },
    margin: { l: 50, r: 50, t: 50, b: 50 }
};

const COMMON_CONFIG = {
    responsive: true,
    displayModeBar: false
};

// ============================================================================
// MAIN CHART RENDERING
// ============================================================================

/**
 * Render all charts for current lap
 */
function renderAllCharts() {
    if (!AppState.lapData) return;

    renderFocusGauge();
    renderPerformanceRadar();
    renderStatusCard();
    renderLapEvents();
    renderTelemetryGrid();
}

/**
 * Update all charts when lap changes
 */
function updateAllCharts(lapData) {
    renderFocusGauge();
    renderPerformanceRadar();
    renderStatusCard();
    renderLapEvents();
    renderTelemetryGrid();
}

// ============================================================================
// TAB 1: LIVE MONITOR CHARTS
// ============================================================================

/**
 * Render focus gauge
 */
function renderFocusGauge() {
    if (!AppState.lapData) return;

    const focusScore = AppState.lapData.FocusScore_smooth || 0;
    const predictedScore = AppState.lapData.focus_score_predicted || null;

    const data = [{
        type: 'indicator',
        mode: 'gauge+number+delta',
        value: focusScore,
        delta: { reference: 50, increasing: { color: '#00ff88' }, decreasing: { color: '#ff4444' } },
        number: { font: { size: 50, color: 'white' } },
        gauge: {
            axis: { range: [0, 100], tickcolor: 'white' },
            bar: { color: 'rgba(102, 126, 234, 0.9)', thickness: 0.25 },
            bgcolor: 'rgba(255,255,255,0.05)',
            borderwidth: 3,
            bordercolor: 'rgba(255,255,255,0.3)',
            steps: [
                { range: [0, 30], color: 'rgba(255,68,68,0.4)' },
                { range: [30, 60], color: 'rgba(255,170,0,0.4)' },
                { range: [60, 100], color: 'rgba(68,255,68,0.4)' }
            ],
            threshold: {
                line: { color: 'rgba(255,255,255,0.8)', width: 4 },
                thickness: 0.8,
                value: 30
            }
        }
    }];

    const layout = {
        ...COMMON_LAYOUT,
        height: 350,
        title: { text: 'Focus Score', font: { size: 24, color: 'white' } },
        annotations: predictedScore ? [{
            x: 0.5,
            y: 0.5,
            text: `Predicted Next: ${predictedScore.toFixed(0)}`,
            showarrow: false,
            font: { size: 16, color: 'cyan' },
            bgcolor: 'rgba(0,0,0,0.5)',
            bordercolor: 'cyan',
            borderwidth: 2,
            borderpad: 8
        }] : []
    };

    Plotly.newPlot('chart-focus-gauge', data, layout, COMMON_CONFIG);
}

/**
 * Render performance radar chart
 */
function renderPerformanceRadar() {
    if (!AppState.lapData) return;

    const lap = AppState.lapData;

    // Calculate normalized values (0-100 scale)
    const values = [
        100 - Math.min((lap.ThrottleJerk_1s_mean || 0) * 2, 100), // Throttle Control
        100 - Math.min((lap.BrakeSpikeRate_5s_mean || 0) * 30, 100), // Brake Consistency
        100 - Math.min((lap.SteerEntropy_10s_mean || 0) * 50, 100), // Steering Smoothness
        100 - Math.min((lap.speed_std || 0) * 2.5, 100), // Speed Stability
        lap.FocusScore_smooth || 50 // Overall Focus
    ];

    const categories = [
        'Throttle<br>Control',
        'Brake<br>Consistency',
        'Steering<br>Smoothness',
        'Speed<br>Stability',
        'Overall<br>Focus'
    ];

    const data = [{
        type: 'scatterpolar',
        r: values,
        theta: categories,
        fill: 'toself',
        name: 'Current',
        line: { color: '#667eea', width: 3 },
        fillcolor: 'rgba(102,126,234,0.4)'
    }];

    const layout = {
        ...COMMON_LAYOUT,
        height: 450,
        polar: {
            bgcolor: 'rgba(20,20,30,0.3)',
            radialaxis: {
                visible: true,
                range: [0, 100],
                tickfont: { size: 10, color: 'white' },
                gridcolor: 'rgba(255,255,255,0.2)',
                linecolor: 'rgba(255,255,255,0.3)'
            },
            angularaxis: {
                tickfont: { size: 11, color: 'white' },
                gridcolor: 'rgba(255,255,255,0.2)',
                linecolor: 'rgba(255,255,255,0.3)'
            }
        },
        showlegend: false
    };

    Plotly.newPlot('chart-performance-radar', data, layout, COMMON_CONFIG);
}

/**
 * Render status card
 */
function renderStatusCard() {
    if (!AppState.lapData) return;

    const lap = AppState.lapData;
    const alertLevel = lap.alert_level || 0;
    const statusCard = document.getElementById('status-message');

    let statusHTML = '';
    let actions = [];

    if (alertLevel === 0) {
        statusHTML = '<div class="alert-ok">✅ All systems nominal - Performance excellent</div>';
    } else if (alertLevel === 1) {
        statusHTML = '<div class="alert-info">🔵 Minor alerts detected - Continue monitoring</div>';
        actions.push('👀 Monitor next 2-3 laps closely');
    } else if (alertLevel === 2) {
        statusHTML = '<div class="alert-warning">⚠️ WARNING - Intervention advised</div>';
        actions.push('👀 Monitor next 2-3 laps intensively');
        if (lap.BrakeSpikeRate_5s_mean > 2.5) {
            actions.push('🛑 High brake spike rate detected');
        }
    } else {
        statusHTML = '<div class="alert-critical">🚨 CRITICAL ALERT - Immediate action required</div>';
        actions.push('🚨 Immediate radio check-in with driver');
        actions.push('🔧 Review pit strategy - consider early stop');
    }

    if (lap.SteerEntropy_10s_mean > 1.7) {
        actions.push('🎯 Steering indecision detected');
    }

    statusCard.innerHTML = statusHTML;

    const actionsDiv = document.getElementById('recommended-actions');
    if (actions.length > 0) {
        actionsDiv.innerHTML = '<h4 style="margin-top: 1rem;">📋 Recommended Actions:</h4><ul style="margin-top: 0.5rem;">' +
            actions.map(a => `<li style="padding: 0.25rem 0;">${a}</li>`).join('') +
            '</ul>';
    } else {
        actionsDiv.innerHTML = '';
    }
}

/**
 * Render lap events
 */
function renderLapEvents() {
    if (!AppState.lapData) return;

    const lap = AppState.lapData;
    const eventsDiv = document.getElementById('lap-events');

    const events = [];

    if (lap.focus_drop_next === 1) {
        events.push('<span class="event-marker event-focus-drop">⬇️ Focus Drop Next Lap</span>');
    }
    if (lap.mistake_event === 1) {
        events.push('<span class="event-marker event-mistake">⚠️ Mistake Event</span>');
    }
    if (lap.is_anomaly === 1) {
        events.push('<span class="event-marker event-anomaly">🔍 Anomaly Detected</span>');
    }

    if (events.length > 0) {
        eventsDiv.innerHTML = events.join(' ');
    } else {
        eventsDiv.innerHTML = '<p style="color: #00ff88;">✅ No events detected - Clean lap</p>';
    }
}

/**
 * Render telemetry grid
 */
function renderTelemetryGrid() {
    if (!AppState.lapData) return;

    const lap = AppState.lapData;
    const grid = document.getElementById('telemetry-grid');

    grid.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;">
            <div>
                <h4 style="margin-bottom: 0.5rem;">Control Inputs</h4>
                <p><strong>Throttle Jerk:</strong> ${lap.ThrottleJerk_1s_mean?.toFixed(1) || 'N/A'}</p>
                <p><strong>Brake Spikes:</strong> ${lap.BrakeSpikeRate_5s_mean?.toFixed(2) || 'N/A'}</p>
                <p><strong>Steer Entropy:</strong> ${lap.SteerEntropy_10s_mean?.toFixed(2) || 'N/A'}</p>
            </div>
            <div>
                <h4 style="margin-bottom: 0.5rem;">Performance</h4>
                <p><strong>Speed Avg:</strong> ${lap.speed_mean?.toFixed(0) || 'N/A'} km/h</p>
                <p><strong>Speed StdDev:</strong> ${lap.speed_std?.toFixed(1) || 'N/A'}</p>
                <p><strong>Throttle Avg:</strong> ${lap.ath_mean?.toFixed(0) || 'N/A'}%</p>
            </div>
            <div>
                <h4 style="margin-bottom: 0.5rem;">Dynamics</h4>
                <p><strong>Brake Pressure:</strong> ${lap.pbrake_f_max?.toFixed(1) || 'N/A'} bar</p>
                <p><strong>Lateral G:</strong> ${lap.accy_can_mean?.toFixed(2) || 'N/A'}</p>
                <p><strong>CLI Raw:</strong> ${lap.CLI_raw?.toFixed(2) || 'N/A'}</p>
            </div>
        </div>
    `;
}

// ============================================================================
// TAB 2: TIMELINE CHART
// ============================================================================

/**
 * Render timeline chart for Tab 2
 */
function renderTimelineChart() {
    if (!AppState.driverData || AppState.driverData.length === 0) return;

    const laps = AppState.driverData.map(d => d.lap);
    const focusScores = AppState.driverData.map(d => d.FocusScore_smooth);

    // Main line trace
    const trace1 = {
        x: laps,
        y: focusScores,
        mode: 'lines+markers',
        name: 'Focus Score',
        line: { color: '#667eea', width: 4, shape: 'spline' },
        marker: { size: 8, line: { width: 2, color: 'white' } }
    };

    // Focus drops
    const focusDrops = AppState.driverData.filter(d => d.focus_drop_next === 1);
    const trace2 = {
        x: focusDrops.map(d => d.lap),
        y: focusDrops.map(d => d.FocusScore_smooth),
        mode: 'markers',
        name: 'Focus Drops',
        marker: { color: '#ff4444', size: 15, symbol: 'x', line: { width: 2, color: 'white' } }
    };

    // Mistakes
    const mistakes = AppState.driverData.filter(d => d.mistake_event === 1);
    const trace3 = {
        x: mistakes.map(d => d.lap),
        y: mistakes.map(d => d.FocusScore_smooth),
        mode: 'markers',
        name: 'Mistakes',
        marker: { color: '#ffaa00', size: 12, symbol: 'diamond', line: { width: 2, color: 'white' } }
    };

    const data = [trace1, trace2, trace3];

    const layout = {
        ...COMMON_LAYOUT,
        height: 500,
        xaxis: { title: 'Lap Number', gridcolor: 'rgba(255,255,255,0.1)' },
        yaxis: { title: 'Focus Score', gridcolor: 'rgba(255,255,255,0.1)' },
        hovermode: 'x unified',
        showlegend: true,
        legend: { bgcolor: 'rgba(0,0,0,0.7)', bordercolor: 'rgba(255,255,255,0.2)' },
        shapes: [
            // Critical zone
            {
                type: 'rect',
                xref: 'paper',
                x0: 0,
                x1: 1,
                yref: 'y',
                y0: 0,
                y1: 30,
                fillcolor: 'rgba(255,68,68,0.2)',
                line: { width: 0 }
            },
            // Warning zone
            {
                type: 'rect',
                xref: 'paper',
                x0: 0,
                x1: 1,
                yref: 'y',
                y0: 30,
                y1: 60,
                fillcolor: 'rgba(255,170,0,0.15)',
                line: { width: 0 }
            }
        ]
    };

    Plotly.newPlot('chart-timeline', data, layout, COMMON_CONFIG);
}

/**
 * Render session summary
 */
function renderSessionSummary() {
    if (!AppState.driverData || AppState.driverData.length === 0) return;

    const avgFocus = AppState.driverData.reduce((sum, d) => sum + d.FocusScore_smooth, 0) / AppState.driverData.length;
    const focusDrops = AppState.driverData.filter(d => d.focus_drop_next === 1).length;
    const mistakes = AppState.driverData.filter(d => d.mistake_event === 1).length;
    const totalAlerts = AppState.driverData.filter(d => d.alert_level > 0).length;

    const recentLaps = AppState.driverData.slice(-5);
    let trend = 'Stable';
    if (recentLaps.length > 2) {
        const trendValue = recentLaps[recentLaps.length - 1].FocusScore_smooth - recentLaps[0].FocusScore_smooth;
        if (trendValue > 5) trend = '📈 Improving';
        else if (trendValue < -5) trend = '📉 Declining';
        else trend = '➡️ Stable';
    }

    const summaryDiv = document.getElementById('session-summary');
    summaryDiv.innerHTML = `
        <div style="padding: 1rem;">
            <div style="margin-bottom: 1rem;">
                <h4>Avg Focus Score</h4>
                <p style="font-size: 2rem; font-weight: 700; color: #667eea;">${avgFocus.toFixed(1)}/100</p>
            </div>
            <div style="margin-bottom: 0.5rem;">
                <strong>Focus Drops:</strong> <span style="color: #ff4444;">${focusDrops}</span>
            </div>
            <div style="margin-bottom: 0.5rem;">
                <strong>Mistakes:</strong> <span style="color: #ffaa00;">${mistakes}</span>
            </div>
            <div style="margin-bottom: 0.5rem;">
                <strong>Total Alerts:</strong> ${totalAlerts}
            </div>
            <div style="margin-top: 1rem; padding: 0.75rem; background: rgba(255,255,255,0.05); border-radius: 8px;">
                <strong>Performance Trend:</strong><br>${trend}
            </div>
        </div>
    `;
}

// ============================================================================
// TAB 3: FULL TIMELINE AND EVENT LOG
// ============================================================================

/**
 * Render full timeline for Tab 3
 */
function renderFullTimelineChart() {
    renderTimelineChart(); // Same as Tab 2 but in different container
    // Copy chart to full timeline container
    setTimeout(() => {
        const chartData = document.getElementById('chart-timeline').data;
        const chartLayout = document.getElementById('chart-timeline').layout;
        if (chartData && chartLayout) {
            Plotly.newPlot('chart-full-timeline', chartData, { ...chartLayout, height: 600 }, COMMON_CONFIG);
        }
    }, 100);
}

/**
 * Render event log table
 */
function renderEventLog() {
    if (!AppState.driverData || AppState.driverData.length === 0) return;

    const events = [];

    AppState.driverData.forEach(lap => {
        const lapEvents = [];
        if (lap.focus_drop_next === 1) lapEvents.push('Focus Drop');
        if (lap.mistake_event === 1) lapEvents.push('Mistake');
        if (lap.alert_level > 1) lapEvents.push(`Alert Level ${lap.alert_level}`);
        if (lap.is_anomaly === 1) lapEvents.push('Anomaly');

        if (lapEvents.length > 0) {
            events.push({
                lap: lap.lap,
                focusScore: lap.FocusScore_smooth.toFixed(1),
                events: lapEvents.join(', ')
            });
        }
    });

    const tableDiv = document.getElementById('event-log-table');

    if (events.length > 0) {
        tableDiv.innerHTML = `
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: rgba(255,255,255,0.05);">
                        <th style="padding: 0.75rem; text-align: left;">Lap</th>
                        <th style="padding: 0.75rem; text-align: left;">Focus Score</th>
                        <th style="padding: 0.75rem; text-align: left;">Events</th>
                    </tr>
                </thead>
                <tbody>
                    ${events.map(e => `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                            <td style="padding: 0.75rem;">${e.lap}</td>
                            <td style="padding: 0.75rem;">${e.focusScore}</td>
                            <td style="padding: 0.75rem;">${e.events}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } else {
        tableDiv.innerHTML = '<p style="text-align: center; padding: 2rem; color: #00ff88;">✅ No significant events detected during session</p>';
    }
}

// ============================================================================
// TAB 4: ADVANCED ANALYTICS
// ============================================================================

/**
 * Render heatmap of CLI components
 */
function renderHeatmapChart() {
    if (!AppState.driverData || AppState.driverData.length === 0) return;

    const laps = AppState.driverData.map(d => d.lap);

    // Normalize data to 0-100 scale
    const throttleData = AppState.driverData.map(d => 100 - Math.min((d.ThrottleJerk_1s_mean || 0) * 2, 100));
    const brakeData = AppState.driverData.map(d => 100 - Math.min((d.BrakeSpikeRate_5s_mean || 0) * 30, 100));
    const steerData = AppState.driverData.map(d => 100 - Math.min((d.SteerEntropy_10s_mean || 0) * 50, 100));
    const speedData = AppState.driverData.map(d => 100 - Math.min((d.speed_std || 0) * 2.5, 100));
    const focusData = AppState.driverData.map(d => d.FocusScore_smooth);

    const data = [{
        z: [throttleData, brakeData, steerData, speedData, focusData],
        x: laps,
        y: ['Throttle Jerk', 'Brake Spikes', 'Steer Entropy', 'Speed Var', 'Focus Score'],
        type: 'heatmap',
        colorscale: 'RdYlGn',
        hovertemplate: 'Lap: %{x}<br>%{y}: %{z:.1f}<extra></extra>'
    }];

    const layout = {
        ...COMMON_LAYOUT,
        height: 400,
        xaxis: { title: 'Lap Number' },
        yaxis: { title: '' }
    };

    Plotly.newPlot('chart-heatmap', data, layout, COMMON_CONFIG);
}

/**
 * Render statistics table
 */
function renderStatisticsTable() {
    if (!AppState.driverData || AppState.driverData.length === 0) return;

    const metrics = [
        { name: 'Focus Score', key: 'FocusScore_smooth' },
        { name: 'Throttle Jerk', key: 'ThrottleJerk_1s_mean' },
        { name: 'Brake Spikes', key: 'BrakeSpikeRate_5s_mean' },
        { name: 'Steer Entropy', key: 'SteerEntropy_10s_mean' }
    ];

    const stats = metrics.map(metric => {
        const values = AppState.driverData.map(d => d[metric.key]);
        const mean = values.reduce((a, b) => a + b, 0) / values.length;
        const sorted = [...values].sort((a, b) => a - b);
        const min = Math.min(...values);
        const max = Math.max(...values);
        const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
        const stdDev = Math.sqrt(variance);

        return { name: metric.name, mean, stdDev, min, max };
    });

    const tableDiv = document.getElementById('statistics-table');
    tableDiv.innerHTML = `
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background: rgba(255,255,255,0.05);">
                    <th style="padding: 0.75rem; text-align: left;">Metric</th>
                    <th style="padding: 0.75rem; text-align: right;">Mean</th>
                    <th style="padding: 0.75rem; text-align: right;">StdDev</th>
                    <th style="padding: 0.75rem; text-align: right;">Min</th>
                    <th style="padding: 0.75rem; text-align: right;">Max</th>
                </tr>
            </thead>
            <tbody>
                ${stats.map(s => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <td style="padding: 0.75rem;">${s.name}</td>
                        <td style="padding: 0.75rem; text-align: right;">${s.mean.toFixed(2)}</td>
                        <td style="padding: 0.75rem; text-align: right;">${s.stdDev.toFixed(2)}</td>
                        <td style="padding: 0.75rem; text-align: right;">${s.min.toFixed(2)}</td>
                        <td style="padding: 0.75rem; text-align: right;">${s.max.toFixed(2)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

/**
 * Render percentiles chart
 */
function renderPercentilesChart() {
    if (!AppState.driverData || AppState.driverData.length === 0) return;

    const focusScores = AppState.driverData.map(d => d.FocusScore_smooth).sort((a, b) => a - b);
    const percentiles = [10, 25, 50, 75, 90];
    const values = percentiles.map(p => {
        const index = Math.floor((p / 100) * focusScores.length);
        return focusScores[index];
    });

    const data = [{
        x: percentiles.map(p => `P${p}`),
        y: values,
        type: 'bar',
        marker: {
            color: values,
            colorscale: 'RdYlGn',
            showscale: false
        },
        text: values.map(v => v.toFixed(1)),
        textposition: 'auto'
    }];

    const layout = {
        ...COMMON_LAYOUT,
        height: 300,
        xaxis: { title: 'Percentile' },
        yaxis: { title: 'Focus Score' },
        title: 'Focus Score Distribution'
    };

    Plotly.newPlot('chart-percentiles', data, layout, COMMON_CONFIG);
}

// ============================================================================
// TAB 5: MULTI-DRIVER COMPARISON
// ============================================================================

/**
 * Render multi-driver comparison
 */
async function renderMultiDriverComparison() {
    const selectedDrivers = AppState.selectedDriversForComparison;

    if (selectedDrivers.length === 0) {
        document.getElementById('compare-empty-state').style.display = 'block';
        document.getElementById('comparison-stats-card').style.display = 'none';
        return;
    }

    document.getElementById('compare-empty-state').style.display = 'none';

    // Fetch comparison data
    try {
        const response = await fetch('/api/drivers/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ driver_ids: selectedDrivers })
        });

        const result = await response.json();

        if (!result.success) {
            throw new Error('Failed to load comparison data');
        }

        const data = result.data;

        // Create traces
        const colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a'];
        const traces = selectedDrivers.map((driverId, idx) => {
            const driverData = data[driverId];
            if (!driverData) return null;

            return {
                x: driverData.laps,
                y: driverData.focus_scores,
                mode: 'lines+markers',
                name: `Car #${driverId}`,
                line: { color: colors[idx % colors.length], width: 3 },
                marker: { size: 6 }
            };
        }).filter(t => t !== null);

        const layout = {
            ...COMMON_LAYOUT,
            height: 500,
            title: 'Multi-Driver Focus Comparison',
            xaxis: { title: 'Lap Number' },
            yaxis: { title: 'Focus Score' },
            hovermode: 'x unified',
            legend: { bgcolor: 'rgba(0,0,0,0.5)' }
        };

        Plotly.newPlot('chart-multi-driver', traces, layout, COMMON_CONFIG);

        // Show comparison stats
        if (selectedDrivers.length >= 2) {
            document.getElementById('comparison-stats-card').style.display = 'block';
            renderComparisonStatsTable(data);
        }

    } catch (error) {
        console.error('Failed to render comparison:', error);
    }
}

/**
 * Render comparison statistics table
 */
function renderComparisonStatsTable(data) {
    const tableDiv = document.getElementById('comparison-stats-table');

    const rows = Object.keys(data).map(driverId => {
        const d = data[driverId];
        return {
            driver: `Car #${driverId}`,
            avgFocus: d.avg_focus.toFixed(1),
            focusDrops: d.focus_drops,
            mistakes: d.mistakes,
            totalLaps: d.laps.length
        };
    });

    tableDiv.innerHTML = `
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background: rgba(255,255,255,0.05);">
                    <th style="padding: 0.75rem; text-align: left;">Driver</th>
                    <th style="padding: 0.75rem; text-align: right;">Avg Focus</th>
                    <th style="padding: 0.75rem; text-align: right;">Focus Drops</th>
                    <th style="padding: 0.75rem; text-align: right;">Mistakes</th>
                    <th style="padding: 0.75rem; text-align: right;">Total Laps</th>
                </tr>
            </thead>
            <tbody>
                ${rows.map(r => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <td style="padding: 0.75rem;">${r.driver}</td>
                        <td style="padding: 0.75rem; text-align: right;">${r.avgFocus}</td>
                        <td style="padding: 0.75rem; text-align: right;">${r.focusDrops}</td>
                        <td style="padding: 0.75rem; text-align: right;">${r.mistakes}</td>
                        <td style="padding: 0.75rem; text-align: right;">${r.totalLaps}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// ============================================================================
// TAB 6: PERSONALIZED BASELINE
// ============================================================================

/**
 * Render baseline tab
 */
function renderBaselineTab() {
    if (!AppState.driverBaseline) {
        document.getElementById('baseline-unavailable').style.display = 'block';
        return;
    }

    document.getElementById('baseline-unavailable').style.display = 'none';

    renderBaselineGauge();
    renderDriverProfile();
    renderBaselineTimeline();
    renderPerformanceVsBaseline();
}

/**
 * Render baseline gauge
 */
function renderBaselineGauge() {
    if (!AppState.lapData || !AppState.driverBaseline) return;

    const currentScore = AppState.lapData.FocusScore_smooth;
    const baseline = AppState.driverBaseline;

    const data = [{
        type: 'indicator',
        mode: 'gauge+number+delta',
        value: currentScore,
        delta: {
            reference: baseline.focus_baseline,
            suffix: ' vs baseline'
        },
        number: { suffix: '/100', font: { size: 45, color: 'white' } },
        gauge: {
            axis: { range: [0, 100] },
            bar: { color: 'rgba(100, 200, 255, 0.8)', thickness: 0.25 },
            steps: [
                { range: [0, baseline.critical_threshold], color: 'rgba(255,68,68,0.4)' },
                { range: [baseline.critical_threshold, baseline.warning_threshold], color: 'rgba(255,170,0,0.3)' },
                { range: [baseline.warning_threshold, baseline.excellent_threshold], color: 'rgba(100,200,100,0.2)' },
                { range: [baseline.excellent_threshold, 100], color: 'rgba(68,255,68,0.4)' }
            ],
            threshold: {
                line: { color: 'cyan', width: 4 },
                value: baseline.focus_baseline
            }
        }
    }];

    const layout = {
        ...COMMON_LAYOUT,
        height: 400,
        title: { text: 'Personalized Focus Score', font: { size: 24 } }
    };

    Plotly.newPlot('chart-baseline-gauge', data, layout, COMMON_CONFIG);
}

/**
 * Render driver profile card
 */
function renderDriverProfile() {
    if (!AppState.driverBaseline) return;

    const baseline = AppState.driverBaseline;
    const profileDiv = document.getElementById('driver-profile');

    profileDiv.innerHTML = `
        <div style="padding: 1rem;">
            <div style="margin-bottom: 1rem;">
                <strong>Personal Baseline:</strong>
                <p style="font-size: 1.5rem; color: cyan;">${baseline.focus_baseline.toFixed(1)}</p>
            </div>
            <div style="margin-bottom: 0.5rem;">
                <strong>Consistency (Std Dev):</strong> ±${baseline.focus_std.toFixed(1)}
            </div>
            <div style="margin-bottom: 0.5rem;">
                <strong>Total Laps Analyzed:</strong> ${baseline.total_laps}
            </div>
            <hr style="margin: 1rem 0; border-color: rgba(255,255,255,0.1);">
            <h4>🎚️ Personalized Thresholds</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-top: 0.5rem;">
                <div>
                    <p><strong>🔴 Critical Alert:</strong></p>
                    <p><${baseline.critical_threshold.toFixed(1)}</p>
                </div>
                <div>
                    <p><strong>🟡 Warning Alert:</strong></p>
                    <p><${baseline.warning_threshold.toFixed(1)}</p>
                </div>
                <div>
                    <p><strong>🟢 Excellent:</strong></p>
                    <p>>${baseline.excellent_threshold.toFixed(1)}</p>
                </div>
                <div>
                    <p><strong>📊 Median Score:</strong></p>
                    <p>${baseline.focus_median.toFixed(1)}</p>
                </div>
            </div>
        </div>
    `;
}

/**
 * Render baseline timeline
 */
function renderBaselineTimeline() {
    if (!AppState.driverData || !AppState.driverBaseline) return;

    const baseline = AppState.driverBaseline;
    const laps = AppState.driverData.map(d => d.lap);
    const focusScores = AppState.driverData.map(d => d.FocusScore_smooth);

    const traces = [
        {
            x: laps,
            y: focusScores,
            mode: 'lines+markers',
            name: 'Your Performance',
            line: { color: '#667eea', width: 2 },
            marker: { size: 4 }
        },
        {
            x: laps,
            y: Array(laps.length).fill(baseline.focus_baseline),
            mode: 'lines',
            name: 'Your Baseline',
            line: { color: 'cyan', width: 3, dash: 'dash' }
        },
        {
            x: laps,
            y: Array(laps.length).fill(baseline.critical_threshold),
            mode: 'lines',
            name: 'Critical Threshold',
            line: { color: 'red', width: 2, dash: 'dot' }
        },
        {
            x: laps,
            y: Array(laps.length).fill(baseline.excellent_threshold),
            mode: 'lines',
            name: 'Excellent Threshold',
            line: { color: 'green', width: 2, dash: 'dot' }
        }
    ];

    const layout = {
        ...COMMON_LAYOUT,
        height: 400,
        title: 'Performance History with Personalized Thresholds',
        xaxis: { title: 'Lap Number' },
        yaxis: { title: 'Focus Score' },
        hovermode: 'x unified',
        legend: { bgcolor: 'rgba(0,0,0,0.5)' }
    };

    Plotly.newPlot('chart-baseline-timeline', traces, layout, COMMON_CONFIG);
}

/**
 * Render performance vs baseline card
 */
function renderPerformanceVsBaseline() {
    if (!AppState.lapData || !AppState.driverBaseline) return;

    const currentScore = AppState.lapData.FocusScore_smooth;
    const baseline = AppState.driverBaseline.focus_baseline;
    const perfVsBaseline = ((currentScore - baseline) / baseline) * 100;

    const card = document.getElementById('performance-vs-baseline');

    let message = '';
    let className = '';

    if (perfVsBaseline > 10) {
        message = `🔥 Exceptional Performance! ${perfVsBaseline.toFixed(1)}% above your baseline`;
        className = 'alert-ok';
    } else if (perfVsBaseline > 0) {
        message = `✅ Good Performance - ${perfVsBaseline.toFixed(1)}% above your baseline`;
        className = 'alert-info';
    } else if (perfVsBaseline > -10) {
        message = `⚠️ Below Baseline - ${Math.abs(perfVsBaseline).toFixed(1)}% below your typical performance`;
        className = 'alert-warning';
    } else {
        message = `🚨 Significant Decline - ${Math.abs(perfVsBaseline).toFixed(1)}% below your baseline`;
        className = 'alert-critical';
    }

    card.innerHTML = `<div class="${className}" style="padding: 1.5rem; border-radius: 12px; margin-top: 1rem;">${message}</div>`;
}

// Export functions
window.renderAllCharts = renderAllCharts;
window.updateAllCharts = updateAllCharts;
window.renderTimelineChart = renderTimelineChart;
window.renderSessionSummary = renderSessionSummary;
window.renderFullTimelineChart = renderFullTimelineChart;
window.renderEventLog = renderEventLog;
window.renderHeatmapChart = renderHeatmapChart;
window.renderStatisticsTable = renderStatisticsTable;
window.renderPercentilesChart = renderPercentilesChart;
window.renderMultiDriverComparison = renderMultiDriverComparison;
window.renderBaselineTab = renderBaselineTab;
