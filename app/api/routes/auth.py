import json
from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

from app.core.security import authenticate_user, create_access_token
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.models.token import Token
from app.db.redis import main_redis
from app.db.redis_utils import create_redis_client

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    # Create a fresh Redis client for authentication
    redis_client = create_redis_client()
    
    # Attempt to authenticate the user
    user = authenticate_user(redis_client, form_data.username, form_data.password)
    
    # Create a fresh Redis client for logs
    logs_client = create_redis_client(db=1)
    
    if not user:
        # Log failed login attempt
        logs_entry = json.dumps({
            "timestamp": datetime.now().isoformat(),
            "action": "login_failed",
            "username": form_data.username,
            "tenant_id": "unknown",  # We don't know the tenant_id for failed logins
            "reason": "Incorrect username or password"
        })
        logs_client.lpush("logs:audit", logs_entry)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "tenant_id": user.tenant_id}, 
        expires_delta=access_token_expires
    )
    
    # Log successful login
    logs_entry = json.dumps({
        "timestamp": datetime.now().isoformat(),
        "action": "login_success",
        "username": user.username,
        "tenant_id": user.tenant_id,
        "token_expires_minutes": ACCESS_TOKEN_EXPIRE_MINUTES
    })
    logs_client.lpush("logs:audit", logs_entry)
    
    return {"access_token": access_token, "token_type": "bearer"}
