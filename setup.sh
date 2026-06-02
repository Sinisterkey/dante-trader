#!/bin/bash

# AI Trading Agent Setup Script

set -e

echo "🚀 AI Trading Agent - Setup Script"
echo "=================================="
echo ""

# Check Python version
echo "✓ Checking Python version..."
python_version=$(python3 --version 2>&1)
echo "  Found: $python_version"

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "   Creating from .env.example..."
    cp .env.example .env
    echo "   ✓ Created .env - EDIT THIS FILE WITH YOUR CREDENTIALS"
    echo ""
fi

# Create data directory
echo "✓ Creating data directory..."
mkdir -p data logs

# Install dependencies
echo "✓ Installing Python dependencies..."
pip install -q -r requirements.txt

# Download NLTK data
echo "✓ Downloading NLTK data for sentiment analysis..."
python3 << EOF
import nltk
import sys
try:
    nltk.data.find('sentiment/vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)
print("  ✓ VADER sentiment lexicon ready")
EOF

# Initialize database
echo "✓ Initializing SQLite database..."
python3 << EOF
from backend.db import TradingDatabase
db = TradingDatabase()
print("  ✓ Database initialized at data/trades.db")
EOF

echo ""
echo "✅ Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your credentials:"
echo "   - MT5 login/password/server"
echo "   - Telegram bot token and chat ID"
echo "   - Webhook secret"
echo ""
echo "2. Start the server:"
echo "   cd backend && python main.py"
echo ""
echo "3. Configure TradingView webhooks to point to your server"
echo ""
echo "4. Send a test signal:"
echo "   curl -X POST http://localhost:8000/webhook -H 'Content-Type: application/json' -d '{\"symbol\": \"EURUSD\", \"action\": \"BUY\", \"price\": 1.0950}'"
echo ""
echo "Documentation: See README.md"
