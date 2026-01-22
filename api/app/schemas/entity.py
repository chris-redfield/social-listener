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


class EntityTopResponse(BaseModel):
    id: int
    entity_type: str
    entity_text: str
    display_text: str
    occurrence_count: int
