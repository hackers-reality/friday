"""Friday UI Dashboard - Flask-based web interface."""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import os
import threading
import queue
import json
import time

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'friday-dashboard-secret')
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
ui_queue = queue.Queue()
friday_state = {
    'status': 'idle',
    'current_task': None,
    'thoughts': [],
    'tools_called': [],
    'screen_capture': None,
    'conversation': [],
    'trust_tier': 'new',
    'background_tasks': []
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state')
def get_state():
    return jsonify(friday_state)

@app.route('/api/send', methods=['POST'])
def send_message():
    data = request.json
    message = data.get('message', '')
    if message:
        ui_queue.put({'type': 'user_message', 'content': message})
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'message': 'No message'})

@socketio.on('connect')
def handle_connect():
    emit('state_update', friday_state)
    print('UI client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('UI client disconnected')

@socketio.on('send_message')
def handle_message(data):
    message = data.get('message', '')
    if message:
        ui_queue.put({'type': 'user_message', 'content': message})
        emit('message_received', {'status': 'ok'})

def update_ui(state_update):
    """Update UI state and broadcast to clients."""
    global friday_state
    friday_state.update(state_update)
    socketio.emit('state_update', friday_state, namespace='/')

def add_thought(thought):
    """Add a thought to the UI."""
    friday_state['thoughts'].append({
        'timestamp': time.time(),
        'content': thought
    })
    # Keep only last 50 thoughts
    friday_state['thoughts'] = friday_state['thoughts'][-50:]
    socketio.emit('thought_added', {'thought': thought}, namespace='/')

def add_tool_call(tool_name, args, result=None):
    """Add a tool call to the UI."""
    call = {
        'timestamp': time.time(),
        'tool': tool_name,
        'args': args,
        'result': result
    }
    friday_state['tools_called'].append(call)
    friday_state['tools_called'] = friday_state['tools_called'][-50:]
    socketio.emit('tool_called', call, namespace='/')

def update_status(status, task=None):
    """Update Friday's status."""
    friday_state['status'] = status
    if task:
        friday_state['current_task'] = task
    socketio.emit('status_update', {
        'status': status,
        'current_task': task
    }, namespace='/')

def add_conversation_message(role, content):
    """Add a message to the conversation history."""
    msg = {
        'timestamp': time.time(),
        'role': role,
        'content': content
    }
    friday_state['conversation'].append(msg)
    friday_state['conversation'] = friday_state['conversation'][-100:]
    socketio.emit('conversation_update', msg, namespace='/')

def update_screen_capture(image_data):
    """Update the screen capture display."""
    friday_state['screen_capture'] = image_data
    socketio.emit('screen_update', {'image': image_data}, namespace='/')

def run_ui(host='127.0.0.1', port=5000):
    """Run the UI server."""
    print(f"Friday UI running at http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=False)

if __name__ == '__main__':
    run_ui()
