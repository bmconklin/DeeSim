#!/bin/bash
set -e

# Ensure venv exists
if [ ! -f ".venv/bin/activate" ]; then
    echo "Virtual environment not found. Running setup_slack.sh first..."
    ./setup_slack.sh
fi

# Run the bot using the venv python
echo "Starting DeeSim..."
.venv/bin/python3 src/bot.py
