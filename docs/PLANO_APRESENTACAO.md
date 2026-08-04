# Roteiro de apresentação — 12 a 15 minutos

## 1. Problema e objetivo — 1 minuto

Explicar a diferença entre manutenção preditiva e prescritiva e destacar a regra de não recomendar sem documento.

## 2. Arquitetura — 2 minutos

Mostrar Clean Architecture, fluxo de dados e separação entre domínio, aplicação, infraestrutura e apresentação.

## 3. Demonstração — 5 minutos

1. subir o Docker Compose;
2. abrir `/docs`;
3. carregar um documento;
4. enviar o JSON de exemplo;
5. mostrar eventos similares;
6. mostrar frequência e distribuição;
7. mostrar evidências;
8. repetir com defeito sem documento;
9. comprovar que a solução recusa inventar instruções.

## 4. IA e resultados — 3 minutos

- StandardScaler;
- Isolation Forest;
- pgvector;
- embeddings;
- RAG;
- limiares;
- referências;
- controle de alucinação.

## 5. Produção — 2 minutos

Apresentar MQTT/Kafka, OIDC, observabilidade, MLflow, drift e validação humana.

## Perguntas esperadas

- Por que PostgreSQL/pgvector?
- Como o limiar foi definido?
- Como evitar alucinação?
- Como atualizar a documentação?
- Como medir qualidade do RAG?
- Como lidar com drift?
- Por que não classificar previamente todas as falhas?
