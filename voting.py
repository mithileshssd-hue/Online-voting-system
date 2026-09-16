"""
voting.py
---------
Handles the voting window, candidate selection, review dialog, and secure vote submission.

Responsibilities:
- Fetch dynamic candidate list from SQLite database
- Present clean, accessible candidate selection with radio buttons
- Review vote confirmation step before final submission
- Enforce strict double-voting prevention using SQLite transaction
- Immediately disable submit button upon click to prevent double-click race conditions

1st-Year Viva Note:
"Double voting is prevented at two levels:
1. Application level: Submit button is immediately disabled upon click.
2. Database level: An atomic SQLite transaction checks has_voted, records the vote in
   the votes table (which has a UNIQUE constraint on voter_id), and sets has_voted = 1.
   If a voter tries to vote twice, the database constraint rejects it."
"""

import tkinter as tk
from tkinter import messagebox

from database import get_candidates, has_voted, is_registered, record_vote


# ── Color Palette ─────────────────────────────────────────────────────────────
BG_COLOR = "#F8FAFC"       # Light slate background
CARD_COLOR = "#FFFFFF"     # Clean white card
BTN_PRIMARY = "#2563EB"    # Blue primary button
BTN_HOVER = "#1D4ED8"      # Darker blue on hover
TEXT_DARK = "#111827"      # High-contrast dark text
TEXT_MUTED = "#64748B"     # Slate gray for secondary text
BORDER_COLOR = "#CBD5E1"   # Border line color
SEPARATOR = "#E2E8F0"      # Divider line

# Visual party/candidate color accents
CANDIDATE_ACCENTS = {
    "AIADMK": "#15803D",  # Green
    "DMK":    "#DC2626",  # Red
    "NTK":    "#7C3AED",  # Purple
    "TVK":    "#D97706",  # Amber
    "NOTA":   "#475569",  # Slate gray
}


def open_voting(root: tk.Tk, user_id: str) -> None:
    """
    Opens the Voting Toplevel window for an authenticated voter.

    Flow:
      1. Pre-check database status (must be registered and not voted).
      2. Fetch registered candidates from database.
      3. Display candidate selection with radio buttons.
      4. On submit: Prompt voter to review and confirm choice.
      5. Atomically commit vote via record_vote() transaction.
      6. Show success screen and close voting window.

    Args:
        root (tk.Tk): Main application window.
        user_id (str): Voter ID of the authenticated user.
    """
    clean_user_id = str(user_id).strip().upper()

    # Pre-check 1: Voter registration
    if not is_registered(clean_user_id):
        messagebox.showerror(
            "Access Denied",
            "Voter ID is not registered in the system."
        )
        return

    # Pre-check 2: Prevent double voting
    if has_voted(clean_user_id):
        messagebox.showerror(
            "Already Voted",
            "You have already voted. Double voting is strictly prohibited."
        )
        return

    # Fetch candidates from SQLite
    candidates = get_candidates()
    if not candidates:
        messagebox.showerror(
            "Election Error",
            "No candidates are registered in the database. Please contact the administrator."
        )
        return

    # ── Create Voting Window ──────────────────────────────────────────────────
    vote_window = tk.Toplevel(root)
    vote_window.title("Cast Your Vote - Online Voting System")
    vote_window.geometry("450x640")
    vote_window.resizable(False, False)
    vote_window.config(bg=BG_COLOR)

    # Modal grab to prevent interacting with main window while voting
    vote_window.grab_set()

    # ── Header ────────────────────────────────────────────────────────────────
    header_frame = tk.Frame(vote_window, bg=BG_COLOR)
    header_frame.pack(fill="x", pady=(22, 10), padx=30)

    tk.Label(
        header_frame,
        text="🗳️  CAST YOUR VOTE",
        font=("Segoe UI", 18, "bold"),
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).pack()

    tk.Label(
        header_frame,
        text=f"Authenticated Voter ID: {clean_user_id}",
        font=("Segoe UI", 10, "bold"),
        bg=BG_COLOR,
        fg=BTN_PRIMARY
    ).pack(pady=(3, 0))

    tk.Label(
        header_frame,
        text="Please select one candidate below and confirm your choice.",
        font=("Segoe UI", 9),
        bg=BG_COLOR,
        fg=TEXT_MUTED
    ).pack(pady=(2, 0))

    tk.Frame(vote_window, bg=SEPARATOR, height=1).pack(fill="x", padx=30, pady=10)

    # ── Candidate Radio Selection ─────────────────────────────────────────────
    selected_candidate = tk.StringVar(value="")

    # Scrollable / flexible frame for candidates
    cand_container = tk.Frame(vote_window, bg=BG_COLOR)
    cand_container.pack(fill="both", expand=True, padx=30, pady=(0, 10))

    for cand_name in candidates:
        card_row = tk.Frame(cand_container, bg=CARD_COLOR, bd=0)
        card_row.config(highlightbackground=BORDER_COLOR, highlightthickness=1)
        card_row.pack(fill="x", pady=5)

        # Colored accent stripe
        accent_color = CANDIDATE_ACCENTS.get(cand_name, BTN_PRIMARY)
        tk.Frame(card_row, bg=accent_color, width=6).pack(side="left", fill="y")

        # Radio button inside card
        rb = tk.Radiobutton(
            card_row,
            text=f"  {cand_name}",
            variable=selected_candidate,
            value=cand_name,
            font=("Segoe UI", 12, "bold"),
            bg=CARD_COLOR,
            fg=TEXT_DARK,
            selectcolor=CARD_COLOR,
            activebackground=CARD_COLOR,
            activeforeground=accent_color,
            cursor="hand2"
        )
        rb.pack(side="left", padx=12, pady=12, fill="both", expand=True)

    # ── Review & Confirm Vote Logic ───────────────────────────────────────────
    def handle_submit():
        choice = selected_candidate.get().strip()

        # Step 1: Validate selection
        if not choice:
            messagebox.showwarning(
                "No Selection",
                "Please select a candidate before proceeding.",
                parent=vote_window
            )
            return

        # Step 2: Review and Confirmation dialog
        confirmed = messagebox.askyesno(
            "Review & Confirm Your Vote",
            f"Please review your selection carefully:\n\n"
            f"Voter ID:            {clean_user_id}\n"
            f"Selected Candidate:  {choice}\n\n"
            f"Are you sure you want to cast your vote for {choice}?\n\n"
            f"NOTE: Once confirmed, this action CANNOT be reversed.",
            icon="question",
            parent=vote_window
        )

        if not confirmed:
            return

        # Step 3: Prevent double-click race conditions by disabling the button
        submit_btn.config(state="disabled", text="Recording Vote...")
        vote_window.update_idletasks()

        # Step 4: Atomic SQLite transaction to record vote
        success, message = record_vote(clean_user_id, choice)

        if success:
            messagebox.showinfo(
                "Vote Submitted Successfully",
                "✓ VOTE RECORDED\n\n"
                f"Your vote for '{choice}' has been safely recorded.\n"
                "Thank you for exercising your democratic right.",
                parent=vote_window
            )
            vote_window.destroy()
        else:
            messagebox.showerror(
                "Submission Error",
                f"Failed to submit vote:\n\n{message}",
                parent=vote_window
            )
            vote_window.destroy()

    # ── Bottom Action Bar ─────────────────────────────────────────────────────
    tk.Frame(vote_window, bg=SEPARATOR, height=1).pack(fill="x", padx=30, pady=(5, 12))

    submit_btn = tk.Button(
        vote_window,
        text="Review & Confirm Vote  ✓",
        font=("Segoe UI", 11, "bold"),
        bg=BTN_PRIMARY,
        fg="white",
        activebackground=BTN_HOVER,
        activeforeground="white",
        relief="flat",
        cursor="hand2",
        command=handle_submit
    )
    submit_btn.pack(fill="x", padx=30, ipady=8, pady=(0, 20))
