# test the system under sustained load

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

# Run continuous load test
echo "Starting continuous load test..."
echo "Press Ctrl+C to stop the test"

iteration=0
while true; do
    iteration=$((iteration+1))
    echo "Iteration $iteration"
    
    # Run a batch of read requests
    hey -n 1000 -c 50 -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/data?key=test-key" > /dev/null 2>&1
    
    # Run a batch of write requests
    hey -n 1000 -c 50 -m PUT -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"value":"updated-value-'$iteration'","ttl":null,"version":2,"tags":["test"]}' \
      "$SERVICE_URL/data?key=test-key" > /dev/null 2>&1
    
    # Sleep for a short time to avoid overwhelming the system
    sleep 1
done
