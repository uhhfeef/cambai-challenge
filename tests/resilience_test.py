#!/usr/bin/env python3
import os
import json
import time
import requests
from datetime import datetime, timedelta
import sys

# Configuration
SERVICE_URL = "http://localhost:8080"
TOKEN_FILE = "access_token.txt"

def load_token():
    """Load access token from file or generate a new one"""
    if not os.path.exists(TOKEN_FILE):
        print("No access token found. Please run generate_token.py first.")
        sys.exit(1)
    
    with open(TOKEN_FILE, 'r') as f:
        return f.read().strip()

def delete_resilience_test_data(token, tenant_id):
    """Delete all data keys that have 'resilience_test' in their name for a specific tenant"""
    print(f"\nDeleting existing resilience test data for tenant {tenant_id}...")
    try:
        # List all data keys (we'll use a direct Redis query for this)
        for i in range(1, 100):  # Try up to 100 keys
            key = f"resilience_test_{i}"
            response = requests.delete(
                f"{SERVICE_URL}/data",
                params={"key": key},
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Tenant-ID": tenant_id
                }
            )
            if response.status_code == 404:
                break  # Stop when we hit a non-existent key
            print(f"Deleted data key: {key}")
    except Exception as e:
        print(f"Error while deleting existing data: {e}")

def delete_resilience_test_keys(token):
    """Delete all API keys that have 'resilience_test' in their name"""
    print("\nDeleting existing resilience test API keys...")
    try:
        # List all API keys
        response = requests.get(
            f"{SERVICE_URL}/api-keys",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            print(f"Failed to list API keys. Status: {response.status_code}, Response: {response.text}")
            return
        
        keys = response.json()
        deleted_count = 0
        
        # Delete keys with 'resilience_test' in their name
        for key in keys:
            if 'resilience_test' in key.get('name', '').lower():
                # Use key_id instead of id for deletion
                key_id = key.get('key_id')
                if not key_id:
                    print(f"Warning: Key missing key_id field: {key}")
                    continue
                    
                del_response = requests.delete(
                    f"{SERVICE_URL}/api-keys/{key_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if del_response.status_code == 200:
                    deleted_count += 1
                else:
                    print(f"Failed to delete key {key_id}. Status: {del_response.status_code}")
        
        print(f"Deleted {deleted_count} existing resilience test API keys")
        
    except Exception as e:
        print(f"Error while deleting existing API keys: {e}")

def create_api_key(token, tenant_id, name):
    """Create an API key for a tenant"""
    print(f"Creating API key for tenant {tenant_id}...")
    response = requests.post(
        f"{SERVICE_URL}/api-keys",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"name": name}
    )
    
    if response.status_code != 200:
        print(f"Failed to create API key. Status: {response.status_code}, Response: {response.text}")
        return None
    
    key_value = response.json().get('key_value')
    print(f"Created API key for {tenant_id}: {key_value}")
    return key_value

def generate_logs(token, api_key, count, tenant_id):
    """Generate logs using the data endpoint"""
    print(f"\nGenerating {count} logs for tenant {tenant_id}...")
    failed_logs = 0
    successful_logs = 0
    
    for i in range(1, count + 1):
        response = requests.post(
            f"{SERVICE_URL}/data",
            params={"key": f"resilience_test_{i}"},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Tenant-ID": tenant_id
            },
            json={
                "value": "test_log",
                "ttl": 3600,
                "version": 1,
                "tags": ["resilience_test"],
                "metadata": {
                    "test_id": i,
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "action": "set_value",
                    "tenant_id": tenant_id
                }
            }
        )
        
        if response.status_code == 200:
            successful_logs += 1
        else:
            failed_logs += 1
            print(f"Failed to generate log {i}. Status: {response.status_code}, Response: {response.text}")
        
        if i % 10 == 0:
            print(f"Generated {i} logs...")
    
    print(f"Successfully generated {successful_logs}/{count} logs for tenant {tenant_id}")
    return successful_logs, failed_logs

def trigger_log_offload(token):
    """Trigger the log offloading task"""
    print("\nTriggering log offloading...")
    response = requests.post(
        f"{SERVICE_URL}/trigger-log-offload",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        print(f"Failed to trigger log offloading. Status: {response.status_code}, Response: {response.text}")
        return None
    
    task_id = response.json().get('task_id')
    print(f"Log offload task triggered successfully. Task ID: {task_id}")
    return task_id

def check_logs_in_loki(tenant_id, retries=3, retry_delay=10):
    """Check for logs in Loki with retries using direct HTTP requests"""
    def query_loki():
        try:
            # Calculate time range (last 5 minutes)
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=5)
            
            # Convert to nanoseconds for Loki
            end_time_ns = int(end_time.timestamp() * 1_000_000_000)
            start_time_ns = int(start_time.timestamp() * 1_000_000_000)
            
            # Build the LogQL query
            # Look for logs with our specific action (create_key) and tenant
            query = '{job="audit_logs", tenant_id="' + tenant_id + '", action="create_key"}'
            
            # Query Loki
            response = requests.get(
                'http://localhost:3100/loki/api/v1/query_range',
                params={
                    'query': query,
                    'start': start_time_ns,
                    'end': end_time_ns,
                    'limit': 1000
                },
                headers={'X-Scope-OrgID': tenant_id},
                timeout=5
            )
            
            if response.status_code != 200:
                print(f"Error from Loki API: {response.status_code} - {response.text}")
                return 0, None
            
            data = response.json()
            if not data.get('data', {}).get('result'):
                return 0, None
            
            # Count the number of log entries
            total_logs = sum(len(stream.get('values', [])) for stream in data['data']['result'])
            return total_logs, data
            
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Loki: {e}")
            return 0, None
        except Exception as e:
            print(f"Unexpected error querying Loki: {e}")
            return 0, None
    
    print(f"\nChecking logs for tenant {tenant_id}...")
    count, data = query_loki()
    
    attempt = 1
    while count == 0 and attempt < retries:
        print(f"No logs found, waiting {retry_delay}s and retrying... (Attempt {attempt}/{retries})")
        time.sleep(retry_delay)
        count, data = query_loki()
        attempt += 1
    
    if count > 0:
        print(f"Found {count} logs in Loki for tenant {tenant_id}")
        print("\nSample of logs:")
        if data and data.get('data', {}).get('result'):
            # Display the first 3 logs
            for stream in data['data']['result'][:1]:  # Show first stream
                values = stream.get('values', [])
                for ts, log in values[:3]:  # Show first 3 logs
                    try:
                        log_data = json.loads(log)
                        print(f"Timestamp: {datetime.fromtimestamp(int(ts)/1e9).strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"Action: {log_data.get('action')}")
                        print(f"Key: {log_data.get('key')}")
                        print("---")
                    except json.JSONDecodeError:
                        print(f"Raw log: {log}")
                        print("---")
    else:
        print(f"WARNING: No logs found in Loki for {tenant_id} after {retries} attempts")
    
    return count

def main():
    # Load access token
    token = load_token()
    tenant_id = "tenant1"
    
    # Delete any existing resilience test data and API keys
    delete_resilience_test_data(token, tenant_id)
    delete_resilience_test_keys(token)
    
    # Create fresh API key for tenant1
    api_key = create_api_key(token, tenant_id, "resilience_test_key_1")
    
    # Use default test value if API key creation fails
    if not api_key:
        api_key = "sk_test_abcdefghijklmnopqrstuvwxyz123456"
        print("Using default API key for tenant1")
    
    # Step 1: Generate initial logs
    print("\nStep 1: Generating initial logs...")
    successful, failed = generate_logs(token, api_key, 50, tenant_id)
    
    # Step 2: Trigger log offloading
    task_id = trigger_log_offload(token)
    if not task_id:
        print("Failed to trigger log offloading. Exiting...")
        sys.exit(1)
    
    # Step 3: Verify logs in Loki
    print("\nStep 3: Verifying logs in Loki...")
    print("Waiting 30s for logs to be processed...")
    time.sleep(30)
    
    log_count = check_logs_in_loki(tenant_id)
    
    # Print summary
    print("\nTest Summary:")
    print("-" * 50)
    print(f"Generated Logs: {successful}/{50}")
    print(f"Logs in Loki: {log_count}")
    
    if log_count < successful:
        print("WARNING: Some logs appear to be missing in Loki")
    elif log_count > successful:
        print("WARNING: More logs found in Loki than were generated")

if __name__ == "__main__":
    main()
