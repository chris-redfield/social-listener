import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.routes import api_router
from app.routes.views import router as views_router

# Template and static directories
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.api_title,
    description="""
## Social Listener - Management API

Monitor brand mentions across social media platforms.

### Features
- **Listeners**: Create and manage monitoring rules
- **Posts**: View and filter collected posts
- **Entities**: Browse extracted named entities
- **Analytics**: Sentiment analysis, timelines, and engagement stats

### Platforms Supported
- Bluesky (AT Protocol)
- Threads (coming soon)
    """,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Include API routes
app.include_router(api_router, prefix="/api")

# Include view routes (templates)
app.include_router(views_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "api"}


@app.get("/api-info")
async def api_info():
    """API info endpoint (root now serves dashboard)."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
    }
