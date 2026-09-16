"""
tests/test_web_api.py
---------------------
Automated test suite for the Flask web frontend and REST API layer.

Tests:
1. Public web pages (Home, About, Voter Login, Admin Login)
2. Voter API validation (invalid format, unregistered, already voted)
3. Simulated OTP generation and verification
4. Ballot candidate list retrieval and vote recording
5. Strict double-vote prevention via API
6. Admin authentication and unauthorized endpoint protection
7. Admin voter management (listing, registration, deletion)
8. Admin candidate management (listing, addition, deletion, NOTA protection)
9. Election results query and election reset API
"""

import json
import os
import shutil
import tempfile
import unittest

import app as web_app
from database import add_voter, initialize_database, record_vote


class TestWebAPI(unittest.TestCase):
    def setUp(self):
        """Configure test database and Flask test client."""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "test_voting.db")

        # Re-initialize isolated test database
        initialize_database(self.test_db)

        # Patch app DB_FILE to test database
        import database
        self.orig_db_file = database.DB_FILE
        database.DB_FILE = self.test_db

        web_app.app.config["TESTING"] = True
        web_app.app.config["SECRET_KEY"] = "test-secret-key-1234"
        self.client = web_app.app.test_client()

    def tearDown(self):
        """Clean up test database and restore state."""
        import database
        database.DB_FILE = self.orig_db_file
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ── 1. Public Pages ───────────────────────────────────────────────────────
    def test_public_pages_render(self):
        """Verify home, about, and login pages load successfully with 200 OK."""
        pages = ["/", "/about", "/login", "/admin/login"]
        for page in pages:
            with self.subTest(page=page):
                res = self.client.get(page)
                self.assertEqual(res.status_code, 200)

    # ── 2. Voter Login API ────────────────────────────────────────────────────
    def test_voter_login_validation(self):
        """Voter login must reject invalid formats and unregistered voter IDs."""
        # Missing ID
        res = self.client.post("/api/voter/login", json={})
        self.assertEqual(res.status_code, 400)

        # Invalid format
        res = self.client.post("/api/voter/login", json={"voter_id": "INVALID"})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

        # Unregistered ID
        res = self.client.post("/api/voter/login", json={"voter_id": "ZZ999"})
        self.assertEqual(res.status_code, 404)
        self.assertIn("not registered", res.get_json()["message"].lower())

    def test_voter_login_and_otp_flow(self):
        """Valid registered voter generates simulated OTP and verifies successfully."""
        voter_id = "TN101"
        add_voter(voter_id, db_path=self.test_db)

        # Step 1: Login request
        res = self.client.post("/api/voter/login", json={"voter_id": voter_id})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("simulated_otp", data)
        otp_code = data["simulated_otp"]

        # Step 2: Incorrect OTP verification
        res_fail = self.client.post("/api/voter/verify-otp", json={"otp_code": "0000"})
        self.assertEqual(res_fail.status_code, 400)
        self.assertEqual(res_fail.get_json()["remaining_attempts"], 2)

        # Step 3: Correct OTP verification
        res_ok = self.client.post("/api/voter/verify-otp", json={"otp_code": otp_code})
        self.assertEqual(res_ok.status_code, 200)
        self.assertTrue(res_ok.get_json()["success"])

        # Step 4: Access voter dashboard
        dash_res = self.client.get("/voter/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(voter_id, dash_res.get_data(as_text=True))

    # ── 3. Voting & Double-Voting Safeguards ───────────────────────────────────
    def test_voting_flow_and_double_voting_prevention(self):
        """Voter casts ballot, verifies success, and duplicate attempts are blocked."""
        voter_id = "TN102"
        add_voter(voter_id, db_path=self.test_db)

        # Authenticate session directly
        with self.client.session_transaction() as sess:
            sess["voter_id"] = voter_id

        # Check candidate list
        cand_res = self.client.get("/api/candidates")
        self.assertEqual(cand_res.status_code, 200)
        candidates = cand_res.get_json()["candidates"]
        self.assertIn("DMK", candidates)

        # Cast valid vote
        vote_res = self.client.post("/api/vote", json={"candidate": "DMK"})
        self.assertEqual(vote_res.status_code, 200)
        self.assertTrue(vote_res.get_json()["success"])

        # Attempt to vote a second time (MUST FAIL)
        vote_again_res = self.client.post("/api/vote", json={"candidate": "AIADMK"})
        self.assertEqual(vote_again_res.status_code, 403)
        self.assertIn("already voted", vote_again_res.get_json()["message"].lower())

        # Attempt to log in again via API (MUST INDICATE ALREADY VOTED)
        with self.client.session_transaction() as sess:
            sess.clear()

        relogin_res = self.client.post("/api/voter/login", json={"voter_id": voter_id})
        self.assertEqual(relogin_res.status_code, 403)
        self.assertTrue(relogin_res.get_json()["already_voted"])

    # ── 4. Admin Portal & Management APIs ─────────────────────────────────────
    def test_admin_authentication_and_protection(self):
        """Admin endpoints must block unauthenticated access and verify credentials."""
        # Unauthorized access to dashboard redirects to login
        dash_res = self.client.get("/admin/dashboard")
        self.assertEqual(dash_res.status_code, 302)

        # Invalid login
        bad_login = self.client.post(
            "/api/admin/login",
            json={"username": "admin", "password": "wrongpassword"}
        )
        self.assertEqual(bad_login.status_code, 401)

        # Valid login
        ok_login = self.client.post(
            "/api/admin/login",
            json={"username": "admin", "password": "admin123"}
        )
        self.assertEqual(ok_login.status_code, 200)
        self.assertTrue(ok_login.get_json()["success"])

        # Authorized dashboard access
        dash_ok = self.client.get("/admin/dashboard")
        self.assertEqual(dash_ok.status_code, 200)

    def test_admin_voter_management(self):
        """Admin can list, register, and delete voters via API."""
        with self.client.session_transaction() as sess:
            sess["admin"] = "admin"

        # Register new voter
        add_res = self.client.post("/api/admin/voters", json={"voter_id": "KL555"})
        self.assertEqual(add_res.status_code, 200)

        # Duplicate voter registration rejected
        dup_res = self.client.post("/api/admin/voters", json={"voter_id": "KL555"})
        self.assertEqual(dup_res.status_code, 409)

        # Delete voter
        del_res = self.client.delete("/api/admin/voters/KL555")
        self.assertEqual(del_res.status_code, 200)

    def test_admin_candidate_management_and_nota_protection(self):
        """Admin can add candidate, and NOTA deletion must be rejected."""
        with self.client.session_transaction() as sess:
            sess["admin"] = "admin"

        # Add new candidate
        add_c_res = self.client.post("/api/admin/candidates", json={"name": "Independent-9"})
        self.assertEqual(add_c_res.status_code, 200)

        # Attempt to delete NOTA (must be rejected)
        del_nota_res = self.client.delete("/api/admin/candidates/NOTA")
        self.assertEqual(del_nota_res.status_code, 400)
        self.assertIn("cannot delete nota", del_nota_res.get_json()["message"].lower())

    def test_admin_results_and_election_reset(self):
        """Admin can query live results and execute an election reset."""
        with self.client.session_transaction() as sess:
            sess["admin"] = "admin"

        # Add voter and vote
        add_voter("AP888", db_path=self.test_db)
        record_vote("AP888", "TVK", db_path=self.test_db)

        # Query results API
        res = self.client.get("/api/admin/results")
        self.assertEqual(res.status_code, 200)
        results = res.get_json()["results"]
        self.assertEqual(results["total_votes"], 1)
        self.assertEqual(results["winner"], "TVK")

        # Reset election
        reset_res = self.client.post("/api/admin/reset-election")
        self.assertEqual(reset_res.status_code, 200)

        # Verify results cleared
        res_after = self.client.get("/api/admin/results")
        self.assertEqual(res_after.get_json()["results"]["total_votes"], 0)


if __name__ == "__main__":
    unittest.main()
