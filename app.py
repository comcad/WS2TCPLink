from flask import Flask, request, render_template_string, redirect, make_response, jsonify
import os, socket, asyncio, threading, websockets

app = Flask(__name__)
app.secret_key = "aero_v7_stable_revival"
DB_PATH = '/app/data/ports.conf'
os.makedirs('/app/data', exist_ok=True)

active_proxies = {}
connection_counts = {}  # Track active connections per port

# --- ENHANCED FRUTIGER AERO UI ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="notranslate">
<head>
<meta name="google" content="notranslate">
<meta name="googlebot" content="notranslate">
    <title>WS2TCPLink // WS to TCP Bridge</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@300;400;600;700&display=swap');
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            background: linear-gradient(135deg, #00d4ff 0%, #0099ff 50%, #0066cc 100%); 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            padding: 30px 20px;
            color: #1a1a2e;
            position: relative;
            overflow-x: hidden;
        }
        
        /* Aero glass bubbles background effect */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 30%, rgba(255,255,255,0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(255,255,255,0.1) 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, rgba(255,255,255,0.08) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }
        
        .container { 
            max-width: 1100px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .header h1 {
            font-size: 3.5em;
            font-weight: 300;
            color: white;
            text-shadow: 0 4px 20px rgba(0,0,0,0.2);
            letter-spacing: -1px;
        }
        
        .header h1 span {
            font-weight: 700;
            background: linear-gradient(135deg, #fff 0%, #e0f7ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .header p {
            color: rgba(255,255,255,0.9);
            font-size: 1.1em;
            margin-top: 10px;
            font-weight: 300;
        }
        
        .glass-card {
            background: rgba(255, 255, 255, 0.25);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 30px;
            padding: 35px;
            margin-bottom: 30px;
            border: 1px solid rgba(255, 255, 255, 0.4);
            box-shadow: 
                0 8px 32px rgba(0, 0, 0, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.6);
            overflow: hidden;
        }
        
        .form-section {
            background: rgba(255, 255, 255, 0.35);
            padding: 30px 30px 30px 30px;
            border-radius: 25px;
            border: 1px solid rgba(255, 255, 255, 0.5);
        }
        
        .form-title {
            font-size: 1.3em;
            font-weight: 600;
            color: white;
            margin-bottom: 20px;
            text-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .input-row {
            display: grid;
            grid-template-columns: 1.7fr 0.75fr 2fr 100px 115px;
            gap: 10px;
            align-items: center;
        }
        
        input {
            padding: 14px 20px;
            border-radius: 50px;
            border: 1px solid rgba(255, 255, 255, 0.6);
            background: rgba(255, 255, 255, 0.7);
            font-size: 0.95em;
            font-weight: 500;
            color: #2d3436;
            outline: none;
            transition: all 0.3s ease;
            box-shadow: inset 0 2px 5px rgba(0,0,0,0.05);
        }
        
        input:focus {
            background: rgba(255, 255, 255, 0.9);
            border-color: rgba(255, 255, 255, 0.9);
            box-shadow: 
                inset 0 2px 5px rgba(0,0,0,0.05),
                0 0 0 3px rgba(255, 255, 255, 0.3);
        }
        
        input::placeholder {
            color: rgba(0, 0, 0, 0.4);
        }
        
        .btn {
            padding: 12px 16px;
            border-radius: 50px;
            border: none;
            background: linear-gradient(135deg, #0984e3 0%, #0770c9 100%);
            color: white;
            font-weight: 700;
            font-size: 0.8em;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 
                0 4px 15px rgba(9, 132, 227, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
            text-transform: uppercase;
            letter-spacing: 0.8px;
            white-space: nowrap;
        }
        
        .btn-test {
            background: linear-gradient(135deg, #00b894 0%, #00a383 100%);
            box-shadow: 
                0 4px 15px rgba(0, 184, 148, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
            padding: 12px 20px;
        }
        
        .btn-test:hover {
            transform: translateY(-2px);
            box-shadow: 
                0 6px 20px rgba(0, 184, 148, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 
                0 6px 20px rgba(9, 132, 227, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .bridges-section {
            margin-top: 30px;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .section-title {
            font-size: 1.5em;
            font-weight: 600;
            color: white;
            text-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .badge {
            background: rgba(255, 255, 255, 0.4);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
            color: rgba(0, 0, 0, 0.7);
        }
        
        .bridge-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .bridge-item {
            background: rgba(255, 255, 255, 0.35);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px 25px;
            border: 1px solid rgba(255, 255, 255, 0.5);
            display: grid;
            grid-template-columns: 1.5fr 0.6fr 2.2fr 70px 100px 85px;
            gap: 25px;
            align-items: center;
            transition: all 0.3s ease;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .bridge-item:hover {
            background: rgba(255, 255, 255, 0.45);
            transform: translateX(5px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .bridge-name {
            font-weight: 700;
            font-size: 1.05em;
            color: #2d3436;
        }
        
        .bridge-port {
            background: rgba(9, 132, 227, 0.2);
            padding: 6px 14px;
            border-radius: 15px;
            font-family: 'Courier New', monospace;
            font-weight: 700;
            color: #0984e3;
            text-align: center;
            border: 1px solid rgba(9, 132, 227, 0.3);
        }
        
        .bridge-target {
            font-family: 'Courier New', monospace;
            color: #636e72;
            font-size: 0.95em;
        }
        
        .connection-badge {
            background: linear-gradient(135deg, rgba(108, 92, 231, 0.2) 0%, rgba(74, 58, 189, 0.15) 100%);
            color: #6c5ce7;
            border: 2px solid rgba(108, 92, 231, 0.4);
            padding: 6px 12px;
            border-radius: 12px;
            font-weight: 800;
            font-size: 0.85em;
            text-align: center;
            white-space: nowrap;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            max-width: 70px;
        }
        
        .connection-badge.active {
            background: linear-gradient(135deg, rgba(0, 184, 148, 0.25) 0%, rgba(0, 163, 131, 0.2) 100%);
            color: #00b894;
            border-color: rgba(0, 184, 148, 0.5);
        }
        
        .bridge-arrow {
            color: #0984e3;
            font-size: 1.2em;
            font-weight: 700;
        }
        
        .mode-badge {
            padding: 6px 14px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .mode-maple {
            background: linear-gradient(135deg, #a29bfe 0%, #6c5ce7 100%);
            color: white;
        }
        
        .mode-standard {
            background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
            color: white;
        }
        
        .del-btn {
            background: rgba(214, 48, 49, 0.15);
            color: #d63031;
            border: 1px solid rgba(214, 48, 49, 0.3);
            padding: 7px 10px;
            border-radius: 15px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            font-size: 0.68em;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }
        
        .test-btn {
            background: rgba(0, 184, 148, 0.15);
            color: #00b894;
            border: 1px solid rgba(0, 184, 148, 0.3);
            padding: 7px 18px;
            border-radius: 15px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            font-size: 0.68em;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }
        
        .test-btn:hover {
            background: rgba(0, 184, 148, 0.25);
            border-color: rgba(0, 184, 148, 0.5);
            transform: scale(1.05);
        }
        
        .del-btn:hover {
            background: rgba(214, 48, 49, 0.25);
            border-color: rgba(214, 48, 49, 0.5);
            transform: scale(1.05);
        }
        
        /* Modal Popup */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(5px);
            animation: fadeIn 0.3s ease;
        }
        
        .modal.show {
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .modal-content {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 25px;
            padding: 40px;
            max-width: 500px;
            width: 90%;
            border: 1px solid rgba(255, 255, 255, 0.6);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            animation: slideUp 0.3s ease;
            text-align: center;
        }
        
        .modal-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        
        .modal-icon.success {
            color: #00b894;
        }
        
        .modal-icon.error {
            color: #d63031;
        }
        
        .modal-title {
            font-size: 1.8em;
            font-weight: 700;
            margin-bottom: 15px;
            color: #2d3436;
        }
        
        .modal-message {
            font-size: 1.1em;
            color: #636e72;
            margin-bottom: 30px;
            line-height: 1.6;
        }
        
        .modal-close {
            padding: 12px 40px;
            border-radius: 50px;
            border: none;
            background: linear-gradient(135deg, #0984e3 0%, #0770c9 100%);
            color: white;
            font-weight: 700;
            cursor: pointer;
            font-size: 1em;
            text-transform: uppercase;
            letter-spacing: 1px;
            box-shadow: 0 4px 15px rgba(9, 132, 227, 0.4);
        }
        
        .modal-close:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(9, 132, 227, 0.5);
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes slideUp {
            from { 
                opacity: 0;
                transform: translateY(30px);
            }
            to { 
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: rgba(255, 255, 255, 0.8);
        }
        
        .empty-state svg {
            width: 80px;
            height: 80px;
            margin-bottom: 20px;
            opacity: 0.6;
        }
        
        .empty-state p {
            font-size: 1.1em;
            font-weight: 300;
        }
        
        @media (max-width: 768px) {
            .input-row {
                grid-template-columns: 1fr;
            }
            
            .bridge-item {
                grid-template-columns: 1fr;
                gap: 12px;
            }
            
            .header h1 {
                font-size: 2.5em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>WS2TCP<span>Link</span></h1>
            <p>Universal WebSocket to TCP Bridge</p>
        </div>
        
        <div class="glass-card">
            <div class="form-section">
                <div class="form-title">⚡ Establish New Bridge</div>
                <form method="POST" action="/add" class="input-row" id="bridgeForm" onsubmit="handleSubmit(event)">
                    <input name="name" id="newName" placeholder="Bridge Name" required>
                    <input name="port" id="newPort" type="number" placeholder="Port" required>
                    <input name="target" id="newTarget" placeholder="Target (IP:Port)" required>
                    <button type="button" class="btn btn-test" onclick="testConnection('new')">Test</button>
                    <button type="submit" class="btn">Connect</button>
                </form>
            </div>
        </div>
        
        <div class="glass-card bridges-section">
            <div class="section-header">
                <div class="section-title">🌐 Active Bridges</div>
                <div class="badge">{{ entries|length }} Active</div>
            </div>
            
            {% if entries %}
            <div class="bridge-list">
                {% for name, port, target, mode in entries %}
                <div class="bridge-item">
                    <div class="bridge-name">{{ name }}</div>
                    <div class="bridge-port">:{{ port }}</div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span class="bridge-arrow">→</span>
                        <span class="bridge-target">{{ target }}</span>
                    </div>
                    <div class="connection-badge" id="conn-{{ port }}">0</div>
                    <button class="test-btn" onclick="testConnection('{{ port }}', '{{ target }}')">Test</button>
                    <form method="POST" action="/delete" style="margin: 0;">
                        <input type="hidden" name="port" value="{{ port }}">
                        <button type="submit" class="del-btn">Remove</button>
                    </form>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="empty-state">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
                <p>No bridges established yet. Create one above to get started!</p>
            </div>
            {% endif %}
        </div>
    </div>
    
    <!-- Modal for test results -->
    <div id="testModal" class="modal">
        <div class="modal-content">
            <div class="modal-icon" id="modalIcon"></div>
            <div class="modal-title" id="modalTitle"></div>
            <div class="modal-message" id="modalMessage"></div>
            <button class="modal-close" onclick="closeModal()">Close</button>
        </div>
    </div>
    
    <script>
        function closeModal() {
            document.getElementById('testModal').classList.remove('show');
        }
        
        function showModal(success, title, message) {
            const modal = document.getElementById('testModal');
            const icon = document.getElementById('modalIcon');
            const titleEl = document.getElementById('modalTitle');
            const messageEl = document.getElementById('modalMessage');
            
            if (success) {
                icon.innerHTML = '✓';
                icon.className = 'modal-icon success';
            } else {
                icon.innerHTML = '✕';
                icon.className = 'modal-icon error';
            }
            
            titleEl.textContent = title;
            messageEl.textContent = message;
            modal.classList.add('show');
        }
        
        // Update connection counts every 2 seconds
        async function updateConnectionCounts() {
            try {
                const response = await fetch('/connections');
                const counts = await response.json();
                
                // Update each badge
                for (const [port, count] of Object.entries(counts)) {
                    const badge = document.getElementById(`conn-${port}`);
                    if (badge) {
                        badge.textContent = count;
                        if (count > 0) {
                            badge.classList.add('active');
                        } else {
                            badge.classList.remove('active');
                        }
                    }
                }
            } catch (error) {
                console.error('Failed to update connection counts:', error);
            }
        }
        
        // Start polling for connection counts
        setInterval(updateConnectionCounts, 2000);
        // Update immediately on load
        updateConnectionCounts();

        
        async function testConnection(port, target) {
            let testPort, testTarget, isExisting;
            
            if (port === 'new') {
                // Testing new bridge
                testPort = document.getElementById('newPort').value;
                testTarget = document.getElementById('newTarget').value;
                isExisting = false;
                
                if (!testPort || !testTarget) {
                    showModal(false, 'Invalid Input', 'Please fill in both Port and Target fields before testing.');
                    return;
                }
            } else {
                // Testing existing bridge
                testPort = port;
                testTarget = target;
                isExisting = true;
            }
            
            try {
                const response = await fetch('/test', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        port: testPort,
                        target: testTarget,
                        existing: isExisting
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showModal(true, 'Connection Test Passed!', 
                        result.message || `Port ${testPort} is available and ${testTarget} is reachable. Ready to establish bridge!`);
                } else {
                    showModal(false, 'Connection Test Failed', 
                        result.error || `Could not establish connection. Please verify your settings.`);
                }
            } catch (error) {
                showModal(false, 'Test Error', `Failed to test connection: ${error.message}`);
            }
        }
        
        async function handleSubmit(event) {
            event.preventDefault();
            
            const formData = new FormData(event.target);
            
            try {
                const response = await fetch('/add', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Immediately reload page on success
                    window.location.reload();
                } else {
                    showModal(false, 'Failed to Create Bridge', 
                        result.error || 'Could not establish bridge. Please check your settings.');
                }
            } catch (error) {
                showModal(false, 'Error', `Failed to create bridge: ${error.message}`);
            }
        }
    </script>
</body>
</html>
"""

# --- AUTO-DETECTION ENGINE ---

async def bridge_handler(websocket, target_host, target_port, mode, port):
    """Bridge handler with connection tracking"""
    writer = None
    
    # Increment connection count
    if port not in connection_counts:
        connection_counts[port] = 0
    connection_counts[port] += 1
    
    try:
        # Peek at the first packet to determine protocol
        first_packet = await websocket.recv()
        reader, writer = await asyncio.open_connection(target_host, target_port)

        # Auto-detection logic:
        # MapleStory sends small text handshake that should be DROPPED
        # Stick Arena and other games send binary data that should be FORWARDED
        is_maple = False
        
        # Check if it's a text string (MapleStory handshake)
        if isinstance(first_packet, str):
            is_maple = True
        elif isinstance(first_packet, bytes):
            # Try to decode as UTF-8 text - if successful and small, it's MapleStory
            try:
                decoded = first_packet.decode('utf-8', errors='strict')
                # MapleStory handshakes are usually short text strings
                if len(decoded) < 200 and decoded.isprintable():
                    is_maple = True
                else:
                    is_maple = False
            except (UnicodeDecodeError, AttributeError):
                # Binary data that can't be decoded = Standard mode (Stick Arena)
                is_maple = False

        if not is_maple:
            # Standard mode (Stick Arena): Forward the initial binary data immediately
            data = first_packet if isinstance(first_packet, bytes) else first_packet.encode()
            writer.write(data)
            await writer.drain()
        # MapleStory mode: Drop the handshake (do nothing with first_packet)

        async def ws_to_tcp():
            async for message in websocket:
                data = message if isinstance(message, bytes) else message.encode()
                writer.write(data)
                await writer.drain()

        async def tcp_to_ws():
            while True:
                data = await reader.read(65536)
                if not data: break
                await websocket.send(data)

        await asyncio.gather(ws_to_tcp(), tcp_to_ws())
    except: 
        pass
    finally:
        # Decrement connection count
        if port in connection_counts:
            connection_counts[port] -= 1
            if connection_counts[port] < 0:
                connection_counts[port] = 0
        
        if writer:
            writer.close()
            try: 
                await writer.wait_closed()
            except: 
                pass

def universal_subprotocol_select(arg1, arg2=None):
    """Handles v14 library handshake compatibility"""
    prots = arg1 if isinstance(arg1, list) else arg2
    return prots[0] if isinstance(prots, list) and prots else None

async def start_srv(port, target, mode='auto'):
    """Starts WebSocket server with auto-detection and returns server object"""
    h, tp = target.split(':')
    server = await websockets.serve(
        lambda ws: bridge_handler(ws, h, int(tp), mode, str(port)), 
        "0.0.0.0", port, 
        select_subprotocol=universal_subprotocol_select,
        ping_interval=None
    )
    # Store the server object in active_proxies
    active_proxies[str(port)]['server'] = server
    # Initialize connection count
    if str(port) not in connection_counts:
        connection_counts[str(port)] = 0
    # Keep running
    await asyncio.Future()

# --- SCAFFOLDING ---

proxy_loop = asyncio.new_event_loop()
threading.Thread(target=lambda: (asyncio.set_event_loop(proxy_loop), proxy_loop.run_forever()), daemon=True).start()

def get_entries():
    """Reads bridge entries from config file"""
    if not os.path.exists(DB_PATH): 
        return []
    entries = []
    with open(DB_PATH, 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) >= 3:
                # Auto-detect mode if not specified
                if len(parts) == 3: 
                    parts.append('auto')
                entries.append(parts)
    return entries

def sync():
    """Synchronizes active proxies with config file"""
    for _, port, target, mode in get_entries():
        if port not in active_proxies:
            active_proxies[port] = {}  # Pre-create entry
            asyncio.run_coroutine_threadsafe(start_srv(int(port), target, mode), proxy_loop)

@app.route('/')
def index(): 
    
    response = make_response(render_template_string(HTML_TEMPLATE, entries=get_entries()))
    response.headers['Content-Language'] = 'en'
    return response

@app.route('/add', methods=['POST'])
def add():
    """Adds new bridge with auto-detection and port validation"""
    import socket
    n = request.form['name']
    p = request.form['port']
    t = request.form['target']
    m = 'auto'  # Always use auto-detection
    
    try:
        # Validate port number
        local_port = int(p)
        if local_port < 1 or local_port > 65535:
            return jsonify({
                'success': False, 
                'error': 'Port must be between 1 and 65535'
            })
        
        # Check if port is already in use
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            test_socket.bind(('0.0.0.0', local_port))
            test_socket.close()
        except OSError as e:
            if e.errno == 98 or e.errno == 10048:  # Address already in use
                return jsonify({
                    'success': False,
                    'error': f'Port {p} is already in use by another application or bridge. Please choose a different port.'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Cannot use port {p}: {str(e)}'
                })
        
        # Validate target format
        if ':' not in t:
            return jsonify({
                'success': False,
                'error': 'Invalid target format. Use IP:Port (e.g., 192.168.1.1:8080)'
            })
        
        # All checks passed, add the bridge
        with open(DB_PATH, 'a') as f: 
            f.write(f"{n}|{p}|{t}|{m}\n")
        sync()
        return jsonify({'success': True, 'message': 'Bridge established successfully!'})
        
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid port number. Please enter a valid number.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to create bridge: {str(e)}'
        })

@app.route('/delete', methods=['POST'])
def delete():
    """Removes bridge by port and stops the WebSocket server"""
    p = request.form['port']
    
    # Close the server if it exists (non-blocking)
    if p in active_proxies and 'server' in active_proxies[p]:
        server = active_proxies[p]['server']
        server.close()
        # Schedule cleanup without blocking
        async def wait_close():
            await server.wait_closed()
        asyncio.run_coroutine_threadsafe(wait_close(), proxy_loop)
    
    # Remove from tracking
    if p in active_proxies:
        del active_proxies[p]
    
    # Clear connection count
    if p in connection_counts:
        del connection_counts[p]
    
    # Remove from config file
    entries = [e for e in get_entries() if e[1] != p]
    with open(DB_PATH, 'w') as f:
        for e in entries: 
            f.write("|".join(e) + "\n")
    
    return redirect('/')

@app.route('/connections', methods=['GET'])
def get_connections():
    """Returns current connection counts for all bridges"""
    return jsonify(connection_counts)

@app.route('/test', methods=['POST'])
def test():
    """Tests connection to target and checks if local port is available"""
    import socket
    data = request.get_json()
    port = data.get('port')
    target = data.get('target')
    is_existing = data.get('existing', False)  # Flag to check if testing existing bridge
    
    try:
        # Validate port number
        try:
            local_port = int(port)
            if local_port < 1 or local_port > 65535:
                return jsonify({'success': False, 'error': 'Port must be between 1 and 65535'})
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid port number'})
        
        # Only check if port is available for NEW bridges (not existing ones)
        if not is_existing:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                test_socket.bind(('0.0.0.0', local_port))
                test_socket.close()
            except OSError as e:
                if e.errno == 98 or e.errno == 10048:  # Address already in use (Linux/Windows)
                    return jsonify({
                        'success': False, 
                        'error': f'Port {local_port} is already in use by another application or bridge'
                    })
                else:
                    return jsonify({'success': False, 'error': f'Cannot bind to port {local_port}: {str(e)}'})
        
        # Parse target
        if ':' not in target:
            return jsonify({'success': False, 'error': 'Invalid target format. Use IP:Port'})
        
        host, target_port = target.split(':', 1)
        try:
            target_port = int(target_port)
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid target port number'})
        
        # Test TCP connection to target
        target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_socket.settimeout(3)
        result = target_socket.connect_ex((host, target_port))
        target_socket.close()
        
        if result == 0:
            if is_existing:
                return jsonify({
                    'success': True,
                    'message': f'Bridge is active and target {target} is reachable'
                })
            else:
                return jsonify({
                    'success': True,
                    'message': f'Port {local_port} is available and target {target} is reachable'
                })
        else:
            return jsonify({
                'success': False, 
                'error': f'Cannot reach target {target} (connection refused or timeout)'
            })
            
    except socket.gaierror:
        return jsonify({'success': False, 'error': 'Could not resolve target hostname'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Test failed: {str(e)}'})

if __name__ == '__main__':
    sync()
    app.run(host='0.0.0.0', port=5050)
