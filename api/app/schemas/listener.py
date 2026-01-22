from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ListenerCreate(BaseModel):
    name: str
    platform: Literal["threads", "bluesky", "all"]
    rule_type: Literal["keyword", "mention", "hashtag"]
    rule_value: str
    poll_frequency: int = 300


class ListenerUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    poll_frequency: int | None = None


class ListenerResponse(BaseModel):
    id: int
    name: str
    platform: str
    rule_type: str
    rule_value: str
    is_active: bool
    has_new_content: bool
    poll_frequency: int
    last_polled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    post_count: int | None = None

    class Config:
        from_attributes = True
