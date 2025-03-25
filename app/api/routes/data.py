import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from app.core.security import get_current_active_user
from app.models.data import KeyValueItem
from app.db.redis import main_redis, logs_redis, get_namespaced_key
from app.db.redis_utils import create_redis_client

router = APIRouter()

@router.post("/data")
def create_item(item: KeyValueItem, key: str, user=Depends(get_current_active_user)):
    # Debug print
    print(f"Item model fields: {item.model_dump().keys()}")
    tenant_id = user.tenant_id
    namespaced_key = get_namespaced_key(tenant_id, key)
    
    if main_redis.exists(namespaced_key):
        raise HTTPException(status_code=400, detail="Key already exists")
    
    # Create a fresh Redis client for write operations to ensure we connect to the master
    redis_client = create_redis_client()
    
    # Save the full data (value and metadata) as JSON
    data = item.model_dump()
    redis_client.set(namespaced_key, json.dumps(data))
    
    # Set TTL if provided
    if item.ttl:
        redis_client.expire(namespaced_key, item.ttl)
    
    # Log the key creation
    logs_entry = json.dumps({
        "timestamp": datetime.now().isoformat(),
        "action": "create_key",
        "key": key,
        "value": item.value,
        "ttl": item.ttl,
        "metadata": item.metadata,
        "tenant_id": tenant_id,
    })
    
    # Create a fresh Redis client for logs to ensure we connect to the master
    logs_client = create_redis_client(db=1)
    logs_client.lpush("logs:audit", logs_entry)
    
    return {"status": "success", "key": key}

@router.get("/data/{key}")
def get_item(key: str, user=Depends(get_current_active_user)):
    tenant_id = user.tenant_id
    namespaced_key = get_namespaced_key(tenant_id, key)
    
    data = main_redis.get(namespaced_key)
    if not data:
        raise HTTPException(status_code=404, detail="Key not found")
    
    # Log the key retrieval
    logs_entry = json.dumps({
        "timestamp": datetime.now().isoformat(),
        "action": "get_key",
        "key": key,
        "value": json.loads(data)["value"],
        "metadata": json.loads(data)["metadata"],
        "tenant_id": tenant_id,
    })
    
    # Create a fresh Redis client for logs to ensure we connect to the master
    logs_client = create_redis_client(db=1)
    logs_client.lpush("logs:audit", logs_entry)
    
    return json.loads(data)

@router.put("/data/{key}")
def update_item(key: str, item: KeyValueItem, user=Depends(get_current_active_user)):
    tenant_id = user.tenant_id
    namespaced_key = get_namespaced_key(tenant_id, key)
    
    if not main_redis.exists(namespaced_key):
        raise HTTPException(status_code=404, detail="Key not found")
    
    # Create a fresh Redis client for write operations to ensure we connect to the master
    redis_client = create_redis_client()
    
    # Save the full data (value and metadata) as JSON
    data = item.model_dump()
    redis_client.set(namespaced_key, json.dumps(data))
    
    # Set or update TTL if provided
    if item.ttl:
        redis_client.expire(namespaced_key, item.ttl)
    
    # Log the key update
    logs_entry = json.dumps({
        "timestamp": datetime.now().isoformat(),
        "action": "update_key",
        "key": key,
        "value": item.value,
        "ttl": item.ttl,
        "metadata": item.metadata,
        "tenant_id": tenant_id,
    })
    
    # Create a fresh Redis client for logs to ensure we connect to the master
    logs_client = create_redis_client(db=1)
    logs_client.lpush("logs:audit", logs_entry)
    
    return {"status": "success", "key": key}

@router.delete("/data/{key}")
def delete_item(key: str, user=Depends(get_current_active_user)):
    tenant_id = user.tenant_id
    namespaced_key = get_namespaced_key(tenant_id, key)
    
    if not main_redis.exists(namespaced_key):
        raise HTTPException(status_code=404, detail="Key not found")
    
    # Get the data before deleting for logging
    data = json.loads(main_redis.get(namespaced_key))
    
    # Create a fresh Redis client for write operations to ensure we connect to the master
    redis_client = create_redis_client()
    
    # Delete the key
    redis_client.delete(namespaced_key)
    
    # Log the key deletion
    logs_entry = json.dumps({
        "timestamp": datetime.now().isoformat(),
        "action": "delete_key",
        "key": key,
        "value": data["value"],
        "metadata": data["metadata"],
        "tenant_id": tenant_id,
    })
    
    # Create a fresh Redis client for logs to ensure we connect to the master
    logs_client = create_redis_client(db=1)
    logs_client.lpush("logs:audit", logs_entry)
    
    return {"status": "success", "key": key}
