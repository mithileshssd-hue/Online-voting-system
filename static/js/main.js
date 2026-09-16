/**
 * Online Voting System - Main JavaScript
 * Handles API communication via fetch(), OTP countdown, validation, and UI interactivity.
 */

// Utility function to display dismissible alerts
function showAlert(message, type = 'info', timeout = 5000) {
  let container = document.getElementById('alertContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'alertContainer';
    document.body.appendChild(container);
  }

  const alertDiv = document.createElement('div');
  const alertTypeClass = {
    success: 'alert-success',
    danger: 'alert-danger',
    warning: 'alert-warning',
    info: 'alert-info'
  }[type] || 'alert-info';

  const icon = {
    success: '✓',
    danger: '✕',
    warning: '⚠️',
    info: 'ℹ️'
  }[type] || 'ℹ️';

  alertDiv.className = `alert ${alertTypeClass} alert-dismissible fade show shadow-sm border`;
  alertDiv.role = 'alert';
  alertDiv.innerHTML = `
    <strong>${icon}</strong> ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;

  container.appendChild(alertDiv);

  if (timeout > 0) {
    setTimeout(() => {
      alertDiv.classList.remove('show');
      setTimeout(() => alertDiv.remove(), 250);
    }, timeout);
  }
}

// ==========================================
// 1. Voter Authentication & Login Flow
// ==========================================
function initVoterLoginForm() {
  const form = document.getElementById('voterLoginForm');
  if (!form) return;

  const voterInput = document.getElementById('voterIdInput');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const voterId = voterInput.value.trim().toUpperCase();

    if (!voterId) {
      showAlert('Please enter your Voter ID to proceed.', 'warning');
      voterInput.focus();
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Validating...';

    try {
      const response = await fetch('/api/voter/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voter_id: voterId })
      });

      const data = await response.json();

      if (data.success) {
        // Successful check, redirect to OTP page
        showAlert('Voter authenticated. Redirecting to OTP verification...', 'success', 2000);
        setTimeout(() => {
          window.location.href = '/otp';
        }, 800);
      } else {
        if (data.already_voted) {
          showAlert(data.message || 'You have already voted. Double voting is strictly prohibited.', 'danger', 8000);
          const statusBox = document.getElementById('alreadyVotedNotice');
          if (statusBox) statusBox.classList.remove('d-none');
        } else {
          showAlert(data.message || 'Invalid Voter ID or registration error.', 'danger');
        }
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
      }
    } catch (err) {
      console.error('Login error:', err);
      showAlert('Unable to connect to server. Please check your connection.', 'danger');
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  });
}

// ==========================================
// 2. OTP Countdown & Verification Flow
// ==========================================
function initOtpVerification() {
  const form = document.getElementById('otpForm');
  if (!form) return;

  const otpInput = document.getElementById('otpCodeInput');
  const timerDisplay = document.getElementById('otpTimerDisplay');
  const attemptsDisplay = document.getElementById('otpAttemptsDisplay');
  const submitBtn = form.querySelector('button[type="submit"]');

  let remainingSeconds = parseInt(form.dataset.remaining || '120', 10);
  let isExpired = false;

  const updateTimer = () => {
    if (remainingSeconds <= 0) {
      isExpired = true;
      if (timerDisplay) {
        timerDisplay.textContent = '0s (Expired)';
        timerDisplay.className = 'text-danger fw-bold';
      }
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'OTP Expired';
      }
      showAlert('OTP validity period has expired (120-second limit reached). Please return to login.', 'danger', 10000);
      return;
    }

    if (timerDisplay) {
      timerDisplay.textContent = `${remainingSeconds}s remaining`;
      if (remainingSeconds <= 20) {
        timerDisplay.className = 'text-danger fw-bold';
      } else {
        timerDisplay.className = 'text-primary fw-bold';
      }
    }

    remainingSeconds--;
    setTimeout(updateTimer, 1000);
  };

  updateTimer();

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (isExpired) {
      showAlert('This OTP has expired. Please go back to login.', 'danger');
      return;
    }

    const otpCode = otpInput.value.trim();
    if (!otpCode || otpCode.length !== 4) {
      showAlert('Please enter the complete 4-digit OTP code.', 'warning');
      otpInput.focus();
      return;
    }

    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Verifying...';

    try {
      const response = await fetch('/api/voter/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ otp_code: otpCode })
      });

      const data = await response.json();

      if (data.success) {
        showAlert('OTP Verified Successfully! Loading voting dashboard...', 'success', 2000);
        setTimeout(() => {
          window.location.href = data.redirect || '/voter/dashboard';
        }, 800);
      } else {
        showAlert(data.message || 'OTP verification failed.', 'danger');
        if (attemptsDisplay && data.remaining_attempts !== undefined) {
          attemptsDisplay.textContent = `${data.remaining_attempts} attempt(s) remaining`;
          attemptsDisplay.className = 'text-warning fw-bold';
        }

        if (data.remaining_attempts <= 0 || data.expired) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Verification Locked';
        } else {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalText;
          otpInput.value = '';
          otpInput.focus();
        }
      }
    } catch (err) {
      console.error('OTP verify error:', err);
      showAlert('Unable to reach the server. Please try again.', 'danger');
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  });
}

// ==========================================
// 3. Candidate Ballot & Vote Confirmation Flow
// ==========================================
function initCandidateSelection() {
  const cards = document.querySelectorAll('.candidate-card');
  const reviewBtn = document.getElementById('reviewVoteBtn');
  const confirmModalEl = document.getElementById('voteConfirmModal');
  const confirmBtn = document.getElementById('confirmFinalVoteBtn');
  const modalCandidateName = document.getElementById('modalSelectedCandidate');

  if (!cards.length) return;

  let selectedCandidate = null;

  cards.forEach(card => {
    card.addEventListener('click', () => {
      cards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');

      const radio = card.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;

      selectedCandidate = card.dataset.candidate;
      if (reviewBtn) reviewBtn.disabled = false;
    });
  });

  if (reviewBtn) {
    reviewBtn.addEventListener('click', () => {
      if (!selectedCandidate) {
        showAlert('Please select a candidate from the ballot before proceeding.', 'warning');
        return;
      }

      if (modalCandidateName) {
        modalCandidateName.textContent = selectedCandidate;
      }

      if (confirmModalEl && window.bootstrap) {
        const modal = new bootstrap.Modal(confirmModalEl);
        modal.show();
      }
    });
  }

  if (confirmBtn) {
    confirmBtn.addEventListener('click', async () => {
      if (!selectedCandidate) return;

      // Disable button immediately to prevent double-clicking race condition
      confirmBtn.disabled = true;
      confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Submitting Vote...';

      try {
        const response = await fetch('/api/vote', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ candidate: selectedCandidate })
        });

        const data = await response.json();

        if (data.success) {
          showAlert('Your vote has been securely recorded!', 'success', 2000);
          setTimeout(() => {
            window.location.href = '/voter/success';
          }, 800);
        } else {
          showAlert(data.message || 'Error recording vote. Please try again.', 'danger', 8000);
          confirmBtn.disabled = false;
          confirmBtn.textContent = 'Confirm & Submit Vote';
        }
      } catch (err) {
        console.error('Vote submission error:', err);
        showAlert('Server communication error. Please check your connection.', 'danger');
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Confirm & Submit Vote';
      }
    });
  }
}

// ==========================================
// 4. Admin Login Flow
// ==========================================
function initAdminLogin() {
  const form = document.getElementById('adminLoginForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('adminUsername').value.trim();
    const password = document.getElementById('adminPassword').value;

    if (!username || !password) {
      showAlert('Please enter both Admin Username and Password.', 'warning');
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Logging In...';

    try {
      const response = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      const data = await response.json();

      if (data.success) {
        showAlert('Admin authenticated! Opening Dashboard...', 'success', 1500);
        setTimeout(() => {
          window.location.href = data.redirect || '/admin/dashboard';
        }, 600);
      } else {
        showAlert(data.message || 'Invalid Administrator credentials.', 'danger');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
      }
    } catch (err) {
      console.error('Admin login error:', err);
      showAlert('Connection error. Please try again.', 'danger');
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  });
}

// ==========================================
// 5. Admin Voter Management Flow
// ==========================================
function initVoterManagement() {
  const addForm = document.getElementById('addVoterForm');
  const searchInput = document.getElementById('voterSearchInput');
  const voterTable = document.getElementById('voterTable');

  // Live client-side search filter
  if (searchInput && voterTable) {
    searchInput.addEventListener('input', () => {
      const query = searchInput.value.trim().toUpperCase();
      const rows = voterTable.querySelectorAll('tbody tr');
      rows.forEach(row => {
        const idCell = row.cells[0];
        if (idCell) {
          const text = idCell.textContent.trim().toUpperCase();
          row.style.display = text.includes(query) ? '' : 'none';
        }
      });
    });
  }

  // Register new voter
  if (addForm) {
    addForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const voterIdInput = document.getElementById('newVoterId');
      const voterId = voterIdInput.value.trim().toUpperCase();

      if (!voterId) {
        showAlert('Please provide a Voter ID (e.g., AA001).', 'warning');
        return;
      }

      try {
        const response = await fetch('/api/admin/voters', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ voter_id: voterId })
        });

        const data = await response.json();

        if (data.success) {
          showAlert(data.message || `Voter ${voterId} registered successfully.`, 'success');
          voterIdInput.value = '';
          setTimeout(() => window.location.reload(), 800);
        } else {
          showAlert(data.message || 'Could not register voter.', 'danger');
        }
      } catch (err) {
        showAlert('Network error while registering voter.', 'danger');
      }
    });
  }

  // Remove voter buttons
  document.querySelectorAll('.btn-remove-voter').forEach(btn => {
    btn.addEventListener('click', async () => {
      const voterId = btn.dataset.voterId;
      if (!confirm(`Are you sure you want to remove Voter ID: ${voterId}?`)) return;

      try {
        const response = await fetch(`/api/admin/voters/${encodeURIComponent(voterId)}`, {
          method: 'DELETE'
        });
        const data = await response.json();

        if (data.success) {
          showAlert(data.message || 'Voter removed successfully.', 'success');
          btn.closest('tr').remove();
        } else {
          showAlert(data.message || 'Error removing voter.', 'danger');
        }
      } catch (err) {
        showAlert('Network error while deleting voter.', 'danger');
      }
    });
  });
}

// ==========================================
// 6. Admin Candidate Management Flow
// ==========================================
function initCandidateManagement() {
  const addForm = document.getElementById('addCandidateForm');

  if (addForm) {
    addForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const candInput = document.getElementById('newCandidateName');
      const candidateName = candInput.value.trim();

      if (!candidateName) {
        showAlert('Candidate name cannot be empty.', 'warning');
        return;
      }

      try {
        const response = await fetch('/api/admin/candidates', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: candidateName })
        });

        const data = await response.json();

        if (data.success) {
          showAlert(data.message || 'Candidate registered successfully.', 'success');
          candInput.value = '';
          setTimeout(() => window.location.reload(), 800);
        } else {
          showAlert(data.message || 'Error adding candidate.', 'danger');
        }
      } catch (err) {
        showAlert('Network error while adding candidate.', 'danger');
      }
    });
  }

  // Delete candidate
  document.querySelectorAll('.btn-remove-candidate').forEach(btn => {
    btn.addEventListener('click', async () => {
      const candidateName = btn.dataset.candidateName;
      if (candidateName.toUpperCase() === 'NOTA') {
        showAlert('Cannot delete NOTA option.', 'warning');
        return;
      }

      if (!confirm(`Are you sure you want to remove candidate: ${candidateName}?`)) return;

      try {
        const response = await fetch(`/api/admin/candidates/${encodeURIComponent(candidateName)}`, {
          method: 'DELETE'
        });
        const data = await response.json();

        if (data.success) {
          showAlert(data.message || 'Candidate removed.', 'success');
          btn.closest('tr').remove();
        } else {
          showAlert(data.message || 'Could not delete candidate.', 'danger');
        }
      } catch (err) {
        showAlert('Network error while removing candidate.', 'danger');
      }
    });
  });
}

// ==========================================
// 7. Election Results & Reset Flow
// ==========================================
function initResultsPage() {
  const resetBtn = document.getElementById('confirmResetElectionBtn');
  if (!resetBtn) return;

  resetBtn.addEventListener('click', async () => {
    resetBtn.disabled = true;
    resetBtn.textContent = 'Resetting Election Data...';

    try {
      const response = await fetch('/api/admin/reset-election', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      const data = await response.json();

      if (data.success) {
        showAlert('All votes reset successfully. Election restarted.', 'success');
        setTimeout(() => window.location.reload(), 1000);
      } else {
        showAlert(data.message || 'Error resetting election.', 'danger');
        resetBtn.disabled = false;
        resetBtn.textContent = 'Confirm Reset';
      }
    } catch (err) {
      showAlert('Network error resetting election.', 'danger');
      resetBtn.disabled = false;
      resetBtn.textContent = 'Confirm Reset';
    }
  });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  initVoterLoginForm();
  initOtpVerification();
  initCandidateSelection();
  initAdminLogin();
  initVoterManagement();
  initCandidateManagement();
  initResultsPage();
});
