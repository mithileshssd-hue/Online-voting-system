"""
security.py
-----------
Contains security and validation functions for the Online Voting System.

Responsibilities:
- Validate Voter ID format (AA001 to ZZ999)
- Validate Candidate names
- Hash passwords using SHA-256 for secure storage
- Verify passwords against stored SHA-256 hashes

1st-Year Viva Note:
"Passwords are never stored in plain text. We hash them using SHA-256
so that even if someone views the database, they cannot see the real password."
"""

import hashlib
import re


# ── Voter ID Validation ────────────────────────────────────────────────────────
def validate_voter_id(voter_id: str) -> bool:
    """
    Checks that the Voter ID follows the standard format:
      1. Exactly 5 characters long.
      2. First two characters are uppercase letters (A-Z).
      3. Last three characters are digits (0-9).
      4. The numeric part must be between 001 and 999 (000 is invalid).
      5. Valid range: AA001 to ZZ999.

    Args:
        voter_id (str): The voter ID to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    if not voter_id or not isinstance(voter_id, str):
        return False

    cleaned_id = voter_id.strip().upper()

    # Regex: 2 uppercase letters followed by 3 digits
    pattern = r"^[A-Z]{2}[0-9]{3}$"
    if not re.match(pattern, cleaned_id):
        return False

    # Prevent '000' as the numeric portion
    if cleaned_id[2:] == "000":
        return False

    return True




# ── Candidate Name Validation ──────────────────────────────────────────────────
def validate_candidate_name(name: str) -> bool:
    """
    Validates a candidate name:
      1. Must be between 2 and 30 characters.
      2. Can contain letters, numbers, spaces, and hyphens.

    Args:
        name (str): Candidate or party name.

    Returns:
        bool: True if valid, False otherwise.
    """
    if not name or not isinstance(name, str):
        return False

    cleaned = name.strip()
    if len(cleaned) < 2 or len(cleaned) > 30:
        return False

    # Allow alphanumeric, spaces, and hyphens/parentheses (e.g. "AIADMK", "Independent-1", "NOTA")
    pattern = r"^[A-Za-z0-9\s\-()]+$"
    return bool(re.match(pattern, cleaned))


# ── Password Hashing ──────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using SHA-256.

    Args:
        password (str): The plain-text password.

    Returns:
        str: 64-character hexadecimal SHA-256 hash.
    """
    if not isinstance(password, str):
        password = str(password)
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ── Password Verification ─────────────────────────────────────────────────────
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compares a plain-text password against a stored SHA-256 hash.

    Args:
        plain_password (str): The password entered by the user.
        hashed_password (str): The stored SHA-256 hash from the database.

    Returns:
        bool: True if passwords match, False otherwise.
    """
    return hash_password(plain_password) == hashed_password
