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
