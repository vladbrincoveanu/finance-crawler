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
]
