/**
 * GR Cup CLI Monitor - PythonAnywhere Compatible WebSocket Handler
 * Uses HTTP polling fallback since free tier doesn't support WebSockets
 *
 * This file replaces websocket.js for PythonAnywhere deployment
 * To use: rename this file to websocket.js before deploying
 */

// ============================================================================
// POLLING-BASED SYNC (WebSocket Alternative)
// ============================================================================

let socket = null;
let pollingInterval = null;
let isConnected = false;

/**
 * Simulated socket object for compatibility
 * Provides the same interface as Socket.IO but uses HTTP polling
 */
class PollingSocket {
    constructor() {
        this.connected = false;
        this.callbacks = {};
    }

    on(event, callback) {
        if (!this.callbacks[event]) {
            this.callbacks[event] = [];
        }
        this.callbacks[event].push(callback);
    }

    emit(event, data) {
        // Log the event (in a real implementation, this would POST to an endpoint)
        console.log(`[Polling] Would emit ${event}:`, data);

        // For local events, trigger immediately
        if (event === 'lap_change') {
            // Store in session storage for other tabs
            sessionStorage.setItem('racing_ai_lap', JSON.stringify({
                ...data,
                timestamp: Date.now()
            }));
        }
    }

    trigger(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(cb => cb(data));
        }
    }

    disconnect() {
        this.connected = false;
        this.trigger('disconnect');
    }
}

/**
 * Connect to server (using polling instead of WebSocket)
 */
function connectWebSocket() {
    try {
        // Check if we're on PythonAnywhere or if Socket.IO is available
        const isPythonAnywhere = window.location.hostname.includes('pythonanywhere.com');

        if (!isPythonAnywhere && typeof io !== 'undefined') {
            // Try real WebSocket connection (for local development)
            try {
                socket = io(window.location.origin);

                socket.on('connect', () => {
                    console.log('WebSocket connected');
                    isConnected = true;
                });

                socket.on('disconnect', () => {
                    console.log('WebSocket disconnected');
                    isConnected = false;
                });

                socket.on('connected', (data) => {
                    console.log('Server acknowledged connection:', data.message);
                });

                socket.on('lap_changed', (data) => {
                    console.log('Received lap change from another client:', data);
                    if (typeof AppState !== 'undefined' && data.driver_id === AppState.selectedDriver) {
                        if (data.lap !== AppState.currentLap && typeof setLap === 'function') {
                            setLap(data.lap);
                        }
                    }
                });

                socket.on('playback_updated', (data) => {
                    console.log('Received playback state from another client:', data);
                });

                socket.on('replay_started', (data) => {
                    console.log('Another client started replay:', data);
                });

                window.socket = socket;
                return;
            } catch (e) {
                console.log('WebSocket connection failed, falling back to polling');
            }
        }

        // Use polling fallback for PythonAnywhere
        console.log('Using HTTP polling (WebSocket not available on PythonAnywhere free tier)');

        socket = new PollingSocket();
        socket.connected = true;
        isConnected = true;

        // Trigger connected event
        setTimeout(() => {
            socket.trigger('connect');
            socket.trigger('connected', { message: 'Connected via HTTP polling' });
        }, 100);

        // Start polling for health/updates
        startPolling();

        window.socket = socket;

    } catch (error) {
        console.error('Failed to connect:', error);
    }
}

/**
 * Start HTTP polling for updates
 */
function startPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }

    // Poll server health every 30 seconds
    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/health');
            if (response.ok) {
                const data = await response.json();
                if (!isConnected) {
                    isConnected = true;
                    console.log('Connection restored');
                    if (socket && socket.trigger) {
                        socket.trigger('connect');
                    }
                }
            }
        } catch (error) {
            if (isConnected) {
                isConnected = false;
                console.log('Connection lost');
                if (socket && socket.trigger) {
                    socket.trigger('disconnect');
                }
            }
        }
    }, 30000);

    // Check for updates from other tabs via sessionStorage
    window.addEventListener('storage', (event) => {
        if (event.key === 'racing_ai_lap') {
            try {
                const data = JSON.parse(event.newValue);
                if (socket && socket.trigger) {
                    socket.trigger('lap_changed', data);
                }
            } catch (e) {
                // Ignore parse errors
            }
        }
    });

    console.log('HTTP polling started');
}

/**
 * Stop polling
 */
function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
        console.log('HTTP polling stopped');
    }
}

/**
 * Disconnect (stop polling)
 */
function disconnectWebSocket() {
    stopPolling();
    if (socket) {
        if (typeof socket.disconnect === 'function') {
            socket.disconnect();
        }
        isConnected = false;
        console.log('Disconnected');
    }
}

/**
 * Check if connected
 */
function isWebSocketConnected() {
    return isConnected;
}

// ============================================================================
// EXPORT FUNCTIONS
// ============================================================================

window.connectWebSocket = connectWebSocket;
window.disconnectWebSocket = disconnectWebSocket;
window.isWebSocketConnected = isWebSocketConnected;

// ============================================================================
// AUTO-CONNECT (if enabled)
// ============================================================================

// Uncomment the line below to auto-connect on page load:
// document.addEventListener('DOMContentLoaded', connectWebSocket);
