from fastapi import FastAPI
from app.api.api import api_router
from app.db.redis import init_redis_db

app = FastAPI(title="Multi-tenant API Key Management System")

# Include all routes from the API router
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    # Initialize the Redis database
    init_redis_db()
