import re

import httpx

from app.domain.entities import DocumentEvidence


class TemplateRecommendationGenerator:
    async def generate(
        self, fault: str, evidence: list[DocumentEvidence]
    ) -> tuple[str, list[str]]:
        best = evidence[0]
        sentences = [
            item.strip()
            for item in re.split(r"(?<=[.!?])\s+", best.content)
            if len(item.strip()) >= 25
        ]
        steps = sentences[:4] or [
            "Consultar o documento técnico recuperado antes de qualquer intervenção."
        ]
        summary = (
            f"Foram encontrados documentos relacionados ao defeito '{fault}'. "
            "A recomendação deve ser validada pela equipe técnica antes da execução."
        )
        return summary, steps


class OpenAICompatibleRecommendationGenerator:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout_seconds

    async def generate(
        self, fault: str, evidence: list[DocumentEvidence]
    ) -> tuple[str, list[str]]:
        context = "\n\n".join(
            f"[Fonte {index + 1}: {item.filename}]\n{item.content}"
            for index, item in enumerate(evidence)
        )
        prompt = f"""
Você é um assistente de manutenção industrial.
Responda exclusivamente com base nas fontes fornecidas.
Não invente ferramentas, limites, peças, causas ou procedimentos.
Defeito: {fault}

Fontes:
{context}

Retorne JSON válido:
{{
  "summary": "resumo curto",
  "steps": ["passo sustentado pelas fontes"]
}}
"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "Não use conhecimento externo às fontes."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=payload
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]

        import json
        parsed = json.loads(content)
        summary = str(parsed.get("summary", "")).strip()
        steps = [str(step).strip() for step in parsed.get("steps", []) if str(step).strip()]
        if not summary or not steps:
            raise ValueError("Resposta do LLM não contém resumo e passos válidos.")
        return summary, steps
