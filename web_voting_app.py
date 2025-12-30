#!/usr/bin/env python3
"""
Professional Web-Based Voice Voting System
Uses subprocess for voice processing to avoid web framework conflicts
"""
from flask import Flask, render_template, jsonify, request
import subprocess
import json
import os
import threading
import time
from db import init_db, get_candidates, record_vote, get_votes
from console_utils import safe_print

app = Flask(__name__)

# Directory for subprocess log files (keeps project root clean)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Global state for web interface
voting_sessions = {}

@app.route('/')
def index():
    """Main voting interface"""
    return render_template('web_voting.html')

@app.route('/api/candidates')
def get_candidates_api():
    """Get available candidates"""
    try:
        candidates = get_candidates()
        return jsonify({
            'success': True, 
            'candidates': [{'id': cid, 'name': name} for cid, name in candidates]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/start-voice-voting', methods=['POST'])
def start_voice_voting():
    """Start voice voting process using subprocess"""
    try:
        session_id = str(int(time.time()))
        
        # Create a subprocess to handle voice voting
        safe_print(f"Starting voice subprocess for session {session_id}")
        
        # Create log file for subprocess output inside dedicated logs directory
        log_file = os.path.join(LOG_DIR, f'subprocess_{session_id}.log')
        
        process = subprocess.Popen([
            'python', 'voice_subprocess.py', session_id
        ], 
        stdout=open(log_file, 'w'), 
        stderr=subprocess.STDOUT, 
        text=True)
        safe_print(f"Subprocess started with PID: {process.pid}")
        
        voting_sessions[session_id] = {
            'process': process,
            'status': 'listening',
            'step': 1,
            'message': 'Starting voice voting...',
            'result': None
        }
        
        return jsonify({
            'success': True, 
            'session_id': session_id,
            'message': 'Voice voting started'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/voting-status/<session_id>')
def voting_status(session_id):
    """Get status of voice voting session"""
    if session_id not in voting_sessions:
        return jsonify({'success': False, 'error': 'Session not found'})
    
    session = voting_sessions[session_id]
    process = session['process']
    
    # Try to read status from file
    status_file = f'status_{session_id}.json'
    try:
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                file_data = json.load(f)
                session.update(file_data)
                safe_print(f"Updated session {session_id} with status: {file_data.get('status', 'unknown')}")
        else:
            safe_print(f"Status file {status_file} does not exist yet")
    except Exception as e:
        safe_print(f"Error reading status file: {e}")
    
    # Check if process is still running
    if process.poll() is None:
        # Process still running
        return jsonify({
            'success': True,
            'status': session.get('status', 'listening'),
            'step': session.get('step', 1), 
            'message': session.get('message', 'Processing...')
        })
    else:
        # Process finished
        safe_print(f"Process for session {session_id} has completed with return code: {process.returncode}")
        if process.returncode != 0 and session.get('status') != 'success':
            session['status'] = 'error'
            session['message'] = 'Voice processing failed'
        try:
            if os.path.exists(status_file):
                os.remove(status_file)
        except Exception:
            pass
            
        return jsonify({
            'success': True,
            'status': session.get('status', 'completed'),
            'step': session.get('step', 3),
            'message': session.get('message', 'Process completed'),
            'result': session.get('result')
        })

@app.route('/api/results')
def get_results():
    """Get voting results"""
    try:
        results = get_votes()
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/reset-session/<session_id>')
def reset_session(session_id):
    """Reset a voting session"""
    if session_id in voting_sessions:
        process = voting_sessions[session_id]['process']
        if process.poll() is None:
            process.terminate()
        del voting_sessions[session_id]
    
    # Clean up status file
    status_file = f'status_{session_id}.json'
    try:
        if os.path.exists(status_file):
            os.remove(status_file)
    except Exception:
        pass
    
    return jsonify({'success': True})

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    safe_print("Starting Professional Web-Based Voice Voting System")
    safe_print("Open your browser to: http://localhost:5000")
    safe_print("Voice processing runs in separate subprocess (no conflicts!)")
    safe_print("Perfect for major projects!")
    safe_print("-" * 60)
    
    app.run(debug=False, host='127.0.0.1', port=5000)