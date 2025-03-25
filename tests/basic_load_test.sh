#!/bin/bash
# Basic load test for FastAPI Redis application
# Tests read and write operations with proper error handling

set -e  # Exit on error

# Configuration
SERVICE_URL="http://127.0.0.1:54120"
TEST_KEY="load-test-key-$(date +%s)"  # Use timestamp for unique key
REQUEST_COUNT=1000
CONCURRENCY=50

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}FastAPI Redis Load Test${NC}"
echo "Service URL: $SERVICE_URL"
echo "Test key: $TEST_KEY"


# Check for access token
if [ ! -f "access_token.txt" ]; then
    echo -e "${RED}No access token found. Generating one...${NC}"
    python generate_token.py
    if [ ! -f "access_token.txt" ]; then
        echo -e "${RED}Failed to generate access token. Exiting.${NC}"
        exit 1
    fi
fi

TOKEN=$(cat access_token.txt)
echo "Using token: ${TOKEN:0:10}..."

# Create a test item
echo -e "\n${YELLOW}1. Creating test item...${NC}"
CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$SERVICE_URL/data?key=$TEST_KEY" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value":"test-value","ttl":null,"metadata":{"test":"test"}}')

HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -ne 200 ]; then
    echo -e "${RED}Failed to create test item. HTTP Code: $HTTP_CODE${NC}"
    echo "Response: $RESPONSE_BODY"
    exit 1
fi

echo -e "${GREEN}Test item created successfully.${NC}"

# Run load test for reads
echo -e "\n${YELLOW}2. Running read load test ($REQUEST_COUNT requests, $CONCURRENCY concurrent)...${NC}"
echo "Command: hey -n $REQUEST_COUNT -c $CONCURRENCY -H \"Authorization: Bearer $TOKEN\" \"$SERVICE_URL/data/$TEST_KEY\""

READ_RESULT=$(hey -n $REQUEST_COUNT -c $CONCURRENCY -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/data/$TEST_KEY")
echo -e "${GREEN}Read test completed.${NC}"
echo "$READ_RESULT" | grep -E "Total:|Requests/sec:|Average:|Slowest:|Fastest:|Status code distribution:" -A 10

# Run load test for writes
echo -e "\n${YELLOW}3. Running write load test ($REQUEST_COUNT requests, $CONCURRENCY concurrent)...${NC}"
echo "Command: hey -n $REQUEST_COUNT -c $CONCURRENCY -m PUT -H \"Authorization: Bearer $TOKEN\" -H \"Content-Type: application/json\" -d '{...}' \"$SERVICE_URL/data/$TEST_KEY\""

WRITE_RESULT=$(hey -n $REQUEST_COUNT -c $CONCURRENCY -m PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value":"updated-value","ttl":null,"metadata":{"test":"test"}}' \
  "$SERVICE_URL/data/$TEST_KEY")
echo -e "${GREEN}Write test completed.${NC}"
echo "$WRITE_RESULT" | grep -E "Total:|Requests/sec:|Average:|Slowest:|Fastest:|Status code distribution:" -A 10

# Cleanup - delete the test key
echo -e "\n${YELLOW}4. Cleaning up - deleting test key...${NC}"
DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$SERVICE_URL/data/$TEST_KEY" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" -ne 200 ]; then
    echo -e "${RED}Warning: Failed to delete test key. HTTP Code: $HTTP_CODE${NC}"
else
    echo -e "${GREEN}Test key deleted successfully.${NC}"
fi

echo -e "\n${GREEN}Load test completed successfully!${NC}"
