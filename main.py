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

from models import Token, TokenData, APIKey, Tenant, TenantCreate, User, UserInDB, UserCreate, APIKeyCreate
from database import fake_tenants_db, fake_users_db, fake_api_keys_db

# Load environment variables from .env file
load_dotenv()

# Security configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
SECRET_KEY = os.getenv("SECRET_KEY", "a_default_secret_key_for_development_only")

app = FastAPI(title="Multi-tenant API Key Management System")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



def get_tenant(tenant_id: str):
    if tenant_id in fake_tenants_db:
        tenant_dict = fake_tenants_db[tenant_id]
        return Tenant(**tenant_dict)
    return None

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None

def get_api_keys_for_tenant(tenant_id: str) -> List[APIKey]:
    keys = []
    for key_id, key_data in fake_api_keys_db.items():
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

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
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
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# API endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
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

@app.post("/tenants", response_model=Tenant)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    # In a real app, you might want to check if the user has admin privileges
    tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"
    tenant_dict = tenant_data.dict()
    tenant_dict.update({
        "tenant_id": tenant_id,
        "created_at": datetime.now(timezone.utc)
    })
    fake_tenants_db[tenant_id] = tenant_dict
    return Tenant(**tenant_dict)

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
        "created_at": datetime.now(timezone.utc),
        "last_used": None,
        "tenant_id": current_user.tenant_id
    }
    
    fake_api_keys_db[key_id] = api_key
    print("API Keys: ", fake_api_keys_db)
    
    # Return without tenant_id in the response
    return APIKey(**{k: v for k, v in api_key.items() if k != "tenant_id"})

# User management endpoints
@app.post("/users", response_model=User)
async def create_user(
    user_data: UserCreate,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    # Check if the user is creating a user in their own tenant
    if user_data.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=403, 
            detail="You can only create users in your own tenant"
        )
    
    # Check if username already exists
    if user_data.username in fake_users_db:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    # Create the new user
    hashed_password = get_password_hash(user_data.password)
    user_dict = user_data.dict()
    user_dict.pop("password")  # Remove plain password
    user_dict["hashed_password"] = hashed_password
    user_dict["disabled"] = False
    
    fake_users_db[user_data.username] = user_dict
    
    return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})

# Example protected endpoint that uses tenant isolation
@app.get("/data", response_model=dict)
async def get_tenant_data(current_user: Annotated[User, Depends(get_current_active_user)]):
    return {
        "tenant_id": current_user.tenant_id,
        "message": f"This is private data for tenant: {current_user.tenant_id}"
    }

