#!/bin/bash

echo "Starting monitoring..."
echo "Press Ctrl+C to stop monitoring"

while true; do
    clear
    echo "=== Pods ==="
    kubectl get pods
    
    echo ""
    echo "=== HPA ==="
    kubectl get hpa
    
    echo ""
    echo "=== Pod CPU/Memory Usage ==="
    kubectl top pods
    
    sleep 5
done
