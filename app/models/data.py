from pydantic import BaseModel
from typing import Optional, Any, Dict

class KeyValueItem(BaseModel):
    value: Any
    ttl: Optional[int] = None
    metadata: Optional[Dict] = None
