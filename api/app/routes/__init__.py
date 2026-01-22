from fastapi import APIRouter

from app.routes import listeners, posts, entities, analytics

api_router = APIRouter()

api_router.include_router(listeners.router, prefix="/listeners", tags=["Listeners"])
api_router.include_router(posts.router, prefix="/posts", tags=["Posts"])
api_router.include_router(entities.router, prefix="/entities", tags=["Entities"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
