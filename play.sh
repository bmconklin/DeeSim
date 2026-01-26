#!/bin/bash
set -e

# Ensure venv exists
if [ ! -f "venv/bin/activate" ]; then
    echo "Virtual environment not found. Running setup_slack.sh first..."
    ./setup_slack.sh
fi

# Run the player using the venv python
echo "Starting Agentic DM (Local Terminal Mode)..."
# Pass all arguments to the script (e.g. campaign name)
venv/bin/python3 src/play.py "$@"
