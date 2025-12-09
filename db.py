import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "votes.db"

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS voters (
        id TEXT PRIMARY KEY,
        name TEXT
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY,
        name TEXT
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_token TEXT,
        candidate_id INTEGER,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for stmt in SCHEMA:
        cur.execute(stmt)

    # Demo data
    cur.execute("INSERT OR IGNORE INTO voters (id, name) VALUES ('FIRST1','Demo Voter')")
    cur.execute("INSERT OR IGNORE INTO candidates (id, name) VALUES (1,'Alice')")
    cur.execute("INSERT OR IGNORE INTO candidates (id, name) VALUES (2,'Bob')")
    cur.execute("INSERT OR IGNORE INTO candidates (id, name) VALUES (3,'Charlie')")

    conn.commit()
    conn.close()

def get_candidates():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM candidates ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows

def record_vote(voter_token, candidate_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO votes (voter_token, candidate_id) VALUES (?,?)", (voter_token, candidate_id))
    conn.commit()
    conn.close()

def get_votes():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT candidate_id, COUNT(*) FROM votes GROUP BY candidate_id")
    rows = cur.fetchall()
    conn.close()
    return rows
