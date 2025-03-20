from huey import RedisHuey
# from main import get_namespaced_key
import json
from datetime import datetime

# Initialize Huey with Redis connection
huey = RedisHuey(host="localhost", port=6379, db=2)

@huey.task()
def audit_log_expiration(key: str, tenant_id: str):
    import redis
    
    # Create Redis connections
    main_redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    logs_redis = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
    
    # Log the key expiration
    logs_entry = json.dumps({
        "timestamp": datetime.now().isoformat(),
        "action": "key_expiration",
        "key": key,
        "tenant_id": tenant_id,
    })
    logs_redis.lpush("logs:audit", logs_entry)
    
    print(f"Audit Log: Key '{tenant_id}:{key}' has expired.")
