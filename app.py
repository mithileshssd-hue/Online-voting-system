"""
app.py
------
Flask Web Application & API Layer for the Online Voting System.

Connects the modern web frontend (HTML5/CSS3/JS) to the existing Python
modules (database.py, security.py, otp.py) without altering backend logic.

How to Run:
    python app.py
"""

import functools
import os
import time
from typing import Callable

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

# ── Import Existing Python Logic ─────────────────────────────────────────────
from database import (
    add_candidate,
    add_voter,
    get_admin_stats,
    get_all_voters,
    get_candidates,
    get_election_results,
    has_voted,
    initialize_database,
    is_registered,
    load_votes,
    record_vote,
    remove_candidate,
    remove_voter,
    reset_election_data,
    verify_admin_login,
)
from otp import OTP_VALIDITY_SECONDS, MAX_ATTEMPTS, generate_otp
from security import validate_candidate_name, validate_voter_id

# ── Initialize Database ──────────────────────────────────────────────────────
# Ensures SQLite tables (users, candidates, votes, admin) exist and are seeded
initialize_database()

# ── Flask Application Setup ──────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "online-voting-system-academic-cse-2026-key")


# ── Authentication Helper Decorators ─────────────────────────────────────────
def voter_required(view_func: Callable) -> Callable:
    """Decorator requiring an authenticated voter session."""
    @functools.wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("voter_id"):
            flash("Please authenticate with your Voter ID to access the voting portal.", "warning")
            return redirect(url_for("login_page"))
        return view_func(*args, **kwargs)
    return wrapped_view


def admin_required(view_func: Callable) -> Callable:
    """Decorator requiring an active administrator session."""
    @functools.wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin"):
            flash("Administrator authentication required to access this page.", "danger")
            return redirect(url_for("admin_login_page"))
        return view_func(*args, **kwargs)
    return wrapped_view


# ── Public Page Routes ───────────────────────────────────────────────────────
@app.route("/")
def home():
    """Renders the public landing page."""
    return render_template("index.html")


@app.route("/about")
def about():
    """Renders the architecture and viva information page."""
    return render_template("about.html")


# ── Voter Web Flow ───────────────────────────────────────────────────────────
@app.route("/login")
def login_page():
    """Renders the voter login portal."""
    if session.get("voter_id"):
        return redirect(url_for("voter_dashboard"))
    return render_template("login.html")


@app.route("/otp")
def otp_page():
    """Renders the OTP verification screen for a pending voter."""
    pending_voter = session.get("pending_voter_id")
    if not pending_voter:
        flash("Please enter your Voter ID first.", "warning")
        return redirect(url_for("login_page"))

    # Calculate remaining validity seconds
    created_at = session.get("otp_created_at", time.time())
    elapsed = time.time() - created_at
    remaining_seconds = max(0, int(OTP_VALIDITY_SECONDS - elapsed))

    return render_template(
        "otp.html",
        voter_id=pending_voter,
        simulated_otp=session.get("otp_code", "0000"),
        remaining_seconds=remaining_seconds,
    )


@app.route("/voter/dashboard")
@voter_required
def voter_dashboard():
    """Renders the voter dashboard showing voting status."""
    voter_id = session.get("voter_id")
    voted = has_voted(voter_id)
    return render_template("voter_dashboard.html", voter_id=voter_id, has_voted=voted)


@app.route("/voter/candidates")
@voter_required
def voter_candidates():
    """Renders the official candidate ballot for eligible voters."""
    voter_id = session.get("voter_id")
    if has_voted(voter_id):
        flash("You have already cast your ballot. Double voting is prohibited.", "info")
        return redirect(url_for("voter_dashboard"))

    candidates = get_candidates()
    return render_template("candidates.html", voter_id=voter_id, candidates=candidates)


@app.route("/voter/confirm")
@voter_required
def vote_confirmation_page():
    """Renders the review and confirm vote screen."""
    voter_id = session.get("voter_id")
    if has_voted(voter_id):
        return redirect(url_for("voter_dashboard"))

    candidate = request.args.get("candidate", "")
    return render_template("vote_confirmation.html", voter_id=voter_id, candidate=candidate)


@app.route("/voter/success")
@voter_required
def vote_success():
    """Renders the vote submission success receipt."""
    voter_id = session.get("voter_id")
    return render_template("vote_success.html", voter_id=voter_id)


@app.route("/logout")
def logout():
    """Safely terminates the voter session."""
    session.pop("voter_id", None)
    session.pop("pending_voter_id", None)
    session.pop("otp_code", None)
    session.pop("otp_created_at", None)
    session.pop("otp_attempts", None)
    flash("You have safely logged out.", "info")
    return redirect(url_for("home"))


# ── Voter REST API Endpoints ─────────────────────────────────────────────────
@app.route("/api/voter/login", methods=["POST"])
def api_voter_login():
    """
    Validates Voter ID format, checks registration, verifies double-voting,
    and generates a simulated OTP.
    """
    data = request.get_json() or {}
    raw_id = data.get("voter_id", "")

    if not raw_id or not str(raw_id).strip():
        return jsonify({"success": False, "message": "Please enter your Voter ID."}), 400

    voter_id = str(raw_id).strip().upper()

    # 1. Format validation using security.py
    if not validate_voter_id(voter_id):
        return jsonify({
            "success": False,
            "message": "Invalid Voter ID format. Expected 2 letters and 3 digits (e.g. AA001 - ZZ999)."
        }), 400

    # 2. Check registration in SQLite users table
    if not is_registered(voter_id):
        return jsonify({
            "success": False,
            "message": f"Voter ID '{voter_id}' is not registered in the election database."
        }), 404

    # 3. Double-voting check
    if has_voted(voter_id):
        return jsonify({
            "success": False,
            "already_voted": True,
            "message": f"Voter ID '{voter_id}' has already cast a vote. Double voting is strictly prohibited."
        }), 403

    # 4. Generate simulated OTP using otp.py
    otp_record = generate_otp()
    session["pending_voter_id"] = voter_id
    session["otp_code"] = otp_record.code
    session["otp_created_at"] = otp_record.created_at
    session["otp_attempts"] = 0

    return jsonify({
        "success": True,
        "message": "Voter ID validated. Simulated OTP generated.",
        "simulated_otp": otp_record.code,
        "voter_id": voter_id
    })


@app.route("/api/voter/verify-otp", methods=["POST"])
def api_voter_verify_otp():
    """
    Validates the entered OTP code against session state with expiration and attempt limits.
    """
    pending_voter = session.get("pending_voter_id")
    correct_otp = session.get("otp_code")
    created_at = session.get("otp_created_at")

    if not pending_voter or not correct_otp or not created_at:
        return jsonify({
            "success": False,
            "message": "No pending OTP verification session found. Please log in again."
        }), 400

    # Check 120-second expiration
    elapsed = time.time() - created_at
    if elapsed > OTP_VALIDITY_SECONDS:
        session.pop("otp_code", None)
        return jsonify({
            "success": False,
            "expired": True,
            "message": "The OTP has expired (120-second limit reached). Please log in again."
        }), 400

    data = request.get_json() or {}
    entered_code = str(data.get("otp_code", "")).strip()

    attempts = session.get("otp_attempts", 0) + 1
    session["otp_attempts"] = attempts

    if entered_code == correct_otp:
        # Successful verification: establish authenticated voter session
        session["voter_id"] = pending_voter
        session.pop("pending_voter_id", None)
        session.pop("otp_code", None)
        session.pop("otp_created_at", None)
        session.pop("otp_attempts", None)
        return jsonify({
            "success": True,
            "message": "OTP verified successfully.",
            "redirect": url_for("voter_dashboard")
        })

    remaining = max(0, MAX_ATTEMPTS - attempts)
    if remaining > 0:
        return jsonify({
            "success": False,
            "remaining_attempts": remaining,
            "message": f"Incorrect OTP code. You have {remaining} attempt(s) remaining."
        }), 400
    else:
        # Lock out session upon exceeding max attempts
        session.pop("pending_voter_id", None)
        session.pop("otp_code", None)
        return jsonify({
            "success": False,
            "remaining_attempts": 0,
            "message": "Incorrect OTP. Maximum 3 attempts exceeded. Session locked."
        }), 403


@app.route("/api/candidates", methods=["GET"])
def api_candidates():
    """Returns the list of registered candidates from database.py."""
    candidates = get_candidates()
    return jsonify({"success": True, "candidates": candidates})


@app.route("/api/voter/status", methods=["GET"])
def api_voter_status():
    """Returns registration and voting status for active or queried voter ID."""
    voter_id = request.args.get("voter_id") or session.get("voter_id")
    if not voter_id:
        return jsonify({"success": False, "message": "Voter ID required."}), 400

    clean_id = str(voter_id).strip().upper()
    registered = is_registered(clean_id)
    voted = has_voted(clean_id) if registered else False

    return jsonify({
        "success": True,
        "voter_id": clean_id,
        "registered": registered,
        "has_voted": voted
    })


@app.route("/api/vote", methods=["POST"])
def api_cast_vote():
    """
    Submits a vote atomically using database.py record_vote().
    Enforces server-side authentication and double-voting prevention.
    """
    voter_id = session.get("voter_id")
    if not voter_id:
        return jsonify({"success": False, "message": "Authentication required to cast a vote."}), 401

    if has_voted(voter_id):
        return jsonify({
            "success": False,
            "message": "You have already voted. Double voting is strictly prohibited."
        }), 403

    data = request.get_json() or {}
    candidate = data.get("candidate", "").strip()

    if not candidate:
        return jsonify({"success": False, "message": "Please select a candidate before submitting."}), 400

    # Atomic SQLite transaction executed by existing database.py function
    success, message = record_vote(voter_id, candidate)

    if success:
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"success": False, "message": message}), 400


# ── Administrator Web Flow ───────────────────────────────────────────────────
@app.route("/admin/login")
def admin_login_page():
    """Renders the administrator login portal."""
    if session.get("admin"):
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html")


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """Renders the administrator dashboard with real-time statistics."""
    stats = get_admin_stats()
    return render_template("admin_dashboard.html", stats=stats)


@app.route("/admin/voters")
@admin_required
def admin_voters():
    """Renders the voter management table and registration form."""
    voters = get_all_voters()
    return render_template("manage_voters.html", voters=voters)


@app.route("/admin/candidates")
@admin_required
def admin_candidates():
    """Renders candidate management with tally and delete protections."""
    candidate_votes = load_votes()
    return render_template("manage_candidates.html", candidate_votes=candidate_votes)


@app.route("/admin/results")
@admin_required
def admin_results():
    """Renders certified election results, distribution bars, and tie status."""
    results = get_election_results()
    return render_template("results.html", results=results)


@app.route("/admin/logout")
def admin_logout():
    """Terminates the administrator session."""
    session.pop("admin", None)
    flash("Administrator logged out safely.", "info")
    return redirect(url_for("admin_login_page"))


# ── Administrator REST API Endpoints ─────────────────────────────────────────
@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    """Authenticates admin credentials using verify_admin_login() SHA-256 check."""
    data = request.get_json() or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not username or not password:
        return jsonify({"success": False, "message": "Please enter both username and password."}), 400

    if verify_admin_login(username, password):
        session["admin"] = username
        return jsonify({
            "success": True,
            "message": "Administrator authenticated successfully.",
            "redirect": url_for("admin_dashboard")
        })

    return jsonify({"success": False, "message": "Invalid Administrator ID or password."}), 401


@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def api_admin_stats():
    """Returns live summary metrics from database.py get_admin_stats()."""
    stats = get_admin_stats()
    return jsonify({"success": True, "stats": stats})


@app.route("/api/admin/voters", methods=["GET", "POST"])
@admin_required
def api_admin_voters():
    """Lists registered voters or adds a new voter via add_voter()."""
    if request.method == "GET":
        voters = get_all_voters()
        return jsonify({"success": True, "voters": voters})

    data = request.get_json() or {}
    voter_id = str(data.get("voter_id", "")).strip().upper()

    if not validate_voter_id(voter_id):
        return jsonify({
            "success": False,
            "message": "Invalid Voter ID format. Must be 2 letters + 3 digits (e.g. AA001 - ZZ999)."
        }), 400

    if add_voter(voter_id):
        return jsonify({"success": True, "message": f"Voter '{voter_id}' registered successfully."})
    else:
        return jsonify({"success": False, "message": f"Voter '{voter_id}' is already registered."}), 409


@app.route("/api/admin/voters/<voter_id>", methods=["DELETE"])
@admin_required
def api_admin_remove_voter(voter_id: str):
    """Deletes a voter from the database using remove_voter()."""
    clean_id = str(voter_id).strip().upper()
    if remove_voter(clean_id):
        return jsonify({"success": True, "message": f"Voter '{clean_id}' removed successfully."})
    return jsonify({"success": False, "message": f"Voter '{clean_id}' not found."}), 404


@app.route("/api/admin/candidates", methods=["GET", "POST"])
@admin_required
def api_admin_candidates():
    """Lists candidates with vote counts or registers a new candidate."""
    if request.method == "GET":
        cand_votes = load_votes()
        return jsonify({"success": True, "candidates": cand_votes})

    data = request.get_json() or {}
    name = str(data.get("name", "")).strip()

    if not validate_candidate_name(name):
        return jsonify({
            "success": False,
            "message": "Invalid candidate name. Length must be 2-30 characters (letters, numbers, spaces, hyphens)."
        }), 400

    success, message = add_candidate(name)
    if success:
        return jsonify({"success": True, "message": message})
    return jsonify({"success": False, "message": message}), 409


@app.route("/api/admin/candidates/<candidate_name>", methods=["DELETE"])
@admin_required
def api_admin_remove_candidate(candidate_name: str):
    """Deletes a candidate (with NOTA and cast-vote protection) via remove_candidate()."""
    clean_name = str(candidate_name).strip()
    success, message = remove_candidate(clean_name)
    if success:
        return jsonify({"success": True, "message": message})
    return jsonify({"success": False, "message": message}), 400


@app.route("/api/admin/results", methods=["GET"])
@admin_required
def api_admin_results():
    """Returns certified election results from get_election_results()."""
    results = get_election_results()
    return jsonify({"success": True, "results": results})


@app.route("/api/admin/reset-election", methods=["POST"])
@admin_required
def api_admin_reset_election():
    """Resets all election ballots using reset_election_data()."""
    reset_election_data()
    return jsonify({"success": True, "message": "All election votes cleared. Election restarted successfully."})


# ── Error Handlers ───────────────────────────────────────────────────────────
@app.errorhandler(404)
def page_not_found(e):
    return render_template("base.html", content="<div class='container text-center py-5'><h2>404 - Page Not Found</h2><p class='text-muted'>The requested URL does not exist.</p><a href='/' class='btn btn-primary'>Back to Home</a></div>"), 404


# ── Main Entry Point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"==================================================")
    print(f"Online Voting System Web Server running at:")
    print(f"  Server URL: http://0.0.0.0:{port}")
    print(f"==================================================")
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )

