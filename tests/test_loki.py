# initial Loki integration

#!/usr/bin/env python3
import requests
import json
from datetime import datetime
import sys

# Loki configuration
LOKI_HOST = "loki-gateway"
LOKI_PORT = "80"
LOKI_URL = f'http://{LOKI_HOST}:{LOKI_PORT}/loki/api/v1/push'

# Tenant ID to use
TENANT_ID = "tenant1"  # This should match the tenant_id in your JWT token

# Create a test log entry
current_time_ns = int(datetime.now().timestamp() * 1_000_000_000)
test_log = {
    "timestamp": datetime.now().isoformat(),
    "action": "test_log",
    "message": "This is a test log entry",
    "tenant_id": TENANT_ID
}

# Format for Loki
streams = [{
    "stream": {
        "job": "audit_logs",
        "tenant_id": TENANT_ID,
        "action": "test_log"
    },
    "values": [
        [str(current_time_ns), json.dumps(test_log)]
    ]
}]

# Prepare payload
loki_payload = {"streams": streams}

print(f"Sending test log to Loki at {LOKI_URL}")
print(f"Using tenant ID: {TENANT_ID}")
print(f"Payload: {json.dumps(loki_payload, indent=2)}")

try:
    # Send logs to Loki
    response = requests.post(
        LOKI_URL,
        json=loki_payload,
        headers={
            "Content-Type": "application/json",
            "X-Scope-OrgID": TENANT_ID
        },
        timeout=10
    )

    print(f"Response status code: {response.status_code}")
    print(f"Response text: {response.text}")
    
    if response.status_code >= 200 and response.status_code < 300:
        print("Successfully sent test log to Loki")
        print("Now check Grafana with the query: {job=\"audit_logs\", tenant_id=\"tenant1\"}")
        print("Make sure to set the X-Scope-OrgID header in Grafana to 'tenant1'")
    else:
        print("Failed to send test log to Loki")
        
except Exception as e:
    print(f"Error sending test log to Loki: {str(e)}")
