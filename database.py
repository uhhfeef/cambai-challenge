from typing import Dict
from datetime import datetime, timezone

# Mock databases
fake_tenants_db: Dict[str, dict] = {
    "tenant1": {
        "tenant_id": "tenant1",
        "name": "Demo Tenant",
        "description": "A demo tenant for testing",
        "created_at": datetime.now(timezone.utc),
    },
    "tenant2": {
        "tenant_id": "tenant2",
        "name": "Another Tenant",
        "description": "Another tenant for testing",
        "created_at": datetime.now(timezone.utc),
    }
}

fake_users_db: Dict[str, dict] = {
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

fake_api_keys_db: Dict[str, dict] = {
    "key1": {
        "key_id": "key1",
        "key_value": "sk_test_abcdefghijklmnopqrstuvwxyz123456",
        "name": "Test API Key",
        "created_at": datetime.now(timezone.utc),
        "last_used": None,
        "tenant_id": "tenant1",
    },
    "key2": {
        "key_id": "key2",
        "key_value": "sk_test_abcdefghijklmnopqrstuvwxyz123456",
        "name": "Test API Key 2",
        "created_at": datetime.now(timezone.utc),
        "last_used": None,
        "tenant_id": "tenant2",
    },
    "key3": {
        "key_id": "key3",
        "key_value": "sk_test_abcdefghijklmnopqrstuvwxyz123456",
        "name": "Test API Key 3",
        "created_at": datetime.now(timezone.utc),
        "last_used": None,
        "tenant_id": "tenant2",
    }
}
