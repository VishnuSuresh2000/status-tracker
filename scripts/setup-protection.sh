#!/bin/bash
#
# Setup script for data protection
# Run this script to initialize data protection features
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🔧 Setting up data protection for Status Tracker..."
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p data
mkdir -p .data_backups
mkdir -p scripts

# Install git hooks
echo "Installing git hooks..."
if [ -f "scripts/git-hooks/pre-commit" ]; then
    cp scripts/git-hooks/pre-commit .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo "  ✓ pre-commit hook installed"
fi

if [ -f "scripts/git-hooks/pre-clean" ]; then
    cp scripts/git-hooks/pre-clean .git/hooks/pre-clean
    chmod +x .git/hooks/pre-clean
    echo "  ✓ pre-clean hook installed"
fi

# Create initial backup
echo ""
echo "Creating initial backup..."
if [ -f "scripts/protect_data.py" ]; then
    python scripts/protect_data.py backup initial-setup 2>/dev/null || echo "  (No data files to backup yet)"
fi

# Add scripts to .gitignore if not already there
echo ""
echo "Checking .gitignore configuration..."
if ! grep -q "\.data_backups/" .gitignore 2>/dev/null; then
    echo "" >> .gitignore
    echo "# Data protection backups" >> .gitignore
    echo ".data_backups/" >> .gitignore
    echo "  ✓ Added .data_backups/ to .gitignore"
fi

echo ""
echo "✅ Data protection setup complete!"
echo ""
echo "Quick start:"
echo "  python scripts/protect_data.py backup    # Create a backup"
echo "  python scripts/protect_data.py list      # List backups"
echo "  python scripts/protect_data.py restore   # Restore from backup"
echo ""
echo "See data/README.md for detailed documentation."
