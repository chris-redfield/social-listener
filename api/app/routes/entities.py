from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Entity, PostEntity, Post
from app.schemas import EntityResponse, EntityTopResponse

router = APIRouter()


@router.get("", response_model=list[EntityResponse])
async def list_entities(
    entity_type: str | None = None,
    listener_id: int | None = None,
    search: str | None = Query(None, description="Search in entity text"),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    """List all unique entities."""
    query = select(Entity).order_by(Entity.created_at.desc())

    if listener_id:
        query = (
            query.join(PostEntity, Entity.id == PostEntity.entity_id)
            .join(Post, PostEntity.post_id == Post.id)
            .where(Post.listener_id == listener_id)
            .distinct()
        )

    if entity_type:
        query = query.where(Entity.entity_type == entity_type)
    if search:
        query = query.where(Entity.entity_text.ilike(f"%{search}%"))

    query = query.limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/top", response_model=list[EntityTopResponse])
async def top_entities(
    entity_type: str | None = None,
    listener_id: int | None = None,
    limit: int = Query(20, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    """Get top entities by occurrence count."""
    query = (
        select(
            Entity.id,
            Entity.entity_type,
            Entity.entity_text,
            Entity.display_text,
            func.count(PostEntity.id).label("occurrence_count"),
        )
        .join(PostEntity, Entity.id == PostEntity.entity_id)
    )

    if listener_id:
        query = query.join(Post, PostEntity.post_id == Post.id).where(
            Post.listener_id == listener_id
        )

    # Apply entity_type filter BEFORE group_by
    if entity_type:
        query = query.where(Entity.entity_type == entity_type)

    query = (
        query.group_by(Entity.id, Entity.entity_type, Entity.entity_text, Entity.display_text)
        .order_by(func.count(PostEntity.id).desc())
        .limit(limit)
    )

    result = await session.execute(query)
    rows = result.all()

    return [
        EntityTopResponse(
            id=row.id,
            entity_type=row.entity_type,
            entity_text=row.entity_text,
            display_text=row.display_text,
            occurrence_count=row.occurrence_count,
        )
        for row in rows
    ]


@router.get("/types")
async def entity_types(session: AsyncSession = Depends(get_session)):
    """Get all entity types with counts."""
    query = (
        select(Entity.entity_type, func.count(Entity.id).label("count"))
        .group_by(Entity.entity_type)
        .order_by(func.count(Entity.id).desc())
    )
    result = await session.execute(query)
    rows = result.all()

    return [{"entity_type": row.entity_type, "count": row.count} for row in rows]


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific entity by ID."""
    result = await session.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.get("/{entity_id}/posts")
async def get_entity_posts(
    entity_id: int,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Get posts containing a specific entity."""
    # Check entity exists
    result = await session.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Get posts via junction table
    query = (
        select(Post)
        .join(PostEntity, Post.id == PostEntity.post_id)
        .where(PostEntity.entity_id == entity_id)
        .order_by(Post.collected_at.desc())
        .limit(limit)
    )

    result = await session.execute(query)
    posts = result.scalars().all()

    return {
        "entity": EntityResponse.model_validate(entity),
        "posts": posts,
        "total": len(posts),
    }
