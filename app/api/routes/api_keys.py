import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, List

from app.core.security import get_current_active_user
from app.models.user import User
from app.models.api_key import APIKey, APIKeyCreate
from app.db.redis import main_redis, logs_redis, get_api_keys_for_tenant

router = APIRouter()

@router.get("/api-keys", response_model=List[APIKey])
async def list_api_keys(current_user: Annotated[User, Depends(get_current_active_user)]):
    return get_api_keys_for_tenant(current_user.tenant_id)

@router.post("/api-keys", response_model=APIKey)
async def create_api_key(key_data: APIKeyCreate, current_user: Annotated[User, Depends(get_current_active_user)]):
    key_id = f"key_{uuid.uuid4().hex[:8]}"
    key_value = f"sk_{'test' if current_user.tenant_id == 'tenant1' else 'prod'}_{uuid.uuid4().hex}"
    
    # Get current API keys
    api_keys_data = json.loads(main_redis.get("fake_api_keys_db"))
    
    # Create new API key
    api_key = {
        "key_id": key_id,
        "name": key_data.name,
        "key_value": key_value,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_used": None,
        "tenant_id": current_user.tenant_id,
    }
    
    # Add to database
    api_keys_data[key_id] = api_key
    main_redis.set("fake_api_keys_db", json.dumps(api_keys_data))
    
    # Log the creation
    logs_entry = json.dumps({
        "timestamp": datetime.now().isoformat(),
        "action": "create_api_key",
        "name": key_data.name,
        "tenant_id": current_user.tenant_id,
        "username": current_user.username,
    })
    logs_redis.lpush("logs:audit", logs_entry)
    
    # Return without tenant_id in the response
    return APIKey(**{k: v for k, v in api_key.items() if k != "tenant_id"})
