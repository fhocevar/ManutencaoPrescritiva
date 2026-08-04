# Deploy

## Local

```bash
cp .env.example .env
docker compose up --build -d
make migrate
make demo-seed
```

## Homologação

1. Criar banco PostgreSQL com extensão `vector`.
2. Configurar `.env` com credenciais reais.
3. Executar `alembic upgrade head`.
4. Publicar API atrás de API Gateway.
5. Publicar dashboard com autenticação.
6. Configurar Prometheus.
7. Carregar CSV histórico e documentos.
8. Executar testes de contrato.

## Produção industrial

- Deploy em Kubernetes ou VM corporativa.
- Separar API, worker e dashboard.
- Habilitar TLS.
- Criar política de backup do banco.
- Monitorar latência do endpoint `/api/v1/events/analyze`.
- Versionar modelos e embeddings.
- Controlar aprovação humana das recomendações.
