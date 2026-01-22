import logging
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.bluesky import BlueskyCollector
from app.config import settings
from app.database import async_session, get_session, init_db
from app.models import Listener, Post
from app.schemas import (
    CollectRequest,
    CollectResponse,
    CollectorStatus,
    ListenerCreate,
    ListenerResponse,
    PostResponse,
)
from app.schemas.collector import SchedulerJob

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Scheduler instance
scheduler = AsyncIOScheduler()

# Collector instances
bluesky_collector = BlueskyCollector()


async def scheduled_collect():
    """Scheduled job to collect posts for all active listeners."""
    logger.info("Running scheduled collection...")
    async with async_session() as session:
        # Get all active Bluesky listeners
        result = await session.execute(
            select(Listener).where(
                Listener.is_active == True,
                Listener.platform.in_(["bluesky", "all"]),
            )
        )
        listeners = result.scalars().all()

        total_posts = 0
        for listener in listeners:
            try:
                count = await bluesky_collector.collect(listener, session)
                total_posts += count
                listener.last_polled_at = datetime.utcnow()
                if count > 0:
                    listener.has_new_content = True
                await session.commit()
                logger.info(f"Collected {count} posts for listener '{listener.name}'")
            except Exception as e:
                logger.error(f"Error collecting for listener '{listener.name}': {e}")
                await session.rollback()

        logger.info(f"Scheduled collection complete. Total posts: {total_posts}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting collector service...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Start scheduler
    scheduler.add_job(
        scheduled_collect,
        "interval",
        seconds=settings.bluesky_poll_interval,
        id="bluesky_collector",
        name="Bluesky Collector",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started (poll interval: {settings.bluesky_poll_interval}s)")

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Collector service stopped")


app = FastAPI(
    title="Social Listener - Collector Service",
    description="Collects posts from social media platforms",
    version="0.1.0",
    lifespan=lifespan,
)


# ===================
# Health & Status
# ===================


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "collector"}


@app.get("/status", response_model=CollectorStatus)
async def status():
    """Get collector status and scheduler info."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            SchedulerJob(
                id=job.id,
                name=job.name,
                next_run_time=job.next_run_time,
            )
        )

    return CollectorStatus(
        status="running" if scheduler.running else "stopped",
        bluesky_configured=await bluesky_collector.is_configured(),
        threads_configured=False,  # Not implemented yet
        scheduler_running=scheduler.running,
        jobs=jobs,
    )


# ===================
# Manual Collection
# ===================


@app.post("/collect/bluesky", response_model=CollectResponse)
async def collect_bluesky(
    request: CollectRequest = None,
    session: AsyncSession = Depends(get_session),
):
    """Manually trigger Bluesky collection."""
    if not await bluesky_collector.is_configured():
        raise HTTPException(status_code=400, detail="Bluesky credentials not configured")

    # Build query for listeners
    query = select(Listener).where(
        Listener.is_active == True,
        Listener.platform.in_(["bluesky", "all"]),
    )

    if request and request.listener_id:
        query = query.where(Listener.id == request.listener_id)

    result = await session.execute(query)
    listeners = result.scalars().all()

    if not listeners:
        raise HTTPException(status_code=404, detail="No active Bluesky listeners found")

    total_posts = 0
    for listener in listeners:
        try:
            count = await bluesky_collector.collect(listener, session)
            total_posts += count
            listener.last_polled_at = datetime.utcnow()
            if count > 0:
                listener.has_new_content = True
        except Exception as e:
            logger.error(f"Error collecting for listener '{listener.name}': {e}")
            raise HTTPException(status_code=500, detail=str(e))

    await session.commit()

    return CollectResponse(
        status="success",
        message=f"Collected posts from {len(listeners)} listener(s)",
        posts_collected=total_posts,
        listener_id=request.listener_id if request else None,
    )


@app.post("/collect/bluesky/test")
async def test_bluesky_connection():
    """Test Bluesky API connection."""
    if not await bluesky_collector.is_configured():
        raise HTTPException(status_code=400, detail="Bluesky credentials not configured")

    try:
        success = await bluesky_collector.test_connection()
        if success:
            return {"status": "success", "message": "Connected to Bluesky"}
        else:
            return {"status": "error", "message": "Failed to connect"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================
# Listeners (basic CRUD for testing)
# ===================


@app.get("/listeners", response_model=list[ListenerResponse])
async def list_listeners(session: AsyncSession = Depends(get_session)):
    """List all listeners."""
    result = await session.execute(select(Listener))
    return result.scalars().all()


@app.post("/listeners", response_model=ListenerResponse)
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


@app.get("/listeners/{listener_id}", response_model=ListenerResponse)
async def get_listener(
    listener_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific listener."""
    result = await session.execute(select(Listener).where(Listener.id == listener_id))
    listener = result.scalar_one_or_none()
    if not listener:
        raise HTTPException(status_code=404, detail="Listener not found")
    return listener


@app.delete("/listeners/{listener_id}")
async def delete_listener(
    listener_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete a listener."""
    result = await session.execute(select(Listener).where(Listener.id == listener_id))
    listener = result.scalar_one_or_none()
    if not listener:
        raise HTTPException(status_code=404, detail="Listener not found")
    await session.delete(listener)
    await session.commit()
    return {"status": "deleted", "id": listener_id}


# ===================
# Posts (basic read for testing)
# ===================


@app.get("/posts", response_model=list[PostResponse])
async def list_posts(
    listener_id: int | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    """List collected posts."""
    query = select(Post).order_by(Post.collected_at.desc()).limit(limit)
    if listener_id:
        query = query.where(Post.listener_id == listener_id)
    result = await session.execute(query)
    return result.scalars().all()


@app.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific post."""
    result = await session.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post
