"""
Template view routes for the frontend UI.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session

router = APIRouter()

# Templates directory
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@router.get("/")
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    """Main dashboard page."""
    return templates.TemplateResponse(
        "pages/dashboard.html",
        {"request": request, "page_title": "Dashboard"},
    )


@router.get("/listeners")
async def listeners_page(request: Request, session: AsyncSession = Depends(get_session)):
    """Listeners management page."""
    return templates.TemplateResponse(
        "pages/listeners.html",
        {"request": request, "page_title": "Listeners"},
    )


@router.get("/posts")
async def posts_page(request: Request, session: AsyncSession = Depends(get_session)):
    """Posts browser page."""
    return templates.TemplateResponse(
        "pages/posts.html",
        {"request": request, "page_title": "Posts"},
    )


@router.get("/entities")
async def entities_page(request: Request, session: AsyncSession = Depends(get_session)):
    """Entities explorer page."""
    return templates.TemplateResponse(
        "pages/entities.html",
        {"request": request, "page_title": "Entities"},
    )
