from datetime import datetime

from pydantic import BaseModel


class CollectRequest(BaseModel):
    listener_id: int | None = None  # If None, collect for all active listeners


class CollectResponse(BaseModel):
    status: str
    message: str
    posts_collected: int
    listener_id: int | None = None


class SchedulerJob(BaseModel):
    id: str
    name: str
    next_run_time: datetime | None


class CollectorStatus(BaseModel):
    status: str
    bluesky_configured: bool
    threads_configured: bool
    scheduler_running: bool
    jobs: list[SchedulerJob]
