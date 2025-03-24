#!/bin/bash

echo "Starting HPA monitoring..."
echo "Press Ctrl+C to stop monitoring"

while true; do
    clear
    echo "=== HPA Status ==="
    kubectl get hpa fastapi-hpa
    
    echo ""
    echo "=== Pod Status ==="
    kubectl get pods
    
    echo ""
    echo "=== Pod CPU/Memory Usage ==="
    kubectl top pods
    
    sleep 5
done
