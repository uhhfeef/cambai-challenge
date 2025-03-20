from typing import Annotated, Dict, List, Optional
import uuid
import os
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jwt.exceptions import InvalidTokenError
import jwt
from datetime import datetime, timedelta, timezone
import redis
import json

from models import Token, TokenData, APIKey, Tenant, TenantCreate, User, UserInDB, APIKeyCreate, KeyValueItem

# Load environment variables from .env file
load_dotenv()

# Security configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
SECRET_KEY = os.getenv("SECRET_KEY")

app = FastAPI(title="Multi-tenant API Key Management System")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

redis_conn = redis.Redis(host="localhost", port=6379, db=0)


def get_tenant(tenant_id: str):
    tenants_data = json.loads(redis_conn.get("fake_tenants_db"))
    if tenant_id in tenants_data:
        tenant_dict = tenants_data[tenant_id]
        return Tenant(**tenant_dict)
    return None

def get_user(redis_conn, username: str):
    users_data = json.loads(redis_conn.get("fake_users_db"))
    if username in users_data:
        user_dict = users_data[username]
        return UserInDB(**user_dict)
    return None

def get_api_keys_for_tenant(tenant_id: str) -> List[APIKey]:
    keys = []
    api_keys_data = json.loads(redis_conn.get("fake_api_keys_db"))
    for key_id, key_data in api_keys_data.items():
        if key_data.get("tenant_id") == tenant_id:
            keys.append(APIKey(**{k: v for k, v in key_data.items() if k != "tenant_id"}))
    return keys

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(redis_conn, username: str, password: str):
    user = get_user(redis_conn, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def generate_api_key() -> str:
    """Generate a random API key"""
    return f"sk_live_{uuid.uuid4().hex}"

# Authentication dependencies
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, tenant_id=tenant_id)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(redis_conn, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_namespaced_key(tenant_id: str, key: str) -> str:
    return f"{tenant_id}:{key}"

# API endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = authenticate_user(redis_conn, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "tenant_id": user.tenant_id}, 
        expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user

# Tenant management endpoints
@app.get("/tenants/me", response_model=Tenant)
async def get_my_tenant(current_user: Annotated[User, Depends(get_current_active_user)]):
    tenant = get_tenant(current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


# API key management endpoints
@app.get("/api-keys", response_model=List[APIKey])
async def list_api_keys(current_user: Annotated[User, Depends(get_current_active_user)]):
    return get_api_keys_for_tenant(current_user.tenant_id)

@app.post("/api-keys", response_model=APIKey)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    key_id = f"key_{uuid.uuid4().hex[:8]}"
    key_value = generate_api_key()
    
    api_key = {
        "key_id": key_id,
        "key_value": key_value,
        "name": key_data.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_used": None,
        "tenant_id": current_user.tenant_id
    }
    
    api_keys_data = json.loads(redis_conn.get("fake_api_keys_db"))
    api_keys_data[key_id] = api_key
    redis_conn.set("fake_api_keys_db", json.dumps(api_keys_data))
    
    # Return without tenant_id in the response
    return APIKey(**{k: v for k, v in api_key.items() if k != "tenant_id"})

# @app.get("/data", response_model=dict)
# async def get_tenant_data(current_user: Annotated[User, Depends(get_current_active_user)]):
#     return {
#         "tenant_id": current_user.tenant_id,
#         "message": f"This is private data for tenant: {current_user.tenant_id}"
#     }

@app.post("/data")
def create_item(item: KeyValueItem, user=Depends(get_current_active_user)):
    tenant_id = user.tenant_id
    namespaced_key = get_namespaced_key(tenant_id, item.key)
    
    if redis_conn.exists(namespaced_key):
        raise HTTPException(status_code=400, detail="Key already exists")
    
    # Save the full data (value and metadata) as JSON
    data = item.model_dump()
    redis_conn.set(namespaced_key, json.dumps(data))
    
    # Set TTL if provided
    if item.ttl:
        redis_conn.expire(namespaced_key, item.ttl)
    
    return {"message": "Key created", "data": data}

@app.get("/data", response_model=KeyValueItem)
def get_item(key: str, user=Depends(get_current_active_user)):
    tenant_id = user.tenant_id
    namespaced_key = get_namespaced_key(tenant_id, key)
    print(namespaced_key)
    if not redis_conn.exists(namespaced_key):
        raise HTTPException(status_code=404, detail="Key not found")
    
    data = json.loads(redis_conn.get(namespaced_key))
    return data

@app.put("/data", response_model=KeyValueItem)
def update_item(key: str, item: KeyValueItem, user=Depends(get_current_active_user)):
    tenant_id = user.tenant_id
    namespaced_key = get_namespaced_key(tenant_id, key)
    
    if not redis_conn.exists(namespaced_key):
        raise HTTPException(status_code=404, detail="Key not found")
    
    data = item.model_dump()
    redis_conn.set(namespaced_key, json.dumps(data))
    
    if item.ttl:
        redis_conn.expire(namespaced_key, item.ttl)
    
    return data

@app.delete("/data")
def delete_item(key: str, user=Depends(get_current_active_user)):
    tenant_id = user.tenant_id
    namespaced_key = get_namespaced_key(tenant_id, key)
    
    if not redis_conn.exists(namespaced_key):
        raise HTTPException(status_code=404, detail="Key not found")
    
    redis_conn.delete(namespaced_key)
    return {"message": "Key deleted"}
