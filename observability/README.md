# Local Observability

Start the profile with:

```bash
docker compose --profile observability up -d
```

Services:

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001`
- Loki: `http://localhost:3100`
- Tempo: `http://localhost:3200`
- Uptime Kuma: `http://localhost:3002`

The API exports Prometheus metrics at `/metrics`, liveness at `/health/live`, and database readiness at `/health/ready`. Telemetry storage is local with seven-day retention. Exporter failures are logged and do not fail ingestion transactions.
