"""
The comment model stores individual comments/messages left on an idea.
"""
try:
    from ValueInvestorsClub.models.Base import Base
    from ValueInvestorsClub.models.Idea import Idea
except ImportError:
    from ValueInvestorsClub.ValueInvestorsClub.models.Base import Base
    from ValueInvestorsClub.ValueInvestorsClub.models.Idea import Idea
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy import String
from sqlalchemy import ForeignKey


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(primary_key=True)
    idea_id: Mapped[str] = mapped_column(ForeignKey(Idea.id))
    author: Mapped[str] = mapped_column(String(256))
    posted_at: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(String(32000))

    def __repr__(self) -> str:
        return f"Comment(idea_id={self.idea_id!r}, author={self.author!r})"
