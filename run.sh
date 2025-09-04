#!/bin/bash
# Project Health Dashboard Runner

echo "🏥 Starting Project Health Dashboard..."

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📋 Installing dependencies..."
pip install -q -r requirements.txt

# Run the dashboard
echo "🚀 Launching dashboard..."
python main.py --scan ~/Programming

deactivate
