/**
 * GR Cup CLI Monitor - WebSocket Handler
 * Real-time synchronization between clients
 */

// ============================================================================
// WEBSOCKET CONNECTION
// ============================================================================

let socket = null;

/**
 * Connect to WebSocket server
 */
function connectWebSocket() {
    try {
        socket = io('http://localhost:5000');

        socket.on('connect', () => {
            console.log('🔌 WebSocket connected');
        });

        socket.on('disconnect', () => {
            console.log('🔌 WebSocket disconnected');
        });

        socket.on('connected', (data) => {
            console.log('✅ Server acknowledged connection:', data.message);
        });

        // Listen for lap changes from other clients
        socket.on('lap_changed', (data) => {
            console.log('📡 Received lap change from another client:', data);

            // Update lap if same driver
            if (data.driver_id === AppState.selectedDriver) {
                if (data.lap !== AppState.currentLap) {
                    console.log(`Syncing lap to ${data.lap} from remote client`);
                    setLap(data.lap);
                }
            }
        });

        // Listen for playback state changes
        socket.on('playback_updated', (data) => {
            console.log('📡 Received playback state from another client:', data);

            // Could sync playback state here if desired
            // For now, just log it
        });

        // Listen for replay start
        socket.on('replay_started', (data) => {
            console.log('📡 Another client started replay:', data);
        });

        // Store socket globally
        window.socket = socket;

    } catch (error) {
        console.error('❌ Failed to connect WebSocket:', error);
    }
}

/**
 * Disconnect WebSocket
 */
function disconnectWebSocket() {
    if (socket && socket.connected) {
        socket.disconnect();
        console.log('🔌 WebSocket disconnected manually');
    }
}

// ============================================================================
// INITIALIZE WEBSOCKET ON PAGE LOAD
// ============================================================================

// Note: WebSocket initialization is called from main.js after app init
// To enable real-time sync, uncomment the line below:
// document.addEventListener('DOMContentLoaded', connectWebSocket);

// Export functions
window.connectWebSocket = connectWebSocket;
window.disconnectWebSocket = disconnectWebSocket;
