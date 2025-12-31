#!/usr/bin/env python3
"""
Professional Web-Based Voice Voting System
Uses subprocess for voice processing to avoid web framework conflicts
"""
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
import subprocess
import json
import os
import threading
import time
from functools import wraps
from db import (
    init_db,
    get_candidates,
    record_vote,
    get_votes,
    get_admin,
    record_admin_action,
    list_voters,
    create_voter,
    set_voter_enabled,
    list_elections,
    create_election,
    set_election_active,
    assign_candidate_to_election,
    remove_candidate_from_election,
    get_vote_logs,
    get_admin_logs,
)
from console_utils import safe_print

app = Flask(__name__)
app.secret_key = "change-this-secret-key-for-production"

# Directory for subprocess log files (keeps project root clean)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Global state for web interface
voting_sessions = {}


def admin_login_required(f):
    """Decorator to restrict routes to authenticated admins."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_username"):
            next_url = request.path
            return redirect(url_for("admin_login", next=next_url))
        return f(*args, **kwargs)

    return wrapper


@app.route('/')
def home():
    """Landing page with separate links for each major feature"""
    return render_template('home.html')


@app.route('/voice-voting')
def voice_voting_page():
    """Dedicated page for the voice voting flow"""
    return render_template('web_voting.html')


@app.route('/results')
def results_page():
    """Dedicated page for viewing aggregated voting results"""
    return render_template('results.html')


@app.route('/overview')
def overview_page():
    """Project overview and documentation page"""
    return render_template('overview.html')


# ----------------
# Admin views
# ----------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page."""
    error = None
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        admin_row = get_admin(username)
        if not admin_row:
            error = 'Invalid username or password.'
        else:
            from werkzeug.security import check_password_hash

            _, password_hash, _ = admin_row
            if not check_password_hash(password_hash, password):
                error = 'Invalid username or password.'
            else:
                session['admin_username'] = username
                record_admin_action(username, 'login', 'Admin logged in')
                next_url = request.args.get('next') or url_for('admin_dashboard')
                return redirect(next_url)

    return render_template('admin_login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    username = session.get('admin_username')
    if username:
        record_admin_action(username, 'logout', 'Admin logged out')
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_login_required
def admin_dashboard():
    return render_template('admin_dashboard.html', admin_username=session.get('admin_username'))


@app.route('/admin/voters', methods=['GET', 'POST'])
@admin_login_required
def admin_voters():
    username = session.get('admin_username')
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            voter_id = (request.form.get('voter_id') or '').strip()
            name = (request.form.get('name') or '').strip()
            constituency = (request.form.get('constituency') or '').strip()
            language = (request.form.get('language') or '').strip()
            accessibility_flag = request.form.get('accessibility_flag') or 'NORMAL'
            if voter_id and name:
                create_voter(voter_id, name, constituency, language, accessibility_flag)
                record_admin_action(username, 'create_voter', f'Created voter {voter_id}')
        elif action == 'toggle_enabled':
            voter_id = request.form.get('voter_id')
            enabled = request.form.get('enabled') == '1'
            if voter_id:
                set_voter_enabled(voter_id, enabled)
                state = 'enabled' if enabled else 'disabled'
                record_admin_action(username, 'set_voter_enabled', f'{state} voter {voter_id}')
        return redirect(url_for('admin_voters'))

    voters = list_voters()
    return render_template('admin_voters.html', admin_username=username, voters=voters)


@app.route('/admin/elections', methods=['GET', 'POST'])
@admin_login_required
def admin_elections():
    username = session.get('admin_username')
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_election':
            name = (request.form.get('name') or '').strip()
            if name:
                create_election(name)
                record_admin_action(username, 'create_election', f'Created election {name}')
        elif action == 'set_active':
            try:
                election_id = int(request.form.get('election_id') or '0')
            except ValueError:
                election_id = 0
            active = request.form.get('active') == '1'
            if election_id:
                set_election_active(election_id, active)
                record_admin_action(username, 'set_election_active', f'set active={active} for election {election_id}')
        elif action == 'assign_candidate':
            try:
                election_id = int(request.form.get('election_id') or '0')
                candidate_id = int(request.form.get('candidate_id') or '0')
            except ValueError:
                election_id = 0
                candidate_id = 0
            if election_id and candidate_id:
                assign_candidate_to_election(election_id, candidate_id)
                record_admin_action(username, 'assign_candidate', f'election={election_id}, candidate={candidate_id}')
        elif action == 'remove_candidate':
            try:
                election_id = int(request.form.get('election_id') or '0')
                candidate_id = int(request.form.get('candidate_id') or '0')
            except ValueError:
                election_id = 0
                candidate_id = 0
            if election_id and candidate_id:
                remove_candidate_from_election(election_id, candidate_id)
                record_admin_action(username, 'remove_candidate', f'election={election_id}, candidate={candidate_id}')
        return redirect(url_for('admin_elections'))

    elections = list_elections()
    candidates = get_candidates()
    return render_template('admin_elections.html', admin_username=username, elections=elections, candidates=candidates)


@app.route('/admin/results')
@admin_login_required
def admin_results():
    username = session.get('admin_username')
    vote_totals = get_votes()
    candidates = {cid: name for cid, name in get_candidates()}
    overall_total = sum(count for _, count in vote_totals)
    return render_template(
        'admin_results.html',
        admin_username=username,
        vote_totals=vote_totals,
        candidates=candidates,
        overall_total=overall_total,
    )


@app.route('/admin/logs')
@admin_login_required
def admin_logs_view():
    username = session.get('admin_username')
    vote_logs = get_vote_logs(limit=100)
    admin_logs_rows = get_admin_logs(limit=100)
    return render_template(
        'admin_logs.html',
        admin_username=username,
        vote_logs=vote_logs,
        admin_logs=admin_logs_rows,
    )


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