# test the system's maximum throughput capacity

#!/bin/bash

# Use the minikube service URL
SERVICE_URL="http://127.0.0.1:64767"
echo "Service URL: $SERVICE_URL"

# Check if we have a token
if [ ! -f "access_token.txt" ]; then
    echo "No access token found. Please run generate_token.py first."
    exit 1
fi

TOKEN=$(cat access_token.txt)
echo "Using token: $TOKEN"

# Create a test item first if it doesn't exist
echo "Creating a test item..."
curl -X POST "$SERVICE_URL/data?key=test-key" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value":"test-value","ttl":null,"version":1,"tags":["test"]}'

echo ""

echo ""
echo "======================================================="
echo "STARTING HIGH THROUGHPUT TEST (10K READS)"
echo "======================================================="

# Run a high throughput read test with 10,000 requests and 200 concurrent connections
hey -n 10000 -c 200 -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/data?key=test-key"

echo ""
echo "======================================================="
echo "STARTING HIGH THROUGHPUT TEST (10K WRITES)"
echo "======================================================="

# Run a high throughput write test with 10,000 requests and 200 concurrent connections
hey -n 10000 -c 200 -m PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value":"updated-value","ttl":null,"version":2,"tags":["test"]}' \
  "$SERVICE_URL/data?key=test-key"

echo ""
echo "High throughput test completed!"
