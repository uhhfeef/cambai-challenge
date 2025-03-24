#!/usr/bin/env python3
"""
Script to initialize Redis from the FastAPI pod.
This script will be copied to the FastAPI pod and executed there.
"""
import redis
import json
import os
from datetime import datetime, timezone
import subprocess

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

def init_redis_from_fastapi():
    """Initialize Redis from the FastAPI pod"""
    print("Initializing Redis from FastAPI pod...")
    
    # Get FastAPI pod name
    result = subprocess.run(
        ["kubectl", "get", "pods", "-l", "app=fastapi", "-o", "jsonpath='{.items[0].metadata.name}'"],
        capture_output=True,
        text=True
    )
    pod_name = result.stdout.strip("'")
    
    if not pod_name:
        print("Error: Could not find FastAPI pod")
        return False
    
    print(f"Found FastAPI pod: {pod_name}")
    
    # Create a temporary Python script to initialize Redis
    script_content = """
#!/usr/bin/env python3
import redis
import json
import os

# Connect to Redis using the service name that FastAPI uses
r = redis.Redis(host='redis-service', port=6379, db=0, decode_responses=True)

# Set tenant data
tenant_data = '''%s'''
r.set("fake_tenants_db", tenant_data)

# Set user data
user_data = '''%s'''
r.set("fake_users_db", user_data)

# Set API keys data
api_keys_data = '''%s'''
r.set("fake_api_keys_db", api_keys_data)

# Verify the keys were set correctly
for key in ["fake_tenants_db", "fake_users_db", "fake_api_keys_db"]:
    value = r.get(key)
    if value:
        print(f"Key '{key}' exists in Redis")
    else:
        print(f"ERROR: Key '{key}' is missing in Redis")
""" % (json.dumps(fake_tenants_db), json.dumps(fake_users_db), json.dumps(fake_api_keys_db))
    
    # Write the script to a temporary file
    with open('temp_fastapi_init_redis.py', 'w') as f:
        f.write(script_content)
    
    # Copy the script to the FastAPI pod
    subprocess.run(["kubectl", "cp", "temp_fastapi_init_redis.py", f"{pod_name}:/tmp/init_redis.py"])
    
    # Execute the script in the FastAPI pod
    result = subprocess.run(
        ["kubectl", "exec", pod_name, "--", "python", "/tmp/init_redis.py"],
        capture_output=True,
        text=True
    )
    
    # Clean up the temporary file
    os.remove('temp_fastapi_init_redis.py')
    
    # Print the output from the Redis initialization script
    print(result.stdout)
    
    # Test if the FastAPI application can now access the Redis data
    print("\nTesting FastAPI Redis access...")
    test_cmd = f'kubectl exec {pod_name} -- python -c "import redis, json; r = redis.Redis(host=\'redis-service\', port=6379, db=0, decode_responses=True); print(\'Redis test: Users data exists =\', r.get(\'fake_users_db\') is not None)"'
    test_result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
    print(test_result.stdout)
    
    return True

if __name__ == "__main__":
    init_redis_from_fastapi()
