import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, List

from app.models.user import User
from app.models.api_key import APIKey
from app.db.redis_utils import create_redis_client

# Initialize Redis clients
main_redis = create_redis_client(db=0)
logs_redis = create_redis_client(db=1)

# Fake database initialization
def init_redis_db():
    # Create Redis connection with direct pod connection strategy and failover support
    r = create_redis_client(db=0)
    
    # Check all required keys exist
    required_keys = ["fake_tenants_db", "fake_users_db", "fake_api_keys_db"]
    
    # Initialize if any key is missing
    if not all(r.exists(key) for key in required_keys):
        print("Initializing Redis database with fake data...")
        
        # Fake tenants data
        fake_tenants = {
            "tenant1": {
                "name": "Tenant 1",
                "plan": "basic",
                "active": True
            },
            "tenant2": {
                "name": "Tenant 2",
                "plan": "premium",
                "active": True
            }
        }
        
        # Fake users data
        fake_users = {
            "user1": {
                "username": "user1",
                "email": "user1@example.com",
                "full_name": "User One",
                "disabled": False,
                "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
                "tenant_id": "tenant1"
            },
            "admin": {
                "username": "admin",
                "email": "admin@example.com",
                "full_name": "Admin User",
                "disabled": False,
                "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
                "tenant_id": "tenant1"
            },
            "user2": {
                "username": "user2",
                "email": "user2@example.com",
                "full_name": "User Two",
                "disabled": False,
                "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
                "tenant_id": "tenant2"
            }
        }
        
        # Fake API keys data
        fake_api_keys = {
            "key_12345678": {
                "key_id": "key_12345678",
                "name": "Test API Key",
                "key_value": "sk_test_12345678901234567890123456789012",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_used": None,
                "tenant_id": "tenant1",
            },
            "key_87654321": {
                "key_id": "key_87654321",
                "name": "Production API Key",
                "key_value": "sk_prod_12345678901234567890123456789012",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_used": None,
                "tenant_id": "tenant2",
            }
        }
        
        # Store in Redis
        r.set("fake_tenants_db", json.dumps(fake_tenants))
        r.set("fake_users_db", json.dumps(fake_users))
        r.set("fake_api_keys_db", json.dumps(fake_api_keys))
        
        print("Redis database initialized with fake data.")
    else:
        print("Redis database already initialized.")
    
    return r

def get_user(redis_client, username: str) -> Optional[User]:

    users_data = json.loads(redis_client.get("fake_users_db"))
    user_data = users_data.get(username)
    if user_data:
        return User(**user_data)
    return None

def get_api_keys_for_tenant(tenant_id: str) -> List[APIKey]:
    # Create a fresh Redis client for read operations
    redis_client = create_redis_client()
    
    api_keys_data = json.loads(redis_client.get("fake_api_keys_db"))
    tenant_keys = []
    
    for key_id, key_data in api_keys_data.items():
        if key_data.get("tenant_id") == tenant_id:
            # Exclude tenant_id from the response
            api_key = {k: v for k, v in key_data.items() if k != "tenant_id"}
            tenant_keys.append(APIKey(**api_key))
    
    return tenant_keys

def get_namespaced_key(tenant_id: str, key: str) -> str:
    """Create a namespaced key for multi-tenant data isolation"""
    return f"tenant:{tenant_id}:data:{key}"
