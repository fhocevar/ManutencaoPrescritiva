# Arquitetura Enterprise

## Visão de camadas

```mermaid
flowchart TD
    A[Presentation: FastAPI / Streamlit] --> B[Application: Use Cases]
    B --> C[Domain: Entidades e Políticas]
    B --> D[Ports]
    D --> E[Infrastructure: PostgreSQL, ML, RAG, LLM]
```

## Fluxo industrial

```mermaid
sequenceDiagram
    participant Sensor
    participant Gateway
    participant API
    participant ML
    participant PG as PostgreSQL/pgvector
    participant RAG
    participant User

    Sensor->>Gateway: Métricas de vibração
    Gateway->>API: JSON do evento
    API->>ML: Normalização + anomalia
    API->>PG: Busca de eventos similares
    API->>RAG: Busca documental
    alt documento encontrado
        RAG-->>API: Evidências e instruções controladas
    else sem documento
        RAG-->>API: Bloqueio de recomendação
    end
    API-->>User: Resultado + evidências + frequência
```

## Decisões

- `PostgreSQL + pgvector`: reduz complexidade operacional e centraliza histórico, JSONB e embeddings.
- `FastAPI`: contrato OpenAPI e validação forte.
- `Streamlit`: acelera a interação exigida no estudo de caso.
- `Isolation Forest`: adequado para detectar comportamento anômalo sem depender de rótulo completo.
- `RAG guardado`: responde somente com base nos documentos recuperados.
- `Unit of Work`: permite transações consistentes e testabilidade.
- `Redis/Celery`: preparado para indexação assíncrona e reprocessamentos.
- `Prometheus`: instrumentação mínima para operação.

## Produção

Para produção, recomenda-se:

- autenticação OIDC/AD;
- TLS/mTLS;
- API Gateway;
- segregação de rede OT/IT;
- fila Kafka/MQTT;
- PostgreSQL HA;
- MLflow;
- validação humana obrigatória;
- auditoria imutável;
- monitoramento de drift;
- revisão periódica dos documentos técnicos.
