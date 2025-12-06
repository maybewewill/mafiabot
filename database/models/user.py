from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from .base import Base

if TYPE_CHECKING:
    from .game import Game

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    in_game: Mapped[bool] = mapped_column(Boolean, default=False)
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True)
    visitor_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )
    doctor_rescued: Mapped[bool] = mapped_column(Boolean, default=False)
    lover_affected: Mapped[bool] = mapped_column(Boolean, default=False)
    advocate_saved: Mapped[bool] = mapped_column(Boolean, default=False)
    homeless_visit: Mapped[bool] = mapped_column(Boolean, default=False)
    killer_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )
    game_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("games.id"),
        nullable=True,
    )
    mafia_choose: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    last_message_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    kamikaze_target_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    game: Mapped["Game | None"] = relationship(
        "Game",
        back_populates="users",
    )
