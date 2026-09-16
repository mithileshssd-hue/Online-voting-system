"""
otp.py
------
Handles OTP (One-Time Password) generation, validation, expiration, and GUI window.

Responsibilities:
- Generate random 4-digit numeric OTP
- Enforce OTP expiration (120 seconds / 2 minutes)
- Limit verification attempts (maximum 3 attempts)
- Invalidate OTP immediately upon successful verification or expiry
- Display simulated OTP clearly for educational/academic viva demonstration

1st-Year Viva Note:
"In real production systems, OTPs are sent via SMS gateways (like Twilio).
In this college project, we simulate the OTP transmission by displaying it in a pop-up,
while strictly implementing real OTP security logic: random generation, expiration timer,
and attempt limits."
"""

import random
import time



# ── Configuration Constants ────────────────────────────────────────────────────
OTP_VALIDITY_SECONDS = 120  # 2 minutes
MAX_ATTEMPTS = 3

# UI Colors (Consistent Slate/Blue Theme)
BG_COLOR = "#F8FAFC"
CARD_COLOR = "#FFFFFF"
BTN_PRIMARY = "#2563EB"
BTN_HOVER = "#1D4ED8"
TEXT_DARK = "#111827"
TEXT_MUTED = "#64748B"
BORDER_COLOR = "#CBD5E1"
WARNING_COLOR = "#D97706"
DANGER_COLOR = "#DC2626"
SUCCESS_COLOR = "#16A34A"


# ── OTP Data Class ─────────────────────────────────────────────────────────────
class OTPRecord:
    """
    Represents a single generated OTP instance with timestamp and state.
    """
    def __init__(self, code: str):
        self.code = str(code)
        self.created_at = time.time()
        self.attempts = 0
        self.is_used = False

    def is_expired(self) -> bool:
        """Checks if the OTP has exceeded its validity window."""
        return (time.time() - self.created_at) > OTP_VALIDITY_SECONDS

    def seconds_remaining(self) -> int:
        """Returns the number of seconds left before the OTP expires."""
        elapsed = time.time() - self.created_at
        return max(0, int(OTP_VALIDITY_SECONDS - elapsed))

    def verify(self, entered_code: str) -> tuple[bool, str]:
        """
        Validates the entered OTP string.

        Returns:
            (True, "Success message") or (False, "Reason for failure")
        """
        if self.is_used:
            return False, "This OTP has already been used and is no longer valid."

        if self.is_expired():
            return False, "This OTP has expired. Please log in again to receive a new OTP."

        self.attempts += 1

        if entered_code.strip() == self.code:
            self.is_used = True  # Invalidate OTP once verified
            return True, "OTP verified successfully."

        remaining = MAX_ATTEMPTS - self.attempts
        if remaining > 0:
            return False, f"Incorrect OTP. You have {remaining} attempt(s) remaining."
        else:
            return False, "Incorrect OTP. Maximum attempts reached. Window will now close."


# ── OTP Generator Function ─────────────────────────────────────────────────────
def generate_otp() -> OTPRecord:
    """
    Generates a secure, random 4-digit OTP object between 1000 and 9999.

    Returns:
        OTPRecord: Object holding the 4-digit code and timestamp.
    """
    code = str(random.randint(1000, 9999))
    return OTPRecord(code)


# ── OTP Verification Window ───────────────────────────────────────────────────
def open_otp_window(root, user_id: str, otp_record: OTPRecord, success_function) -> None:
    """
    Opens a modal Toplevel window where the voter must enter the OTP.

    Features:
      - Live countdown timer (2 minutes)
      - Attempts counter (max 3)
      - Educational notice that OTP is simulated for demonstration
      - Auto-focus on entry and Enter key submission

    Args:
        root (tk.Tk): Main application window.
        user_id (str): Authenticated voter ID.
        otp_record (OTPRecord): Active OTP record.
        success_function (callable): Callback function invoked on verification success:
                                     success_function(root, user_id)
    """
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError as exc:
        raise ImportError(
            "Tkinter is required to open the desktop OTP window, but is not installed in this environment."
        ) from exc

    clean_user_id = str(user_id).strip().upper()

    otp_win = tk.Toplevel(root)
    otp_win.title("OTP Verification - Online Voting System")
    otp_win.geometry("400x420")
    otp_win.resizable(False, False)
    otp_win.config(bg=BG_COLOR)


    # Modal window: lock interaction to this popup until closed
    otp_win.grab_set()

    # ── Header ────────────────────────────────────────────────────────────────
    header_frame = tk.Frame(otp_win, bg=BG_COLOR)
    header_frame.pack(fill="x", pady=(20, 10), padx=25)

    tk.Label(
        header_frame,
        text="🔐  OTP Verification",
        font=("Segoe UI", 16, "bold"),
        bg=BG_COLOR,
        fg=TEXT_DARK
    ).pack()

    tk.Label(
        header_frame,
        text=f"Voter ID: {clean_user_id}",
        font=("Segoe UI", 10, "bold"),
        bg=BG_COLOR,
        fg=BTN_PRIMARY
    ).pack(pady=(2, 2))

    tk.Label(
        header_frame,
        text="Enter the 4-digit verification code sent to you.",
        font=("Segoe UI", 9),
        bg=BG_COLOR,
        fg=TEXT_MUTED
    ).pack()

    # Educational notice badge
    edu_frame = tk.Frame(otp_win, bg="#EFF6FF", bd=1, relief="solid")
    edu_frame.config(highlightbackground="#BFDBFE", highlightthickness=1, bd=0)
    edu_frame.pack(fill="x", padx=30, pady=(5, 12))

    tk.Label(
        edu_frame,
        text="ℹ️ Educational Demo: OTP is simulated via pop-up alert",
        font=("Segoe UI", 8, "italic"),
        bg="#EFF6FF",
        fg="#1E40AF"
    ).pack(pady=4)

    # ── Card Container ────────────────────────────────────────────────────────
    card = tk.Frame(otp_win, bg=CARD_COLOR, bd=0)
    card.config(highlightbackground=BORDER_COLOR, highlightthickness=1)
    card.pack(fill="x", padx=30, pady=(0, 15))

    tk.Label(
        card,
        text="Enter 4-Digit Code",
        font=("Segoe UI", 10, "bold"),
        bg=CARD_COLOR,
        fg=TEXT_DARK
    ).pack(pady=(16, 8))

    otp_entry = tk.Entry(
        card,
        font=("Segoe UI", 20, "bold"),
        justify="center",
        width=8,
        bg="#F1F5F9",
        fg=TEXT_DARK,
        relief="flat",
        insertbackground=TEXT_DARK
    )
    otp_entry.pack(ipady=6, pady=(0, 10))
    otp_entry.focus()

    # Countdown Timer Label
    timer_lbl = tk.Label(
        card,
        text=f"⏱️ Time Remaining: {otp_record.seconds_remaining()}s",
        font=("Segoe UI", 9),
        bg=CARD_COLOR,
        fg=TEXT_MUTED
    )
    timer_lbl.pack(pady=(0, 4))

    # Attempts Counter Label
    attempts_lbl = tk.Label(
        card,
        text=f"Attempts remaining: {MAX_ATTEMPTS}",
        font=("Segoe UI", 9),
        bg=CARD_COLOR,
        fg=TEXT_MUTED
    )
    attempts_lbl.pack(pady=(0, 14))

    # Live Timer Updater
    is_active = [True]

    def update_timer():
        if not is_active[0]:
            return

        remaining = otp_record.seconds_remaining()
        if remaining > 0:
            timer_lbl.config(
                text=f"⏱️ Time Remaining: {remaining}s",
                fg=DANGER_COLOR if remaining <= 20 else TEXT_MUTED
            )
            otp_win.after(1000, update_timer)
        else:
            timer_lbl.config(text="⏱️ OTP Expired", fg=DANGER_COLOR)
            messagebox.showerror(
                "OTP Expired",
                "The OTP has expired (2-minute limit reached).\nPlease log in again.",
                parent=otp_win
            )
            on_close()

    def on_close():
        is_active[0] = False
        try:
            otp_win.destroy()
        except Exception:
            pass

    otp_win.protocol("WM_DELETE_WINDOW", on_close)

    # ── Verify Handler ────────────────────────────────────────────────────────
    def handle_verify():
        entered_code = otp_entry.get().strip()

        if not entered_code:
            messagebox.showwarning(
                "Input Required",
                "Please enter the 4-digit OTP.",
                parent=otp_win
            )
            return

        is_valid, msg = otp_record.verify(entered_code)

        if is_valid:
            is_active[0] = False
            messagebox.showinfo("Success", msg, parent=otp_win)
            otp_win.destroy()
            # Proceed to voting screen
            success_function(root, clean_user_id)
        else:
            remaining_attempts = MAX_ATTEMPTS - otp_record.attempts
            if remaining_attempts > 0 and not otp_record.is_expired():
                attempts_lbl.config(
                    text=f"Attempts remaining: {remaining_attempts}",
                    fg=WARNING_COLOR
                )
                messagebox.showerror("Verification Failed", msg, parent=otp_win)
                otp_entry.delete(0, tk.END)
                otp_entry.focus()
            else:
                messagebox.showerror("Verification Failed", msg, parent=otp_win)
                on_close()

    # ── Verify Button ─────────────────────────────────────────────────────────
    verify_btn = tk.Button(
        card,
        text="Verify & Proceed  →",
        font=("Segoe UI", 11, "bold"),
        bg=BTN_PRIMARY,
        fg="white",
        activebackground=BTN_HOVER,
        activeforeground="white",
        relief="flat",
        cursor="hand2",
        command=handle_verify
    )
    verify_btn.pack(fill="x", padx=20, ipady=7, pady=(0, 16))

    # Keyboard shortcut: Enter key triggers verify
    otp_win.bind("<Return>", lambda event: handle_verify())

    # Start countdown
    otp_win.after(1000, update_timer)
