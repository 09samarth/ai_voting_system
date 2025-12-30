import sqlite3
from pathlib import Path
import random

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
