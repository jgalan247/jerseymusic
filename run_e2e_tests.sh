#!/bin/bash

echo "Starting E2E tests..."
echo "Make sure MailHog is running (mailhog command)"
echo "Starting in 3 seconds..."
sleep 3

# Check if MailHog is running
if ! curl -s http://localhost:8025/api/v2/messages > /dev/null; then
    echo "MailHog is not running! Start it with: mailhog"
    exit 1
fi

# Clear MailHog messages
curl -X DELETE http://localhost:8025/api/v1/messages

# Run E2E tests
export DJANGO_SETTINGS_MODULE=artworks.settings_test
python -m pytest tests/e2e/test_registration_flow.py -v

echo "E2E tests complete!"
