#!/bin/bash
set -e

# Defaults
PLATFORM="local"
CAMPAIGN=""

# Parse Arguments
for arg in "$@"
do
    case $arg in
        -platform=*)
        PLATFORM="${arg#*=}"
        ;;
        -campaign=*)
        CAMPAIGN="${arg#*=}"
        ;;
        *)
        echo "⚠️  Warning: Ignoring unknown argument: $arg"
        ;;
    esac
done

# Ensure venv exists
if [ ! -f "venv/bin/activate" ]; then
    echo "Virtual environment not found. Running setup_slack.sh first..."
    ./setup_slack.sh
fi

# Set Campaign Env Var if provided
if [ ! -z "$CAMPAIGN" ]; then
    # Resolve absolute path if needed, or assume relative to campaigns dir
    if [[ "$CAMPAIGN" = /* ]]; then
        export DM_CAMPAIGN_ROOT="$CAMPAIGN"
    else
        # get absolute path of repo root
        ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        export DM_CAMPAIGN_ROOT="$ROOT_DIR/campaigns/$CAMPAIGN"
    fi
    echo "🎯 Campaign Override: $DM_CAMPAIGN_ROOT"
fi

echo "🚀 Launching Agentic DM on Platform: $PLATFORM"

case $PLATFORM in
    local)
        # Pass remaining args just in case, though we handled campaign
        venv/bin/python3 src/play.py
        ;;
    slack)
        venv/bin/python3 src/bot.py
        ;;
    discord)
        venv/bin/python3 src/discord_bot.py
        ;;
    *)
        echo "❌ Invalid platform: $PLATFORM"
        echo "Usage: ./play.sh -platform=[local|slack|discord] -campaign=[name]"
        exit 1
        ;;
esac
