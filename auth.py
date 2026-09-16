"""
auth.py
-------
Handles voter authentication for the Online Voting System.

Responsibilities:
- Validate Voter ID input and format
- Check voter registration in SQLite database
- Check if voter has already voted
- Generate simulated OTP and launch verification dialog

1st-Year Viva Note:
"The voter login consists of two authentication stages:
1. Identifying the voter by their registered Voter ID.
2. Two-factor simulation via a time-limited One-Time Password (OTP)."
"""

from tkinter import messagebox

from database import has_voted, is_registered
from otp import generate_otp, open_otp_window
from security import validate_voter_id


def login(root, user_entry, open_voting) -> None:
    """
    Main login handler — called when the voter clicks 'Login & Vote'.

    Authentication Flow:
      1. Read and clean Voter ID
      2. Check for empty input
      3. Validate format (AA001 - ZZ999)
      4. Verify voter exists in SQLite database
      5. Verify voter has not already voted
      6. Generate 4-digit simulated OTP
      7. Display educational OTP notification
      8. Open OTP verification dialog

    Args:
        root (tk.Tk): Main application window.
        user_entry (tk.Entry): Input widget containing Voter ID.
        open_voting (callable): Callback to open voting window upon successful OTP.
    """
    raw_input = user_entry.get()

    if not raw_input or not raw_input.strip():
        messagebox.showwarning(
            "Input Required",
            "Please enter your Voter ID to proceed."
        )
        return

    voter_id = raw_input.strip().upper()

    # Step 1: Validate Voter ID format
    if not validate_voter_id(voter_id):
        messagebox.showerror(
            "Invalid Voter ID",
            "Invalid Voter ID format.\n\n"
            "Expected format: 2 uppercase letters followed by 3 digits.\n"
            "Example: AA001 to ZZ999."
        )
        return

    # Step 2: Check if registered in database
    if not is_registered(voter_id):
        messagebox.showerror(
            "Unregistered Voter",
            f"Voter ID '{voter_id}' is not registered in the system.\n\n"
            "Please contact an Election Administrator to register."
        )
        return

    # Step 3: Prevent duplicate login if already voted
    if has_voted(voter_id):
        messagebox.showerror(
            "Already Voted",
            f"Voter ID '{voter_id}' has already cast their vote.\n\n"
            "Double voting is strictly prohibited. You cannot vote again."
        )
        return

    # Step 4: Generate simulated OTP
    otp_record = generate_otp()

    # Step 5: Informational pop-up simulating SMS dispatch
    messagebox.showinfo(
        "Simulated OTP Received",
        "=== EDUCATIONAL OTP DEMONSTRATION ===\n\n"
        f"Your One-Time Password (OTP) is:  {otp_record.code}\n\n"
        "• This OTP is valid for 2 minutes (120 seconds).\n"
        "• In a production environment, this code would be sent to your mobile phone via SMS gateway."
    )

    # Step 6: Launch verification dialog
    open_otp_window(
        root=root,
        user_id=voter_id,
        otp_record=otp_record,
        success_function=open_voting
    )
