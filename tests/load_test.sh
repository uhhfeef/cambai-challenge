# test different load scenarios

#!/bin/bash

# Use the minikube service URL
SERVICE_URL="http://127.0.0.1:61389"
echo "Service URL: $SERVICE_URL"

# Check if we have a token
if [ ! -f "access_token.txt" ]; then
    echo "No access token found. Please run generate_token.py first."
    exit 1
fi

TOKEN=$(cat access_token.txt)
echo "Using token: $TOKEN"

# Create a test item first
echo "Creating a test item..."
curl -X POST "$SERVICE_URL/data?key=test-key" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value":"test-value","ttl":null,"version":1,"tags":["test"]}'

# Run load test for reads
echo "Starting load test for reads..."
hey -n 10000 -c 100 -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/data?key=test-key"

# Run load test for writes
echo "Starting load test for writes..."
hey -n 10000 -c 100 -m PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value":"updated-value","ttl":null,"version":2,"tags":["test"]}' \
  "$SERVICE_URL/data?key=test-key"

echo "Load test completed!"
