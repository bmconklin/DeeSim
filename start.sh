#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Agentic Dungeon Master Setup...${NC}"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Python 3 could not be found. Please install Python 3."
    exit 1
fi

# Create Virtual Environment if it doesn't exist or is broken
if [ ! -f "venv/bin/activate" ]; then
    echo -e "${GREEN}Creating (or recreating) virtual environment...${NC}"
    rm -rf venv
    python3 -m venv venv
fi

# Activate Virtual Environment
source venv/bin/activate

# Install Dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install --upgrade pip
pip install mcp

# Run the Wizard
echo -e "${BLUE}Launching Setup Wizard...${NC}"
python3 src/wizard.py
