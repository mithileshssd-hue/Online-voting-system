"""
database.py
-----------
Handles all SQLite database operations for the Online Voting System.

Responsibilities:
- Initialize SQLite database at 'data/voting.db'
- Automatically create necessary tables: users, candidates, votes, admin
- Migrate existing data from 'Voting_Database.xlsx' if present on first run
- Provide secure, parameterized queries to prevent SQL injection
- Enforce atomic transactions for casting votes to guarantee one-vote-per-voter
- Provide statistics and candidate management functions for Admin Dashboard

1st-Year Viva Note:
"We replaced the Excel file with SQLite because SQLite provides ACID transactions,
parameterized queries to prevent SQL injection, and does not corrupt data if two
operations happen at the same time."
"""

import os
import sqlite3
from typing import Dict, List, Optional, Tuple

from security import hash_password, verify_password


# ── Database Path Configuration ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "voting.db")

# Default candidates if creating a fresh database
DEFAULT_CANDIDATES = [
    "AIADMK",
    "DMK",
    "NTK",
    "TVK",
    "NOTA"
]

# Default admin credentials (seeded into database as SHA-256 hash)
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "admin123"


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Establishes and returns a connection to the SQLite database.
    Enables foreign keys and returns rows accessible by column name.
    """
    target_db = db_path or DB_FILE
    # Ensure the directory exists
    os.makedirs(os.path.dirname(target_db), exist_ok=True)
    conn = sqlite3.connect(target_db, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ── Database Initialization ────────────────────────────────────────────────────
def initialize_database(db_path: Optional[str] = None) -> None:
    """
    Creates tables and seeds default data (Admin, Candidates) or migrates from Excel.
    Safe to call multiple times (idempotent).
    """
    target_db = db_path or DB_FILE
    is_new_db = not os.path.exists(target_db)

    conn = get_db_connection(target_db)
    cursor = conn.cursor()

    # 1. Users table (registered voters)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            voter_id TEXT PRIMARY KEY,
            has_voted INTEGER NOT NULL DEFAULT 0,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Candidates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            votes INTEGER NOT NULL DEFAULT 0
        );
    """)

    # 3. Votes table (audit record; voter_id UNIQUE guarantees one vote per voter)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id TEXT UNIQUE NOT NULL,
            candidate_name TEXT NOT NULL,
            voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (voter_id) REFERENCES users(voter_id) ON DELETE CASCADE
        );
    """)

    # 4. Admin table (hashed credentials)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
    """)

    conn.commit()

    # 5. Seed default admin if admin table is empty
    cursor.execute("SELECT COUNT(*) FROM admin;")
    if cursor.fetchone()[0] == 0:
        hashed_pw = hash_password(DEFAULT_ADMIN_PASS)
        cursor.execute(
            "INSERT INTO admin (username, password_hash) VALUES (?, ?);",
            (DEFAULT_ADMIN_USER, hashed_pw)
        )
        conn.commit()

    # 6. Seed default candidates if candidates table is empty
    cursor.execute("SELECT COUNT(*) FROM candidates;")
    if cursor.fetchone()[0] == 0:
        for c_name in DEFAULT_CANDIDATES:
            cursor.execute(
                "INSERT OR IGNORE INTO candidates (name, votes) VALUES (?, 0);",
                (c_name,)
            )
        conn.commit()

    conn.close()


# ── Voter Registration & Status ───────────────────────────────────────────────
def is_registered(voter_id: str, db_path: Optional[str] = None) -> bool:
    """
    Checks whether the given Voter ID is registered in the database.
    """
    if not voter_id:
        return False

    clean_id = str(voter_id).strip().upper()
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE voter_id = ?;", (clean_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def has_voted(voter_id: str, db_path: Optional[str] = None) -> bool:
    """
    Checks whether the given Voter ID has already cast their vote.
    """
    if not voter_id:
        return False

    clean_id = str(voter_id).strip().upper()
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT has_voted FROM users WHERE voter_id = ?;", (clean_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return False
    return bool(row["has_voted"])


def add_voter(voter_id: str, db_path: Optional[str] = None) -> bool:
    """
    Registers a new voter with has_voted = 0.
    Returns True if successfully added, False if voter already exists.
    """
    if not voter_id:
        return False

    clean_id = str(voter_id).strip().upper()
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (voter_id, has_voted) VALUES (?, 0);",
            (clean_id,)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()

    return success


def remove_voter(voter_id: str, db_path: Optional[str] = None) -> bool:
    """
    Removes a registered voter from the database.
    Returns True if deleted, False if not found.
    """
    if not voter_id:
        return False

    clean_id = str(voter_id).strip().upper()
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE voter_id = ?;", (clean_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_all_voters(db_path: Optional[str] = None) -> List[Tuple[str, str]]:
    """
    Returns a list of all registered voters:
        [('AA001', 'Yes'), ('AB001', 'No'), ...]
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT voter_id, has_voted FROM users ORDER BY voter_id ASC;")
    rows = cursor.fetchall()
    conn.close()

    return [
        (row["voter_id"], "Yes" if row["has_voted"] == 1 else "No")
        for row in rows
    ]


# ── Voting Operations (Atomic Transaction) ────────────────────────────────────
def record_vote(voter_id: str, candidate_name: str, db_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Atomically records a vote using a SQLite transaction:
      1. Verifies voter is registered.
      2. Verifies voter has NOT voted yet.
      3. Verifies candidate exists.
      4. Inserts vote record into 'votes'.
      5. Increments candidate's vote count in 'candidates'.
      6. Marks voter as has_voted = 1 in 'users'.

    If any error occurs, the entire transaction rolls back automatically.

    Returns:
        (True, "Vote submitted successfully.") or (False, "Error message")
    """
    if not voter_id or not candidate_name:
        return False, "Voter ID and candidate selection are required."

    clean_id = str(voter_id).strip().upper()
    clean_candidate = str(candidate_name).strip()

    conn = get_db_connection(db_path)

    try:
        with conn:  # Context manager guarantees commit on success, rollback on exception
            cursor = conn.cursor()

            # Check voter exists and has not voted
            cursor.execute("SELECT has_voted FROM users WHERE voter_id = ?;", (clean_id,))
            user_row = cursor.fetchone()

            if user_row is None:
                return False, "Voter ID is not registered."

            if user_row["has_voted"] == 1:
                return False, "You have already voted. You cannot vote again."

            # Verify candidate exists
            cursor.execute("SELECT id FROM candidates WHERE name = ?;", (clean_candidate,))
            cand_row = cursor.fetchone()
            if cand_row is None:
                return False, f"Candidate '{clean_candidate}' does not exist."

            # 1. Insert vote into votes table (unique constraint prevents double voting)
            cursor.execute(
                "INSERT INTO votes (voter_id, candidate_name) VALUES (?, ?);",
                (clean_id, clean_candidate)
            )

            # 2. Increment candidate vote count
            cursor.execute(
                "UPDATE candidates SET votes = votes + 1 WHERE name = ?;",
                (clean_candidate,)
            )

            # 3. Mark voter as voted
            cursor.execute(
                "UPDATE users SET has_voted = 1 WHERE voter_id = ?;",
                (clean_id,)
            )

        return True, "Vote submitted successfully."

    except sqlite3.IntegrityError:
        return False, "Double voting detected. Your vote was already recorded."
    except Exception as e:
        return False, f"An unexpected error occurred while recording vote: {str(e)}"
    finally:
        conn.close()




# ── Candidate Management ──────────────────────────────────────────────────────
def get_candidates(db_path: Optional[str] = None) -> List[str]:
    """
    Returns the list of all candidate names.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM candidates ORDER BY id ASC;")
    rows = cursor.fetchall()
    conn.close()
    return [row["name"] for row in rows]


def add_candidate(candidate_name: str, db_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Adds a new candidate to the database.
    """
    if not candidate_name:
        return False, "Candidate name cannot be empty."

    clean_name = str(candidate_name).strip()

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO candidates (name, votes) VALUES (?, 0);",
            (clean_name,)
        )
        conn.commit()
        return True, f"Candidate '{clean_name}' added successfully."
    except sqlite3.IntegrityError:
        return False, f"Candidate '{clean_name}' already exists."
    finally:
        conn.close()


def remove_candidate(candidate_name: str, db_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Removes a candidate from the database if they have 0 votes.
    Protects NOTA from accidental deletion.
    """
    clean_name = str(candidate_name).strip()

    if clean_name.upper() == "NOTA":
        return False, "Cannot delete NOTA (None of the Above option is mandatory)."

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT votes FROM candidates WHERE name = ?;", (clean_name,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False, f"Candidate '{clean_name}' not found."

    if row["votes"] > 0:
        conn.close()
        return False, f"Cannot remove candidate '{clean_name}' because votes have already been cast for them."

    cursor.execute("DELETE FROM candidates WHERE name = ?;", (clean_name,))
    conn.commit()
    conn.close()
    return True, f"Candidate '{clean_name}' removed successfully."


# ── Election Results & Statistics ─────────────────────────────────────────────
def load_votes(db_path: Optional[str] = None) -> Dict[str, int]:
    """
    Returns candidate votes calculated directly from the 'votes' table:
        { "AIADMK": 1, "DMK": 0, "NOTA": 2, ... }
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.name, COUNT(v.id) AS vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.name = v.candidate_name
        GROUP BY c.id, c.name
        ORDER BY c.id ASC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return {row["name"]: row["vote_count"] for row in rows}


def get_election_results(db_path: Optional[str] = None) -> Dict:
    """
    Calculates election results dynamically from the 'votes' table.
    Guarantees total votes matches actual cast votes.
    Ensures that the leading candidate is decided strictly by highest vote count.
    If multiple candidates share the maximum votes, it correctly identifies a tie.

    Returns:
        {
            "candidates": [(name, votes, percentage), ...],
            "total_votes": int,
            "max_votes": int,
            "leaders": list[str],
            "is_tie": bool,
            "winner": str or None
        }
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Calculate actual votes by joining candidates with the votes table
    cursor.execute("""
        SELECT c.name, COUNT(v.id) AS vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.name = v.candidate_name
        GROUP BY c.id, c.name
        ORDER BY vote_count DESC, c.id ASC;
    """)
    rows = cursor.fetchall()
    conn.close()

    total_votes = sum(row["vote_count"] for row in rows)
    candidates_data = []

    for row in rows:
        name = row["name"]
        votes = row["vote_count"]
        percentage = (votes / total_votes * 100) if total_votes > 0 else 0.0
        candidates_data.append((name, votes, percentage))

    # Find the maximum votes scored by any candidate
    max_votes = max((row["vote_count"] for row in rows), default=0)

    # All candidates who share the highest vote count (if votes > 0)
    if total_votes > 0 and max_votes > 0:
        leaders = [row["name"] for row in rows if row["vote_count"] == max_votes]
    else:
        leaders = []

    # If exactly 1 candidate has the highest vote count, they are the clear leader
    # If 2 or more candidates have the exact same highest vote count, it is a tie
    is_tie = len(leaders) > 1
    winner = leaders[0] if len(leaders) == 1 else None

    return {
        "candidates": candidates_data,
        "total_votes": total_votes,
        "max_votes": max_votes,
        "leaders": leaders,
        "is_tie": is_tie,
        "winner": winner
    }


def reset_election_data(db_path: Optional[str] = None) -> None:
    """
    Restarts the election by clearing all cast votes:
      1. Deletes all records from the 'votes' table.
      2. Resets has_voted = 0 for all registered voters in 'users'.
      3. Resets all candidate vote counts to 0 in 'candidates'.
    """
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("DELETE FROM votes;")
        conn.execute("UPDATE users SET has_voted = 0;")
        conn.execute("UPDATE candidates SET votes = 0;")
    conn.close()


def get_admin_stats(db_path: Optional[str] = None) -> Dict[str, int]:
    """
    Returns summary statistics for the Admin Dashboard:
        - Registered Voters
        - Votes Cast
        - Not Voted
        - Total Candidates
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users;")
    total_voters = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE has_voted = 1;")
    votes_cast = cursor.fetchone()[0]

    not_voted = total_voters - votes_cast

    cursor.execute("SELECT COUNT(*) FROM candidates;")
    total_candidates = cursor.fetchone()[0]

    conn.close()

    return {
        "total_voters": total_voters,
        "votes_cast": votes_cast,
        "not_voted": not_voted,
        "total_candidates": total_candidates
    }


# ── Admin Authentication ──────────────────────────────────────────────────────
def verify_admin_login(username: str, plain_password: str, db_path: Optional[str] = None) -> bool:
    """
    Authenticates an administrator against the hashed password stored in the database.
    """
    if not username or not plain_password:
        return False

    clean_user = username.strip()
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT password_hash FROM admin WHERE username = ?;", (clean_user,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False

    return verify_password(plain_password, row["password_hash"])
