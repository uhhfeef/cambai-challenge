from pydantic import BaseModel
from typing import Optional

class APIKey(BaseModel):
    key_id: str
    name: str
    key_value: str
    created_at: str
    last_used: Optional[str] = None

class APIKeyCreate(BaseModel):
    name: str
