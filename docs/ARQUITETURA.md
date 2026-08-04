# Arquitetura técnica para ambiente industrial

## Fluxo online

```text
Sensor/SCADA/PLC
       │
       ▼
Gateway industrial / MQTT
       │
       ▼
Fila de eventos (Kafka ou broker corporativo)
       │
       ▼
API de inferência FastAPI
       ├── normalização + detector de anomalia
       ├── pesquisa pgvector de eventos
       ├── recuperação pgvector de documentos
       └── geração controlada de recomendação
       │
       ▼
PostgreSQL/pgvector ── trilha de auditoria
       │
       ▼
Streamlit / portal corporativo
```

## Zonas

1. **OT/chão de fábrica**: sensores, PLC, SCADA e gateway.
2. **DMZ industrial**: broker e API Gateway.
3. **TI corporativa**: serviços da aplicação, banco, observabilidade e documentos.
4. **Usuário**: dashboard e integração com sistemas de manutenção.

## Controles

- tráfego somente de saída da rede OT;
- TLS mútuo;
- autenticação por identidade de máquina;
- RBAC;
- segregação por unidade e ativo;
- armazenamento criptografado;
- logs imutáveis;
- recomendação sujeita a aceite humano;
- nenhuma atuação automática em máquina no MVP.
