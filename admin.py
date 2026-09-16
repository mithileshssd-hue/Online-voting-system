"""
admin.py
--------
Handles administrator authentication, dashboard statistics, voter management,
candidate management, and live election results display.

Responsibilities:
- Verify admin credentials against SHA-256 hashed password in SQLite
- Display summary statistics (Registered Voters, Votes Cast, Not Voted, Total Candidates)
- Voter management: Add voter, view voter list with status, search filter, remove voter
- Candidate management: Add candidate, view candidate list, remove candidate
- Election results: Real-time vote counts, percentages, visual bar chart, winner display
- Clean logout to return to main login screen

1st-Year Viva Note:
"Admin credentials are authenticated by hashing the entered password with SHA-256
and comparing it against the hash stored in the SQLite 'admin' table.
The dashboard calculates statistics dynamically using SQL COUNT and SUM queries."
"""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from database import (
    add_candidate,
    add_voter,
    get_admin_stats,
    get_all_voters,
    get_candidates,
    get_election_results,
    is_registered,
    load_votes,
    remove_candidate,
    remove_voter,
    reset_election_data,
    verify_admin_login,
)
from security import validate_candidate_name, validate_voter_id


# ── Color Palette ─────────────────────────────────────────────────────────────
BG_COLOR = "#F8FAFC"
CARD_COLOR = "#FFFFFF"
TEXT_DARK = "#111827"
TEXT_MUTED = "#64748B"
BORDER_COLOR = "#CBD5E1"
SEPARATOR = "#E2E8F0"
BLUE_PRIMARY = "#2563EB"
BLUE_HOVER = "#1D4ED8"
GREEN_SUCCESS = "#16A34A"
RED_DANGER = "#DC2626"
GOLD_WINNER = "#D97706"
STAT_BG = "#F1F5F9"

CANDIDATE_COLORS = {
    "AIADMK": "#15803D",
    "DMK":    "#DC2626",
    "NTK":    "#7C3AED",
    "TVK":    "#D97706",
    "NOTA":   "#475569",
}


# ── Admin Panel Login & Launcher ──────────────────────────────────────────────
def open_admin_panel(admin_id_entry: tk.Entry, admin_pass_entry: Optional[tk.Entry] = None) -> None:
    """
    Verifies admin credentials against the SQLite database and launches the dashboard.

    Args:
        admin_id_entry: Entry widget containing Admin Username (or password in single-arg mode).
        admin_pass_entry: Entry widget containing Admin Password.
    """
    if admin_pass_entry is None:
        entered_user = "admin"
        entered_pass = admin_id_entry.get().strip()
        id_widget = None
        pass_widget = admin_id_entry
    else:
        entered_user = admin_id_entry.get().strip()
        entered_pass = admin_pass_entry.get().strip()
        id_widget = admin_id_entry
        pass_widget = admin_pass_entry

    if not entered_user or not entered_pass:
        messagebox.showwarning(
            "Input Required",
            "Please enter both Admin ID and Password."
        )
        return

    # Verify against hashed credentials in SQLite
    if not verify_admin_login(entered_user, entered_pass):
        messagebox.showerror(
            "Access Denied",
            "Invalid Admin ID or Password.\nPlease check your credentials and try again."
        )
        return

    # Clear input entries for security
    if id_widget:
        id_widget.delete(0, tk.END)
    pass_widget.delete(0, tk.END)

    # Launch dashboard window
    _open_dashboard_window()




# ── Admin Dashboard Window ───────────────────────────────────────────────────
def _open_dashboard_window() -> None:
    """
    Opens the tabbed Admin Dashboard containing Statistics, Voter Management,
    Candidate Management, and Live Results.
    """
    admin_win = tk.Toplevel()
    admin_win.title("Admin Dashboard - Online Voting System")
    admin_win.geometry("680x760")
    admin_win.resizable(False, False)
    admin_win.config(bg=BG_COLOR)
    admin_win.grab_set()

    # ── Header ────────────────────────────────────────────────────────────────
    header_frame = tk.Frame(admin_win, bg=BG_COLOR)
    header_frame.pack(fill="x", pady=(16, 8), padx=25)

    title_box = tk.Frame(header_frame, bg=BG_COLOR)
    title_box.pack(side="left")

    tk.Label(
        title_box,
        text="🔐  ADMIN DASHBOARD",
        font=("Segoe UI", 16, "bold"),
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).pack(anchor="w")

    tk.Label(
        title_box,
        text="Election Administration & Real-Time Monitoring",
        font=("Segoe UI", 9),
        bg=BG_COLOR,
        fg=TEXT_MUTED
    ).pack(anchor="w")

    logout_btn = tk.Button(
        header_frame,
        text="🚪 Logout",
        font=("Segoe UI", 9, "bold"),
        bg="#FEE2E2",
        fg=RED_DANGER,
        activebackground="#FECACA",
        activeforeground=RED_DANGER,
        relief="flat",
        cursor="hand2",
        command=admin_win.destroy
    )
    logout_btn.pack(side="right", ipady=4, ipadx=10)

    tk.Frame(admin_win, bg=SEPARATOR, height=1).pack(fill="x", padx=25, pady=8)

    # ── Section 1: Dashboard Statistics Cards ─────────────────────────────────
    stats_frame = tk.Frame(admin_win, bg=BG_COLOR)
    stats_frame.pack(fill="x", padx=25, pady=(0, 10))

    stat_cards = {}

    def create_stat_tile(parent, title: str, col_idx: int):
        card = tk.Frame(parent, bg=CARD_COLOR, bd=0)
        card.config(highlightbackground=BORDER_COLOR, highlightthickness=1)
        card.grid(row=0, column=col_idx, padx=4, sticky="nsew")
        parent.grid_columnconfigure(col_idx, weight=1)

        tk.Label(
            card,
            text=title,
            font=("Segoe UI", 8, "bold"),
            bg=CARD_COLOR,
            fg=TEXT_MUTED
        ).pack(pady=(8, 2))

        val_lbl = tk.Label(
            card,
            text="0",
            font=("Segoe UI", 16, "bold"),
            bg=CARD_COLOR,
            fg=BLUE_PRIMARY
        )
        val_lbl.pack(pady=(0, 8))
        return val_lbl

    stat_cards["total_voters"] = create_stat_tile(stats_frame, "Registered Voters", 0)
    stat_cards["votes_cast"] = create_stat_tile(stats_frame, "Votes Cast", 1)
    stat_cards["not_voted"] = create_stat_tile(stats_frame, "Not Voted", 2)
    stat_cards["total_candidates"] = create_stat_tile(stats_frame, "Candidates", 3)

    def refresh_stats():
        stats = get_admin_stats()
        stat_cards["total_voters"].config(text=str(stats["total_voters"]))
        stat_cards["votes_cast"].config(text=str(stats["votes_cast"]), fg=GREEN_SUCCESS)
        stat_cards["not_voted"].config(text=str(stats["not_voted"]), fg=GOLD_WINNER)
        stat_cards["total_candidates"].config(text=str(stats["total_candidates"]))

    # ── Section 2: Tabbed Management Notebook ─────────────────────────────────
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "TNotebook",
        background=BG_COLOR,
        borderwidth=0
    )
    style.configure(
        "TNotebook.Tab",
        font=("Segoe UI", 10, "bold"),
        padding=[16, 6],
        background="#E2E8F0",
        foreground=TEXT_DARK
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", CARD_COLOR)],
        foreground=[("selected", BLUE_PRIMARY)]
    )

    notebook = ttk.Notebook(admin_win)
    notebook.pack(fill="both", expand=True, padx=25, pady=(5, 15))

    voter_tab = tk.Frame(notebook, bg=BG_COLOR)
    cand_tab = tk.Frame(notebook, bg=BG_COLOR)
    results_tab = tk.Frame(notebook, bg=BG_COLOR)

    notebook.add(voter_tab, text="👥 Manage Voters")
    notebook.add(cand_tab, text="🏛️ Manage Candidates")
    notebook.add(results_tab, text="📊 Live Results")

    # =========================================================================
    # TAB 1: VOTER MANAGEMENT
    # =========================================================================
    add_v_card = tk.Frame(voter_tab, bg=CARD_COLOR)
    add_v_card.config(highlightbackground=BORDER_COLOR, highlightthickness=1)
    add_v_card.pack(fill="x", padx=10, pady=(10, 8))

    add_v_inner = tk.Frame(add_v_card, bg=CARD_COLOR)
    add_v_inner.pack(fill="x", padx=14, pady=10)

    tk.Label(
        add_v_inner,
        text="Register New Voter",
        font=("Segoe UI", 10, "bold"),
        bg=CARD_COLOR,
        fg=TEXT_DARK
    ).pack(anchor="w")

    tk.Label(
        add_v_inner,
        text="Enter Voter ID (Format: AA001 to ZZ999). Example: AC104",
        font=("Segoe UI", 8),
        bg=CARD_COLOR,
        fg=TEXT_MUTED
    ).pack(anchor="w", pady=(1, 6))

    add_v_row = tk.Frame(add_v_inner, bg=CARD_COLOR)
    add_v_row.pack(fill="x")

    voter_id_entry = tk.Entry(
        add_v_row,
        font=("Segoe UI", 10),
        bg=STAT_BG,
        fg=TEXT_DARK,
        relief="flat",
        insertbackground=TEXT_DARK
    )
    voter_id_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))

    def handle_add_voter():
        raw_id = voter_id_entry.get().strip().upper()
        if not raw_id:
            messagebox.showwarning("Input Required", "Please enter a Voter ID.", parent=admin_win)
            return

        if not validate_voter_id(raw_id):
            messagebox.showerror(
                "Invalid Format",
                "Invalid Voter ID format.\nExpected: 2 letters + 3 digits (e.g. AA001).",
                parent=admin_win
            )
            return

        if is_registered(raw_id):
            messagebox.showerror("Duplicate Voter", f"Voter ID '{raw_id}' already exists.", parent=admin_win)
            return

        success = add_voter(raw_id)
        if success:
            messagebox.showinfo("Success", f"Voter '{raw_id}' registered successfully.", parent=admin_win)
            voter_id_entry.delete(0, tk.END)
            refresh_voter_table()
            refresh_stats()
        else:
            messagebox.showerror("Error", "Could not register voter.", parent=admin_win)

    add_v_btn = tk.Button(
        add_v_row,
        text="Add Voter",
        font=("Segoe UI", 9, "bold"),
        bg=BLUE_PRIMARY,
        fg="white",
        activebackground=BLUE_HOVER,
        activeforeground="white",
        relief="flat",
        cursor="hand2",
        command=handle_add_voter
    )
    add_v_btn.pack(side="right", ipady=4, ipadx=10)
    voter_id_entry.bind("<Return>", lambda event: handle_add_voter())

    # Voters Table Card
    v_table_card = tk.Frame(voter_tab, bg=CARD_COLOR)
    v_table_card.config(highlightbackground=BORDER_COLOR, highlightthickness=1)
    v_table_card.pack(fill="both", expand=True, padx=10, pady=(0, 8))

    v_table_inner = tk.Frame(v_table_card, bg=CARD_COLOR)
    v_table_inner.pack(fill="both", expand=True, padx=12, pady=10)

    # Search Bar
    search_row = tk.Frame(v_table_inner, bg=CARD_COLOR)
    search_row.pack(fill="x", pady=(0, 6))

    tk.Label(
        search_row,
        text="🔍 Search Voter ID:",
        font=("Segoe UI", 9),
        bg=CARD_COLOR,
        fg=TEXT_DARK
    ).pack(side="left", padx=(0, 6))

    search_entry = tk.Entry(
        search_row,
        font=("Segoe UI", 9),
        bg=STAT_BG,
        fg=TEXT_DARK,
        relief="flat",
        width=15
    )
    search_entry.pack(side="left", ipady=3)

    voter_tree_frame = tk.Frame(v_table_inner, bg=CARD_COLOR)
    voter_tree_frame.pack(fill="both", expand=True)

    v_scroll = ttk.Scrollbar(voter_tree_frame, orient="vertical")
    voter_tree = ttk.Treeview(
        voter_tree_frame,
        columns=("Voter_ID", "Status"),
        show="headings",
        selectmode="browse",
        yscrollcommand=v_scroll.set
    )
    v_scroll.config(command=voter_tree.yview)
    v_scroll.pack(side="right", fill="y")
    voter_tree.pack(side="left", fill="both", expand=True)

    voter_tree.heading("Voter_ID", text="Voter ID")
    voter_tree.heading("Status", text="Voting Status")
    voter_tree.column("Voter_ID", width=240, anchor="center")
    voter_tree.column("Status", width=240, anchor="center")

    def refresh_voter_table(query: str = ""):
        for item in voter_tree.get_children():
            voter_tree.delete(item)

        voters = get_all_voters()
        clean_q = query.strip().upper()

        for vid, status in voters:
            if clean_q and clean_q not in vid:
                continue
            status_text = "Voted" if status.lower() == "yes" else "Not Voted"
            tag = "voted" if status.lower() == "yes" else "not_voted"
            voter_tree.insert("", "end", values=(vid, status_text), tags=(tag,))

        voter_tree.tag_configure("voted", foreground=GREEN_SUCCESS)
        voter_tree.tag_configure("not_voted", foreground=TEXT_DARK)

    search_entry.bind("<KeyRelease>", lambda event: refresh_voter_table(search_entry.get()))

    # Voter Table Actions
    v_act_row = tk.Frame(v_table_inner, bg=CARD_COLOR)
    v_act_row.pack(fill="x", pady=(8, 0))

    def handle_remove_voter():
        selected = voter_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a voter to remove.", parent=admin_win)
            return

        vid_to_remove = voter_tree.item(selected[0])["values"][0]

        confirmed = messagebox.askyesno(
            "Confirm Removal",
            f"Are you sure you want to remove voter '{vid_to_remove}'?\n"
            "This will permanently delete this voter from the database.",
            parent=admin_win
        )
        if not confirmed:
            return

        if remove_voter(vid_to_remove):
            messagebox.showinfo("Success", f"Voter '{vid_to_remove}' removed.", parent=admin_win)
            refresh_voter_table(search_entry.get())
            refresh_stats()
        else:
            messagebox.showerror("Error", "Failed to remove voter.", parent=admin_win)

    tk.Button(
        v_act_row,
        text="🗑 Remove Selected",
        font=("Segoe UI", 9),
        bg="#FEE2E2",
        fg=RED_DANGER,
        activebackground="#FECACA",
        relief="flat",
        cursor="hand2",
        command=handle_remove_voter
    ).pack(side="left", ipady=3, ipadx=8)

    tk.Button(
        v_act_row,
        text="🔄 Refresh List",
        font=("Segoe UI", 9),
        bg=STAT_BG,
        fg=TEXT_DARK,
        activebackground=BORDER_COLOR,
        relief="flat",
        cursor="hand2",
        command=lambda: [refresh_voter_table(), refresh_stats()]
    ).pack(side="right", ipady=3, ipadx=8)

    # =========================================================================
    # TAB 2: CANDIDATE MANAGEMENT
    # =========================================================================
    add_c_card = tk.Frame(cand_tab, bg=CARD_COLOR)
    add_c_card.config(highlightbackground=BORDER_COLOR, highlightthickness=1)
    add_c_card.pack(fill="x", padx=10, pady=(10, 8))

    add_c_inner = tk.Frame(add_c_card, bg=CARD_COLOR)
    add_c_inner.pack(fill="x", padx=14, pady=10)

    tk.Label(
        add_c_inner,
        text="Register New Candidate / Party",
        font=("Segoe UI", 10, "bold"),
        bg=CARD_COLOR,
        fg=TEXT_DARK
    ).pack(anchor="w")

    tk.Label(
        add_c_inner,
        text="Enter candidate or party name (2-30 alphanumeric characters).",
        font=("Segoe UI", 8),
        bg=CARD_COLOR,
        fg=TEXT_MUTED
    ).pack(anchor="w", pady=(1, 6))

    add_c_row = tk.Frame(add_c_inner, bg=CARD_COLOR)
    add_c_row.pack(fill="x")

    cand_name_entry = tk.Entry(
        add_c_row,
        font=("Segoe UI", 10),
        bg=STAT_BG,
        fg=TEXT_DARK,
        relief="flat",
        insertbackground=TEXT_DARK
    )
    cand_name_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))

    def handle_add_cand():
        raw_name = cand_name_entry.get().strip()
        if not raw_name:
            messagebox.showwarning("Input Required", "Please enter a candidate name.", parent=admin_win)
            return

        if not validate_candidate_name(raw_name):
            messagebox.showerror(
                "Invalid Name",
                "Candidate name must be 2-30 characters long and contain only letters, numbers, and spaces.",
                parent=admin_win
            )
            return

        success, msg = add_candidate(raw_name)
        if success:
            messagebox.showinfo("Success", msg, parent=admin_win)
            cand_name_entry.delete(0, tk.END)
            refresh_cand_table()
            refresh_stats()
        else:
            messagebox.showerror("Error", msg, parent=admin_win)

    add_c_btn = tk.Button(
        add_c_row,
        text="Add Candidate",
        font=("Segoe UI", 9, "bold"),
        bg=BLUE_PRIMARY,
        fg="white",
        activebackground=BLUE_HOVER,
        activeforeground="white",
        relief="flat",
        cursor="hand2",
        command=handle_add_cand
    )
    add_c_btn.pack(side="right", ipady=4, ipadx=10)
    cand_name_entry.bind("<Return>", lambda event: handle_add_cand())

    # Candidates Table Card
    c_table_card = tk.Frame(cand_tab, bg=CARD_COLOR)
    c_table_card.config(highlightbackground=BORDER_COLOR, highlightthickness=1)
    c_table_card.pack(fill="both", expand=True, padx=10, pady=(0, 8))

    c_table_inner = tk.Frame(c_table_card, bg=CARD_COLOR)
    c_table_inner.pack(fill="both", expand=True, padx=12, pady=10)

    cand_tree_frame = tk.Frame(c_table_inner, bg=CARD_COLOR)
    cand_tree_frame.pack(fill="both", expand=True)

    c_scroll = ttk.Scrollbar(cand_tree_frame, orient="vertical")
    cand_tree = ttk.Treeview(
        cand_tree_frame,
        columns=("Candidate", "Votes"),
        show="headings",
        selectmode="browse",
        yscrollcommand=c_scroll.set
    )
    c_scroll.config(command=cand_tree.yview)
    c_scroll.pack(side="right", fill="y")
    cand_tree.pack(side="left", fill="both", expand=True)

    cand_tree.heading("Candidate", text="Candidate / Party Name")
    cand_tree.heading("Votes", text="Current Vote Count")
    cand_tree.column("Candidate", width=320, anchor="w")
    cand_tree.column("Votes", width=160, anchor="center")

    def refresh_cand_table():
        for item in cand_tree.get_children():
            cand_tree.delete(item)

        votes_dict = load_votes()
        for name, count in votes_dict.items():
            cand_tree.insert("", "end", values=(name, count))

    # Candidate Table Actions
    c_act_row = tk.Frame(c_table_inner, bg=CARD_COLOR)
    c_act_row.pack(fill="x", pady=(8, 0))

    def handle_remove_cand():
        selected = cand_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a candidate to remove.", parent=admin_win)
            return

        cand_to_remove = cand_tree.item(selected[0])["values"][0]

        confirmed = messagebox.askyesno(
            "Confirm Removal",
            f"Are you sure you want to remove candidate '{cand_to_remove}'?",
            parent=admin_win
        )
        if not confirmed:
            return

        success, msg = remove_candidate(cand_to_remove)
        if success:
            messagebox.showinfo("Success", msg, parent=admin_win)
            refresh_cand_table()
            refresh_stats()
        else:
            messagebox.showerror("Cannot Remove", msg, parent=admin_win)

    tk.Button(
        c_act_row,
        text="🗑 Remove Selected",
        font=("Segoe UI", 9),
        bg="#FEE2E2",
        fg=RED_DANGER,
        activebackground="#FECACA",
        relief="flat",
        cursor="hand2",
        command=handle_remove_cand
    ).pack(side="left", ipady=3, ipadx=8)

    tk.Button(
        c_act_row,
        text="🔄 Refresh Candidates",
        font=("Segoe UI", 9),
        bg=STAT_BG,
        fg=TEXT_DARK,
        activebackground=BORDER_COLOR,
        relief="flat",
        cursor="hand2",
        command=lambda: [refresh_cand_table(), refresh_stats()]
    ).pack(side="right", ipady=3, ipadx=8)

    # =========================================================================
    # TAB 3: LIVE RESULTS
    # =========================================================================
    results_inner = tk.Frame(results_tab, bg=BG_COLOR)
    results_inner.pack(fill="both", expand=True, padx=10, pady=10)

    # Winner Banner Frame
    winner_banner = tk.Frame(results_inner, bg="#ECFDF5", bd=1, relief="solid")
    winner_banner.config(highlightbackground="#A7F3D0", highlightthickness=1, bd=0)
    winner_banner.pack(fill="x", pady=(0, 10))

    winner_lbl = tk.Label(
        winner_banner,
        text="No votes recorded yet.",
        font=("Segoe UI", 11, "bold"),
        bg="#ECFDF5",
        fg="#047857"
    )
    winner_lbl.pack(pady=8)

    # Scrollable / Container frame for candidate results bars
    bars_card = tk.Frame(results_inner, bg=CARD_COLOR)
    bars_card.config(highlightbackground=BORDER_COLOR, highlightthickness=1)
    bars_card.pack(fill="both", expand=True, pady=(0, 10))

    bars_inner = tk.Frame(bars_card, bg=CARD_COLOR)
    bars_inner.pack(fill="both", expand=True, padx=16, pady=12)

    def render_live_results():
        for widget in bars_inner.winfo_children():
            widget.destroy()

        res = get_election_results()
        total_votes = res["total_votes"]
        candidates_data = res["candidates"]
        winner = res["winner"]
        leaders = res.get("leaders", [])
        is_tie = res.get("is_tie", False)
        max_votes = res.get("max_votes", 0)

        # Update winner banner strictly based on vote counts
        if total_votes == 0 or max_votes == 0:
            winner_lbl.config(
                text="📊 No votes have been cast yet.",
                fg=TEXT_MUTED
            )
            winner_banner.config(bg=CARD_COLOR)
        elif is_tie:
            # Multiple candidates share the highest vote count — it's a tie
            tied_names = ", ".join(leaders)
            winner_lbl.config(
                text=f"⚖️ Tie for Lead: {tied_names} ({max_votes} votes each • {total_votes} total votes cast)",
                fg="#B45309"
            )
            winner_banner.config(bg="#FEF3C7")
        elif winner:
            # One candidate has strictly more votes than all others
            winner_lbl.config(
                text=f"🏆 Current Leading Candidate: {winner} ({max_votes} votes • {total_votes} total votes cast)",
                fg="#047857"
            )
            winner_banner.config(bg="#ECFDF5")

        if not candidates_data:
            tk.Label(
                bars_inner,
                text="No candidates available.",
                font=("Segoe UI", 10),
                bg=CARD_COLOR,
                fg=TEXT_MUTED
            ).pack(pady=20)
            return

        for name, votes, pct in candidates_data:
            row_box = tk.Frame(bars_inner, bg=CARD_COLOR)
            row_box.pack(fill="x", pady=6)

            # Label row: Name on left, Votes + Percentage on right
            top_line = tk.Frame(row_box, bg=CARD_COLOR)
            top_line.pack(fill="x")

            # Only show leading indicator if candidate has strictly highest vote count
            if not is_tie and winner and name == winner and total_votes > 0:
                prefix = "⭐ "
                status_note = " (Leading)"
                name_color = GOLD_WINNER
            elif is_tie and name in leaders and total_votes > 0:
                prefix = "⚖️ "
                status_note = " (Tied)"
                name_color = "#B45309"
            else:
                prefix = ""
                status_note = ""
                name_color = TEXT_DARK

            tk.Label(
                top_line,
                text=f"{prefix}{name}{status_note}",
                font=("Segoe UI", 10, "bold"),
                bg=CARD_COLOR,
                fg=name_color
            ).pack(side="left")

            tk.Label(
                top_line,
                text=f"{votes} votes  ({pct:.1f}%)",
                font=("Segoe UI", 9),
                bg=CARD_COLOR,
                fg=TEXT_MUTED
            ).pack(side="right")

            # Visual progress bar
            accent_col = CANDIDATE_COLORS.get(name, BLUE_PRIMARY)
            bar_canvas = tk.Canvas(row_box, height=10, bg="#F1F5F9", highlightthickness=0)
            bar_canvas.pack(fill="x", pady=(4, 0))

            ratio = (votes / total_votes) if total_votes > 0 else 0.0

            def _draw(c=bar_canvas, r=ratio, col=accent_col):
                c.update_idletasks()
                w = c.winfo_width()
                if w > 1:
                    c.delete("all")
                    c.create_rectangle(0, 0, w, 10, fill="#E2E8F0", outline="")
                    c.create_rectangle(0, 0, int(w * r), 10, fill=col, outline="")

            admin_win.after(50, _draw)

    def handle_reset_election():
        confirmed = messagebox.askyesno(
            "Restart Election / Reset Votes",
            "Are you sure you want to restart the election?\n\n"
            "This action will:\n"
            "• Clear all recorded votes\n"
            "• Reset all registered voters back to 'Not Voted'\n"
            "• Reset all candidate vote counts to 0\n\n"
            "Note: Registered voter accounts and candidate names will NOT be deleted.\n\n"
            "Do you wish to proceed?",
            icon="warning",
            parent=admin_win
        )
        if confirmed:
            reset_election_data()
            messagebox.showinfo(
                "Election Reset",
                "✓ All election votes have been reset to 0.\n"
                "Registered voters can now cast their votes again.",
                parent=admin_win
            )
            refresh_stats()
            refresh_voter_table()
            refresh_cand_table()
            render_live_results()

    res_btn_row = tk.Frame(results_inner, bg=BG_COLOR)
    res_btn_row.pack(fill="x", pady=(5, 0))

    tk.Button(
        res_btn_row,
        text="⚠️ Reset / Restart Election",
        font=("Segoe UI", 9, "bold"),
        bg="#FEE2E2",
        fg=RED_DANGER,
        activebackground="#FECACA",
        activeforeground=RED_DANGER,
        relief="flat",
        cursor="hand2",
        command=handle_reset_election
    ).pack(side="left", ipady=4, ipadx=10)

    tk.Button(
        res_btn_row,
        text="🔄 Refresh Live Results",
        font=("Segoe UI", 9, "bold"),
        bg=BLUE_PRIMARY,
        fg="white",
        activebackground=BLUE_HOVER,
        activeforeground="white",
        relief="flat",
        cursor="hand2",
        command=lambda: [render_live_results(), refresh_stats()]
    ).pack(side="right", ipady=4, ipadx=12)

    # Initial data load
    refresh_stats()
    refresh_voter_table()
    refresh_cand_table()
    render_live_results()
