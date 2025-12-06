from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from .base import Base

if TYPE_CHECKING:
    from .user import User

class Game(Base):
    __tablename__ = 'games'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(Integer, nullable=False)

    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="game",
    )
    started: Mapped[bool] = mapped_column(Boolean, default=False)
    day: Mapped[int] = mapped_column(Integer, default=1)
    night: Mapped[int] = mapped_column(Integer, default=1)
    current_phase: Mapped[str] = mapped_column(String(50), default="day")
    next_phase_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    voting_target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    voting_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
