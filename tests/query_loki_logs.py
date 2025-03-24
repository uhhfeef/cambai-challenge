# to verify logs were successfully stored in Loki

#!/usr/bin/env python3
import requests
import json
import argparse
from datetime import datetime, timedelta
import os

def format_timestamp(ts_str):
    """Convert nanosecond timestamp string to human-readable format."""
    ts_ns = int(ts_str)
    ts_s = ts_ns / 1_000_000_000
    dt = datetime.fromtimestamp(ts_s)
    return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

def query_loki(tenant_id, job, action=None, limit=100, hours=1):
    """Query Loki for logs with the specified parameters."""
    # Loki configuration
    LOKI_HOST = os.getenv('LOKI_HOST', 'loki-gateway')
    LOKI_PORT = os.getenv('LOKI_PORT', '80')
    LOKI_URL = f'http://{LOKI_HOST}:{LOKI_PORT}/loki/api/v1/query_range'
    
    # Calculate time range (last n hours)
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # Convert to nanoseconds for Loki
    end_time_ns = int(end_time.timestamp() * 1_000_000_000)
    start_time_ns = int(start_time.timestamp() * 1_000_000_000)
    
    # Build query
    query = f'{{job="{job}"'
    if action:
        query += f', action="{action}"'
    query += '}'
    
    # Query parameters
    params = {
        'query': query,
        'start': start_time_ns,
        'end': end_time_ns,
        'limit': limit
    }
    
    # Headers with tenant ID
    headers = {
        'X-Scope-OrgID': tenant_id
    }
    
    try:
        response = requests.get(LOKI_URL, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

def print_logs(data):
    """Print logs in a readable format."""
    if not data or 'data' not in data or 'result' not in data['data']:
        print("No logs found or invalid response format")
        return
    
    results = data['data']['result']
    if not results:
        print("No logs found matching the query")
        return
    
    for stream in results:
        stream_labels = stream['stream']
        print(f"\n=== Stream: {json.dumps(stream_labels)} ===")
        
        for value in stream['values']:
            timestamp, log_line = value
            formatted_time = format_timestamp(timestamp)
            
            # Try to parse and pretty-print JSON log
            try:
                log_data = json.loads(log_line)
                print(f"{formatted_time} | {json.dumps(log_data, indent=2)}")
            except:
                print(f"{formatted_time} | {log_line}")
        
        print("=" * 80)

def main():
    parser = argparse.ArgumentParser(description='Query logs from Loki')
    parser.add_argument('--tenant', default='tenant1', help='Tenant ID')
    parser.add_argument('--job', default='audit_logs', help='Job label')
    parser.add_argument('--action', help='Action label (optional)')
    parser.add_argument('--limit', type=int, default=100, help='Maximum number of logs to return')
    parser.add_argument('--hours', type=int, default=1, help='Query logs from the last N hours')
    
    args = parser.parse_args()
    
    print(f"Querying Loki for logs with job={args.job}, tenant={args.tenant}, last {args.hours} hours...")
    data = query_loki(args.tenant, args.job, args.action, args.limit, args.hours)
    if data:
        print_logs(data)

if __name__ == '__main__':
    main()
