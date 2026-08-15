try:
    from ValueInvestorsClub.models.Base import Base
except ImportError:
    from ValueInvestorsClub.ValueInvestorsClub.models.Base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String


class Investor(Base):
    __tablename__ = "investors"
    # id format: "<source>:<source_slug>", e.g. "dataroma:BRK" — keeps sources disjoint by construction.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    source: Mapped[str] = mapped_column(String(32))
    source_slug: Mapped[str] = mapped_column(String(32))
    profile_url: Mapped[str] = mapped_column(String(256))

    holdings = relationship("Holding", backref="investor")

    def __repr__(self) -> str:
        return f"Investor(id={self.id!r}, name={self.name!r}, source={self.source!r})"
