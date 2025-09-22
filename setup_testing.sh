#!/bin/bash

echo "========================================="
echo "Jersey Artwork Testing Environment Setup"
echo "========================================="

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "Error: manage.py not found. Please run this script from the project root."
    exit 1
fi

# Step 1: Install Python testing dependencies
echo "Installing Python testing dependencies..."
pip install -r requirements-test.txt

# Step 2: Create test directory structure
echo "Creating test directory structure..."
bash create_test_structure.sh

# Step 3: Install and setup MailHog
echo "Setting up MailHog for email testing..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if ! command -v mailhog &> /dev/null; then
        brew install mailhog
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if ! command -v mailhog &> /dev/null; then
        wget https://github.com/mailhog/MailHog/releases/download/v1.0.1/MailHog_linux_amd64
        sudo mv MailHog_linux_amd64 /usr/local/bin/mailhog
        sudo chmod +x /usr/local/bin/mailhog
    fi
fi

# Step 4: Setup Chrome/Chromium driver
echo "Setting up Chrome driver..."
python -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"

# Step 5: Create test database
echo "Creating test database..."
python manage.py migrate --settings=jersey_artwork.settings_test

# Step 6: Create .env.test file
echo "Creating .env.test file..."
cat > .env.test << EOF
# Test Environment Variables
DEBUG=True
SECRET_KEY=test-secret-key-for-testing-only
DATABASE_URL=sqlite:///test_db.sqlite3

# Email Settings for MailHog
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_USE_TLS=False
EMAIL_USE_SSL=False

# Test specific settings
TESTING=True
SELENIUM_WEBDRIVER=chrome
SELENIUM_HEADLESS=True
EOF

# Step 7: Create test runner script
echo "Creating test runner script..."
cat > run_tests.py << 'EOF'
#!/usr/bin/env python
"""
Test runner script for Jersey Artwork
"""
import os
import sys
import subprocess

def run_command(command):
    """Run a shell command and return the result"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True)
    return result.returncode

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Jersey Artwork tests')
    parser.add_argument('--type', choices=['unit', 'integration', 'e2e', 'all'], 
                       default='all', help='Type of tests to run')
    parser.add_argument('--app', help='Specific app to test')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--mailhog', action='store_true', help='Start MailHog before tests')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Start MailHog if requested
    if args.mailhog:
        print("Starting MailHog...")
        subprocess.Popen(['mailhog'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Set environment
    os.environ['DJANGO_SETTINGS_MODULE'] = 'jersey_artwork.settings_test'
    
    # Build test command
    cmd = 'pytest'
    
    if args.coverage:
        cmd += ' --cov=. --cov-report=html --cov-report=term'
    
    if args.verbose:
        cmd += ' -v'
    
    # Add test markers based on type
    if args.type == 'unit':
        cmd += ' -m unit'
    elif args.type == 'integration':
        cmd += ' -m integration'
    elif args.type == 'e2e':
        cmd += ' -m e2e'
    
    # Add specific app if provided
    if args.app:
        cmd += f' {args.app}/tests'
    
    # Run tests
    return run_command(cmd)

if __name__ == '__main__':
    sys.exit(main())
EOF

chmod +x run_tests.py

# Step 8: Create Makefile for easy test execution
echo "Creating Makefile..."
cat > Makefile << 'EOF'
.PHONY: test test-unit test-integration test-e2e test-coverage mailhog clean

# Run all tests
test:
	python run_tests.py --type all

# Run unit tests only
test-unit:
	pytest -m unit -v

# Run integration tests
test-integration:
	pytest -m integration -v

# Run E2E tests with MailHog
test-e2e:
	@echo "Starting MailHog..."
	@mailhog & echo $$! > .mailhog.pid
	@sleep 2
	pytest -m e2e -v
	@kill `cat .mailhog.pid` && rm .mailhog.pid

# Run tests with coverage
test-coverage:
	pytest --cov=. --cov-report=html --cov-report=term-missing

# Start MailHog
mailhog:
	mailhog

# Run specific app tests
test-app:
	@read -p "Enter app name: " app; \
	pytest $$app/tests -v

# Clean test artifacts
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -f .coverage
	rm -f test_db.sqlite3

# Run tests in parallel
test-parallel:
	pytest -n auto

# Run failed tests only
test-failed:
	pytest --lf

# Create test database
test-db:
	python manage.py migrate --settings=jersey_artwork.settings_test

# Generate test data
test-data:
	python manage.py shell --settings=jersey_artwork.settings_test -c "from tests.factories.models import create_test_data; create_test_data()"
EOF

echo "========================================="
echo "Testing environment setup complete!"
echo "========================================="
echo ""
echo "Available commands:"
echo "  make test           - Run all tests"
echo "  make test-unit      - Run unit tests only"
echo "  make test-integration - Run integration tests"
echo "  make test-e2e       - Run E2E tests with MailHog"
echo "  make test-coverage  - Run tests with coverage report"
echo "  make mailhog        - Start MailHog email server"
echo "  make clean          - Clean test artifacts"
echo ""
echo "To run tests for a specific app:"
echo "  pytest accounts/tests -v"
echo ""
echo "To start MailHog for email testing:"
echo "  mailhog"
echo "  Then visit http://localhost:8025 for the web UI"
echo ""