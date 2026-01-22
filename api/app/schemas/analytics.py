from datetime import datetime

from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    total_posts: int
    total_listeners: int
    total_entities: int
    posts_today: int
    posts_this_week: int
    sentiment_breakdown: dict[str, int]
    top_platforms: dict[str, int]


class SentimentBreakdown(BaseModel):
    label: str
    count: int
    percentage: float


class TimelinePoint(BaseModel):
    date: datetime
    count: int
    sentiment_positive: int
    sentiment_negative: int
    sentiment_neutral: int


class AuthorStats(BaseModel):
    author_handle: str
    author_display_name: str | None
    post_count: int
    avg_likes: float
    avg_sentiment: float | None
