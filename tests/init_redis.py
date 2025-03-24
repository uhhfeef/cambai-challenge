#!/usr/bin/env python3
import redis
import json
import os
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

def init_redis_db():
    # Create Redis connection
    redis_host = os.getenv('REDIS_HOST', 'localhost')  # Use localhost when running outside K8s
    redis_port = int(os.getenv('REDIS_PORT', 6380))  # Using port-forwarded port
    r = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
    
    # Force initialization of all keys
    print("Initializing Redis database...")
    r.set("fake_tenants_db", json.dumps(fake_tenants_db))
    r.set("fake_users_db", json.dumps(fake_users_db))
    r.set("fake_api_keys_db", json.dumps(fake_api_keys_db))
    print("Redis database initialized successfully")
    
    # Verify the keys were set correctly
    for key in ["fake_tenants_db", "fake_users_db", "fake_api_keys_db"]:
        value = r.get(key)
        if value:
            print(f"Key '{key}' exists in Redis")
        else:
            print(f"ERROR: Key '{key}' is missing in Redis")
    
    return r

if __name__ == "__main__":
    init_redis_db()
