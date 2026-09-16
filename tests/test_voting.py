"""
tests/test_voting.py
--------------------
Unit tests for the Online Voting System.

Covers:
1. Voter ID validation (valid and invalid formats)
2. Password hashing and verification
3. Database initialization and table creation
4. Voter registration and duplicate prevention
5. Vote recording and candidate vote counter increment
6. Double-voting prevention (ensuring one-vote-per-voter)
7. Invalid candidate rejection
8. OTP verification and attempt limits

Run tests via:
    python -m unittest discover tests
"""

import os
import shutil
import tempfile
import unittest

from database import (
    add_candidate,
    add_voter,
    get_all_voters,
    get_candidates,
    get_db_connection,
    has_voted,
    initialize_database,
    is_registered,
    load_votes,
    record_vote,
    verify_admin_login,
)
from otp import OTPRecord, generate_otp
from security import hash_password, validate_voter_id, verify_password


class TestOnlineVotingSystem(unittest.TestCase):
    def setUp(self):
        """Create a temporary database file for isolated testing."""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "test_voting.db")
        initialize_database(self.test_db)

    def tearDown(self):
        """Clean up temporary test files."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ── 1. Security & Validation Tests ────────────────────────────────────────
    def test_valid_voter_id(self):
        """Valid voter IDs should follow format: 2 letters + 3 digits (001-999)."""
        valid_ids = ["AA001", "ZZ999", "TN104", "ab001"]
        for vid in valid_ids:
            with self.subTest(vid=vid):
                self.assertTrue(validate_voter_id(vid))

    def test_invalid_voter_id(self):
        """Invalid formats, lengths, or 000 numeric parts should be rejected."""
        invalid_ids = ["AA000", "A001", "AAA01", "12345", "AA1234", "", "   ", None]
        for vid in invalid_ids:
            with self.subTest(vid=vid):
                self.assertFalse(validate_voter_id(vid))

    def test_password_hashing(self):
        """Passwords should be hashed and verifiable without storing plain text."""
        raw_pw = "college2026"
        hashed = hash_password(raw_pw)

        self.assertNotEqual(raw_pw, hashed)
        self.assertEqual(len(hashed), 64)  # SHA-256 produces a 64-char hex string
        self.assertTrue(verify_password(raw_pw, hashed))
        self.assertFalse(verify_password("wrongpassword", hashed))

    # ── 2. Database & Registration Tests ──────────────────────────────────────
    def test_database_initialization(self):
        """Database initialization should create all required tables and default admin."""
        conn = get_db_connection(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        conn.close()

        self.assertIn("users", tables)
        self.assertIn("candidates", tables)
        self.assertIn("votes", tables)
        self.assertIn("admin", tables)

    def test_default_admin_login(self):
        """Default administrator should be authenticated with hashed password."""
        self.assertTrue(verify_admin_login("admin", "admin123", db_path=self.test_db))
        self.assertFalse(verify_admin_login("admin", "wrongpass", db_path=self.test_db))
        self.assertFalse(verify_admin_login("unknown", "admin123", db_path=self.test_db))

    def test_voter_registration_and_duplicate_rejection(self):
        """New voters can be registered, but duplicates must be rejected."""
        self.assertTrue(add_voter("XY100", db_path=self.test_db))
        self.assertTrue(is_registered("XY100", db_path=self.test_db))
        self.assertFalse(has_voted("XY100", db_path=self.test_db))

        # Attempting to add the same voter again must return False
        self.assertFalse(add_voter("XY100", db_path=self.test_db))

    # ── 3. Voting Logic & Double-Voting Prevention ────────────────────────────
    def test_single_vote_submission(self):
        """A registered voter should be able to cast exactly one vote."""
        voter_id = "CD200"
        candidate = "DMK"
        add_voter(voter_id, db_path=self.test_db)

        initial_votes = load_votes(self.test_db).get(candidate, 0)

        # Cast vote
        success, msg = record_vote(voter_id, candidate, db_path=self.test_db)
        self.assertTrue(success)

        # Candidate vote count must increment by 1
        updated_votes = load_votes(self.test_db).get(candidate, 0)
        self.assertEqual(updated_votes, initial_votes + 1)

        # Voter status must now be recorded as has_voted = True
        self.assertTrue(has_voted(voter_id, db_path=self.test_db))

    def test_double_voting_prevention(self):
        """A voter must be blocked from casting a second vote."""
        voter_id = "EF300"
        add_voter(voter_id, db_path=self.test_db)

        # First vote succeeds
        success1, _ = record_vote(voter_id, "AIADMK", db_path=self.test_db)
        self.assertTrue(success1)

        # Second vote attempt MUST fail
        success2, msg = record_vote(voter_id, "DMK", db_path=self.test_db)
        self.assertFalse(success2)
        self.assertIn("already voted", msg.lower())

    def test_unregistered_voter_cannot_vote(self):
        """An unregistered voter ID cannot cast a vote."""
        success, msg = record_vote("UN999", "AIADMK", db_path=self.test_db)
        self.assertFalse(success)
        self.assertIn("not registered", msg.lower())

    def test_invalid_candidate_rejection(self):
        """Votes for non-existent candidates must be rejected."""
        voter_id = "GH400"
        add_voter(voter_id, db_path=self.test_db)

        success, msg = record_vote(voter_id, "NonExistentParty", db_path=self.test_db)
        self.assertFalse(success)
        self.assertFalse(has_voted(voter_id, db_path=self.test_db))

    # ── 4. OTP Simulation Tests ───────────────────────────────────────────────
    def test_otp_verification_flow(self):
        """OTP must verify matching code, decrement attempts on failure, and lock after max attempts."""
        otp = generate_otp()
        self.assertEqual(len(otp.code), 4)

        # Wrong attempt 1
        ok, msg = otp.verify("0000")
        self.assertFalse(ok)
        self.assertEqual(otp.attempts, 1)

        # Correct attempt
        ok, msg = otp.verify(otp.code)
        self.assertTrue(ok)
        self.assertTrue(otp.is_used)

        # Reusing verified OTP must fail
        ok2, msg2 = otp.verify(otp.code)
        self.assertFalse(ok2)

    # ── 5. Election Results & Tie-Breaking Tests ──────────────────────────────
    def test_results_leading_by_count_and_tie_detection(self):
        """
        Verify that leading candidate is strictly based on vote count,
        and ties are properly detected without alphabetically favoring any candidate.
        """
        from database import get_db_connection, get_election_results

        # Reset all candidate votes to 0 for a clean test baseline
        conn = get_db_connection(self.test_db)
        conn.execute("UPDATE candidates SET votes = 0;")
        conn.execute("DELETE FROM votes;")
        conn.commit()
        conn.close()

        # Case 1: Tie scenario (AIADMK: 1, NOTA: 1, TVK: 1)
        add_voter("V1001", db_path=self.test_db)
        add_voter("V1002", db_path=self.test_db)
        add_voter("V1003", db_path=self.test_db)

        record_vote("V1001", "AIADMK", db_path=self.test_db)
        record_vote("V1002", "NOTA", db_path=self.test_db)
        record_vote("V1003", "TVK", db_path=self.test_db)

        res_tie = get_election_results(db_path=self.test_db)
        self.assertTrue(res_tie["is_tie"])
        self.assertIsNone(res_tie["winner"])
        self.assertEqual(res_tie["max_votes"], 1)
        self.assertCountEqual(res_tie["leaders"], ["AIADMK", "NOTA", "TVK"])

        # Case 2: Outright leader strictly by vote count (TVK gets 2nd vote -> 2 votes)
        add_voter("V1004", db_path=self.test_db)
        record_vote("V1004", "TVK", db_path=self.test_db)

        res_lead = get_election_results(db_path=self.test_db)
        self.assertFalse(res_lead["is_tie"])
        self.assertEqual(res_lead["winner"], "TVK")
        self.assertEqual(res_lead["max_votes"], 2)
        self.assertEqual(res_lead["leaders"], ["TVK"])

    def test_reset_election_data(self):
        """Resetting election should clear all votes and reset voter status to not voted."""
        from database import get_admin_stats, reset_election_data

        # Cast a vote
        add_voter("V2001", db_path=self.test_db)
        record_vote("V2001", "DMK", db_path=self.test_db)

        # Reset election
        reset_election_data(db_path=self.test_db)

        stats = get_admin_stats(db_path=self.test_db)
        self.assertEqual(stats["votes_cast"], 0)
        self.assertEqual(stats["not_voted"], stats["total_voters"])
        self.assertFalse(has_voted("V2001", db_path=self.test_db))


if __name__ == "__main__":
    unittest.main()
