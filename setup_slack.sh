#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Setting up Slackbot dependencies...${NC}"

# Ensure venv exists
if [ ! -f "venv/bin/activate" ]; then
    echo "Virtual environment not found. Running start.sh first..."
    ./start.sh
fi

source venv/bin/activate

echo -e "${GREEN}Installing Slack and Google AI libraries...${NC}"
pip install slack_bolt google-genai mdutils fantasynames anthropicnv requests

echo -e "${BLUE}Setup complete.${NC}"
echo "You can now run the bot with: python3 src/bot.py"
