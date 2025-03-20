from huey import RedisHuey
from main import get_namespaced_key

# Initialize Huey with Redis connection
huey = RedisHuey(host="localhost", port=6379, db=1)

@huey.task()
def audit_log_expiration(key: str, tenant_id: str, redis_conn):
    namespaced_key = get_namespaced_key(tenant_id, key)
    
    # checking if it exists 
    if redis_conn.exists(namespaced_key):
        redis_conn.delete(namespaced_key)
    print(f"Audit Log: Key '{tenant_id}:{key}' has expired.")
