from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Listener(Base):
    __tablename__ = "listeners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_value: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    has_new_content: Mapped[bool] = mapped_column(Boolean, default=False)
    initial_scrape_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    poll_frequency: Mapped[int] = mapped_column(Integer, default=300)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="listener", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Listener {self.id}: {self.name}>"
