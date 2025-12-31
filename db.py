import sqlite3
from pathlib import Path
import random
from typing import List, Tuple, Optional
from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).parent / "votes.db"

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS voters (
        id TEXT PRIMARY KEY,
        name TEXT,
        constituency TEXT,
        language TEXT,
        accessibility_flag TEXT,
        enabled INTEGER DEFAULT 1
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
    """,

    """
    CREATE TABLE IF NOT EXISTS admins (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS elections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        is_active INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        closed_at DATETIME
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS election_candidates (
        election_id INTEGER NOT NULL,
        candidate_id INTEGER NOT NULL,
        PRIMARY KEY (election_id, candidate_id),
        FOREIGN KEY (election_id) REFERENCES elections(id),
        FOREIGN KEY (candidate_id) REFERENCES candidates(id)
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_username TEXT,
        action TEXT,
        details TEXT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for stmt in SCHEMA:
        cur.execute(stmt)

    # Ensure default admin user for demo purposes
    # Username: admin, Password: admin123 (hashed)
    cur.execute("SELECT COUNT(*) FROM admins WHERE username = 'admin'")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            ("admin", generate_password_hash("admin123")),
        )

    # Demo data (legacy non-numeric example)
    cur.execute("INSERT OR IGNORE INTO voters (id, name) VALUES ('FIRST1','Demo Voter')")

    # Core demo candidates
    cur.execute("INSERT OR IGNORE INTO candidates (id, name) VALUES (1,'BJP')")
    cur.execute("INSERT OR IGNORE INTO candidates (id, name) VALUES (2,'CONGRESS')")
    cur.execute("INSERT OR IGNORE INTO candidates (id, name) VALUES (3,'JDS')")

    # Additional parties for academic demo
    cur.execute("INSERT OR IGNORE INTO candidates (id, name) VALUES (4,'AAP')")
    cur.execute("INSERT OR IGNORE INTO candidates (id, name) VALUES (5,'BSP')")
    cur.execute("INSERT OR IGNORE INTO candidates (id, name) VALUES (6,'CPI')")
    cur.execute("INSERT OR IGNORE INTO candidates (id, name) VALUES (7,'TMC')")
    cur.execute("INSERT OR IGNORE INTO candidates (id, name) VALUES (8,'JD(U)')")
    cur.execute("INSERT OR IGNORE INTO candidates (id, name) VALUES (9,'SP')")

    # Ensure any existing demo candidates are renamed to the desired labels
    cur.execute("UPDATE candidates SET name='BJP' WHERE id=1")
    cur.execute("UPDATE candidates SET name='CONGRESS' WHERE id=2")
    cur.execute("UPDATE candidates SET name='JDS' WHERE id=3")
    cur.execute("UPDATE candidates SET name='AAP' WHERE id=4")
    cur.execute("UPDATE candidates SET name='BSP' WHERE id=5")
    cur.execute("UPDATE candidates SET name='CPI' WHERE id=6")
    cur.execute("UPDATE candidates SET name='TMC' WHERE id=7")
    cur.execute("UPDATE candidates SET name='JD(U)' WHERE id=8")
    cur.execute("UPDATE candidates SET name='SP' WHERE id=9")

    # ------------------------------------------------------------------
    # Seed 200 random, unique numeric state-coded voter IDs for the demo
    # Format: StateCode-VoterNumber (e.g., 1-12, 2-45), matching the
    # speech-recognition scheme. These are purely synthetic identifiers.
    # ------------------------------------------------------------------
    # Count how many numeric-style voters we already have (ids containing '-')
    cur.execute("SELECT COUNT(*) FROM voters WHERE id LIKE '%-%'")
    existing_numeric = cur.fetchone()[0]

    target_total = 200
    if existing_numeric < target_total:
        need = target_total - existing_numeric

        # Deterministic seed so the demo is reproducible across runs
        random.seed(42)
        generated = set()

        while len(generated) < need:
            # Simple synthetic scheme: state codes 1-9, voter numbers 1-999
            state_code = random.randint(1, 9)
            voter_number = random.randint(1, 999)
            voter_id = f"{state_code}-{voter_number}"
            generated.add(voter_id)

        # Insert synthetic voters; names are generic demo labels
        # Offset the numbering by any existing numeric voters for uniqueness
        start_index = existing_numeric + 1
        for offset, voter_id in enumerate(sorted(generated), start=start_index):
            name = f"Demo Voter {offset}"
            cur.execute(
                "INSERT OR IGNORE INTO voters (id, name) VALUES (?, ?)",
                (voter_id, name),
            )

    conn.commit()
    conn.close()

# ----------------------
# Public voting helpers
# ----------------------

def get_candidates() -> List[Tuple[int, str]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM candidates ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows

def record_vote(voter_token: str, candidate_id: int) -> None:
    """Record a vote for the given voter token.

    Note: For academic demo purposes, this function does not enforce
    one-vote-per-voter cryptographically. The admin panel can still
    inspect aggregated results and vote logs.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO votes (voter_token, candidate_id) VALUES (?, ?)",
        (voter_token, candidate_id),
    )
    conn.commit()
    conn.close()

def get_votes() -> List[Tuple[int, int]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT candidate_id, COUNT(*) FROM votes GROUP BY candidate_id")
    rows = cur.fetchall()
    conn.close()
    return rows

# ----------------------
# Admin helpers
# ----------------------

def get_admin(username: str) -> Optional[Tuple[str, str, str]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT username, password_hash, created_at FROM admins WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row

def record_admin_action(admin_username: str, action: str, details: str = "") -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO admin_logs (admin_username, action, details) VALUES (?, ?, ?)",
        (admin_username, action, details),
    )
    conn.commit()
    conn.close()

def list_voters() -> List[Tuple]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, constituency, language, accessibility_flag, enabled "
        "FROM voters ORDER BY id"
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def create_voter(voter_id: str, name: str, constituency: str, language: str, accessibility_flag: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO voters (id, name, constituency, language, accessibility_flag, enabled) "
        "VALUES (?, ?, ?, ?, ?, 1)",
        (voter_id, name, constituency, language, accessibility_flag),
    )
    conn.commit()
    conn.close()

def set_voter_enabled(voter_id: str, enabled: bool) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE voters SET enabled = ? WHERE id = ?",
        (1 if enabled else 0, voter_id),
    )
    conn.commit()
    conn.close()

def list_elections() -> List[Tuple]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, is_active, created_at, closed_at FROM elections ORDER BY created_at DESC"
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def create_election(name: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO elections (name, is_active) VALUES (?, 0)", (name,))
    conn.commit()
    conn.close()

def set_election_active(election_id: int, active: bool) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if active:
        cur.execute(
            "UPDATE elections SET is_active = 1, closed_at = NULL WHERE id = ?",
            (election_id,),
        )
    else:
        cur.execute(
            "UPDATE elections SET is_active = 0, closed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (election_id,),
        )
    conn.commit()
    conn.close()

def assign_candidate_to_election(election_id: int, candidate_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO election_candidates (election_id, candidate_id) VALUES (?, ?)",
        (election_id, candidate_id),
    )
    conn.commit()
    conn.close()

def remove_candidate_from_election(election_id: int, candidate_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM election_candidates WHERE election_id = ? AND candidate_id = ?",
        (election_id, candidate_id),
    )
    conn.commit()
    conn.close()

def get_vote_logs(limit: int = 100) -> List[Tuple]:
    """Return recent vote rows as (id, voter_token, candidate_id, ts)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, voter_token, candidate_id, ts FROM votes ORDER BY ts DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_admin_logs(limit: int = 100) -> List[Tuple]:
    """Return recent admin log rows as (id, admin_username, action, details, ts)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, admin_username, action, details, ts FROM admin_logs ORDER BY ts DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows
