#!/bin/bash

echo "Cleaning up Kubernetes resources..."

# Delete the HPA
kubectl delete hpa fastapi-hpa

# Delete the FastAPI deployment and service
kubectl delete -f fastapi-deployment.yaml

# Delete the Redis deployment and service
kubectl delete -f redis-deployment.yaml

echo "All resources have been deleted."
