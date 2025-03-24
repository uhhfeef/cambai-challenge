# Multi-tenant API Key Management System

A robust, Kubernetes-deployed FastAPI application for managing API keys with multi-tenancy support, Redis-based storage, and comprehensive audit logging to Loki.

## Project Overview

This project implements a secure, scalable API key management system with the following features:

- **Multi-tenancy**: Complete data isolation between different tenants
- **High Availability**: Redis master-replica setup with automatic failover
- **Comprehensive Logging**: All operations are logged and stored in Loki for analysis
- **Kubernetes Deployment**: Complete K8s configuration for all components
- **Horizontal Scaling**: Support for scaling API instances based on load

## Architecture

### System Diagram

![Architecture Diagram](diagram.png)

### Components

1. **FastAPI Application**: Core REST API service with multi-tenant support
2. **Redis Database**: Primary data store with master-replica setup for high availability
3. **Redis Sentinel**: Monitors Redis instances and handles automatic failover
4. **Huey Task Queue**: Background task processing for log offloading
5. **Loki**: Log aggregation system with multi-tenant support
6. **Grafana**: Visualization for logs and metrics
7. **Prometheus**: Metrics collection and alerting

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
