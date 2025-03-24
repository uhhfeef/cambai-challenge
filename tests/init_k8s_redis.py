#!/usr/bin/env python3
"""
Script to initialize Redis in the Kubernetes cluster.
This script creates a temporary Python file with Redis initialization code
and executes it in the Redis pod.
"""
import json
import os
import subprocess
from datetime import datetime, timezone

# Mock databases
fake_tenants_db = {
    "tenant1": {
        "tenant_id": "tenant1",
        "name": "Demo Tenant",
        "description": "A demo tenant for testing",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    "tenant2": {
        "tenant_id": "tenant2",
        "name": "Another Tenant",
        "description": "Another tenant for testing",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
}

fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
        "tenant_id": "tenant1",
    },
    "jane": {
        "username": "jane",
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
        "tenant_id": "tenant2",
    },
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "email": "admin@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
        "tenant_id": "tenant1",
    }
}

fake_api_keys_db = {
    "key1": {
        "key_id": "key1",
        "api_key": "sk_live_1234567890abcdef",
        "name": "Test Key 1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": "tenant1",
    },
    "key2": {
        "key_id": "key2",
        "api_key": "sk_live_abcdef1234567890",
        "name": "Test Key 2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": "tenant2",
    }
}

# Initialize Redis using a Python script executed in the pod
def init_redis_with_python():
    """Initialize Redis using a Python script executed in the Redis pod"""
    print("Initializing Redis using Python script...")
    
    # Get Redis pod name
    result = subprocess.run(
        ["kubectl", "get", "pods", "-l", "app=redis", "-o", "jsonpath='{.items[0].metadata.name}'"],
        capture_output=True,
        text=True
    )
    pod_name = result.stdout.strip("'")
    
    if not pod_name:
        print("Error: Could not find Redis pod")
        return False
    
    print(f"Found Redis pod: {pod_name}")
    
    # Create a temporary Python script to initialize Redis
    script_content = f'''
#!/usr/bin/env python3
import redis
import json

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Set tenant data
r.set("fake_tenants_db", '{json.dumps(fake_tenants_db)}')

# Set user data
r.set("fake_users_db", '{json.dumps(fake_users_db)}')

# Set API keys data
r.set("fake_api_keys_db", '{json.dumps(fake_api_keys_db)}')

# Verify the keys were set correctly
for key in ["fake_tenants_db", "fake_users_db", "fake_api_keys_db"]:
    value = r.get(key)
    if value:
        print(f"Key '{{key}}' exists in Redis")
    else:
        print(f"ERROR: Key '{{key}}' is missing in Redis")
'''
    
    # Write the script to a temporary file
    with open('temp_init_redis.py', 'w') as f:
        f.write(script_content)
    
    # Copy the script to the Redis pod
    subprocess.run(["kubectl", "cp", "temp_init_redis.py", f"{pod_name}:/tmp/init_redis.py"])
    
    # Install redis-py in the pod
    subprocess.run(["kubectl", "exec", pod_name, "--", "pip", "install", "redis"])
    
    # Execute the script in the pod
    result = subprocess.run(
        ["kubectl", "exec", pod_name, "--", "python", "/tmp/init_redis.py"],
        capture_output=True,
        text=True
    )
    
    # Clean up the temporary file
    os.remove('temp_init_redis.py')
        
    # Print the output from the Redis initialization script
    print(result.stdout)
    
    # Verify the keys were set correctly
    print("\nVerifying keys...")
    result = subprocess.run(
        f'kubectl exec {pod_name} -- redis-cli KEYS "*"',
        shell=True,
        capture_output=True,
        text=True
    )
    print(f"Keys in Redis: {result.stdout}")
    
    return True

if __name__ == "__main__":
    init_redis_with_python()
