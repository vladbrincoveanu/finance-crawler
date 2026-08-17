from datetime import datetime, timezone

from ValueInvestorsClub.ValueInvestorsClub.models.identity import (
    CuratedCompany,
    CuratedSecurity,
    IdentityCandidate,
    IdentityDecision,
    SecurityAlias,
)
from ValueInvestorsClub.ValueInvestorsClub.models.ingestion import (
    IngestionRun,
    QuarantineRecord,
)
from ValueInvestorsClub.ValueInvestorsClub.models.source import SourceSecurity


def _headers():
    return {"Authorization": "Bearer review-secret"}


def _seed_candidate(db_session):
    run = IngestionRun(
        source="hedgefollow",
        target="holdings",
        parser_version="test-1",
    )
    db_session.add(run)
    db_session.flush()
    candidate = IdentityCandidate(
        run_id=run.id,
        entity_type="security",
        source_record_id="source-security-1",
        candidate_entity_id="security-1",
        deterministic_score=0.95,
        evidence_json={"source_url": "https://example.test/source"},
        status="pending",
    )
    db_session.add(candidate)
    db_session.commit()
    return candidate


def test_review_routes_require_admin_token(client, db_session, monkeypatch):
    monkeypatch.setenv("REVIEW_ADMIN_TOKEN", "review-secret")
    monkeypatch.setenv("REVIEW_BIND_HOST", "127.0.0.1")

    assert client.get("/review/identity").status_code == 401
    response = client.get("/review/identity", headers=_headers())

    assert response.status_code == 200
    assert response.json() == []


def test_review_identity_decision_is_append_only(client, db_session, monkeypatch):
    monkeypatch.setenv("REVIEW_ADMIN_TOKEN", "review-secret")
    monkeypatch.setenv("REVIEW_BIND_HOST", "127.0.0.1")
    candidate = _seed_candidate(db_session)

    response = client.post(
        f"/review/identity/{candidate.id}/decision",
        headers=_headers(),
        json={
            "decision": "defer",
            "reviewer_id": "analyst-1",
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "defer"
    assert db_session.query(IdentityDecision).count() == 1


def test_approved_identity_decision_writes_security_alias(
    client, db_session, monkeypatch
):
    monkeypatch.setenv("REVIEW_ADMIN_TOKEN", "review-secret")
    monkeypatch.setenv("REVIEW_BIND_HOST", "127.0.0.1")
    run = IngestionRun(
        source="hedgefollow", target="holdings", parser_version="test-1"
    )
    source_security = SourceSecurity(
        source="hedgefollow",
        source_key="BRK-B",
        ticker_raw="BRK-B",
        company_name_raw="Berkshire Hathaway",
    )
    company = CuratedCompany(
        display_name="Berkshire Hathaway",
        normalized_name="berkshire hathaway",
    )
    security = CuratedSecurity(primary_ticker="BRK.B", company=company)
    db_session.add_all([run, source_security, company, security])
    db_session.flush()
    candidate = IdentityCandidate(
        run_id=run.id,
        entity_type="security",
        source_record_id=source_security.id,
        candidate_entity_id=security.id,
        deterministic_score=0.95,
        evidence_json={"reason": "ticker_alias"},
        status="pending",
    )
    db_session.add(candidate)
    db_session.commit()

    response = client.post(
        f"/review/identity/{candidate.id}/decision",
        headers=_headers(),
        json={
            "decision": "approve",
            "curated_entity_id": security.id,
            "reviewer_id": "analyst-1",
        },
    )

    assert response.status_code == 200
    assert db_session.query(SecurityAlias).count() == 1


def test_review_quarantine_lists_and_reprocesses_records(
    client, db_session, monkeypatch
):
    monkeypatch.setenv("REVIEW_ADMIN_TOKEN", "review-secret")
    monkeypatch.setenv("REVIEW_BIND_HOST", "127.0.0.1")
    run = IngestionRun(
        source="dataroma",
        target="holdings",
        parser_version="test-1",
    )
    db_session.add(run)
    db_session.flush()
    record = QuarantineRecord(
        run_id=run.id,
        source="dataroma",
        record_type="holding_snapshot",
        source_record_id="source-1",
        reason_code="invalid_numeric",
        reason_detail="bad value",
        raw_payload={"value_usd": "bad"},
        review_status="open",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(record)
    db_session.commit()

    listed = client.get("/review/quarantine", headers=_headers())
    reprocessed = client.post(
        f"/review/quarantine/{record.id}/reprocess", headers=_headers()
    )

    assert listed.status_code == 200
    assert listed.json()[0]["reason_code"] == "invalid_numeric"
    assert reprocessed.status_code == 200
    assert reprocessed.json()["review_status"] == "reprocessed"


def test_review_defaults_to_rejecting_non_local_binding(client, monkeypatch):
    monkeypatch.setenv("REVIEW_ADMIN_TOKEN", "review-secret")
    monkeypatch.delenv("REVIEW_BIND_HOST", raising=False)

    response = client.get(
        "/review/identity", headers={"Authorization": "Bearer review-secret"}
    )

    assert response.status_code == 403
