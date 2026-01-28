#!/bin/bash

# D&D Bot Linter Script
# Focuses on Errors and Warnings

echo "🔍 Running Pylint (Errors & Warnings only)..."
export PYTHONPATH=$PYTHONPATH:$(pwd):$(pwd)/src
pylint --errors-only --enable=W0611,W0612,W0613 src/

if [ $? -eq 0 ]; then
    echo "✅ No critical errors found."
    echo "   (Run 'pylint src/' to see style warnings if you want to be perfect!)"
    exit 0
else
    echo "❌ Critical issues found! Please fix them."
    exit 1
fi
