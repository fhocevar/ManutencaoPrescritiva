# Qualidade e testes

## Testes previstos

- domínio: estados normais, falhas, frequência;
- aplicação: recomendação bloqueada sem documentação;
- API: contrato do payload;
- repositórios: integração com PostgreSQL;
- documentos: parser e chunking;
- ML: compatibilidade de dimensões;
- RAG: evidência obrigatória;
- anti-alucinação: resposta unsupported sem fontes.

## Estratégia de validação

1. Testar com defeito conhecido e documento relacionado.
2. Testar com defeito conhecido sem documento.
3. Testar com estado normal.
4. Testar JSON com métrica ausente.
5. Testar CSV com colunas fora do padrão.
6. Testar alteração de limiares.
7. Validar interpretação com especialista de manutenção.
