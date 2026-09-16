"""
main.py
-------
Main entry point for the Online Voting System.

Responsibilities:
- Initialize the SQLite database automatically upon startup
- Construct the primary Tkinter application window
- Provide a clear Voter Authentication portal
- Provide an Administrator Login portal
- Start the Tkinter event loop

How to Run:
    python main.py

1st-Year Viva Note:
"main.py is the driver script. It connects the GUI interface with the
business logic modules: auth.py for voter login, voting.py for ballot casting,
admin.py for election management, and database.py for SQLite operations."
"""

import tkinter as tk

from admin import open_admin_panel
from auth import login
from database import initialize_database
from voting import open_voting


# ── Color Palette (Modern Clean Slate Theme) ──────────────────────────────────
BG_COLOR = "#F8FAFC"       # Light slate background
CARD_COLOR = "#FFFFFF"     # Crisp white container cards
BORDER_COLOR = "#CBD5E1"   # Subtle input border
BORDER_FOCUS = "#2563EB"   # Primary blue focus outline
BTN_PRIMARY = "#2563EB"    # Primary blue button
BTN_HOVER = "#1D4ED8"      # Hover blue
TEXT_DARK = "#111827"      # High-contrast dark text
TEXT_MUTED = "#64748B"     # Slate gray for secondary text
TEXT_LABEL = "#374151"     # Label text color
SEPARATOR = "#E2E8F0"      # Light border divider


# ── Step 1: Initialize Database ───────────────────────────────────────────────
# Creates data/voting.db and default tables/records if not already created
initialize_database()


# ── Step 2: Main Application Window ───────────────────────────────────────────
root = tk.Tk()
root.title("Online Voting System")
root.geometry("500x700")
root.resizable(False, False)
root.config(bg=BG_COLOR)


# ── Helper: Bordered Input Field ──────────────────────────────────────────────
def make_input_field(parent, label_text: str, is_password: bool = False) -> tk.Entry:
    """
    Creates a styled, bordered input field with focus state indicators.
    """
    container = tk.Frame(parent, bg=CARD_COLOR)
    container.pack(fill="x", pady=(0, 10))

    lbl = tk.Label(
        container,
        text=label_text,
        font=("Segoe UI", 9, "bold"),
        bg=CARD_COLOR,
        fg=TEXT_LABEL
    )
    lbl.pack(anchor="w", pady=(0, 4))

    border_frame = tk.Frame(
        container,
        bg="#FFFFFF",
        highlightbackground=BORDER_COLOR,
        highlightcolor=BORDER_FOCUS,
        highlightthickness=1,
        bd=0
    )
    border_frame.pack(fill="x")

    entry = tk.Entry(
        border_frame,
        font=("Segoe UI", 11),
        bg="#FFFFFF",
        fg=TEXT_DARK,
        insertbackground=TEXT_DARK,
        relief="flat",
        bd=0,
        show="●" if is_password else ""
    )
    entry.pack(fill="x", padx=10, ipady=6)

    def on_focus_in(event):
        border_frame.config(highlightbackground=BORDER_FOCUS, highlightthickness=1.5)

    def on_focus_out(event):
        border_frame.config(highlightbackground=BORDER_COLOR, highlightthickness=1)

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)

    return entry


# ── Step 3: Layout Construction ───────────────────────────────────────────────
outer_frame = tk.Frame(root, bg=BG_COLOR)
outer_frame.place(relx=0.5, rely=0.5, anchor="center")

# ── Title Section ─────────────────────────────────────────────────────────────
title_frame = tk.Frame(outer_frame, bg=BG_COLOR)
title_frame.pack(pady=(0, 16))

tk.Label(
    title_frame,
    text="🗳️",
    font=("Segoe UI", 32),
    bg=BG_COLOR,
    fg=TEXT_DARK
).pack()

tk.Label(
    title_frame,
    text="ONLINE VOTING SYSTEM",
    font=("Segoe UI", 16, "bold"),
    bg=BG_COLOR,
    fg=TEXT_DARK
).pack(pady=(2, 1))

tk.Label(
    title_frame,
    text="Secure · Democratic · Transparent",
    font=("Segoe UI", 9),
    bg=BG_COLOR,
    fg=TEXT_MUTED
).pack()


def make_card(parent, width=420) -> tk.Frame:
    """Creates a card frame with light border outline."""
    card = tk.Frame(
        parent,
        bg=CARD_COLOR,
        width=width,
        bd=0
    )
    card.config(highlightbackground=SEPARATOR, highlightthickness=1)
    return card


# ── Section 1: Voter Login Portal ─────────────────────────────────────────────
voter_card = make_card(outer_frame)
voter_card.pack(pady=6, fill="x")

# Left accent stripe
tk.Frame(voter_card, bg=BTN_PRIMARY, width=5).pack(side="left", fill="y")

voter_inner = tk.Frame(voter_card, bg=CARD_COLOR)
voter_inner.pack(side="left", fill="both", expand=True, padx=18, pady=16)

tk.Label(
    voter_inner,
    text="👤  Voter Login",
    font=("Segoe UI", 12, "bold"),
    bg=CARD_COLOR,
    fg=TEXT_DARK
).pack(anchor="w")

tk.Label(
    voter_inner,
    text="Enter your registered Voter ID to authenticate and cast your vote",
    font=("Segoe UI", 8),
    bg=CARD_COLOR,
    fg=TEXT_MUTED
).pack(anchor="w", pady=(1, 10))

voter_entry = make_input_field(voter_inner, "VOTER ID (e.g. AA001)")

login_btn = tk.Button(
    voter_inner,
    text="Authenticate & Vote  →",
    font=("Segoe UI", 10, "bold"),
    bg=BTN_PRIMARY,
    fg="white",
    activebackground=BTN_HOVER,
    activeforeground="white",
    relief="flat",
    cursor="hand2",
    command=lambda: login(root, voter_entry, open_voting)
)
login_btn.pack(fill="x", ipady=7, pady=(4, 0))

# Enter key triggers login
voter_entry.bind("<Return>", lambda event: login(root, voter_entry, open_voting))


# ── Divider ───────────────────────────────────────────────────────────────────
sep_frame = tk.Frame(outer_frame, bg=BG_COLOR)
sep_frame.pack(fill="x", pady=4)
tk.Frame(sep_frame, bg=SEPARATOR, height=1).pack(fill="x", padx=10)


# ── Section 2: Admin Login Portal ─────────────────────────────────────────────
admin_card = make_card(outer_frame)
admin_card.pack(pady=6, fill="x")

tk.Frame(admin_card, bg="#475569", width=5).pack(side="left", fill="y")

admin_inner = tk.Frame(admin_card, bg=CARD_COLOR)
admin_inner.pack(side="left", fill="both", expand=True, padx=18, pady=16)

tk.Label(
    admin_inner,
    text="🔐  Admin Portal",
    font=("Segoe UI", 12, "bold"),
    bg=CARD_COLOR,
    fg=TEXT_DARK
).pack(anchor="w")

tk.Label(
    admin_inner,
    text="Enter administrative credentials to manage election and view results",
    font=("Segoe UI", 8),
    bg=CARD_COLOR,
    fg=TEXT_MUTED
).pack(anchor="w", pady=(1, 10))

admin_id_entry = make_input_field(admin_inner, "ADMIN USERNAME")
admin_pass_entry = make_input_field(admin_inner, "ADMIN PASSWORD", is_password=True)


def handle_admin_submit():
    open_admin_panel(admin_id_entry, admin_pass_entry)


admin_btn = tk.Button(
    admin_inner,
    text="Admin Dashboard  →",
    font=("Segoe UI", 10, "bold"),
    bg="#334155",
    fg="white",
    activebackground="#1E293B",
    activeforeground="white",
    relief="flat",
    cursor="hand2",
    command=handle_admin_submit
)
admin_btn.pack(fill="x", ipady=7, pady=(4, 0))

admin_id_entry.bind("<Return>", lambda event: handle_admin_submit())
admin_pass_entry.bind("<Return>", lambda event: handle_admin_submit())


# ── Footer ────────────────────────────────────────────────────────────────────
tk.Frame(outer_frame, bg=SEPARATOR, height=1).pack(fill="x", padx=10, pady=(14, 6))

tk.Label(
    outer_frame,
    text="Online Voting System · Academic CSE Project",
    font=("Segoe UI", 8),
    bg=BG_COLOR,
    fg=TEXT_MUTED
).pack()


# ── Step 4: Run Application ───────────────────────────────────────────────────
if __name__ == "__main__":
    root.mainloop()
