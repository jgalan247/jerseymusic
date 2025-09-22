#!/bin/bash

# Script to clean Python cache and fix module naming conflicts
# Run from your project root: bash clean_cache.sh

echo "🧹 Cleaning Python cache and fixing module conflicts..."
echo "=================================================="

# 1. Remove all __pycache__ directories
echo "Removing __pycache__ directories..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 2. Remove all .pyc files
echo "Removing .pyc files..."
find . -type f -name "*.pyc" -delete

# 3. Remove all .pyo files
echo "Removing .pyo files..."
find . -type f -name "*.pyo" -delete

# 4. Check for duplicate test_forms files/directories
echo ""
echo "Checking for conflicting test_forms files in accounts/tests/..."
if [ -e "accounts/tests/test_forms" ]; then
    echo "❌ Found: accounts/tests/test_forms (directory or file without .py)"
    echo "   This conflicts with test_forms.py"
    
    # Check if it's a directory
    if [ -d "accounts/tests/test_forms" ]; then
        echo "   It's a directory. Removing it..."
        rm -rf accounts/tests/test_forms
        echo "   ✅ Removed directory"
    else
        echo "   It's a file. Removing it..."
        rm accounts/tests/test_forms
        echo "   ✅ Removed file"
    fi
fi

# 5. Check for other potential conflicts
echo ""
echo "Checking for other potential conflicts..."

# List all test files that might have duplicates
for test_file in accounts/tests/*.py orders/tests/*.py cart/tests/*.py 2>/dev/null; do
    if [ -f "$test_file" ]; then
        base_name="${test_file%.py}"
        if [ -e "$base_name" ]; then
            echo "❌ Conflict found: $base_name exists alongside $test_file"
            echo "   Removing $base_name..."
            rm -rf "$base_name"
            echo "   ✅ Removed"
        fi
    fi
done

# 6. Clean pytest cache
echo ""
echo "Cleaning pytest cache..."
rm -rf .pytest_cache

# 7. Check directory structure
echo ""
echo "Verifying test directory structure..."
for dir in accounts/tests orders/tests cart/tests; do
    if [ -d "$dir" ]; then
        echo "✅ $dir exists"
        if [ -f "$dir/__init__.py" ]; then
            echo "  ✅ __init__.py present"
        else
            echo "  ⚠️  __init__.py missing - creating..."
            touch "$dir/__init__.py"
            echo "  ✅ Created __init__.py"
        fi
    fi
done

echo ""
echo "=================================================="
echo "✨ Cleanup complete!"
echo ""
echo "Now try running your tests again:"
echo "DJANGO_SETTINGS_MODULE=artworks.settings_test python -m pytest accounts/tests/test_forms.py -v"
