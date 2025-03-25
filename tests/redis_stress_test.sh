#!/bin/bash
# Redis Stress Test for FastAPI application
# Tests Redis performance under various load patterns

set -e  # Exit on error

# Configuration
SERVICE_URL="http://127.0.0.1:57509"
BASE_KEY="redis-stress"
TOKEN_FILE="access_token.txt"

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Redis Stress Test for FastAPI${NC}"
echo "Service URL: $SERVICE_URL"

# Check for access token
if [ ! -f "$TOKEN_FILE" ]; then
    echo -e "${RED}No access token found. Generating one...${NC}"
    python generate_token.py
    if [ ! -f "$TOKEN_FILE" ]; then
        echo -e "${RED}Failed to generate access token. Exiting.${NC}"
        exit 1
    fi
fi

TOKEN=$(cat $TOKEN_FILE)
echo "Using token: ${TOKEN:0:10}..."

# Function to run a test and report results
run_test() {
    local test_name=$1
    local requests=$2
    local concurrency=$3
    local method=$4
    local endpoint=$5
    local data=$6
    
    echo -e "\n${BLUE}Running test: $test_name${NC}"
    echo "Requests: $requests, Concurrency: $concurrency, Method: $method"
    
    local cmd="hey -n $requests -c $concurrency -m $method"
    cmd+=" -H \"Authorization: Bearer $TOKEN\""
    
    if [ "$method" != "GET" ]; then
        cmd+=" -H \"Content-Type: application/json\" -d '$data'"
    fi
    
    cmd+=" \"$SERVICE_URL$endpoint\""
    echo "Command: $cmd"
    
    # Actually run the command
    if [ "$method" != "GET" ]; then
        RESULT=$(hey -n $requests -c $concurrency -m $method \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$SERVICE_URL$endpoint")
    else
        RESULT=$(hey -n $requests -c $concurrency -m $method \
            -H "Authorization: Bearer $TOKEN" \
            "$SERVICE_URL$endpoint")
    fi
    
    echo -e "${GREEN}Test completed.${NC}"
    echo "$RESULT" | grep -E "Total:|Requests/sec:|Average:|Slowest:|Fastest:|Status code distribution:"
    
    # Extract and return the requests/sec
    local rps=$(echo "$RESULT" | grep "Requests/sec:" | awk '{print $2}')
    echo "$rps"
}

# Create multiple test keys first
echo -e "\n${YELLOW}Creating test keys...${NC}"
for i in {1..5}; do
    key="${BASE_KEY}-$i"
    curl -s -X POST "$SERVICE_URL/data?key=$key" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"value\":\"test-value-$i\",\"ttl\":null,\"metadata\":{\"test\":\"$i\"}}" > /dev/null
    echo -e "Created key: $key"
done

# Test 1: Baseline read performance
echo -e "\n${YELLOW}Test 1: Baseline Read Performance${NC}"
read_rps=$(run_test "Baseline Read" 1000 50 "GET" "/data/${BASE_KEY}-1" "")

# Test 2: Baseline write performance
echo -e "\n${YELLOW}Test 2: Baseline Write Performance${NC}"
write_rps=$(run_test "Baseline Write" 1000 50 "PUT" "/data/${BASE_KEY}-1" \
    "{\"value\":\"updated-value\",\"ttl\":null,\"metadata\":{\"test\":\"updated\"}}")

# Test 3: High concurrency read test
echo -e "\n${YELLOW}Test 3: High Concurrency Read Test${NC}"
high_conc_read_rps=$(run_test "High Concurrency Read" 2000 200 "GET" "/data/${BASE_KEY}-2" "")

# Test 4: High concurrency write test
echo -e "\n${YELLOW}Test 4: High Concurrency Write Test${NC}"
high_conc_write_rps=$(run_test "High Concurrency Write" 2000 200 "PUT" "/data/${BASE_KEY}-2" \
    "{\"value\":\"high-concurrency-value\",\"ttl\":null,\"metadata\":{\"test\":\"high-concurrency\"}}")

# Test 5: Mixed read/write test (run in parallel)
echo -e "\n${YELLOW}Test 5: Mixed Read/Write Test${NC}"
echo "Running reads and writes in parallel..."

# Run writes in background
hey -n 1000 -c 50 -m PUT \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"value\":\"mixed-test-value\",\"ttl\":null,\"metadata\":{\"test\":\"mixed\"}}" \
    "$SERVICE_URL/data/${BASE_KEY}-3" > /tmp/mixed_write_results.txt 2>&1 &

# Run reads in foreground
hey -n 1000 -c 50 -m GET \
    -H "Authorization: Bearer $TOKEN" \
    "$SERVICE_URL/data/${BASE_KEY}-4" > /tmp/mixed_read_results.txt

# Wait for background job to finish
wait

echo -e "${GREEN}Mixed test completed.${NC}"
echo -e "${BLUE}Read results:${NC}"
cat /tmp/mixed_read_results.txt | grep -E "Total:|Requests/sec:|Average:|Status code distribution:"
echo -e "${BLUE}Write results:${NC}"
cat /tmp/mixed_write_results.txt | grep -E "Total:|Requests/sec:|Average:|Status code distribution:"

# Test 6: TTL test
echo -e "\n${YELLOW}Test 6: TTL Test${NC}"
echo "Creating key with 5 second TTL..."
curl -s -X POST "$SERVICE_URL/data?key=${BASE_KEY}-ttl" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"value\":\"ttl-test-value\",\"ttl\":5,\"metadata\":{\"test\":\"ttl\"}}" > /dev/null

echo "Waiting for key to expire (6 seconds)..."
sleep 6

# Check if key has expired
response=$(curl -s -w "\n%{http_code}" -X GET "$SERVICE_URL/data/${BASE_KEY}-ttl" \
    -H "Authorization: Bearer $TOKEN")
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" -eq 404 ]; then
    echo -e "${GREEN}TTL test passed: Key expired successfully.${NC}"
else
    echo -e "${RED}TTL test failed: Key did not expire as expected.${NC}"
    echo "Response: $(echo "$response" | sed '$d')"
fi

# Clean up
echo -e "\n${YELLOW}Cleaning up test keys...${NC}"
for i in {1..5}; do
    key="${BASE_KEY}-$i"
    curl -s -X DELETE "$SERVICE_URL/data/$key" \
        -H "Authorization: Bearer $TOKEN" > /dev/null
    echo "Deleted key: $key"
done

# Summary
echo -e "\n${YELLOW}Test Summary:${NC}"
echo -e "Baseline Read: ${GREEN}$read_rps req/sec${NC}"
echo -e "Baseline Write: ${GREEN}$write_rps req/sec${NC}"
echo -e "High Concurrency Read: ${GREEN}$high_conc_read_rps req/sec${NC}"
echo -e "High Concurrency Write: ${GREEN}$high_conc_write_rps req/sec${NC}"
echo -e "Mixed Read/Write: See detailed results above"
echo -e "TTL Test: Completed"

echo -e "\n${GREEN}Redis stress test completed successfully!${NC}"
