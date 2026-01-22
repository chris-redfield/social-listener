from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Post, Listener, Entity
from app.schemas import AnalyticsOverview, SentimentBreakdown, TimelinePoint, AuthorStats

router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverview)
async def analytics_overview(
    listener_id: int | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Get overall analytics summary."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Base query filter
    post_filter = Post.listener_id == listener_id if listener_id else True

    # Total posts
    total_posts = (
        await session.execute(select(func.count(Post.id)).where(post_filter))
    ).scalar()

    # Total listeners
    total_listeners = (await session.execute(select(func.count(Listener.id)))).scalar()

    # Total entities
    total_entities = (await session.execute(select(func.count(Entity.id)))).scalar()

    # Posts today
    posts_today = (
        await session.execute(
            select(func.count(Post.id)).where(
                and_(post_filter, Post.collected_at >= today_start)
            )
        )
    ).scalar()

    # Posts this week
    posts_this_week = (
        await session.execute(
            select(func.count(Post.id)).where(
                and_(post_filter, Post.collected_at >= week_start)
            )
        )
    ).scalar()

    # Sentiment breakdown
    sentiment_query = (
        select(Post.sentiment_label, func.count(Post.id))
        .where(and_(post_filter, Post.sentiment_label.isnot(None)))
        .group_by(Post.sentiment_label)
    )
    sentiment_result = await session.execute(sentiment_query)
    sentiment_breakdown = {row[0]: row[1] for row in sentiment_result.all()}

    # Platform breakdown
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
    listener_id: int | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Get sentiment breakdown with percentages."""
    post_filter = Post.listener_id == listener_id if listener_id else True

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
    listener_id: int | None = None,
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
):
    """Get posts timeline with sentiment breakdown per day."""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    post_filter = Post.listener_id == listener_id if listener_id else True

    query = (
        select(
            func.date_trunc("day", Post.collected_at).label("date"),
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
        .where(and_(post_filter, Post.collected_at >= start_date))
        .group_by(func.date_trunc("day", Post.collected_at))
        .order_by(func.date_trunc("day", Post.collected_at))
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
    listener_id: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get top authors by post count with engagement stats."""
    post_filter = Post.listener_id == listener_id if listener_id else True

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
    listener_id: int | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Get engagement statistics."""
    post_filter = Post.listener_id == listener_id if listener_id else True

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
