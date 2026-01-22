import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Listener, Post
from app.schemas import ListenerCreate, ListenerUpdate, ListenerResponse

router = APIRouter()

# Collector service URL (internal Docker network)
COLLECTOR_URL = "http://collector:8001"


@router.get("", response_model=list[ListenerResponse])
async def list_listeners(
    is_active: bool | None = None,
    platform: str | None = None,
    include_post_count: bool = Query(False, description="Include post count for each listener"),
    session: AsyncSession = Depends(get_session),
):
    """List all listeners with optional filters."""
    query = select(Listener).order_by(Listener.created_at.desc())

    if is_active is not None:
        query = query.where(Listener.is_active == is_active)
    if platform:
        query = query.where(Listener.platform == platform)

    result = await session.execute(query)
    listeners = result.scalars().all()

    if include_post_count:
        # Get post counts for each listener
        response = []
        for listener in listeners:
            count_result = await session.execute(
                select(func.count(Post.id)).where(Post.listener_id == listener.id)
            )
            post_count = count_result.scalar()
            listener_dict = ListenerResponse.model_validate(listener).model_dump()
            listener_dict["post_count"] = post_count
            response.append(listener_dict)
        return response

    return listeners


@router.post("", response_model=ListenerResponse)
async def create_listener(
    listener: ListenerCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new listener."""
    db_listener = Listener(**listener.model_dump())
    session.add(db_listener)
    await session.commit()
    await session.refresh(db_listener)
    return db_listener


@router.get("/{listener_id}", response_model=ListenerResponse)
async def get_listener(
    listener_id: int,
    include_post_count: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific listener by ID."""
    result = await session.execute(select(Listener).where(Listener.id == listener_id))
    listener = result.scalar_one_or_none()
    if not listener:
        raise HTTPException(status_code=404, detail="Listener not found")

    if include_post_count:
        count_result = await session.execute(
            select(func.count(Post.id)).where(Post.listener_id == listener.id)
        )
        post_count = count_result.scalar()
        listener_dict = ListenerResponse.model_validate(listener).model_dump()
        listener_dict["post_count"] = post_count
        return listener_dict

    return listener


@router.put("/{listener_id}", response_model=ListenerResponse)
async def update_listener(
    listener_id: int,
    update: ListenerUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a listener."""
    result = await session.execute(select(Listener).where(Listener.id == listener_id))
    listener = result.scalar_one_or_none()
    if not listener:
        raise HTTPException(status_code=404, detail="Listener not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(listener, field, value)

    await session.commit()
    await session.refresh(listener)
    return listener


@router.delete("/{listener_id}")
async def delete_listener(
    listener_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete a listener and all its posts."""
    result = await session.execute(select(Listener).where(Listener.id == listener_id))
    listener = result.scalar_one_or_none()
    if not listener:
        raise HTTPException(status_code=404, detail="Listener not found")

    await session.delete(listener)
    await session.commit()
    return {"status": "deleted", "id": listener_id}


@router.post("/{listener_id}/toggle", response_model=ListenerResponse)
async def toggle_listener(
    listener_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Toggle a listener's active status."""
    result = await session.execute(select(Listener).where(Listener.id == listener_id))
    listener = result.scalar_one_or_none()
    if not listener:
        raise HTTPException(status_code=404, detail="Listener not found")

    listener.is_active = not listener.is_active
    await session.commit()
    await session.refresh(listener)
    return listener


@router.post("/{listener_id}/acknowledge", response_model=ListenerResponse)
async def acknowledge_new_content(
    listener_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Acknowledge new content (clear the has_new_content flag)."""
    result = await session.execute(select(Listener).where(Listener.id == listener_id))
    listener = result.scalar_one_or_none()
    if not listener:
        raise HTTPException(status_code=404, detail="Listener not found")

    listener.has_new_content = False
    await session.commit()
    await session.refresh(listener)
    return listener


@router.post("/{listener_id}/collect")
async def trigger_collection(
    listener_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Trigger collection for a specific listener."""
    # Verify listener exists
    result = await session.execute(select(Listener).where(Listener.id == listener_id))
    listener = result.scalar_one_or_none()
    if not listener:
        raise HTTPException(status_code=404, detail="Listener not found")

    if not listener.is_active:
        raise HTTPException(status_code=400, detail="Listener is not active")

    # Call collector service
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{COLLECTOR_URL}/collect/bluesky",
                json={"listener_id": listener_id},
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Collection timed out")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger collection: {str(e)}")
