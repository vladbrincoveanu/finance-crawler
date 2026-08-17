def test_health_live_does_not_require_database(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_health_ready_reports_database_failure(client, monkeypatch):
    monkeypatch.setattr("api.routes.health.database_is_ready", lambda: False)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_ingestion_metrics_fail_open_when_exporter_is_down():
    from api.observability import build_metrics

    metrics = build_metrics(exporter_url="http://127.0.0.1:1")
    metrics.record("ingestion_rows_total", 1)

    assert metrics.local_value("ingestion_rows_total") == 1
