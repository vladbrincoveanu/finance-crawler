try:
    from ValueInvestorsClub.models.Base import Base
except ImportError:
    from ValueInvestorsClub.ValueInvestorsClub.models.Base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Date, BigInteger, Numeric, ForeignKey, UniqueConstraint


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("investor_id", "company_id", "quarter_date", name="uq_holding_investor_company_quarter"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    investor_id: Mapped[str] = mapped_column(ForeignKey("investors.id"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.ticker"))
    quarter_date: Mapped[Date] = mapped_column(Date)
    shares: Mapped[int] = mapped_column(BigInteger)
    value_usd: Mapped[float] = mapped_column(Numeric(20, 2))
    pct_portfolio: Mapped[float] = mapped_column(Numeric(6, 2))
    activity: Mapped[str] = mapped_column(String(16))  # buy | add | reduce | hold

    company = relationship("Company", backref="holdings")

    def __repr__(self) -> str:
        return (f"Holding(investor_id={self.investor_id!r}, company_id={self.company_id!r}, "
                f"quarter_date={self.quarter_date!r}, shares={self.shares!r})")
