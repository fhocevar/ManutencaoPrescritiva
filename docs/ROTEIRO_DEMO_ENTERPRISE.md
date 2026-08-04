# Roteiro de demonstração

## 1. Abertura

Apresentar o objetivo: sair de manutenção preditiva para prescritiva, com recomendação baseada em evidência documental.

## 2. Arquitetura

Mostrar Clean Architecture, DDD, PostgreSQL/pgvector, ML, RAG e dashboard.

## 3. Demonstração técnica

```bash
cp .env.example .env
docker compose up --build -d
make migrate
make demo-seed
```

Abrir:

- `/docs` para Swagger;
- `/health/ready` para readiness;
- `/api/v1/stats` para indicadores;
- Streamlit para análise visual.

## 4. Cenários

### Cenário A — falha com documento

Enviar `data/sample_event.json` com `cocked_rotor_2`.

Esperado:

- similaridade histórica;
- score de anomalia;
- recomendação supported;
- evidências documentais.

### Cenário B — falha sem documento

Alterar `fault` para `falha_desconhecida`.

Esperado:

- recomendação unsupported;
- solicitação de novo documento;
- sem alucinação.

### Cenário C — estado normal

Alterar `fault` para `normal`.

Esperado:

- não recomendar manutenção;
- continuar monitoramento.

## 5. Fechamento

Explicar evolução para produção: Kafka/MQTT, OIDC, MLflow, Grafana, validação humana e monitoramento de drift.
