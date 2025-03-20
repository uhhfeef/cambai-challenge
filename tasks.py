from huey import RedisHuey
# from main import get_namespaced_key
import json
from datetime import datetime
import redis

# Initialize Huey with Redis connection
huey = RedisHuey(host="redis", port=6379, db=2)
logs_redis = redis.Redis(host='redis', port=6379, db=1, decode_responses=True)

@huey.task()
def audit_log_expiration(key: str, tenant_id: str):
    import redis
    
    # Create Redis connections
    
    # Log the key expiration
    logs_entry = json.dumps({
        "timestamp": datetime.now().isoformat(),
        "action": "key_expiration",
        "key": key,
        "tenant_id": tenant_id,
    })
    logs_redis.lpush("logs:audit", logs_entry)
    
    print(f"Audit Log: Key '{tenant_id}:{key}' has expired.")

# # Huey background task for audit log offloading
# @huey.periodic_task(crontab(minute='*/15'))
# def offload_audit_logs():
#     logs = []
#     while True:
#         log_data = logs_redis.rpop('logs:audit')
#         if log_data is None:
#             break
#         logs.append(json.loads(log_data))
    
#     if not logs:
#         return

#         # Prepare bulk actions to index logs in Elasticsearch
#     actions = [
#         {
#             "_index": "audit-logs",
#             "_source": log,
#         }
#         for log in logs
#     ]
    
#     # Bulk index the logs
#     success, _ = bulk(elasticsearch_client, actions)
#     print(f"Offloaded {success} audit logs to Elasticsearch.")