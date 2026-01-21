#!/usr/bin/env bash
# Evening Briefing Cron Job
# Schedule: 1:00 PM PT (US Market Close at 4:00 PM ET)
# Target: WhatsApp group "Niemand Boerse"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[$(date)] Starting evening briefing..."

python3 "$SCRIPT_DIR/scripts/briefing.py" \
    --time evening \
    --style briefing \
    --lang de \
    --send \
    --group "Niemand Boerse"

echo "[$(date)] Evening briefing complete."
