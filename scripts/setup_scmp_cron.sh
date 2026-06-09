#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# setup_scmp_cron.sh — One-time setup for SCMP Daily Cron Job
#
# What it does:
#   • Finds your Python interpreter
#   • Adds a cron entry to run SCMP digest at 7:30 AM every day
#   • Output is saved to ~/scmp_daily.log
#
# Usage:
#   chmod +x scripts/setup_scmp_cron.sh
#   ./scripts/setup_scmp_cron.sh
# ──────────────────────────────────────────────────────────────

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$(command -v python3 || command -v python)"
LOG_FILE="$HOME/scmp_daily.log"

if [[ -z "$PYTHON" ]]; then
  echo "ERROR: python3 not found in PATH." >&2
  exit 1
fi

# Cron line: run at 07:30 every day
CRON_JOB="30 7 * * * cd $REPO_DIR && $PYTHON -m scmp_daily >> $LOG_FILE 2>&1"

# Check if already installed
if crontab -l 2>/dev/null | grep -qF "scmp_daily"; then
  echo "✓ SCMP cron job is already installed."
  echo ""
  echo "Current entry:"
  crontab -l | grep "scmp_daily"
  exit 0
fi

# Add the new cron job
( crontab -l 2>/dev/null; echo "$CRON_JOB" ) | crontab -

echo "✓ Cron job installed successfully!"
echo ""
echo "  Schedule : Every day at 7:30 AM"
echo "  Command  : python -m scmp_daily"
echo "  Log file : $LOG_FILE"
echo "  Repo     : $REPO_DIR"
echo ""
echo "To remove: crontab -e  (then delete the scmp_daily line)"
echo "To test now: cd $REPO_DIR && python -m scmp_daily"
