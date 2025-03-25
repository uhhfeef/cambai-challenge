import requests
import json

# URL for the token endpoint
url = "http://localhost:54120/token"  # Using kubectl port-forwarded URL

# Credentials for authentication
data = {
    "username": "user1",
    "password": "secret"
}

# Make the request
try:
    response = requests.post(url, data=data, timeout=10)
except requests.exceptions.RequestException as e:
    print(f"Connection error: {e}")
    exit(1)

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON response
    token_data = response.json()
    print("Access Token:", token_data["access_token"])
    print("Token Type:", token_data["token_type"])
    
    # Save token to a file for load testing
    with open("access_token.txt", "w") as f:
        f.write(token_data["access_token"])
    
    print("Token saved to access_token.txt")
else:
    print("Failed to get token:", response.status_code)
    print(response.text)
