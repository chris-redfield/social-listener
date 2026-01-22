from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("platform", "platform_post_id", name="uq_platform_post"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listener_id: Mapped[int] = mapped_column(Integer, ForeignKey("listeners.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # 'threads' | 'bluesky'
    platform_post_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author_handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Engagement metrics
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    replies_count: Mapped[int] = mapped_column(Integer, default=0)
    reposts_count: Mapped[int] = mapped_column(Integer, default=0)
    quotes_count: Mapped[int] = mapped_column(Integer, default=0)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    shares_count: Mapped[int] = mapped_column(Integer, default=0)
    clicks_count: Mapped[int] = mapped_column(Integer, default=0)

    # NLP Analysis results (Phase 2)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Timestamps
    post_created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    listener: Mapped["Listener"] = relationship("Listener", back_populates="posts")
    post_entities: Mapped[list["PostEntity"]] = relationship(
        "PostEntity", back_populates="post", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Post {self.id}: {self.platform}/{self.platform_post_id[:20]}>"
