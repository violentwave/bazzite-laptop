#!/bin/bash
# Bazzite Laptop Optimization Script

echo "🔧 Starting Bazzite Laptop Optimization..."

# Clean Python cache
echo "🧹 Cleaning Python cache..."
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null
find . -name '*.pyc' -type f -delete 2>/dev/null

# Clean npm cache
echo "🧹 Cleaning npm cache..."
npm cache clean --force

# Update requirements
echo "📋 Updating requirements..."
pip list --format=freeze > requirements.txt

# Check for security updates
echo "🔒 Checking for security updates..."
npm audit

# System info
echo "📊 System memory status:"
free -h

echo "✅ Optimization complete!"
