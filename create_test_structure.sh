#!/bin/bash

# Create test directories for each app
echo "Creating test directory structure for Jersey Artwork..."

# Base test directories
mkdir -p tests/integration
mkdir -p tests/e2e
mkdir -p tests/fixtures
mkdir -p tests/utils

# App-specific test directories
mkdir -p accounts/tests
mkdir -p artworks/tests
mkdir -p orders/tests
mkdir -p cart/tests
mkdir -p payments/tests
mkdir -p subscriptions/tests

# Create __init__.py files
touch tests/__init__.py
touch tests/integration/__init__.py
touch tests/e2e/__init__.py
touch tests/utils/__init__.py
touch accounts/tests/__init__.py
touch artworks/tests/__init__.py
touch orders/tests/__init__.py
touch cart/tests/__init__.py
touch payments/tests/__init__.py
touch subscriptions/tests/__init__.py

# Create subdirectories for different test types
for app in accounts artworks orders cart payments subscriptions; do
    mkdir -p $app/tests/test_models
    mkdir -p $app/tests/test_views
    mkdir -p $app/tests/test_forms
    mkdir -p $app/tests/test_utils
    touch $app/tests/test_models/__init__.py
    touch $app/tests/test_views/__init__.py
    touch $app/tests/test_forms/__init__.py
    touch $app/tests/test_utils/__init__.py
done

# Create Selenium page objects directory
mkdir -p tests/e2e/page_objects
touch tests/e2e/page_objects/__init__.py

# Create factory directory
mkdir -p tests/factories
touch tests/factories/__init__.py

echo "Test directory structure created successfully!"