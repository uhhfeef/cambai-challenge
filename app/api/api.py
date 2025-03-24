from fastapi import APIRouter

from app.api.routes import auth, api_keys, data, utils

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, tags=["authentication"])
api_router.include_router(api_keys.router, tags=["api keys"])
api_router.include_router(data.router, tags=["data"])
api_router.include_router(utils.router, tags=["utilities"])
