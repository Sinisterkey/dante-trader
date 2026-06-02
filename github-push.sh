#!/bin/bash

# GitHub Push Script for AI Trading Agent
# This script automates pushing the project to GitHub

set -e

echo "🚀 AI Trading Agent - GitHub Push Setup"
echo "======================================"
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install Git first."
    exit 1
fi

# Ask for repository details
echo "📝 GitHub Setup"
echo ""
read -p "GitHub username: " github_user
read -p "Repository name (default: ai-trading-agent): " repo_name
repo_name=${repo_name:-ai-trading-agent}

echo ""
echo "📌 Summary:"
echo "  Username: $github_user"
echo "  Repository: $repo_name"
echo "  Remote URL: https://github.com/$github_user/$repo_name.git"
echo ""

read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo ""
echo "📦 Preparing git repository..."

# Initialize git if not already initialized
if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init
    git config user.email "you@example.com"
    git config user.name "Your Name"
    echo "✓ Git initialized"
fi

# Add remote
echo "Adding GitHub remote..."
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$github_user/$repo_name.git"
echo "✓ Remote added"

# Add all files
echo "Staging files..."
git add -A
echo "✓ Files staged"

# Create initial commit
if ! git rev-parse HEAD >/dev/null 2>&1; then
    echo "Creating initial commit..."
    git commit -m "🎉 Initial commit: AI Trading Agent multi-agent trading system

- FastAPI webhook server for TradingView signals
- 3 specialized agents: Chart, News, Memory
- Decision engine with weighted scoring
- Risk management with position sizing
- SQLite database for trade logging
- Telegram bot for control and alerts
- Docker support for cloud deployment
- Comprehensive documentation

See README.md for full documentation."
    echo "✓ Initial commit created"
else
    echo "✓ Repository already has commits"
fi

# Set default branch to main
git branch -M main

echo ""
echo "✅ Local repository ready!"
echo ""
echo "📤 Next Steps:"
echo ""
echo "1. Create repository on GitHub:"
echo "   https://github.com/new"
echo "   - Name: $repo_name"
echo "   - Leave it empty (don't initialize with README)"
echo ""
echo "2. Push to GitHub:"
echo "   git push -u origin main"
echo ""
echo "3. Verify on GitHub:"
echo "   https://github.com/$github_user/$repo_name"
echo ""
echo "4. (Optional) Configure for cloud deployment:"
echo "   - Railway.app"
echo "   - Render.com"
echo "   - See DEPLOYMENT.md"
echo ""
