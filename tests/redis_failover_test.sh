#!/bin/bash
# Script to test Redis failover capabilities

set -e

echo "===== Redis Failover Test ====="

# Check if Redis pods are running
echo "Checking Redis pods..."
kubectl get pods -l app=redis

# Count Redis pods
REDIS_POD_COUNT=$(kubectl get pods -l app=redis | grep -c Running || echo "0")
echo "Number of Redis pods: $REDIS_POD_COUNT"

if [ "$REDIS_POD_COUNT" -lt "2" ]; then
    echo "ERROR: You need at least 2 Redis pods for failover testing."
    echo "Please deploy Redis with replication enabled."
    exit 1
fi

# Get Redis pods
REDIS_PODS=$(kubectl get pods -l app=redis -o jsonpath='{.items[*].metadata.name}')
echo "Redis pods: $REDIS_PODS"

# Check Redis replication status
echo -e "\nChecking Redis replication status before failover..."
for pod in $REDIS_PODS; do
    echo -e "\n--- Pod: $pod ---"
    kubectl exec $pod -- redis-cli info replication
done

# Set a test value in Redis
echo -e "\nSetting test value in Redis..."
TEST_KEY="failover_test_key"
TEST_VALUE="value_$(date +%s)"

# Find the master pod first
MASTER_POD=""
for pod in $REDIS_PODS; do
    ROLE=$(kubectl exec $pod -- redis-cli info replication | grep role | cut -d: -f2 | tr -d '[:space:]')
    if [ "$ROLE" = "master" ]; then
        MASTER_POD=$pod
        echo "Found master pod: $MASTER_POD"
        break
    fi
done

if [ -z "$MASTER_POD" ]; then
    echo "ERROR: Could not identify Redis master pod"
    exit 1
fi

# Set the test value on the master
kubectl exec $MASTER_POD -- redis-cli set $TEST_KEY $TEST_VALUE
echo "Set $TEST_KEY = $TEST_VALUE on master pod $MASTER_POD"

# Verify the value is replicated
echo -e "\nVerifying value is replicated to all Redis instances..."
for pod in $REDIS_PODS; do
    echo "Checking $pod..."
    VALUE=$(kubectl exec $pod -- redis-cli get $TEST_KEY)
    echo "Value from $pod: $VALUE"
    if [ "$VALUE" != "$TEST_VALUE" ]; then
        echo "WARNING: Value not properly replicated to $pod"
    fi
done

# Master pod was already identified when setting the test value

# Kill the master pod
echo -e "\nKilling Redis master pod: $MASTER_POD..."
kubectl delete pod $MASTER_POD &

# Wait a moment for failover to begin
sleep 2

# Check if we can still access the data during failover
echo -e "\nChecking data availability during failover..."
for i in {1..10}; do
    echo "Attempt $i..."
    
    # Try to access data from remaining pods
    for pod in $REDIS_PODS; do
        if [ "$pod" != "$MASTER_POD" ]; then
            echo "Checking $pod..."
            VALUE=$(kubectl exec $pod -- redis-cli get $TEST_KEY 2>/dev/null || echo "error")
            echo "Value from $pod: $VALUE"
            if [ "$VALUE" = "$TEST_VALUE" ]; then
                echo "SUCCESS: Data still accessible from $pod during failover!"
                FAILOVER_SUCCESS=true
            fi
        fi
    done
    
    if [ "$FAILOVER_SUCCESS" = "true" ]; then
        break
    fi
    
    echo "Waiting for failover to complete..."
    sleep 3
done

# Wait for the pod to be recreated
echo -e "\nWaiting for Redis pod to be recreated..."
kubectl wait --for=condition=ready pod $MASTER_POD --timeout=60s

# Check the new replication status
echo -e "\nChecking Redis replication status after failover..."
for pod in $REDIS_PODS; do
    echo -e "\n--- Pod: $pod ---"
    kubectl exec $pod -- redis-cli info replication
done

# Verify data is still available after failover
echo -e "\nVerifying data is still available after failover..."
for pod in $REDIS_PODS; do
    echo "Checking $pod..."
    VALUE=$(kubectl exec $pod -- redis-cli get $TEST_KEY)
    echo "Value from $pod: $VALUE"
    if [ "$VALUE" != "$TEST_VALUE" ]; then
        echo "WARNING: Data lost in $pod after failover!"
    else
        echo "SUCCESS: Data preserved in $pod after failover!"
    fi
done

echo -e "\n===== Redis Failover Test Complete ====="
if [ "$FAILOVER_SUCCESS" = "true" ]; then
    echo "RESULT: Redis failover was SUCCESSFUL!"
else
    echo "RESULT: Redis failover FAILED!"
    echo "To enable proper Redis failover, update your Redis configuration with replication settings."
fi
