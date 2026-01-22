from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import io
import json

from app.database import get_session
from app.models import Post, Entity, PostEntity
from app.schemas import PostResponse, PaginatedResponse

router = APIRouter()


def build_post_filters(
    listener_id: int | None,
    platform: str | None,
    sentiment_label: str | None,
    author_handle: str | None,
    days: int | None,
):
    """Build common filters for posts queries."""
    filters = []
    if listener_id:
        filters.append(Post.listener_id == listener_id)
    if platform:
        filters.append(Post.platform == platform)
    if sentiment_label:
        filters.append(Post.sentiment_label == sentiment_label)
    if author_handle:
        filters.append(Post.author_handle.ilike(f"%{author_handle}%"))
    if days:
        start_date = datetime.utcnow() - timedelta(days=days)
        filters.append(Post.post_created_at.isnot(None))
        filters.append(Post.post_created_at >= start_date)
    return filters


@router.get("", response_model=PaginatedResponse[PostResponse])
async def list_posts(
    listener_id: int | None = None,
    platform: str | None = None,
    sentiment_label: str | None = None,
    author_handle: str | None = None,
    days: int | None = Query(None, ge=1, le=365, description="Filter to last N days"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """List posts with filtering and pagination."""
    # Order by post creation date (when post was made), not when we collected it
    query = select(Post).order_by(Post.post_created_at.desc().nullslast())

    # Apply filters
    filters = build_post_filters(listener_id, platform, sentiment_label, author_handle, days)
    for f in filters:
        query = query.where(f)

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


@router.get("/export/csv")
async def export_posts_csv(
    listener_id: int | None = None,
    platform: str | None = None,
    sentiment_label: str | None = None,
    author_handle: str | None = None,
    days: int | None = Query(None, ge=1, le=365, description="Filter to last N days"),
    session: AsyncSession = Depends(get_session),
):
    """Export posts as CSV file."""
    query = select(Post).order_by(Post.post_created_at.desc().nullslast())

    filters = build_post_filters(listener_id, platform, sentiment_label, author_handle, days)
    for f in filters:
        query = query.where(f)

    result = await session.execute(query)
    posts = result.scalars().all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "id", "platform", "author_handle", "author_display_name", "content",
        "post_url", "likes_count", "replies_count", "reposts_count",
        "sentiment_label", "sentiment_score", "post_created_at", "collected_at"
    ])

    # Data rows
    for post in posts:
        writer.writerow([
            post.id,
            post.platform,
            post.author_handle,
            post.author_display_name,
            post.content,
            post.post_url,
            post.likes_count,
            post.replies_count,
            post.reposts_count,
            post.sentiment_label,
            post.sentiment_score,
            post.post_created_at.isoformat() if post.post_created_at else "",
            post.collected_at.isoformat() if post.collected_at else "",
        ])

    output.seek(0)

    # Generate filename with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"posts_export_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/json")
async def export_posts_json(
    listener_id: int | None = None,
    platform: str | None = None,
    sentiment_label: str | None = None,
    author_handle: str | None = None,
    days: int | None = Query(None, ge=1, le=365, description="Filter to last N days"),
    session: AsyncSession = Depends(get_session),
):
    """Export posts as JSON file."""
    query = select(Post).order_by(Post.post_created_at.desc().nullslast())

    filters = build_post_filters(listener_id, platform, sentiment_label, author_handle, days)
    for f in filters:
        query = query.where(f)

    result = await session.execute(query)
    posts = result.scalars().all()

    # Build JSON data
    data = []
    for post in posts:
        data.append({
            "id": post.id,
            "platform": post.platform,
            "author_handle": post.author_handle,
            "author_display_name": post.author_display_name,
            "content": post.content,
            "post_url": post.post_url,
            "likes_count": post.likes_count,
            "replies_count": post.replies_count,
            "reposts_count": post.reposts_count,
            "quotes_count": post.quotes_count,
            "views_count": post.views_count,
            "sentiment_label": post.sentiment_label,
            "sentiment_score": post.sentiment_score,
            "post_created_at": post.post_created_at.isoformat() if post.post_created_at else None,
            "collected_at": post.collected_at.isoformat() if post.collected_at else None,
        })

    # Generate filename with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"posts_export_{timestamp}.json"

    json_output = json.dumps(data, indent=2, ensure_ascii=False)

    return StreamingResponse(
        iter([json_output]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
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
