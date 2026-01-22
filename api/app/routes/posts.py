from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Post, Entity, PostEntity
from app.schemas import PostResponse, PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[PostResponse])
async def list_posts(
    listener_id: int | None = None,
    platform: str | None = None,
    sentiment_label: str | None = None,
    author_handle: str | None = None,
    search: str | None = Query(None, description="Search in post content"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """List posts with filtering and pagination."""
    query = select(Post).order_by(Post.collected_at.desc())

    # Apply filters
    if listener_id:
        query = query.where(Post.listener_id == listener_id)
    if platform:
        query = query.where(Post.platform == platform)
    if sentiment_label:
        query = query.where(Post.sentiment_label == sentiment_label)
    if author_handle:
        query = query.where(Post.author_handle.ilike(f"%{author_handle}%"))
    if search:
        query = query.where(Post.content.ilike(f"%{search}%"))
    if date_from:
        query = query.where(Post.collected_at >= date_from)
    if date_to:
        query = query.where(Post.collected_at <= date_to)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    posts = result.scalars().all()

    return PaginatedResponse(
        items=posts,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific post by ID."""
    result = await session.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete a specific post."""
    result = await session.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    await session.delete(post)
    await session.commit()
    return {"status": "deleted", "id": post_id}


@router.get("/{post_id}/entities")
async def get_post_entities(
    post_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get entities for a specific post."""
    result = await session.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    query = (
        select(
            PostEntity.id,
            PostEntity.confidence,
            PostEntity.start_pos,
            PostEntity.end_pos,
            Entity.id.label("entity_id"),
            Entity.entity_type,
            Entity.entity_text,
            Entity.display_text,
        )
        .join(Entity, PostEntity.entity_id == Entity.id)
        .where(PostEntity.post_id == post_id)
    )

    result = await session.execute(query)
    rows = result.all()

    return [
        {
            "id": row.id,
            "entity_id": row.entity_id,
            "entity_type": row.entity_type,
            "entity_text": row.entity_text,
            "display_text": row.display_text,
            "confidence": row.confidence,
            "start_pos": row.start_pos,
            "end_pos": row.end_pos,
        }
        for row in rows
    ]
