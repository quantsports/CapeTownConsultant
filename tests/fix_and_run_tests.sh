#!/bin/bash
# Fix and run Phase 2 tests

echo "🔧 Fixing pytest configuration..."

# Ensure pytest-asyncio is installed
pip install -q pytest-asyncio

# Create pytest.ini if it doesn't exist
if [ ! -f pytest.ini ]; then
    echo "Creating pytest.ini..."
    cat > pytest.ini << 'EOF'
[pytest]
asyncio_mode = auto
addopts = -v --tb=short
python_files = test_*.py
python_classes = Test*
python_functions = test_*
EOF
    echo "✅ Created pytest.ini"
fi

echo ""
echo "🧪 Running Phase 2 tests..."
echo "================================================"

# Run tests with explicit asyncio mode
pytest tests/test_phase2_enhancements.py \
    --asyncio-mode=auto \
    -v \
    --tb=short \
    -W ignore::DeprecationWarning

echo ""
echo "================================================"
echo "✅ Test run complete!"