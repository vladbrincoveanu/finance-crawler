from ValueInvestorsClub.ValueInvestorsClub.retrieval.chunking import build_company_chunks


def test_company_chunking_preserves_source_citations():
    chunks = build_company_chunks(
        {
            "company": {"id": "company-1", "name": "Berkshire Hathaway"},
            "securities": [{"ticker": "BRK.B"}],
            "ideas": [
                {
                    "id": "idea-1",
                    "text": "A durable collection of operating businesses.",
                    "citation_id": "idea-citation-1",
                    "citation_url": "https://vic.test/idea/1",
                }
            ],
            "ownership": [
                {
                    "id": "holding-1",
                    "text": "Berkshire held 120 shares.",
                    "citation_id": "holding-citation-1",
                    "citation_url": "https://dataroma.test/brk",
                }
            ],
        }
    )

    assert {chunk.section_type for chunk in chunks} >= {
        "ideas",
        "ownership",
        "metadata",
    }
    assert all(chunk.citation_ids for chunk in chunks)
