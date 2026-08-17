from datetime import datetime, timezone

from ValueInvestorsClub.ValueInvestorsClub.models.retrieval import (
    CompanyChapter,
    EvidenceChunk,
)


def test_search_returns_cited_company_evidence(client, db_session):
    chapter = CompanyChapter(curated_company_id="company-1")
    db_session.add(chapter)
    db_session.flush()
    db_session.add(
        EvidenceChunk(
            chapter_id=chapter.id,
            section_type="ownership",
            content="Berkshire Hathaway held a reported position in Apple.",
            company_id="company-1",
            source_snapshot_ids=["snapshot-1"],
            citation_urls=["https://dataroma.test/brk"],
            created_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    response = client.get("/search?q=Berkshire Apple&limit=5")

    assert response.status_code == 200
    assert response.json()[0]["citation_urls"] == ["https://dataroma.test/brk"]
    assert response.json()[0]["section_type"] == "ownership"


def test_search_abstains_with_empty_result_set(client, db_session):
    response = client.get("/search?q=nonexistent-company&limit=5")

    assert response.status_code == 200
    assert response.json() == []
