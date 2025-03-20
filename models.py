from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel
from typing import List

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

class KeyValueItem(BaseModel):
    value: str
    ttl: Optional[int] = None          
    version: Optional[int] = None      
    tags: Optional[List[str]] = None   
