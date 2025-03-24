# Multi-tenant API Key Management System

A robust, Kubernetes-deployed FastAPI application for managing API keys with multi-tenancy support, Redis-based storage, and comprehensive audit logging to Loki.

## Project Overview

This project implements a secure, scalable API key management system with the following features:

- **Multi-tenancy**: Complete data isolation between different tenants
- **High Availability**: Redis master-replica setup with automatic failover
- **Comprehensive Logging**: All operations are logged and stored in Loki for analysis
- **Kubernetes Deployment**: Complete K8s configuration for all components
- **Horizontal Scaling**: Support for scaling API instances based on load

## Setup & Deployment Instructions

### Local Development Setup

1. **Clone the repository and set up virtual environment**
   ```bash
   git clone <repository-url>
   cd cambai-challenge
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start a local Redis instance**
   ```bash
   redis-server
   ```

4. **Run the FastAPI application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Kubernetes Deployment

1. **Start Minikube (for local Kubernetes)**
   ```bash
   minikube start
   ```

2. **Configure terminal to use Minikube's Docker daemon**
   ```bash
   eval $(minikube docker-env)
   ```

3. **Build the Docker image**
   ```bash
   docker build -t uhhfeef/fastapi-app:latest .
   ```

4. **Deploy Redis and Sentinel**
   ```bash
   kubectl apply -f k8s/redis/redis-configmap.yaml
   kubectl apply -f k8s/redis/redis-statefulset.yaml
   kubectl apply -f k8s/redis/sentinel-statefulset.yaml
   ```

5. **Deploy Loki and Grafana**
   ```bash
   kubectl apply -f k8s/loki/loki-config.yaml
   kubectl apply -f k8s/loki/loki-deployment.yaml
   kubectl apply -f k8s/loki/loki-services.yaml
   kubectl apply -f k8s/grafana/grafana-config.yaml
   kubectl apply -f k8s/grafana/grafana-deployment.yaml
   kubectl apply -f k8s/grafana/grafana-service.yaml
   ```

6. **Deploy FastAPI and Huey worker**
   ```bash
   kubectl apply -f k8s/fastapi/fastapi-deployment.yaml
   kubectl apply -f k8s/fastapi/fastapi-service.yaml
   kubectl apply -f k8s/fastapi/huey-deployment.yaml
   ```

7. **Access the application**
   ```bash
   minikube service fastapi-service
   ```

## Architecture

### System Diagram

![Architecture Diagram](diagram.png)

### Request Flow

The system architecture follows these key flows:

1. **API Requests**: Client requests are received by the FastAPI application, which handles authentication, request validation, and routing.

2. **Data Storage**: The FastAPI application interacts with Redis for all data operations:
   - Redis is configured in a master-replica setup (3 nodes) for high availability
   - Redis Sentinel monitors the Redis nodes and handles automatic failover
   - A custom connection strategy ensures write operations always target the Redis master

3. **Background Processing**: 
   - Huey task queue handles asynchronous operations like log offloading
   - Background tasks run on a separate worker deployment for better resource isolation

4. **Logging Pipeline**:
   - All operations generate audit logs stored temporarily in Redis
   - Logs are periodically offloaded to Loki by Huey background tasks
   - Grafana provides visualization of logs and metrics

### Components

1. **FastAPI Application**: Core REST API service with multi-tenant support
2. **Redis Database**: Primary data store with master-replica setup for high availability
3. **Redis Sentinel**: Monitors Redis instances and handles automatic failover
4. **Huey Task Queue**: Background task processing for log offloading
5. **Loki**: Log aggregation system with multi-tenant support
6. **Grafana**: Visualization for logs and metrics
7. **Prometheus**: Metrics collection and alerting

## Authentication Workflow

### JWT Token Generation and Validation

1. **Token Generation**:
   - Users authenticate via the `/token` endpoint using username/password credentials
   - The system verifies credentials against the Redis database
   - Upon successful authentication, a JWT token is generated containing:
     - User identifier (`sub` claim)
     - Tenant ID (`tenant_id` claim)
     - Expiration time (`exp` claim)
   - The token is signed using HMAC-SHA256 (HS256) with a secret key

2. **Token Validation**:
   - All protected endpoints use OAuth2 password bearer authentication
   - The JWT token is extracted from the Authorization header
   - The system verifies the token signature and checks for expiration
   - User information is retrieved from Redis based on the username in the token

3. **Multi-tenant Data Access**:
   - The tenant ID from the JWT token is used to scope all data access
   - All data keys are namespaced with the tenant ID (e.g., `tenant:{tenant_id}:data:{key}`)
   - This ensures complete data isolation between tenants

### API Key Authentication

In addition to JWT authentication, the system supports API key-based authentication:

- API keys are created and managed through the `/api-keys` endpoints
- Each API key is associated with a specific tenant
- API keys are stored securely in Redis with proper hashing

## Scalability Discussion

### High Throughput Handling

1. **Horizontal Scaling**:
   - The FastAPI application is designed to be stateless, allowing for easy horizontal scaling
   - While an HPA configuration file exists in the repository, it hasn't been implemented yet due to time constraints
   - Future work would include implementing the Horizontal Pod Autoscaler to automatically scale pods based on CPU utilization (3-10 replicas targeting 80% CPU)
   - Currently, manual scaling can be performed using `kubectl scale deployment fastapi-app --replicas=<count>`
   - The application can be scaled independently from the background workers

2. **Efficient Redis Connection Pool**:
   - Connection pooling is used to minimize the overhead of establishing new Redis connections
   - The custom Redis connection strategy ensures optimal use of the Redis cluster

3. **Background Processing**:
   - CPU-intensive and I/O-bound operations are offloaded to background tasks
   - Log processing is handled asynchronously to prevent blocking API requests

### Potential Bottlenecks

1. **Redis Master-Replica Setup**:
   - While Redis provides high performance, having a single master node can become a bottleneck
   - Potential solution: Implement Redis Cluster for sharding across multiple master nodes

2. **Log Processing**:
   - High volume of operations can generate a large number of logs
   - Current solution: Batch processing of logs and periodic offloading
   - Future improvement: Implement log streaming for real-time processing

3. **Authentication Overhead**:
   - JWT validation on every request adds some overhead
   - Potential optimization: Implement token caching or session-based authentication for high-frequency API consumers

### Key Features

#### Redis Master-Replica Connection Strategy

The application implements a sophisticated Redis connection strategy that:

- Attempts to connect directly to individual Redis pods by their stable DNS names
- Tests write capability on each connection with a simple setex/delete operation
- Falls back to the next pod if a connection fails or returns ReadOnlyError
- Uses the Redis service with retry logic as a last resort

This ensures reliable write operations even during Redis master-replica failovers.

#### Comprehensive Audit Logging

All data operations (create, read, update, delete) are logged with:

- Timestamp
- Action type
- Tenant ID
- Username
- Operation-specific details

Logs are stored in Redis and periodically offloaded to Loki via Huey tasks, with proper multi-tenancy support.

## API Endpoints

### Authentication

- **POST /token**: Obtain JWT access token
- **GET /users/me**: Get current user information

### Data Operations

- **POST /data**: Create a new key-value item
- **GET /data/{key}**: Retrieve a key-value item
- **PUT /data/{key}**: Update a key-value item
- **DELETE /data/{key}**: Delete a key-value item

### API Key Management

- **POST /api-keys**: Create a new API key
- **GET /api-keys**: List all API keys for the tenant
- **DELETE /api-keys/{key_id}**: Delete an API key

## Deployment

The application is designed to be deployed on Kubernetes with the following components:

### FastAPI Application

```yaml
# FastAPI Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-app
spec:
  replicas: 3 
  selector:
    matchLabels:
      app: fastapi
  template:
    metadata:
      labels:
        app: fastapi
    spec:
      containers:
      - name: fastapi
        image: uhhfeef/fastapi-app:latest
        env:
        - name: REDIS_HOST
          value: "redis-service"
        - name: REDIS_PORT
          value: "6379"
        - name: LOKI_HOST
          value: "loki-gateway"
        - name: LOKI_PORT
          value: "80"
```

### Redis & Sentinel

The Redis setup includes:

- StatefulSet with 3 replicas (1 master, 2 replicas)
- Sentinel for automatic failover
- Persistent volume claims for data durability
- AOF persistence enabled for immediate data durability

### Loki & Grafana

- Loki configured for multi-tenant log storage
- Grafana dashboards for log visualization
- Proper tenant ID headers (X-Scope-OrgID) for multi-tenancy

## Monitoring and Querying Logs

### Basic Loki Queries

- All tenant logs: `{job="audit_logs", tenant_id="tenant1"}`
- Action-specific queries: `{job="audit_logs", tenant_id="tenant1", action="create_key"}`
- Other available actions: `get_key`, `update_key`, `delete_key`, `create_api_key`

## Development Setup

### Prerequisites

- Docker
- Kubernetes (Minikube or similar)
- Python 3.9+
- Redis CLI (for debugging)

### Local Development

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Start a local Redis instance:
   ```
   redis-server
   ```
4. Run the FastAPI application:
   ```
   uvicorn app.main:app --reload
   ```

### Building and Deploying to Kubernetes

1. Configure Minikube to use the local Docker daemon:
   ```
   eval $(minikube docker-env)
   ```

2. Build the Docker image:
   ```
   docker build -t uhhfeef/fastapi-app:latest .
   ```

3. Deploy the application to Kubernetes:
   ```
   kubectl apply -f k8s/redis/
   kubectl apply -f k8s/loki/
   kubectl apply -f k8s/grafana/
   kubectl apply -f k8s/fastapi/
   ```

## Resilience Testing

The project includes a resilience testing script that:

1. Generates test logs
2. Triggers log offloading to Loki
3. Verifies logs are properly stored and retrievable
4. Tests Redis failover scenarios

To run the resilience test:
```
./resilience_test.sh
```

## Project Structure

```
.
├── app/
│   ├── api/
│   │   └── routes/       # API endpoints
│   ├── core/             # Core functionality (auth, security)
│   ├── db/               # Database connections and utilities
│   ├── models/           # Pydantic models
│   ├── tasks/            # Background tasks (Huey)
│   └── utils/            # Utility functions
├── k8s/                  # Kubernetes configuration
│   ├── fastapi/          # FastAPI deployment
│   ├── grafana/          # Grafana configuration
│   ├── loki/             # Loki configuration
│   ├── prometheus/       # Prometheus configuration
│   └── redis/            # Redis and Sentinel configuration
└── tests/                # Test suite
```

## Security Features

- JWT-based authentication
- Multi-tenant data isolation
- API key management with proper hashing
- Secure Redis connection strategy
