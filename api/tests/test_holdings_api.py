"""Integration tests for the curated holdings API endpoint."""

from .test_curated_holdings_api import seed_curated_rows


def test_get_holdings_returns_joined_rows(client, db_session):
    seed_curated_rows(db_session)

    response = client.get("/holdings/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    dataroma = next(row for row in data if row["source"] == "dataroma")
    assert dataroma["investor_name"] == "Berkshire Hathaway"
    assert dataroma["ticker"] == "BRK.B"
    assert dataroma["shares"] == 120


def test_get_holdings_empty_list_when_no_data(client, db_session):
    response = client.get("/holdings/")
    assert response.status_code == 200
    assert response.json() == []
