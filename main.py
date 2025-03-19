from typing import Annotated, Dict, List, Optional
import uuid
from fastapi import Depends, FastAPI, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from jwt.exceptions import InvalidTokenError
import jwt
from datetime import datetime, timedelta, timezone

# Security configuration
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(title="Multi-tenant API Key Management System")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Models
class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    username: Optional[str] = None
    tenant_id: Optional[str] = None

class APIKey(BaseModel):
    key_id: str
    key_value: str
    name: str
    created_at: datetime
    last_used: Optional[datetime] = None

class Tenant(BaseModel):
    tenant_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    
class TenantCreate(BaseModel):
    name: str
    description: Optional[str] = None

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    tenant_id: str

class UserInDB(User):
    hashed_password: str

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    tenant_id: str

class APIKeyCreate(BaseModel):
    name: str

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
    # This would fetch data specific to the tenant
    return {
        "tenant_id": current_user.tenant_id,
        "message": f"This is private data for tenant: {current_user.tenant_id}"
    }

