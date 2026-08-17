from .test_curated_holdings_api import seed_curated_rows


def test_curated_investor_detail_exposes_identity_managers_and_holdings(
    client, db_session
):
    _, investor = seed_curated_rows(db_session)

    response = client.get(f"/investors/{investor.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Berkshire Hathaway"
    assert data["portfolio_managers"] == ["Warren Buffett"]
    assert len(data["holdings"]) == 2
    assert set(data["coverage"]) >= {"sources", "period_start", "period_end"}
