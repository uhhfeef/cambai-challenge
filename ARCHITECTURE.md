# Architecture Document

## Design Decisions

### Redis Topology Selection

The project implements a Redis master-replica setup with Sentinel for high availability. This architecture was selected for several key reasons:

1. **Reliability and Failover**: The master-replica setup with Sentinel provides automatic failover capabilities, ensuring the system remains operational even if the master node fails.

2. **Read Scalability**: While write operations are directed to the master, read operations can be distributed across replicas, improving read throughput.

3. **Operational Simplicity**: Compared to more complex solutions like Redis Cluster, the master-replica topology offers a good balance of reliability and operational simplicity, making it well-suited for this application's requirements.

### Direct Pod Connection Strategy

A key innovation in this project is the implementation of a direct pod connection strategy for Redis. This approach was developed to solve a specific challenge:

1. **Problem**: The standard Kubernetes service for Redis (`redis-service`) load balances connections between all Redis pods, including read-only replicas. This caused `ReadOnlyError` exceptions when write operations were routed to replica nodes.

2. **Solution**: The custom connection strategy:
   - Attempts direct connections to Redis pods using their stable DNS names (`redis-0.redis-headless`, etc.)
   - Tests write capability on each connection with a simple setex/delete operation
   - Falls back to the next pod if a connection fails or returns ReadOnlyError
   - Uses the Redis service with retry logic as a last resort

This approach ensures write operations always target the Redis master, even during failover events, significantly improving system reliability.

### Multi-Tenancy Implementation

The multi-tenant architecture uses key namespacing for tenant isolation:

1. **Key Namespacing**: All data keys are prefixed with the tenant ID (`tenant:{tenant_id}:data:{key}`), ensuring complete data isolation between tenants.

2. **JWT-Based Tenant Context**: The tenant ID is embedded in the JWT token and used to scope all data access, preventing cross-tenant data leakage.

3. **Efficiency**: This approach provides strong isolation while maintaining the efficiency of a single Redis deployment, avoiding the overhead of managing separate Redis instances per tenant.

### Logging Architecture

The logging pipeline uses a two-stage approach:

1. **Redis as a Buffer**: Logs are first written to Redis before being offloaded to Loki. This design:
   - Decouples log generation from log storage, improving application performance
   - Provides a reliable buffer if Loki is temporarily unavailable
   - Allows for batch processing of logs, reducing network overhead

2. **Tenant-Aware Offloading**: Logs are grouped by tenant ID during offloading, ensuring proper multi-tenancy in Loki.

3. **Asynchronous Processing**: Using Huey for background processing prevents logging operations from impacting API response times.

## Future Enhancements

### Advanced Redis Configurations

With additional time, the project would benefit from evaluating different Redis cluster configurations to address specific bottlenecks:

1. **Redis Cluster**: Implementing Redis Cluster for horizontal scaling of write operations across multiple master nodes, particularly beneficial for high-write workloads.

2. **Redis Enterprise**: Exploring Redis Enterprise features like active-active geo-distribution for multi-region deployments.

3. **Specialized Redis Modules**: Integrating modules like RedisJSON for more efficient handling of JSON data structures.

### Performance Optimizations

Several performance enhancements could be implemented:

1. **Connection Pooling**: Adding proper Redis connection pooling to reduce connection overhead, especially under high load.

2. **Caching Layer**: Implementing an application-level cache for frequently accessed data to reduce Redis load.

3. **Read/Write Splitting**: Enhancing the connection strategy to direct read operations to replicas while ensuring writes go to the master.

4. **Optimized Data Structures**: Refining the data models and Redis key structures for more efficient storage and retrieval.

### Zero-Downtime Deployments

Implementing true zero-downtime deployment capabilities:

1. **Rolling Updates**: Enhancing the Kubernetes deployment to use rolling updates with proper health checks.

2. **Blue-Green Deployments**: Setting up blue-green deployment capabilities for major version changes.

3. **Database Migration Strategy**: Developing a robust approach for handling schema changes without downtime.

### Security Enhancements

Additional security measures that could be implemented:

1. **Enhanced API Key Management**: Implementing rotation policies, usage limits, and fine-grained permissions for API keys.

2. **Encryption**: Adding encryption for sensitive data at rest in Redis.

3. **Network Policies**: Implementing Kubernetes network policies to restrict pod-to-pod communication.

4. **Secret Management**: Integrating with external secret management solutions like HashiCorp Vault or AWS Secrets Manager.


Future work would focus on evaluating different Redis cluster configurations to address specific performance bottlenecks, implementing multi-region support, and enhancing security features for production deployments.
