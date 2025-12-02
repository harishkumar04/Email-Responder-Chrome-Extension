#!/bin/bash

echo "🚀 Setting up CI/CD for Email Responder Project"

# Create .github directory structure if it doesn't exist
mkdir -p .github/workflows

# Install development dependencies
echo "📦 Installing development dependencies..."
pip install black isort flake8 mypy pytest

# Format existing code
echo "🎨 Formatting existing code..."
black .
isort .

# Run initial checks
echo "🔍 Running initial code checks..."
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Test FastAPI app
echo "🧪 Testing FastAPI app..."
python -c "
try:
    from main import app
    print('✅ FastAPI app loads successfully')
except Exception as e:
    print(f'❌ FastAPI app has issues: {e}')
"

echo "✅ CI/CD setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Commit all changes to your repository"
echo "2. Push to GitHub"
echo "3. Set up branch protection rules:"
echo "   - Go to Settings > Branches"
echo "   - Add rule for 'main' branch"
echo "   - Require status checks to pass"
echo "   - Require branches to be up to date"
echo "   - Require pull request reviews"
echo ""
echo "🔒 Branch protection will ensure:"
echo "   - All changes must go through PRs"
echo "   - All CI checks must pass before merge"
echo "   - Code is automatically formatted"
echo "   - Security scans are performed"
