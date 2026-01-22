from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Post, Listener, Entity
from app.schemas import AnalyticsOverview, SentimentBreakdown, TimelinePoint, AuthorStats

router = APIRouter()


def parse_listener_ids(listener_ids: str | None) -> List[int] | None:
    """Parse comma-separated listener IDs into a list of integers."""
    if not listener_ids:
        return None
    try:
        return [int(id.strip()) for id in listener_ids.split(",") if id.strip()]
    except ValueError:
        return None


def build_listener_filter(listener_ids: List[int] | None):
    """Build SQLAlchemy filter for listener IDs."""
    if not listener_ids:
        return True  # No filter
    if len(listener_ids) == 1:
        return Post.listener_id == listener_ids[0]
    return Post.listener_id.in_(listener_ids)


def build_date_filter(days: int | None):
    """Build SQLAlchemy filter for date range based on post_created_at."""
    if not days:
        return True  # No filter
    start_date = datetime.utcnow() - timedelta(days=days)
    return and_(Post.post_created_at.isnot(None), Post.post_created_at >= start_date)


@router.get("/overview", response_model=AnalyticsOverview)
async def analytics_overview(
    listener_ids: str | None = Query(None, description="Comma-separated listener IDs"),
    days: int | None = Query(None, ge=1, le=90, description="Filter to last N days"),
    session: AsyncSession = Depends(get_session),
):
    """Get overall analytics summary."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Base query filters
    parsed_ids = parse_listener_ids(listener_ids)
    listener_filter = build_listener_filter(parsed_ids)
    date_filter = build_date_filter(days)

    # Combined filter for posts
    post_filter = and_(listener_filter, date_filter) if days else listener_filter

    # Total posts (within date range if specified)
    total_posts = (
        await session.execute(select(func.count(Post.id)).where(post_filter))
    ).scalar()

    # Total listeners
    total_listeners = (await session.execute(select(func.count(Listener.id)))).scalar()

    # Total entities
    total_entities = (await session.execute(select(func.count(Entity.id)))).scalar()

    # Posts today (by post creation date, not collection date)
    posts_today = (
        await session.execute(
            select(func.count(Post.id)).where(
                and_(
                    post_filter,
                    Post.post_created_at.isnot(None),
                    Post.post_created_at >= today_start
                )
            )
        )
    ).scalar()

    # Posts this week (by post creation date, not collection date)
    posts_this_week = (
        await session.execute(
            select(func.count(Post.id)).where(
                and_(
                    post_filter,
                    Post.post_created_at.isnot(None),
                    Post.post_created_at >= week_start
                )
            )
        )
    ).scalar()

    # Sentiment breakdown (apply date filter)
    sentiment_query = (
        select(Post.sentiment_label, func.count(Post.id))
        .where(and_(post_filter, Post.sentiment_label.isnot(None)))
        .group_by(Post.sentiment_label)
    )
    sentiment_result = await session.execute(sentiment_query)
    sentiment_breakdown = {row[0]: row[1] for row in sentiment_result.all()}

    # Platform breakdown (apply date filter)
    platform_query = (
        select(Post.platform, func.count(Post.id))
        .where(post_filter)
        .group_by(Post.platform)
    )
    platform_result = await session.execute(platform_query)
    top_platforms = {row[0]: row[1] for row in platform_result.all()}

    return AnalyticsOverview(
        total_posts=total_posts,
        total_listeners=total_listeners,
        total_entities=total_entities,
        posts_today=posts_today,
        posts_this_week=posts_this_week,
        sentiment_breakdown=sentiment_breakdown,
        top_platforms=top_platforms,
    )


@router.get("/sentiment", response_model=list[SentimentBreakdown])
async def sentiment_breakdown(
    listener_ids: str | None = Query(None, description="Comma-separated listener IDs"),
    days: int | None = Query(None, ge=1, le=90, description="Filter to last N days"),
    session: AsyncSession = Depends(get_session),
):
    """Get sentiment breakdown with percentages."""
    parsed_ids = parse_listener_ids(listener_ids)
    listener_filter = build_listener_filter(parsed_ids)
    date_filter = build_date_filter(days)
    post_filter = and_(listener_filter, date_filter) if days else listener_filter

    query = (
        select(Post.sentiment_label, func.count(Post.id).label("count"))
        .where(and_(post_filter, Post.sentiment_label.isnot(None)))
        .group_by(Post.sentiment_label)
    )
    result = await session.execute(query)
    rows = result.all()

    total = sum(row.count for row in rows)
    if total == 0:
        return []

    return [
        SentimentBreakdown(
            label=row.sentiment_label,
            count=row.count,
            percentage=round((row.count / total) * 100, 2),
        )
        for row in rows
    ]


@router.get("/timeline", response_model=list[TimelinePoint])
async def posts_timeline(
    listener_ids: str | None = Query(None, description="Comma-separated listener IDs"),
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
):
    """Get posts timeline with sentiment breakdown per day."""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    parsed_ids = parse_listener_ids(listener_ids)
    post_filter = build_listener_filter(parsed_ids)

    # Use post_created_at (when post was made) instead of collected_at
    # Filter out posts without post_created_at
    # Note: Reuse the same expression for select, group_by, and order_by to avoid SQL errors
    date_col = func.date_trunc("day", Post.post_created_at).label("date")

    query = (
        select(
            date_col,
            func.count(Post.id).label("count"),
            func.sum(case((Post.sentiment_label == "positive", 1), else_=0)).label(
                "sentiment_positive"
            ),
            func.sum(case((Post.sentiment_label == "negative", 1), else_=0)).label(
                "sentiment_negative"
            ),
            func.sum(case((Post.sentiment_label == "neutral", 1), else_=0)).label(
                "sentiment_neutral"
            ),
        )
        .where(
            and_(
                post_filter,
                Post.post_created_at.isnot(None),
                Post.post_created_at >= start_date,
            )
        )
        .group_by(date_col)
        .order_by(date_col)
    )

    result = await session.execute(query)
    rows = result.all()

    return [
        TimelinePoint(
            date=row.date,
            count=row.count,
            sentiment_positive=row.sentiment_positive or 0,
            sentiment_negative=row.sentiment_negative or 0,
            sentiment_neutral=row.sentiment_neutral or 0,
        )
        for row in rows
    ]


@router.get("/authors", response_model=list[AuthorStats])
async def top_authors(
    listener_ids: str | None = Query(None, description="Comma-separated listener IDs"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get top authors by post count with engagement stats."""
    parsed_ids = parse_listener_ids(listener_ids)
    post_filter = build_listener_filter(parsed_ids)

    query = (
        select(
            Post.author_handle,
            Post.author_display_name,
            func.count(Post.id).label("post_count"),
            func.avg(Post.likes_count).label("avg_likes"),
            func.avg(Post.sentiment_score).label("avg_sentiment"),
        )
        .where(and_(post_filter, Post.author_handle.isnot(None)))
        .group_by(Post.author_handle, Post.author_display_name)
        .order_by(func.count(Post.id).desc())
        .limit(limit)
    )

    result = await session.execute(query)
    rows = result.all()

    return [
        AuthorStats(
            author_handle=row.author_handle,
            author_display_name=row.author_display_name,
            post_count=row.post_count,
            avg_likes=round(row.avg_likes or 0, 2),
            avg_sentiment=round(row.avg_sentiment, 4) if row.avg_sentiment else None,
        )
        for row in rows
    ]


@router.get("/engagement")
async def engagement_stats(
    listener_ids: str | None = Query(None, description="Comma-separated listener IDs"),
    days: int | None = Query(None, ge=1, le=90, description="Filter to last N days"),
    session: AsyncSession = Depends(get_session),
):
    """Get engagement statistics."""
    parsed_ids = parse_listener_ids(listener_ids)
    listener_filter = build_listener_filter(parsed_ids)
    date_filter = build_date_filter(days)
    post_filter = and_(listener_filter, date_filter) if days else listener_filter

    query = select(
        func.sum(Post.likes_count).label("total_likes"),
        func.sum(Post.replies_count).label("total_replies"),
        func.sum(Post.reposts_count).label("total_reposts"),
        func.avg(Post.likes_count).label("avg_likes"),
        func.avg(Post.replies_count).label("avg_replies"),
        func.avg(Post.reposts_count).label("avg_reposts"),
        func.max(Post.likes_count).label("max_likes"),
    ).where(post_filter)

    result = await session.execute(query)
    row = result.one()

    return {
        "total_likes": row.total_likes or 0,
        "total_replies": row.total_replies or 0,
        "total_reposts": row.total_reposts or 0,
        "avg_likes": round(row.avg_likes or 0, 2),
        "avg_replies": round(row.avg_replies or 0, 2),
        "avg_reposts": round(row.avg_reposts or 0, 2),
        "max_likes": row.max_likes or 0,
    }
