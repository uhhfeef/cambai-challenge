from huey import RedisHuey
from huey import crontab
# from main import get_namespaced_key
import json
from datetime import datetime
import requests
import os
from app.db.redis_utils import create_redis_client

# Find a writable Redis instance for Huey
_, redis_host, redis_port = create_redis_client(db=2, return_connection_info=True)
huey = RedisHuey(host=redis_host, port=redis_port, db=2)

# Create logs Redis client
logs_redis = create_redis_client(db=1)

# Loki configuration
LOKI_HOST = os.getenv('LOKI_HOST', 'loki-gateway')
LOKI_PORT = os.getenv('LOKI_PORT', '80')
LOKI_URL = f'http://{LOKI_HOST}:{LOKI_PORT}/loki/api/v1/push'

@huey.task()
def audit_log_expiration(key: str, tenant_id: str):
    # Log the key expiration
    logs_entry = json.dumps({
        "timestamp": datetime.now().isoformat(),
        "action": "key_expiration",
        "key": key,
        "tenant_id": tenant_id,
    })
    logs_redis.lpush("logs:audit", logs_entry)
    
    print(f"Audit Log: Key '{tenant_id}:{key}' has expired.")

# Huey background task for audit log offloading to Loki
@huey.periodic_task(crontab(minute='*/1'))
def offload_audit_logs_to_loki():
    print("\n" + "*"*50)
    print("Starting log offloading to Loki...")
    print(f"Loki URL: {LOKI_URL}")
    
    logs_count = logs_redis.llen('logs:audit')
    print(f"Found {logs_count} logs in Redis queue")
    
    logs = []
    while True:
        log_data = logs_redis.rpop('logs:audit')
        if log_data is None:
            break
        try:
            logs.append(json.loads(log_data))
        except json.JSONDecodeError as e:
            print(f"Error decoding log data: {e}, data: {log_data}")
    
    print(f"Successfully parsed {len(logs)} logs to offload")
    
    # Print a sample of the logs for debugging
    if logs:
        print(f"Sample log: {logs[0]}")
    else:
        print("No logs to offload to Loki")
        return

    # Current timestamp in nanoseconds (Loki requires this format)
    current_time_ns = int(datetime.now().timestamp() * 1_000_000_000)
    
    # Group logs by tenant_id for proper multi-tenancy
    logs_by_tenant = {}
    for log in logs:
        tenant_id = log.get('tenant_id', 'unknown')
        if tenant_id not in logs_by_tenant:
            logs_by_tenant[tenant_id] = []
        logs_by_tenant[tenant_id].append(log)
    
    successful_logs = 0
    
    # Process logs for each tenant separately
    for tenant_id, tenant_logs in logs_by_tenant.items():
        # Prepare Loki-formatted payload for this tenant
        streams = []
        for log in tenant_logs:
            # Extract timestamp if available, otherwise use current time
            log_timestamp = log.get('timestamp', current_time_ns)
            if isinstance(log_timestamp, str):
                try:
                    # Convert ISO format to nanoseconds
                    dt = datetime.fromisoformat(log_timestamp)
                    log_timestamp = int(dt.timestamp() * 1_000_000_000)
                except ValueError:
                    log_timestamp = current_time_ns
            
            # Format log entry as string for Loki
            log_line = json.dumps(log)
            
            # Add to streams list with appropriate labels
            streams.append({
                "stream": {
                    "job": "audit_logs",
                    "tenant_id": tenant_id,
                    "action": log.get('action', 'unknown')
                },
                "values": [
                    [str(log_timestamp), log_line]
                ]
            })
        
        # Prepare payload for Loki
        loki_payload = {"streams": streams}
        
        # Retry mechanism with exponential backoff
        max_retries = 5
        base_delay = 1  # Start with 1 second delay
        success = False
        
        for attempt in range(max_retries):
            try:
                # Send logs to Loki using the tenant_id as the X-Scope-OrgID
                response = requests.post(
                    LOKI_URL,
                    json=loki_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Scope-OrgID": tenant_id  
                    },
                    timeout=10
                )
            
                if response.status_code >= 200 and response.status_code < 300:
                    successful_logs += len(tenant_logs)
                    print(f"Successfully offloaded {len(tenant_logs)} audit logs for tenant {tenant_id} to Loki")
                    success = True
                    break
                elif "at least 2 live replicas required" in response.text:
                    print(f"Replica issue detected, trying to send logs one by one for tenant {tenant_id}")
                    
                    individual_success = True
                    individual_successful = 0
                    
                    for log in tenant_logs:
                        log_timestamp = log.get('timestamp', current_time_ns)
                        if isinstance(log_timestamp, str):
                            try:
                                # Convert ISO format to nanoseconds
                                dt = datetime.fromisoformat(log_timestamp)
                                log_timestamp = int(dt.timestamp() * 1_000_000_000)
                            except ValueError:
                                log_timestamp = current_time_ns
                                
                        # Format log entry as string for Loki
                        log_line = json.dumps(log)
                        
                        single_stream = [{
                            "stream": {
                                "job": "audit_logs",
                                "tenant_id": tenant_id,
                                "action": log.get('action', 'unknown')
                            },
                            "values": [
                                [str(log_timestamp), log_line]
                            ]
                        }]
                        
                        single_payload = {"streams": single_stream}
                        
                        try:
                            single_response = requests.post(
                                LOKI_URL,
                                json=single_payload,
                                headers={
                                    "Content-Type": "application/json",
                                    "X-Scope-OrgID": tenant_id
                                },
                                timeout=10
                            )
                            
                            if single_response.status_code >= 200 and single_response.status_code < 300:
                                individual_successful += 1
                            else:
                                print(f"Failed to send individual log: {single_response.status_code} - {single_response.text}")
                                individual_success = False
                        except Exception as e:
                            print(f"Error sending individual log: {str(e)}")
                            individual_success = False
                    
                    if individual_successful > 0:
                        successful_logs += individual_successful
                        print(f"Successfully sent {individual_successful} logs individually for tenant {tenant_id}")
                        success = True
                        break
                else:
                    print(f"Failed to offload logs for tenant {tenant_id} to Loki (attempt {attempt+1}/{max_retries}). Status code: {response.status_code}, Response: {response.text}")
            except Exception as e:
                print(f"Error offloading logs for tenant {tenant_id} to Loki (attempt {attempt+1}/{max_retries}): {str(e)}")
            
            # Exponential backoff
            import time
            delay = base_delay * (2 ** attempt)
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
        
        if not success:
            print(f"Failed to send logs to Loki after {max_retries} attempts for tenant {tenant_id}")
            # Re-add logs to Redis for future processing
            for log in tenant_logs:
                logs_redis.lpush("logs:audit", json.dumps(log))
    
    if successful_logs > 0:
        print(f"Total logs offloaded to Loki: {successful_logs}")