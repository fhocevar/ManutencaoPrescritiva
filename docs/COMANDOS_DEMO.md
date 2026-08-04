# Comandos de demonstração

```bash
cp .env.example .env
docker compose up --build -d
make migrate
make demo-seed
curl http://localhost:8000/health/ready
curl http://localhost:8000/api/v1/stats
curl -X POST http://localhost:8000/api/v1/events/analyze -H "Content-Type: application/json" -d @data/sample_event.json
```
