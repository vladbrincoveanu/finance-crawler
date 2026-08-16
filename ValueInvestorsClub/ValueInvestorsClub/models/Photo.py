"""
The photo model stores image URLs found in an idea's description/body.
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


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[str] = mapped_column(primary_key=True)
    idea_id: Mapped[str] = mapped_column(ForeignKey(Idea.id))
    url: Mapped[str] = mapped_column(String(1024))

    def __repr__(self) -> str:
        return f"Photo(idea_id={self.idea_id!r}, url={self.url!r})"
