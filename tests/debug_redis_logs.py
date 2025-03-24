# troubleshooting why logs aren't appearing in Loki

#!/usr/bin/env python3
import redis
import json
import requests
from datetime import datetime
import os

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'redis-service')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
logs_redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)

# Loki configuration
LOKI_HOST = os.getenv('LOKI_HOST', 'loki-gateway')
LOKI_PORT = os.getenv('LOKI_PORT', '80')
LOKI_URL = f'http://{LOKI_HOST}:{LOKI_PORT}/loki/api/v1/push'

print(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
print(f"Loki URL: {LOKI_URL}")

# Check if we can connect to Loki
try:
    health_check = requests.get(f'http://{LOKI_HOST}:{LOKI_PORT}/ready', timeout=5)
    print(f"Loki health check: {health_check.status_code} - {health_check.text}")
except Exception as e:
    print(f"Loki health check failed: {str(e)}")

# Check if there are logs in Redis
logs_count = logs_redis.llen('logs:audit')
print(f"Found {logs_count} logs in Redis")

# Get all logs from Redis without removing them
logs = []
if logs_count > 0:
    # Get all logs without removing them
    all_logs = logs_redis.lrange('logs:audit', 0, -1)
    for log_data in all_logs:
        try:
            log = json.loads(log_data)
            logs.append(log)
            print(f"Log: {log}")
        except json.JSONDecodeError:
            print(f"Error decoding log: {log_data}")

    print(f"Retrieved {len(logs)} logs from Redis")

    # Try to send a test log to Loki
    if logs:
        # Current timestamp in nanoseconds
        current_time_ns = int(datetime.now().timestamp() * 1_000_000_000)
        
        # If we have logs, use the first one, otherwise create a test log
        if logs:
            test_log = logs[0]
            tenant_id = test_log.get('tenant_id', 'tenant1')
        else:
            # Create a test log with current timestamp
            test_log = {
                "timestamp": datetime.now().isoformat(),
                "action": "test_action",
                "tenant_id": "tenant1",
                "message": "This is a test log"
            }
            tenant_id = "tenant1"
        
        streams = [{
            "stream": {
                "job": "audit_logs",
                "tenant_id": tenant_id,
                "action": test_log.get('action', 'unknown')
            },
            "values": [
                [str(current_time_ns), json.dumps(test_log)]
            ]
        }]
        
        # Prepare payload for Loki
        loki_payload = {"streams": streams}
        
        print(f"Sending test log to Loki with tenant_id: {tenant_id}")
        print(f"Payload: {json.dumps(loki_payload, indent=2)}")
        
        try:
            # Send logs to Loki
            response = requests.post(
                LOKI_URL,
                json=loki_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Scope-OrgID": tenant_id
                },
                timeout=10
            )
            
            print(f"Response status code: {response.status_code}")
            print(f"Response text: {response.text}")
            
            if response.status_code >= 200 and response.status_code < 300:
                print("Successfully sent test log to Loki")
            else:
                print("Failed to send test log to Loki")
                
        except Exception as e:
            print(f"Error sending test log to Loki: {str(e)}")
else:
    print("No logs found in Redis")
