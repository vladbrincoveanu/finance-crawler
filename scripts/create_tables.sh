#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

USE_DOCKER=${USE_DOCKER:-1}
DOCKER_SERVICE=${DOCKER_SERVICE:-api}

run_python_stdin() {
  if [ "$USE_DOCKER" -eq 1 ]; then
    docker-compose exec -T "$DOCKER_SERVICE" python -
  else
    python3 -
  fi
}

run_python_stdin <<'PY'
import os
from sqlalchemy import create_engine

try:
    from ValueInvestorsClub.models import Base  # imports all models
except ImportError:
    from ValueInvestorsClub.ValueInvestorsClub.models import Base

engine = create_engine(os.environ.get("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost/ideas"), future=True)
meta = None
if hasattr(Base, "Base") and hasattr(Base.Base, "metadata"):
    meta = Base.Base.metadata
elif hasattr(Base, "metadata"):
    meta = Base.metadata
else:
    raise RuntimeError(f"Could not locate SQLAlchemy metadata on Base={Base!r}")

meta.create_all(engine)
print("Tables ensured via SQLAlchemy metadata.create_all().")
PY
