import os
import uuid
import redis

def create_redis_client(db=0, return_connection_info=False):
    """
    Create a Redis client that attempts to connect directly to Redis pods
    and tests write capability to ensure it's connecting to the master.
    
    Args:
        db (int): Redis database number
        return_connection_info (bool): If True, returns a tuple of (client, host, port)
                                      If False, returns just the client
    
    Returns:
        If return_connection_info is True:
            Tuple of (redis.Redis, str, int): Redis client, host, and port
        Otherwise:
            redis.Redis: Redis client connected to a writable Redis instance
    """
    # Try to connect directly to Redis pods by their stable DNS names
    redis_hosts = [
        'redis-0.redis-headless',  # Try the initial master first
        'redis-1.redis-headless',  # Then try replicas
        'redis-2.redis-headless',
        os.getenv('REDIS_HOST', 'redis')  # Fallback to the service
    ]
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    
    # Try each host until we find one that works for writes
    for host in redis_hosts:
        try:
            client = redis.Redis(host=host, port=redis_port, db=db, decode_responses=True, socket_timeout=2.0)
            
            # Test if we can write to this Redis instance
            test_key = f"write_test_{uuid.uuid4()}"
            client.setex(test_key, 5, "1")
            client.delete(test_key)
            
            print(f"Successfully connected to Redis at {host}:{redis_port} (db={db})")
            if return_connection_info:
                return client, host, redis_port
            return client
        except (redis.exceptions.ConnectionError, redis.exceptions.ReadOnlyError) as e:
            print(f"Failed to connect to Redis at {host}:{redis_port}: {str(e)}")
            continue
    
    # If all direct connections fail, fall back to the service with retries
    host = os.getenv('REDIS_HOST', 'redis-service')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    print(f"All direct Redis connections failed, falling back to service {host}")
    
    client = redis.Redis(
        host=host,
        port=redis_port,
        db=db,
        decode_responses=True,
        retry_on_timeout=True,
        retry=redis.retry.Retry(max_attempts=3)
    )
    
    if return_connection_info:
        return client, host, redis_port
    return client
