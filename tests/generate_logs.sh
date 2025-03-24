#!/bin/bash

# This script creates multiple API keys to generate audit logs to test log offload triggers to Loki

# Use the port-forwarded service URL
SERVICE_URL="http://localhost:8080"
echo "Service URL: $SERVICE_URL"

# Check if we have a token
if [ ! -f "access_token.txt" ]; then
    echo "No access token found. Please run generate_token.py first."
    exit 1
fi

TOKEN=$(cat access_token.txt)
echo "Using token: $TOKEN"

# Create multiple API keys to generate logs
echo "Creating API keys to generate logs..."

for i in {1..10}
do
    echo "Creating API key $i..."
    curl -X POST "$SERVICE_URL/api-keys" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"test-key-$i\"}"
    
    echo ""
    sleep 1
done

echo ""
echo "Triggering log offload to Loki..."
curl -X POST "$SERVICE_URL/trigger-log-offload"

echo ""
echo "Log generation completed! Check Loki for logs with job=audit_logs"
