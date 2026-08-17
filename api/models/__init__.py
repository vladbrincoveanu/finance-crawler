"""
Models package for the ValueInvestorsClub API.
Imports the SQLAlchemy models from the ValueInvestorsClub package.
"""
from ValueInvestorsClub.ValueInvestorsClub.models.Base import Base
from ValueInvestorsClub.ValueInvestorsClub.models.Idea import Idea
from ValueInvestorsClub.ValueInvestorsClub.models.Company import Company
from ValueInvestorsClub.ValueInvestorsClub.models.Description import Description
from ValueInvestorsClub.ValueInvestorsClub.models.User import User
from ValueInvestorsClub.ValueInvestorsClub.models.Catalysts import Catalysts
from ValueInvestorsClub.ValueInvestorsClub.models.Performance import Performance
from ValueInvestorsClub.ValueInvestorsClub.models.Investor import Investor
from ValueInvestorsClub.ValueInvestorsClub.models.Holding import Holding
from ValueInvestorsClub.ValueInvestorsClub.models.ingestion import (
    IngestionRun,
    QuarantineRecord,
    SourceDocument,
    SourceFetch,
    StagingHoldingSnapshot,
)
from ValueInvestorsClub.ValueInvestorsClub.models.source import (
    SourceHoldingSnapshot,
    SourceInvestor,
    SourcePortfolioManager,
    SourceSecurity,
)
from ValueInvestorsClub.ValueInvestorsClub.models.identity import (
    CuratedCompany,
    CuratedInvestor,
    CuratedInvestorManager,
    CuratedSecurity,
    IdentityCandidate,
    IdentityDecision,
    InvestorAlias,
    PortfolioManager,
    SecurityAlias,
)
from ValueInvestorsClub.ValueInvestorsClub.models.curated import (
    CuratedHoldingEvent,
    CuratedHoldingSnapshot,
)

__all__ = [
    "Base",
    "Idea",
    "Company",
    "Description",
    "User",
    "Catalysts",
    "Performance",
    "Investor",
    "Holding",
    "IngestionRun",
    "SourceDocument",
    "SourceFetch",
    "StagingHoldingSnapshot",
    "QuarantineRecord",
    "SourceInvestor",
    "SourcePortfolioManager",
    "SourceSecurity",
    "SourceHoldingSnapshot",
    "CuratedInvestor",
    "PortfolioManager",
    "CuratedCompany",
    "CuratedSecurity",
    "CuratedInvestorManager",
    "InvestorAlias",
    "SecurityAlias",
    "IdentityCandidate",
    "IdentityDecision",
    "CuratedHoldingSnapshot",
    "CuratedHoldingEvent",
]
