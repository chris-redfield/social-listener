from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_text", name="uq_entity_type_text"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)  # 'PERSON' | 'ORG' | 'PRODUCT' | etc.
    entity_text: Mapped[str] = mapped_column(String(500), nullable=False)  # Normalized text
    display_text: Mapped[str] = mapped_column(String(500), nullable=False)  # Original text as found
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    post_entities: Mapped[list["PostEntity"]] = relationship("PostEntity", back_populates="entity")

    def __repr__(self) -> str:
        return f"<Entity {self.id}: {self.entity_type}/{self.entity_text}>"


class PostEntity(Base):
    """Junction table for M:N relationship between posts and entities."""

    __tablename__ = "post_entities"
    __table_args__ = (
        UniqueConstraint("post_id", "entity_id", "start_pos", name="uq_post_entity_pos"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id", ondelete="CASCADE"))
    entity_id: Mapped[int] = mapped_column(Integer, ForeignKey("entities.id", ondelete="CASCADE"))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_pos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_pos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    post: Mapped["Post"] = relationship("Post", back_populates="post_entities")
    entity: Mapped["Entity"] = relationship("Entity", back_populates="post_entities")

    def __repr__(self) -> str:
        return f"<PostEntity {self.post_id}->{self.entity_id}>"
