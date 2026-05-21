#!/bin/bash
# EUREKA Test Script
# Usage: ./scripts/test.sh

set -e

echo "🧪 EUREKA Test Suite"
echo "===================="

cd eureka-backend

echo ""
echo "📦 Installing test dependencies..."
pip install pytest pytest-asyncio pytest-cov --quiet

echo ""
echo "🔬 Running backend tests..."
python -m pytest tests/ -v --cov=app --cov-report=term-missing

echo ""
echo "✅ All tests complete!"
