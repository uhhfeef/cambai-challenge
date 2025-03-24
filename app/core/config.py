import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Security configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
SECRET_KEY = os.getenv("SECRET_KEY")

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Loki configuration
LOKI_HOST = os.getenv('LOKI_HOST', 'loki-gateway')
LOKI_PORT = os.getenv('LOKI_PORT', '80')
LOKI_URL = f'http://{LOKI_HOST}:{LOKI_PORT}/loki/api/v1/push'
