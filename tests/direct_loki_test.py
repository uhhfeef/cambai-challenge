# verify if Loki was accepting logs properly

#!/usr/bin/env python3
import requests
import json
import time
from datetime import datetime
import os

# Loki configuration
LOKI_HOST = os.getenv('LOKI_HOST', 'loki-gateway')
LOKI_PORT = os.getenv('LOKI_PORT', '80')
LOKI_URL = f'http://{LOKI_HOST}:{LOKI_PORT}/loki/api/v1/push'

print(f"Loki URL: {LOKI_URL}")

# Create a test log entry
test_log = {
    "timestamp": datetime.now().isoformat(),
    "action": "test_action",
    "tenant_id": "tenant1",
    "message": "This is a direct test log"
}

# Current timestamp in nanoseconds
current_time_ns = int(datetime.now().timestamp() * 1_000_000_000)

# Create a stream for Loki
stream = {
    "stream": {
        "job": "direct_test",
        "tenant_id": "tenant1",
        "action": "test_action"
    },
    "values": [
        [str(current_time_ns), json.dumps(test_log)]
    ]
}

# Prepare payload for Loki
loki_payload = {"streams": [stream]}

print(f"Sending payload to Loki: {json.dumps(loki_payload, indent=2)}")

# Retry mechanism with exponential backoff
max_retries = 5
base_delay = 1  # Start with 1 second delay

for attempt in range(max_retries):
    try:
        # Send logs to Loki
        print(f"Attempt {attempt+1}/{max_retries} to send log to Loki")
        response = requests.post(
            LOKI_URL,
            json=loki_payload,
            headers={
                "Content-Type": "application/json",
                "X-Scope-OrgID": "tenant1"
            },
            timeout=10
        )
        
        print(f"Response status code: {response.status_code}")
        print(f"Response text: {response.text}")
        
        if response.status_code >= 200 and response.status_code < 300:
            print("Successfully sent test log to Loki")
            break
        elif "at least 2 live replicas required" in response.text:
            print("Replica issue detected, trying a different approach")
            
            # Try to send a simpler log
            simple_stream = {
                "stream": {
                    "job": "simple_test"
                },
                "values": [
                    [str(current_time_ns), "\"Simple test message\""]
                ]
            }
            
            simple_payload = {"streams": [simple_stream]}
            
            print(f"Sending simplified payload: {json.dumps(simple_payload, indent=2)}")
            
            simple_response = requests.post(
                LOKI_URL,
                json=simple_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Scope-OrgID": "tenant1"
                },
                timeout=10
            )
            
            print(f"Simple response status code: {simple_response.status_code}")
            print(f"Simple response text: {simple_response.text}")
            
            if simple_response.status_code >= 200 and simple_response.status_code < 300:
                print("Successfully sent simplified test log to Loki")
                break
        else:
            print(f"Failed to send log to Loki: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending log to Loki: {str(e)}")
    
    # Exponential backoff
    delay = base_delay * (2 ** attempt)
    print(f"Retrying in {delay} seconds...")
    time.sleep(delay)

# Now let's try to query Loki to see if our logs are there
query_url = f"http://{LOKI_HOST}:{LOKI_PORT}/loki/api/v1/query_range"
query_params = {
    "query": '{job="direct_test"}',
    "start": int((datetime.now().timestamp() - 3600) * 1_000_000_000),  # 1 hour ago
    "end": int(datetime.now().timestamp() * 1_000_000_000),  # now
    "limit": 10
}

print("\nQuerying Loki for logs...")
print(f"Query URL: {query_url}")
print(f"Query params: {query_params}")

try:
    query_response = requests.get(
        query_url,
        params=query_params,
        headers={
            "X-Scope-OrgID": "tenant1"
        },
        timeout=10
    )
    
    print(f"Query response status code: {query_response.status_code}")
    print(f"Query response text: {query_response.text}")
except Exception as e:
    print(f"Error querying Loki: {str(e)}")
