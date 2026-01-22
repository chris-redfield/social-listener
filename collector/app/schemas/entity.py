from datetime import datetime

from pydantic import BaseModel


class EntityResponse(BaseModel):
    id: int
    entity_type: str
    entity_text: str
    display_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class PostEntityResponse(BaseModel):
    id: int
    entity_id: int
    entity_type: str
    entity_text: str
    display_text: str
    confidence: float | None
    start_pos: int | None
    end_pos: int | None

    class Config:
        from_attributes = True
