# DataObs Console demo

```bash
docker compose -f docker-compose.console-demo.yml up -d --build
./scripts/demo_dataobs_console.sh
cd ui/dataobs-console && pnpm playwright test
```

The demo pins Elasticsearch and Kibana 9.4.2, applies migrations through `0005`, creates two isolated tenant/environment fixtures, verifies summary/topology/SSE responses and scans generated artifacts for the sentinel secret. This fixture is demonstrative, not a production-ready deployment.
