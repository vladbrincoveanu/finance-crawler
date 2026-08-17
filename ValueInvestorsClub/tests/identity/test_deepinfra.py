import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ValueInvestorsClub.ValueInvestorsClub.identity.candidates import CandidateOption
from ValueInvestorsClub.ValueInvestorsClub.identity.deepinfra import (
    DeepInfraAdjudicator,
)
from ValueInvestorsClub.ValueInvestorsClub.models import Base
from ValueInvestorsClub.ValueInvestorsClub.models.identity import IdentityCandidate
from ValueInvestorsClub.ValueInvestorsClub.models.ingestion import IngestionRun


def record():
    return {
        "id": "source-security-1",
        "source": "hedgefollow",
        "ticker": "BRK-B",
        "company_name": "Berkshire Hathaway",
    }


def candidate():
    return CandidateOption(
        candidate_id="security-1",
        candidate_type="security",
        candidate_entity_id="security-1",
        deterministic_score=0.95,
        reasons=["ticker_alias"],
        evidence={"source_ticker": "BRK-B"},
    )


def test_deepinfra_returns_strict_resolution_suggestion(httpx_mock, monkeypatch):
    monkeypatch.setenv("DEEPINFRA_API_KEY", "test-only")
    httpx_mock.add_response(
        url="https://api.deepinfra.com/v1/openai/chat/completions",
        json={
            "choices": [
                {
                    "message": {
                        "content": '{"decision":"approve","candidate_id":"security-1","confidence":0.99,"reason_codes":["ticker_alias"]}'
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 25,
                "prompt_tokens_details": {"cached_tokens": 90},
            },
        },
    )

    suggestion = DeepInfraAdjudicator().suggest(
        entity_type="security", source_record=record(), candidates=[candidate()]
    )

    assert suggestion.decision == "approve"
    assert suggestion.candidate_id == "security-1"
    assert suggestion.cached_tokens == 90
    assert suggestion.request_status == "complete"


@pytest.mark.parametrize(
    "response_kwargs",
    [
        {"status_code": 500, "json": {"error": "unavailable"}},
        {
            "json": {
                "choices": [{"message": {"content": "not-json"}}],
            }
        },
    ],
)
def test_deepinfra_failures_return_pending_without_fallback(
    httpx_mock, monkeypatch, response_kwargs
):
    monkeypatch.setenv("DEEPINFRA_API_KEY", "test-only")
    httpx_mock.add_response(
        url="https://api.deepinfra.com/v1/openai/chat/completions",
        **response_kwargs,
    )

    suggestion = DeepInfraAdjudicator().suggest(
        entity_type="security", source_record=record(), candidates=[candidate()]
    )

    assert suggestion.decision == "pending"
    assert suggestion.provider == "deepinfra"
    assert suggestion.request_status in {"http_error", "invalid_response"}


def test_deepinfra_timeout_and_missing_key_remain_pending(
    httpx_mock, monkeypatch
):
    monkeypatch.setenv("DEEPINFRA_API_KEY", "test-only")
    httpx_mock.add_exception(
        httpx.ReadTimeout("timed out"),
        url="https://api.deepinfra.com/v1/openai/chat/completions",
    )
    timed_out = DeepInfraAdjudicator().suggest(
        entity_type="security", source_record=record(), candidates=[candidate()]
    )
    assert timed_out.decision == "pending"
    assert timed_out.request_status == "timeout"

    monkeypatch.delenv("DEEPINFRA_API_KEY")
    missing = DeepInfraAdjudicator().suggest(
        entity_type="security", source_record=record(), candidates=[candidate()]
    )
    assert missing.decision == "pending"
    assert missing.request_status == "missing_api_key"


def test_deepinfra_persists_pending_candidate_when_run_context_is_available(
    monkeypatch,
):
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = IngestionRun(
            source="hedgefollow",
            target="holdings",
            parser_version="test-1",
        )
        session.add(run)
        session.commit()
        monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)

        suggestion = DeepInfraAdjudicator(session=session).suggest(
            entity_type="security",
            source_record={**record(), "run_id": run.id},
            candidates=[candidate()],
        )

        assert suggestion.decision == "pending"
        pending = session.query(IdentityCandidate).one()
        assert pending.status == "pending"
