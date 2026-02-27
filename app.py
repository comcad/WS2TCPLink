from flask import Flask, request, render_template_string, redirect, make_response, jsonify, Response
import os, socket, asyncio, threading, websockets, ssl, collections, time, json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "aero_v7_stable_revival"
DB_PATH = '/app/data/ports.conf'
CERT_DIR = '/app/data/certs'
os.makedirs('/app/data', exist_ok=True)
os.makedirs(CERT_DIR, exist_ok=True)

active_proxies = {}
connection_counts = {}  # Track active connections per port

# --- LOG BUFFERS (NEW) ---
log_buffers = {}          # port -> deque of log entry dicts
log_subscribers = {}      # port -> list of queue objects for SSE

LOG_MAX_LINES = 200

def get_log_buffer(port):
    key = str(port)
    if key not in log_buffers:
        log_buffers[key] = collections.deque(maxlen=LOG_MAX_LINES)
    return log_buffers[key]

def push_log(port, event_type, message):
    key = str(port)
    entry = {
        'ts': time.strftime('%H:%M:%S'),
        'type': event_type,   # 'connect', 'disconnect', 'ws_in', 'ws_out', 'error'
        'msg': message
    }
    get_log_buffer(key).append(entry)
    # Notify SSE subscribers
    if key in log_subscribers:
        dead = []
        for q in log_subscribers[key]:
            try:
                q.put_nowait(entry)
            except Exception:
                dead.append(q)
        for d in dead:
            try:
                log_subscribers[key].remove(d)
            except ValueError:
                pass

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
            max-width: 1200px;
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
            padding: 30px;
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
            grid-template-columns: 1fr 1fr 1fr auto auto;
            gap: 15px; /* Increased gap slightly for better breathing room */
            align-items: center;
        }
        
        input[type="text"], input[type="number"] {
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
        
        input[type="text"]:focus, input[type="number"]:focus {
            background: rgba(255, 255, 255, 0.9);
            border-color: rgba(255, 255, 255, 0.9);
            box-shadow: 
                inset 0 2px 5px rgba(0,0,0,0.05),
                0 0 0 3px rgba(255, 255, 255, 0.3);
        }
        
        input::placeholder {
            color: rgba(0, 0, 0, 0.4);
        }
        

.addbridgebtn {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    min-width: 85px; /* This ensures "SSL" and "DELETE" are the same width */
    height: 38px;    /* Consistent height across all buttons */
    padding: 0 15px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    border-radius: 12px; /* Matches your card aesthetics better than 50px here */
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
    background: linear-gradient(135deg, #0984e3 0%, #0770c9 100%) !important;
    box-shadow: 0 4px 15px rgba(9, 132, 227, 0.4);
}

.btn {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    min-width: 85px; /* This ensures "SSL" and "DELETE" are the same width */
    height: 38px;    /* Consistent height across all buttons */
    padding: 0 15px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    border-radius: 12px; /* Matches your card aesthetics better than 50px here */
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
}

        
        .btn-test {
            background: linear-gradient(135deg, #00b894 0%, #00a383 100%);
            box-shadow: 
                0 4px 15px rgba(0, 184, 148, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
        }
        
        .btn-test:hover {
            transform: translateY(-2px);
            box-shadow: 
                0 6px 20px rgba(0, 184, 148, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
        }

       .addbridgebtn:hover {
            transform: translateY(-2px);
            box-shadow: 
                0 6px 20px rgba(9, 132, 227, 0.5),
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
            grid-template-columns: 2fr 80px 1.5fr 60px 80px auto auto auto auto;
            gap: 15px;
            align-items: center;
            transition: all 0.3s ease;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .bridge-item:hover {
            background: rgba(255, 255, 255, 0.45);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .bridge-info {
            display: flex;
            flex-direction: column;
        }
        
        .bridge-name {
            font-weight: 600;
            font-size: 1.05em;
            color: #1a1a2e;
        }
        
        .port-display {
            background: rgba(9, 132, 227, 0.2);
            color: #0770c9;
            padding: 8px 16px;
            border-radius: 15px;
            font-weight: 700;
            font-size: 1.05em;
            text-align: center;
            border: 1px solid rgba(9, 132, 227, 0.3);
        }
        
        .target-display {
            font-family: 'Courier New', monospace;
            font-size: 0.95em;
            color: rgba(0, 0, 0, 0.7);
            background: rgba(0, 0, 0, 0.05);
            padding: 8px 14px;
            border-radius: 12px;
            font-weight: 500;
        }
        
        .connection-count {
            background: rgba(0, 184, 148, 0.2);
            color: #00a383;
            padding: 6px 12px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 0.9em;
            text-align: center;
            border: 1px solid rgba(0, 184, 148, 0.3);
        }
        
        .ssl-indicator {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 5px;
            padding: 6px 12px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .ssl-enabled {
            background: rgba(0, 184, 148, 0.2);
            color: #00a383;
            border: 1px solid rgba(0, 184, 148, 0.3);
        }
        
        .ssl-disabled {
            background: rgba(255, 107, 107, 0.2);
            color: #d63031;
            border: 1px solid rgba(255, 107, 107, 0.3);
        }
        
        .ssl-icon {
            width: 12px;
            height: 12px;
        }
        
        .btn-delete {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
            box-shadow: 
                0 4px 15px rgba(255, 107, 107, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
            padding: 10px 16px;
            font-size: 0.75em;
        }
        
        .btn-delete:hover {
            box-shadow: 
                0 6px 20px rgba(255, 107, 107, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
        }
        
        .btn-cert {
            background: linear-gradient(135deg, #fd79a8 0%, #e84393 100%);
            box-shadow: 
                0 4px 15px rgba(232, 67, 147, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
            padding: 10px 16px;
            font-size: 0.75em;
        }
        
        .btn-cert:hover {
            box-shadow: 
                0 6px 20px rgba(232, 67, 147, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
        }
        
        .btn-bridge-test {
            background: linear-gradient(135deg, #00b894 0%, #00a383 100%);
            box-shadow: 
                0 4px 15px rgba(0, 184, 148, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
            padding: 10px 16px;
            font-size: 0.75em;
        }
        
        .btn-bridge-test:hover {
            box-shadow: 
                0 6px 20px rgba(0, 184, 148, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
        }

        /* NEW: Log button */
        .btn-log {
            background: linear-gradient(135deg, #6c5ce7 0%, #5849d1 100%);
            box-shadow: 
                0 4px 15px rgba(108, 92, 231, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
            padding: 10px 16px;
            font-size: 0.75em;
            color: white;
        }
        .btn-log:hover {
            box-shadow: 
                0 6px 20px rgba(108, 92, 231, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: rgba(255, 255, 255, 0.8);
        }
        
        .empty-state-icon {
            font-size: 4em;
            margin-bottom: 20px;
            opacity: 0.5;
        }
        
        .empty-state-text {
            font-size: 1.2em;
            font-weight: 300;
        }
        
        /* Enhanced Modal Styles */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(10px);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            animation: fadeIn 0.3s ease;
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
        
        .modal.active {
            display: flex;
        }
        
        .modal-content {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 30px;
            padding: 40px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.6);
            animation: slideUp 0.3s ease;
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
        }
        
        .modal-title {
            font-size: 1.8em;
            font-weight: 600;
            color: #1a1a2e;
        }
        
        .modal-close {
            background: none;
            border: none;
            font-size: 2em;
            color: rgba(0, 0, 0, 0.4);
            cursor: pointer;
            transition: all 0.3s ease;
            padding: 0;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
        }
        
        .modal-close:hover {
            background: rgba(0, 0, 0, 0.1);
            color: rgba(0, 0, 0, 0.7);
            transform: rotate(90deg);
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #1a1a2e;
            font-size: 0.95em;
        }
        
        .file-input-wrapper {
            position: relative;
            display: inline-block;
            width: 100%;
        }
        
        .file-input {
            display: none;
        }
        
        .file-input-button {
            display: block;
            width: 100%;
            padding: 14px 20px;
            background: rgba(9, 132, 227, 0.1);
            border: 2px dashed rgba(9, 132, 227, 0.3);
            border-radius: 15px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            color: #0770c9;
            font-weight: 600;
        }
        
        .file-input-button:hover {
            background: rgba(9, 132, 227, 0.2);
            border-color: rgba(9, 132, 227, 0.5);
            transform: translateY(-2px);
        }
        
        .file-name {
            margin-top: 8px;
            font-size: 0.9em;
            color: rgba(0, 0, 0, 0.6);
            font-style: italic;
        }
        
        .cert-status {
            background: rgba(0, 184, 148, 0.1);
            border: 1px solid rgba(0, 184, 148, 0.3);
            border-radius: 15px;
            padding: 15px 20px;
            margin-bottom: 20px;
        }
        
        .cert-status-title {
            font-weight: 600;
            color: #00a383;
            margin-bottom: 8px;
        }
        
        .cert-status-detail {
            font-size: 0.9em;
            color: rgba(0, 0, 0, 0.6);
            font-family: 'Courier New', monospace;
        }
        
        .btn-full {
            width: 100%;
            padding: 14px 20px;
            font-size: 0.9em;
            margin-top: 10px;
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
            box-shadow: 
                0 4px 15px rgba(255, 107, 107, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
        }
        
        .btn-danger:hover {
            box-shadow: 
                0 6px 20px rgba(255, 107, 107, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
        }
        
        /* Toast Notification */
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 20px 25px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.6);
            z-index: 2000;
            min-width: 300px;
            max-width: 500px;
            animation: slideInRight 0.3s ease;
            display: none;
        }
        
        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(100px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        @keyframes slideOutRight {
            from {
                opacity: 1;
                transform: translateX(0);
            }
            to {
                opacity: 0;
                transform: translateX(100px);
            }
        }
        
        .toast.show {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .toast.hide {
            animation: slideOutRight 0.3s ease;
        }
        
        .toast-icon {
            font-size: 2em;
            flex-shrink: 0;
        }
        
        .toast-content {
            flex: 1;
        }
        
        .toast-title {
            font-weight: 700;
            font-size: 1.05em;
            margin-bottom: 5px;
            color: #1a1a2e;
        }
        
        .toast-message {
            font-size: 0.95em;
            color: rgba(0, 0, 0, 0.7);
            line-height: 1.4;
        }
        
        .toast-close {
            background: none;
            border: none;
            font-size: 1.5em;
            color: rgba(0, 0, 0, 0.4);
            cursor: pointer;
            padding: 0;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: all 0.3s ease;
            flex-shrink: 0;
        }
        
        .toast-close:hover {
            background: rgba(0, 0, 0, 0.1);
            color: rgba(0, 0, 0, 0.7);
        }
        
        .toast.success .toast-icon { color: #00b894; }
        .toast.error .toast-icon { color: #ff6b6b; }
        .toast.info .toast-icon { color: #0984e3; }
        
        /* Confirmation Dialog */
        .confirm-dialog {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 25px;
            padding: 35px;
            max-width: 450px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.6);
            animation: slideUp 0.3s ease;
        }
        
        .confirm-icon {
            font-size: 3.5em;
            text-align: center;
            margin-bottom: 20px;
        }
        
        .confirm-title {
            font-size: 1.5em;
            font-weight: 600;
            color: #1a1a2e;
            text-align: center;
            margin-bottom: 15px;
        }
        
        .confirm-message {
            font-size: 1em;
            color: rgba(0, 0, 0, 0.7);
            text-align: center;
            margin-bottom: 25px;
            line-height: 1.5;
        }
        
        .confirm-buttons {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        /* ---- NEW: Log Modal Styles ---- */
        .log-modal-content {
            background: #0d1117;
            border-radius: 30px;
            padding: 0;
            max-width: 820px;
            width: 95%;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(108, 92, 231, 0.3);
            animation: slideUp 0.3s ease;
            overflow: hidden;
        }
        .log-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 28px;
            background: rgba(108, 92, 231, 0.15);
            border-bottom: 1px solid rgba(108, 92, 231, 0.25);
            flex-shrink: 0;
        }
        .log-modal-title {
            font-size: 1.2em;
            font-weight: 700;
            color: #a29bfe;
            letter-spacing: 0.5px;
        }
        .log-modal-meta {
            font-size: 0.8em;
            color: rgba(162, 155, 254, 0.6);
            margin-top: 2px;
        }
        .log-modal-controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .log-pill {
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 0.72em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
        }
        .log-pill-pause {
            background: rgba(253, 203, 110, 0.2);
            color: #fdcb6e;
            border: 1px solid rgba(253, 203, 110, 0.3);
        }
        .log-pill-pause:hover { background: rgba(253, 203, 110, 0.35); }
        .log-pill-clear {
            background: rgba(255, 107, 107, 0.15);
            color: #ff7675;
            border: 1px solid rgba(255, 107, 107, 0.3);
        }
        .log-pill-clear:hover { background: rgba(255, 107, 107, 0.3); }
        .log-close-btn {
            background: rgba(255,255,255,0.08);
            border: none;
            color: rgba(255,255,255,0.5);
            font-size: 1.4em;
            width: 34px;
            height: 34px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        .log-close-btn:hover { background: rgba(255,255,255,0.15); color: white; transform: rotate(90deg); }
        .log-filter-bar {
            display: flex;
            gap: 8px;
            padding: 12px 28px;
            background: rgba(255,255,255,0.03);
            border-bottom: 1px solid rgba(255,255,255,0.06);
            flex-wrap: wrap;
            flex-shrink: 0;
        }
        .log-filter-btn {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.72em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            cursor: pointer;
            border: 1px solid transparent;
            transition: all 0.2s;
            opacity: 0.5;
        }
        .log-filter-btn.active { opacity: 1; }
        .log-filter-btn[data-type="all"]        { background: rgba(255,255,255,0.1);  color: #dfe6e9; border-color: rgba(255,255,255,0.2); }
        .log-filter-btn[data-type="connect"]    { background: rgba(0,184,148,0.15);   color: #00b894; border-color: rgba(0,184,148,0.3); }
        .log-filter-btn[data-type="disconnect"] { background: rgba(255,107,107,0.15); color: #ff6b6b; border-color: rgba(255,107,107,0.3); }
        .log-filter-btn[data-type="ws_in"]      { background: rgba(9,132,227,0.15);   color: #74b9ff; border-color: rgba(9,132,227,0.3); }
        .log-filter-btn[data-type="ws_out"]     { background: rgba(253,203,110,0.15); color: #fdcb6e; border-color: rgba(253,203,110,0.3); }
        .log-filter-btn[data-type="error"]      { background: rgba(255,107,107,0.15); color: #ff6b6b; border-color: rgba(255,107,107,0.3); }
        .log-body {
            flex: 1;
            overflow-y: auto;
            padding: 16px 0;
            font-family: 'Courier New', 'Cascadia Code', monospace;
            font-size: 0.82em;
            line-height: 1.6;
        }
        .log-body::-webkit-scrollbar { width: 6px; }
        .log-body::-webkit-scrollbar-track { background: transparent; }
        .log-body::-webkit-scrollbar-thumb { background: rgba(108,92,231,0.4); border-radius: 3px; }
        .log-empty {
            text-align: center;
            color: rgba(255,255,255,0.2);
            padding: 60px 20px;
            font-size: 0.9em;
        }
        .log-line {
            display: flex;
            align-items: baseline;
            gap: 12px;
            padding: 3px 28px;
            transition: background 0.1s;
        }
        .log-line:hover { background: rgba(255,255,255,0.04); }
        .log-line.hidden { display: none; }
        .log-ts {
            color: rgba(255,255,255,0.25);
            flex-shrink: 0;
            font-size: 0.9em;
        }
        .log-badge {
            flex-shrink: 0;
            font-size: 0.72em;
            font-weight: 700;
            padding: 1px 8px;
            border-radius: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            min-width: 80px;
            text-align: center;
        }
        .log-badge-connect    { background: rgba(0,184,148,0.25);   color: #00b894; }
        .log-badge-disconnect { background: rgba(255,107,107,0.25); color: #ff6b6b; }
        .log-badge-ws_in      { background: rgba(9,132,227,0.25);   color: #74b9ff; }
        .log-badge-ws_out     { background: rgba(253,203,110,0.25); color: #fdcb6e; }
        .log-badge-error      { background: rgba(255,107,107,0.25); color: #ff6b6b; }
        .log-text {
            color: rgba(255,255,255,0.75);
            word-break: break-all;
        }
        .log-footer {
            padding: 10px 28px;
            background: rgba(255,255,255,0.03);
            border-top: 1px solid rgba(255,255,255,0.06);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-shrink: 0;
        }
        .log-status-dot {
            width: 8px; height: 8px;
            border-radius: 50%;
            background: #00b894;
            display: inline-block;
            margin-right: 6px;
            animation: pulse-dot 1.5s infinite;
        }
        .log-status-dot.paused { background: #fdcb6e; animation: none; }
        .log-status-dot.closed { background: #ff6b6b; animation: none; }
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        .log-status-text { font-size: 0.75em; color: rgba(255,255,255,0.35); }
        .log-line-count { font-size: 0.75em; color: rgba(255,255,255,0.25); }
        /* ---- END Log Modal Styles ---- */
        
        @media (max-width: 1200px) {
            .bridge-item {
                grid-template-columns: 1fr;
                gap: 15px;
            }
            
            .input-row {
                grid-template-columns: 1fr;
            }
            
            .toast {
                left: 20px;
                right: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><span>WS2TCP</span>Link</h1>
            <p>WebSocket to TCP Bridge Manager with SSL/TLS Support</p>
        </div>
        
        <div class="glass-card">
            <div class="form-section">
                <div class="form-title">⚡ Create New Bridge</div>
                <form id="addForm" onsubmit="return addBridge(event)">
                    <div class="input-row">
                        <input type="text" id="name" name="name" placeholder="Bridge Name" required>
                        <input type="number" id="port" name="port" placeholder="Port" min="1" max="65535" required>
                        <input type="text" id="target" name="target" placeholder="Target (IP:Port)" required>
                        <button type="button" class="btn btn-test" onclick="testConnection(false)">TEST</button>
                        <button type="submit" class="addbridgebtn">ADD BRIDGE</button>
                    </div>
                </form>
            </div>
        </div>
        
        <div class="glass-card">
            <div class="bridges-section">
                <div class="section-header">
                    <div class="section-title">🌐 Active Bridges</div>
                    <div class="badge" id="bridgeCount">{{ entries|length }} Active</div>
                </div>
                
                <div class="bridge-list" id="bridgeList">
                    {% if entries %}
                        {% for name, port, target, mode in entries %}
                        <div class="bridge-item">
                            <div class="bridge-info">
                                <div class="bridge-name">{{ name }}</div>
                            </div>
                            <div class="port-display">:{{ port }}</div>
                            <div class="target-display">{{ target }}</div>
                            <div class="connection-count" id="conn-{{ port }}">0</div>
                            <div class="ssl-indicator {% if has_ssl(port) %}ssl-enabled{% else %}ssl-disabled{% endif %}" id="ssl-{{ port }}">
                                <svg class="ssl-icon" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/>
                                </svg>
                                {% if has_ssl(port) %}WSS{% else %}WS{% endif %}
                            </div>
                            <button class="btn btn-bridge-test" onclick="testBridge('{{ port }}', '{{ target }}')">TEST</button>
                            <button class="btn btn-cert" onclick="openCertModal('{{ port }}', '{{ name }}')">SSL</button>
                            <button class="btn btn-log" onclick="openLogModal('{{ port }}', '{{ name }}')">LOG</button>
                            <form method="post" action="/delete" style="margin: 0;" onsubmit="return confirmDelete(event, '{{ name }}')">
                                <input type="hidden" name="port" value="{{ port }}">
                                <button type="submit" class="btn btn-delete">DELETE</button>
                            </form>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div class="empty-state">
                            <div class="empty-state-icon">🌐</div>
                            <div class="empty-state-text">No bridges configured yet. Add one above to get started!</div>
                        </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
    
    <!-- Certificate Upload Modal -->
    <div id="certModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">🔒 SSL Certificate Manager</div>
                <button class="modal-close" onclick="closeCertModal()">&times;</button>
            </div>
            
            <div id="certStatus"></div>
            
            <form id="certForm" enctype="multipart/form-data" onsubmit="return uploadCert(event)">
                <input type="hidden" id="certPort" name="port">
                
                <div class="form-group">
                    <label class="form-label">Certificate File (.crt or .pem)</label>
                    <div class="file-input-wrapper">
                        <input type="file" id="certFile" name="cert" class="file-input" accept=".crt,.pem" onchange="updateFileName('certFile', 'certFileName')">
                        <label for="certFile" class="file-input-button">
                            📄 Choose Certificate File
                        </label>
                        <div id="certFileName" class="file-name"></div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Private Key File (.key or .pem)</label>
                    <div class="file-input-wrapper">
                        <input type="file" id="keyFile" name="key" class="file-input" accept=".key,.pem" onchange="updateFileName('keyFile', 'keyFileName')">
                        <label for="keyFile" class="file-input-button">
                            🔑 Choose Key File
                        </label>
                        <div id="keyFileName" class="file-name"></div>
                    </div>
                </div>
                
                <button type="submit" class="btn btn-full">Upload Certificate</button>
                <button type="button" class="btn btn-danger btn-full" onclick="confirmDeleteCert()" id="deleteCertBtn" style="display: none;">Remove Certificate</button>
            </form>
        </div>
    </div>
    
    <!-- Confirmation Modal -->
    <div id="confirmModal" class="modal">
        <div class="confirm-dialog">
            <div class="confirm-icon" id="confirmIcon">⚠️</div>
            <div class="confirm-title" id="confirmTitle">Confirm Action</div>
            <div class="confirm-message" id="confirmMessage">Are you sure?</div>
            <div class="confirm-buttons">
                <button class="btn" onclick="closeConfirmModal()" style="background: linear-gradient(135deg, #636e72 0%, #505759 100%);">Cancel</button>
                <button class="btn btn-danger" onclick="confirmAction()" id="confirmBtn">Confirm</button>
            </div>
        </div>
    </div>

    <!-- NEW: Live Log Modal -->
    <div id="logModal" class="modal">
        <div class="log-modal-content">
            <div class="log-modal-header">
                <div>
                    <div class="log-modal-title">📡 Live Connection & Packet Log</div>
                    <div class="log-modal-meta" id="logModalMeta">—</div>
                </div>
                <div class="log-modal-controls">
                    <button class="log-pill log-pill-pause" id="logPauseBtn" onclick="toggleLogPause()">⏸ Pause</button>
                    <button class="log-pill log-pill-clear" onclick="clearLogDisplay()">🗑 Clear</button>
                    <button class="log-close-btn" onclick="closeLogModal()">&times;</button>
                </div>
            </div>
            <div class="log-filter-bar">
                <button class="log-filter-btn active" data-type="all"        onclick="setLogFilter('all')">All</button>
                <button class="log-filter-btn"         data-type="connect"   onclick="setLogFilter('connect')">Connect</button>
                <button class="log-filter-btn"         data-type="disconnect" onclick="setLogFilter('disconnect')">Disconnect</button>
                <button class="log-filter-btn"         data-type="ws_in"     onclick="setLogFilter('ws_in')">WS → TCP</button>
                <button class="log-filter-btn"         data-type="ws_out"    onclick="setLogFilter('ws_out')">TCP → WS</button>
                <button class="log-filter-btn"         data-type="error"     onclick="setLogFilter('error')">Errors</button>
            </div>
            <div class="log-body" id="logBody">
                <div class="log-empty" id="logEmpty">No events yet — waiting for activity...</div>
            </div>
            <div class="log-footer">
                <div>
                    <span class="log-status-dot" id="logStatusDot"></span>
                    <span class="log-status-text" id="logStatusText">Connecting...</span>
                </div>
                <div class="log-line-count" id="logLineCount">0 events</div>
            </div>
        </div>
    </div>
    
    <!-- Toast Notification -->
    <div id="toast" class="toast">
        <div class="toast-icon" id="toastIcon">✓</div>
        <div class="toast-content">
            <div class="toast-title" id="toastTitle">Success</div>
            <div class="toast-message" id="toastMessage">Operation completed successfully</div>
        </div>
        <button class="toast-close" onclick="hideToast()">&times;</button>
    </div>
    
    <script>
        let currentPort = null;
        let confirmCallback = null;
        
        // Toast functions
        function showToast(type, title, message, duration = 4000) {
            const toast = document.getElementById('toast');
            const toastIcon = document.getElementById('toastIcon');
            const toastTitle = document.getElementById('toastTitle');
            const toastMessage = document.getElementById('toastMessage');
            
            // Set icon based on type
            const icons = {
                success: '✓',
                error: '✗',
                info: 'ℹ'
            };
            
            toastIcon.textContent = icons[type] || icons.info;
            toastTitle.textContent = title;
            toastMessage.textContent = message;
            
            // Remove old type classes and add new one
            toast.className = 'toast show ' + type;
            
            // Auto hide after duration
            setTimeout(() => {
                hideToast();
            }, duration);
        }
        
        function hideToast() {
            const toast = document.getElementById('toast');
            toast.classList.add('hide');
            setTimeout(() => {
                toast.classList.remove('show', 'hide');
            }, 300);
        }
        
        // Confirmation dialog
        function showConfirm(title, message, callback, icon = '⚠️') {
            const modal = document.getElementById('confirmModal');
            document.getElementById('confirmIcon').textContent = icon;
            document.getElementById('confirmTitle').textContent = title;
            document.getElementById('confirmMessage').textContent = message;
            confirmCallback = callback;
            modal.classList.add('active');
        }
        
        function closeConfirmModal() {
            document.getElementById('confirmModal').classList.remove('active');
            confirmCallback = null;
        }
        
        function confirmAction() {
            if (confirmCallback) {
                confirmCallback();
            }
            closeConfirmModal();
        }
        
        function confirmDelete(event, name) {
            event.preventDefault();
            const form = event.target;
            showConfirm(
                'Delete Bridge',
                `Are you sure you want to delete the bridge "${name}"? This action cannot be undone.`,
                () => {
                    form.submit();
                },
                '🗑️'
            );
            return false;
        }
        
        function confirmDeleteCert() {
            showConfirm(
                'Remove SSL Certificate',
                'Are you sure you want to remove the SSL certificate? The bridge will be restarted with standard WS.',
                () => {
                    deleteCert();
                },
                '🔓'
            );
        }
        
        function openCertModal(port, name) {
            currentPort = port;
            document.getElementById('certPort').value = port;
            document.getElementById('certModal').classList.add('active');
            document.getElementById('certFileName').textContent = '';
            document.getElementById('keyFileName').textContent = '';
            document.getElementById('certFile').value = '';
            document.getElementById('keyFile').value = '';
            
            // Check if certificate exists
            fetch(`/cert-status/${port}`)
                .then(r => r.json())
                .then(data => {
                    const statusDiv = document.getElementById('certStatus');
                    const deleteBtn = document.getElementById('deleteCertBtn');
                    
                    if (data.has_cert) {
                        statusDiv.innerHTML = `
                            <div class="cert-status">
                                <div class="cert-status-title">✓ SSL Certificate Active</div>
                                <div class="cert-status-detail">Bridge: ${name} (Port ${port})</div>
                                <div class="cert-status-detail">WSS connections enabled</div>
                            </div>
                        `;
                        deleteBtn.style.display = 'block';
                    } else {
                        statusDiv.innerHTML = `
                            <div class="cert-status" style="background: rgba(255, 107, 107, 0.1); border-color: rgba(255, 107, 107, 0.3);">
                                <div class="cert-status-title" style="color: #d63031;">⚠ No SSL Certificate</div>
                                <div class="cert-status-detail">Bridge: ${name} (Port ${port})</div>
                                <div class="cert-status-detail">Upload certificate to enable WSS</div>
                            </div>
                        `;
                        deleteBtn.style.display = 'none';
                    }
                });
        }
        
        function closeCertModal() {
            document.getElementById('certModal').classList.remove('active');
            currentPort = null;
        }
        
        function updateFileName(inputId, displayId) {
            const input = document.getElementById(inputId);
            const display = document.getElementById(displayId);
            display.textContent = input.files.length > 0 ? '📎 ' + input.files[0].name : '';
        }
        
        function uploadCert(event) {
            event.preventDefault();
            const formData = new FormData(document.getElementById('certForm'));
            
            fetch('/upload-cert', {
                method: 'POST',
                body: formData
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showToast('success', 'Certificate Uploaded', 'The bridge will be restarted with SSL enabled.');
                    closeCertModal();
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showToast('error', 'Upload Failed', data.error);
                }
            })
            .catch(err => {
                showToast('error', 'Upload Failed', err.message);
            });
            
            return false;
        }
        
        function deleteCert() {
            fetch('/delete-cert', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({port: currentPort})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showToast('success', 'Certificate Removed', 'The bridge has been restarted with standard WS.');
                    closeCertModal();
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showToast('error', 'Removal Failed', data.error);
                }
            });
        }
        
        // Close modals when clicking outside
        document.getElementById('certModal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeCertModal();
            }
        });
        
        document.getElementById('confirmModal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeConfirmModal();
            }
        });

        document.getElementById('logModal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeLogModal();
            }
        });
        
        function addBridge(e) {
            e.preventDefault();
            const formData = new FormData(document.getElementById('addForm'));
            
            fetch('/add', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('success', 'Bridge Created', data.message || 'Bridge established successfully!');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showToast('error', 'Creation Failed', data.error);
                }
            })
            .catch(err => {
                showToast('error', 'Creation Failed', err.message);
            });
            
            return false;
        }
        
        function testConnection(isExisting) {
            const port = document.getElementById('port').value;
            const target = document.getElementById('target').value;
            
            if (!port || !target) {
                showToast('error', 'Missing Information', 'Please fill in both port and target fields');
                return;
            }
            
            fetch('/test', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({port, target, existing: isExisting})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showToast('success', 'Connection Test Passed', data.message);
                } else {
                    showToast('error', 'Connection Test Failed', data.error);
                }
            });
        }
        
        function testBridge(port, target) {
            fetch('/test', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({port, target, existing: true})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showToast('success', 'Bridge Test Passed', data.message);
                } else {
                    showToast('error', 'Bridge Test Failed', data.error);
                }
            });
        }
        
        // Update connection counts
        function updateCounts() {
            fetch('/connections')
                .then(r => r.json())
                .then(counts => {
                    for (const [port, count] of Object.entries(counts)) {
                        const elem = document.getElementById('conn-' + port);
                        if (elem) elem.textContent = count;
                    }
                });
        }
        
        setInterval(updateCounts, 2000);
        updateCounts();

        // ---- NEW: Live Log Logic ----
        let logSSE = null;
        let logPaused = false;
        let logFilter = 'all';
        let logLineCount = 0;
        let logCurrentPort = null;
        const LOG_MAX_DOM = 300;

        function openLogModal(port, name) {
            logCurrentPort = port;
            logPaused = false;
            logFilter = 'all';
            logLineCount = 0;
            document.getElementById('logModal').classList.add('active');
            document.getElementById('logModalMeta').textContent = `Bridge: ${name}  ·  Port :${port}`;
            document.getElementById('logBody').innerHTML = '<div class="log-empty" id="logEmpty">No events yet — waiting for activity...</div>';
            document.getElementById('logPauseBtn').textContent = '⏸ Pause';
            document.getElementById('logStatusDot').className = 'log-status-dot';
            document.getElementById('logStatusText').textContent = 'Connecting...';
            document.getElementById('logLineCount').textContent = '0 events';
            // Reset filter buttons
            document.querySelectorAll('.log-filter-btn').forEach(b => b.classList.remove('active'));
            document.querySelector('.log-filter-btn[data-type="all"]').classList.add('active');

            // Load history first
            fetch(`/log-history/${port}`)
                .then(r => r.json())
                .then(entries => {
                    entries.forEach(e => appendLogLine(e));
                    startLogSSE(port);
                })
                .catch(() => startLogSSE(port));
        }

        function closeLogModal() {
            document.getElementById('logModal').classList.remove('active');
            if (logSSE) { logSSE.close(); logSSE = null; }
            logCurrentPort = null;
        }

        function startLogSSE(port) {
            if (logSSE) { logSSE.close(); }
            logSSE = new EventSource(`/log-stream/${port}`);

            logSSE.onopen = () => {
                document.getElementById('logStatusDot').className = 'log-status-dot';
                document.getElementById('logStatusText').textContent = 'Live';
            };
            logSSE.onmessage = (event) => {
                if (logPaused) return;
                try {
                    const entry = JSON.parse(event.data);
                    appendLogLine(entry);
                } catch(e) {}
            };
            logSSE.onerror = () => {
                document.getElementById('logStatusDot').className = 'log-status-dot closed';
                document.getElementById('logStatusText').textContent = 'Disconnected';
            };
        }

        function appendLogLine(entry) {
            const body = document.getElementById('logBody');
            const empty = document.getElementById('logEmpty');
            if (empty) empty.remove();

            logLineCount++;
            document.getElementById('logLineCount').textContent = `${logLineCount} events`;

            const badgeClass = `log-badge-${entry.type}`;
            const hidden = (logFilter !== 'all' && logFilter !== entry.type) ? 'hidden' : '';

            const line = document.createElement('div');
            line.className = `log-line ${hidden}`;
            line.dataset.type = entry.type;

            const maxLen = 200;
            let msg = entry.msg;
            if (msg.length > maxLen) msg = msg.substring(0, maxLen) + '…';

            line.innerHTML = `
                <span class="log-ts">${entry.ts}</span>
                <span class="log-badge ${badgeClass}">${entry.type.replace('_',' ')}</span>
                <span class="log-text">${escapeHtml(msg)}</span>
            `;
            body.appendChild(line);

            // Trim old lines
            const lines = body.querySelectorAll('.log-line');
            if (lines.length > LOG_MAX_DOM) {
                lines[0].remove();
            }

            // Auto-scroll
            body.scrollTop = body.scrollHeight;
        }

        function escapeHtml(str) {
            return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        }

        function toggleLogPause() {
            logPaused = !logPaused;
            const btn = document.getElementById('logPauseBtn');
            const dot = document.getElementById('logStatusDot');
            const txt = document.getElementById('logStatusText');
            if (logPaused) {
                btn.textContent = '▶ Resume';
                dot.className = 'log-status-dot paused';
                txt.textContent = 'Paused';
            } else {
                btn.textContent = '⏸ Pause';
                dot.className = 'log-status-dot';
                txt.textContent = 'Live';
            }
        }

        function clearLogDisplay() {
            logLineCount = 0;
            document.getElementById('logLineCount').textContent = '0 events';
            document.getElementById('logBody').innerHTML = '<div class="log-empty" id="logEmpty">Log cleared — waiting for new events...</div>';
        }

        function setLogFilter(type) {
            logFilter = type;
            document.querySelectorAll('.log-filter-btn').forEach(b => {
                b.classList.toggle('active', b.dataset.type === type);
            });
            document.querySelectorAll('.log-line').forEach(line => {
                if (type === 'all' || line.dataset.type === type) {
                    line.classList.remove('hidden');
                } else {
                    line.classList.add('hidden');
                }
            });
        }
        // ---- END Log Logic ----
    </script>
</body>
</html>
"""

def has_ssl(port):
    """Check if a port has SSL certificates configured"""
    cert_path = os.path.join(CERT_DIR, f"{port}.crt")
    key_path = os.path.join(CERT_DIR, f"{port}.key")
    return os.path.exists(cert_path) and os.path.exists(key_path)

# --- PROTOCOL HANDLERS ---


def _preview(data, max_bytes=64):
    chunk = data[:max_bytes]
    hex_part = chunk.hex()
    try:
        ascii_part = chunk.decode("utf-8", errors="replace")
        ascii_part = "".join(c if c.isprintable() else "." for c in ascii_part)
        return f"hex:{hex_part}  ascii:{ascii_part}"
    except Exception:
        return f"hex:{hex_part}"

async def bridge_handler(websocket, target_host, target_port, mode, port):
    writer = None
    if port not in connection_counts:
        connection_counts[port] = 0
    connection_counts[port] += 1

    client_addr = websocket.remote_address

    try:
        first_packet = await websocket.recv()

        # Check if first packet is a dynamic target address (e.g. "192.168.2.2:7575")
        dynamic_target = None
        if isinstance(first_packet, bytes):
            try:
                decoded = first_packet.decode('utf-8').strip()
                parts = decoded.split(':')
                if len(parts) == 2 and parts[1].isdigit():
                    octets = parts[0].split('.')
                    if len(octets) == 4 and all(o.isdigit() for o in octets):
                        dynamic_target = (parts[0], int(parts[1]))
            except Exception:
                pass

        if dynamic_target:
            # Dynamic routing mode - connect to requested target
            dhost, dport = dynamic_target
            push_log(port, 'connect', f'New connection from {client_addr[0]}:{client_addr[1]} → {dhost}:{dport} (dynamic)')
            reader, writer = await asyncio.open_connection(dhost, dport)
        else:
            # Static target mode
            push_log(port, 'connect', f'New connection from {client_addr[0]}:{client_addr[1]} → {target_host}:{target_port}')
            reader, writer = await asyncio.open_connection(target_host, target_port)

            # Maple detection only applies to static mode
            is_maple = False
            if isinstance(first_packet, str):
                is_maple = True
            elif isinstance(first_packet, bytes):
                try:
                    decoded = first_packet.decode('utf-8', errors='strict')
                    if len(decoded) < 200 and decoded.isprintable():
                        is_maple = True
                except (UnicodeDecodeError, AttributeError):
                    is_maple = False

            if not is_maple:
                data = first_packet if isinstance(first_packet, bytes) else first_packet.encode()
                push_log(port, 'ws_in', f'{len(data)}B  {_preview(data)}')
                writer.write(data)
                await writer.drain()

        async def ws_to_tcp():
            async for message in websocket:
                data = message if isinstance(message, bytes) else message.encode()
                push_log(port, 'ws_in', f'{len(data)}B  {_preview(data)}')
                writer.write(data)
                await writer.drain()

        async def tcp_to_ws():
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                push_log(port, 'ws_out', f'{len(data)}B  {_preview(data)}')
                await websocket.send(data)

        await asyncio.gather(ws_to_tcp(), tcp_to_ws())

    except Exception as ex:
        push_log(port, 'error', str(ex))
    finally:
        if port in connection_counts:
            connection_counts[port] = max(0, connection_counts[port] - 1)
        push_log(port, 'disconnect', f'Connection from {client_addr[0]}:{client_addr[1]} closed')
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
    """Starts WebSocket server with optional SSL/TLS support"""
    h, tp = target.split(':')
    
    # Check for SSL certificates
    cert_path = os.path.join(CERT_DIR, f"{port}.crt")
    key_path = os.path.join(CERT_DIR, f"{port}.key")
    ssl_context = None
    
    if os.path.exists(cert_path) and os.path.exists(key_path):
        # Create SSL context
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(cert_path, key_path)
    
    server = await websockets.serve(
        lambda ws: bridge_handler(ws, h, int(tp), mode, str(port)), 
        "0.0.0.0", port, 
        select_subprotocol=universal_subprotocol_select,
        ping_interval=None,
        ssl=ssl_context
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

async def restart_server(port, target, mode):
    """Restart a specific server (used after cert changes)"""
    # Stop existing server
    if port in active_proxies and 'server' in active_proxies[port]:
        server = active_proxies[port]['server']
        server.close()
        await server.wait_closed()
    
    # Start new server
    await start_srv(int(port), target, mode)

@app.route('/')
def index(): 
    response = make_response(render_template_string(HTML_TEMPLATE, entries=get_entries(), has_ssl=has_ssl))
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

@app.route('/upload-cert', methods=['POST'])
def upload_cert():
    """Upload SSL certificate and key for a specific port"""
    try:
        port = request.form.get('port')
        cert_file = request.files.get('cert')
        key_file = request.files.get('key')
        
        if not port or not cert_file or not key_file:
            return jsonify({'success': False, 'error': 'Missing required files or port'})
        
        # Save certificate and key
        cert_path = os.path.join(CERT_DIR, f"{port}.crt")
        key_path = os.path.join(CERT_DIR, f"{port}.key")
        
        cert_file.save(cert_path)
        key_file.save(key_path)
        
        # Find the bridge configuration
        entries = get_entries()
        for _, p, target, mode in entries:
            if p == port:
                # Restart the server with SSL
                async def do_restart():
                    await restart_server(port, target, mode)
                asyncio.run_coroutine_threadsafe(do_restart(), proxy_loop)
                break
        
        return jsonify({'success': True, 'message': 'Certificate uploaded successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete-cert', methods=['POST'])
def delete_cert():
    """Delete SSL certificate for a specific port"""
    try:
        data = request.get_json()
        port = data.get('port')
        
        if not port:
            return jsonify({'success': False, 'error': 'Port not specified'})
        
        cert_path = os.path.join(CERT_DIR, f"{port}.crt")
        key_path = os.path.join(CERT_DIR, f"{port}.key")
        
        # Remove certificate files
        if os.path.exists(cert_path):
            os.remove(cert_path)
        if os.path.exists(key_path):
            os.remove(key_path)
        
        # Find the bridge configuration
        entries = get_entries()
        for _, p, target, mode in entries:
            if p == port:
                # Restart the server without SSL
                async def do_restart():
                    await restart_server(port, target, mode)
                asyncio.run_coroutine_threadsafe(do_restart(), proxy_loop)
                break
        
        return jsonify({'success': True, 'message': 'Certificate removed successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/cert-status/<port>', methods=['GET'])
def cert_status(port):
    """Check if a port has SSL certificates configured"""
    return jsonify({'has_cert': has_ssl(port)})

# --- NEW: Log endpoints ---

@app.route('/log-history/<port>', methods=['GET'])
def log_history(port):
    """Return buffered log history for a port"""
    buf = get_log_buffer(port)
    return jsonify(list(buf))

@app.route('/log-stream/<port>', methods=['GET'])
def log_stream(port):
    """SSE stream of live log events for a specific port"""
    import queue

    q = queue.Queue(maxsize=500)
    key = str(port)
    if key not in log_subscribers:
        log_subscribers[key] = []
    log_subscribers[key].append(q)

    def generate():
        try:
            # Send a ping comment to confirm connection
            yield ': connected\n\n'
            while True:
                try:
                    entry = q.get(timeout=15)
                    yield f'data: {json.dumps(entry)}\n\n'
                except queue.Empty:
                    # Send keepalive comment
                    yield ': keepalive\n\n'
        except GeneratorExit:
            pass
        finally:
            try:
                log_subscribers[key].remove(q)
            except (ValueError, KeyError):
                pass

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

if __name__ == '__main__':
    sync()
    app.run(host='0.0.0.0', port=5050)
