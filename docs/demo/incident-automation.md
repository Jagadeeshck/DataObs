# Incident automation demo

Run `docker compose -f docker-compose.incident-automation-demo.yml up -d --build`, apply migrations with `./bin/dataobs elastic apply`, validate/deploy workflows with `./bin/dataobs workflows validate && ./bin/dataobs workflows apply`, then run `./scripts/demo_incident_automation.sh`. The demo exercises duplicate finding deduplication, workflow validation and sentinel-secret absence checks. Docker-backed GitHub Actions must pass before this draft PR is ready for merge.
