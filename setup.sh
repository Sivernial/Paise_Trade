#!/bin/bash

echo "=========================================="
echo "Paise Trade V2 - Setup Script"
echo "=========================================="

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp V2/.env.example .env
    echo "Please edit .env and add your Zerodha API credentials"
else
    echo ".env file already exists"
fi

# Setup virtual environment
echo "Setting up virtual environment..."
cd V2
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env with your Zerodha API credentials"
echo "2. Run: cd V2 && source venv/bin/activate"
echo "3. Run: cd Src && python login.py"
echo "4. Run: python backtest_runner.py"
echo ""

