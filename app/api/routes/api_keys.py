import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, List

from app.core.security import get_current_active_user
from app.models.user import User
from app.models.api_key import APIKey, APIKeyCreate
from app.db.redis import main_redis, logs_redis, get_api_keys_for_tenant
from app.db.redis_utils import create_redis_client

router = APIRouter()

@router.get("/api-keys", response_model=List[APIKey])
async def list_api_keys(current_user: Annotated[User, Depends(get_current_active_user)]):
    return get_api_keys_for_tenant(current_user.tenant_id)

@router.post("/api-keys", response_model=APIKey)
async def create_api_key(key_data: APIKeyCreate, current_user: Annotated[User, Depends(get_current_active_user)]):
    key_id = f"key_{uuid.uuid4().hex[:8]}"
    key_value = f"sk_{'test' if current_user.tenant_id == 'tenant1' else 'prod'}_{uuid.uuid4().hex}"
    
    # Create a fresh Redis client for read/write operations
    redis_client = create_redis_client()
    
    # Get current API keys
    api_keys_data = json.loads(redis_client.get("fake_api_keys_db"))
    
    # Create new API key
    api_key = {
        "key_id": key_id,
        "name": key_data.name,
        "key_value": key_value,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_used": None,
        "tenant_id": current_user.tenant_id,
    }
    
    # Add to database using the fresh Redis client
    api_keys_data[key_id] = api_key
    redis_client.set("fake_api_keys_db", json.dumps(api_keys_data))
    
    # Create a fresh Redis client for logs
    logs_client = create_redis_client(db=1)
    
    # Log the creation
    logs_entry = json.dumps({
        "timestamp": datetime.now().isoformat(),
        "action": "create_api_key",
        "name": key_data.name,
        "tenant_id": current_user.tenant_id,
        "username": current_user.username,
    })
    logs_client.lpush("logs:audit", logs_entry)
    
    # Return without tenant_id in the response
    return APIKey(**{k: v for k, v in api_key.items() if k != "tenant_id"})
