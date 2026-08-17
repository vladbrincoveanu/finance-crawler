"""
Import models so SQLAlchemy's metadata is populated when callers do:

  from ValueInvestorsClub.models import Base
  Base.Base.metadata.create_all(engine)
"""

from . import Base
from .Company import Company
from .User import User
from .Idea import Idea
from .Description import Description
from .Catalysts import Catalysts
from .Performance import Performance
from .Investor import Investor
from .Holding import Holding
from .Comment import Comment
from .Photo import Photo
from .ingestion import (
    IngestionRun,
    QuarantineRecord,
    SourceDocument,
    SourceFetch,
    StagingHoldingSnapshot,
)
from .source import (
    SourceHoldingSnapshot,
    SourceInvestor,
    SourcePortfolioManager,
    SourceSecurity,
)
from .identity import (
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
from .curated import CuratedHoldingEvent, CuratedHoldingSnapshot
from .retrieval import CompanyChapter, EvidenceChunk, RetrievalFeedback, RetrievalRun

__all__ = [
    "Base",
    "Company",
    "User",
    "Idea",
    "Description",
    "Catalysts",
    "Performance",
    "Investor",
    "Holding",
    "Comment",
    "Photo",
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
    "CompanyChapter",
    "EvidenceChunk",
    "RetrievalRun",
    "RetrievalFeedback",
]
