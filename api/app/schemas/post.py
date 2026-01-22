from datetime import datetime

from pydantic import BaseModel


class PostFilters(BaseModel):
    listener_id: int | None = None
    platform: str | None = None
    sentiment_label: str | None = None
    author_handle: str | None = None
    search: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class PostResponse(BaseModel):
    id: int
    listener_id: int
    platform: str
    platform_post_id: str
    author_handle: str | None
    author_display_name: str | None
    author_avatar_url: str | None
    content: str | None
    post_url: str | None
    likes_count: int
    replies_count: int
    reposts_count: int
    quotes_count: int
    views_count: int
    sentiment_score: float | None
    sentiment_label: str | None
    nlp_processed_at: datetime | None
    nlp_error: str | None
    post_created_at: datetime | None
    collected_at: datetime

    class Config:
        from_attributes = True
