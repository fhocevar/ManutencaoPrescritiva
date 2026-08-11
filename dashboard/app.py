import json
import os
from pathlib import Path

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Manutenção Prescritiva Enterprise", page_icon="🛠️", layout="wide")
st.title("Manutenção Prescritiva Enterprise")
st.caption("API + PostgreSQL/pgvector + ML + RAG + Evidências Documentais")


def api_get(path: str):
    try:
        return httpx.get(f"{API_URL}{path}", timeout=20)
    except Exception as exc:
        st.error(f"Falha ao conectar na API: {exc}")
        return None


def api_post(path: str, **kwargs):
    try:
        return httpx.post(f"{API_URL}{path}", timeout=180, **kwargs)
    except Exception as exc:
        st.error(f"Falha ao conectar na API: {exc}")
        return None


with st.sidebar:
    st.header("Operação")
    health = api_get("/health/ready")
    if health and health.is_success:
        st.success("API pronta")
    else:
        st.warning("API indisponível")

    stats = api_get("/api/v1/stats")
    if stats and stats.is_success:
        data = stats.json()
        st.metric("Eventos", data.get("events", 0))
        st.metric("Documentos", data.get("documents", 0))
        st.metric("Chunks", data.get("document_chunks", 0))
        st.metric("Análises", data.get("analyses", 0))

    st.divider()
    st.header("Base documental")
    uploaded = st.file_uploader("Adicionar documento", type=["pdf", "txt", "md"])
    if uploaded and st.button("Indexar documento", use_container_width=True):
        with st.spinner("Extraindo, vetorizando e indexando..."):
            response = api_post(
                "/api/v1/documents/upload",
                files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
            )
        if response and response.is_success:
            st.success(f"Documento indexado em {response.json()['chunks']} trechos.")
        elif response:
            st.error(response.text)

tab_event, tab_chat, tab_stats, tab_arch = st.tabs([
    "Análise de evento", "Chat documental", "Indicadores", "Arquitetura"
])

with tab_event:
    st.subheader("Novo evento")
    sample_path = Path("data/sample_event.json")
    default_json = sample_path.read_text(encoding="utf-8") if sample_path.exists() else "{}"
    event_text = st.text_area("JSON do evento", value=default_json, height=330)

    if st.button("Analisar evento", type="primary", use_container_width=True):
        try:
            payload = json.loads(event_text)
        except json.JSONDecodeError as exc:
            st.error(f"JSON inválido: {exc}")
            st.stop()

        with st.spinner("Analisando histórico, anomalia, similaridade e documentação..."):
            response = api_post("/api/v1/events/analyze", json=payload)
        if not response or not response.is_success:
            st.error(response.text if response else "Sem resposta")
            st.stop()

        result = response.json()
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Defeito", result["detected_fault"])
        col2.metric("É problema?", "Sim" if result["is_problem"] else "Não")
        col3.metric("Similares", result["similar_events_count"])
        col4.metric("Freq./mês", result["frequency_per_month"])
        anomaly = result["anomaly_score"]
        col5.metric("Score de anomalia","N/D" if anomaly is None else f"{anomaly:.2%}")

        status = result["recommendation"]["status"]
        if status == "supported":
            st.success(result["recommendation"]["summary"])
        elif status == "unsupported":
            st.warning(result["recommendation"]["summary"])
        else:
            st.info(result["recommendation"]["summary"])

        st.subheader("Ações prescritivas")
        for index, step in enumerate(result["recommendation"]["steps"], start=1):
            st.write(f"**{index}.** {step}")

        similar = pd.DataFrame(result["similar_events"])
        if not similar.empty:
            similar["created_at"] = pd.to_datetime(similar["created_at"])
            left, right = st.columns(2)
            with left:
                counts = similar.groupby(similar["created_at"].dt.to_period("M").astype(str)).size()
                chart_df = counts.rename("ocorrencias").reset_index()
                chart_df.columns = ["mes", "ocorrencias"]
                st.plotly_chart(px.bar(chart_df, x="mes", y="ocorrencias", title="Distribuição temporal"), use_container_width=True)
            with right:
                fault_counts = similar.groupby("fault").size().rename("ocorrencias").reset_index()
                st.plotly_chart(px.pie(fault_counts, names="fault", values="ocorrencias", title="Falhas similares"), use_container_width=True)
            st.plotly_chart(px.scatter(similar, x="created_at", y="distance", color="fault", title="Distância dos eventos similares"), use_container_width=True)
            st.dataframe(similar[["external_id", "created_at", "fault", "distance"]], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum evento dentro do limiar de similaridade.")

        evidence = result["recommendation"]["evidence"]
        if evidence:
            st.subheader("Evidências documentais")
            for item in evidence:
                with st.expander(f"{item['filename']} — similaridade {item['similarity']:.1%}"):
                    st.write(item["content"])

        with st.expander("Registrar feedback humano"):
            rating = st.slider("Nota da recomendação", 1, 5, 4)
            comment = st.text_area("Comentário")
            if st.button("Enviar feedback"):
                fb = api_post("/api/v1/feedback", json={"event_id": result["event_id"], "rating": rating, "comment": comment})
                if fb and fb.is_success:
                    st.success("Feedback registrado.")

with tab_chat:
    st.subheader("Chat com base documental")
    question = st.text_input("Pergunta", "Qual procedimento de inspeção devo seguir?")
    fault = st.text_input("Defeito opcional", "cocked_rotor_2")
    if st.button("Perguntar", use_container_width=True):
        response = api_post("/api/v1/chat", json={"question": question, "fault": fault or None})
        if response and response.is_success:
            result = response.json()
            if result["status"] == "supported":
                st.success(result["answer"])
                for step in result.get("steps", []):
                    st.write("-", step)
            else:
                st.warning(result["answer"])
            for ev in result.get("evidence", []):
                with st.expander(f"{ev['filename']} — {ev['similarity']:.1%}"):
                    st.write(ev["content"])
        elif response:
            st.error(response.text)

with tab_stats:
    st.subheader("Indicadores gerais")
    response = api_get("/api/v1/stats")
    if response and response.is_success:
        data = response.json()
        cols = st.columns(4)
        cols[0].metric("Eventos", data["events"])
        cols[1].metric("Documentos", data["documents"])
        cols[2].metric("Chunks", data["document_chunks"])
        cols[3].metric("Análises", data["analyses"])
        top = pd.DataFrame(data.get("top_faults", []))
        if not top.empty:
            st.plotly_chart(px.bar(top, x="fault", y="total", title="Top falhas/estados"), use_container_width=True)
    else:
        st.info("Sem dados ainda.")

with tab_arch:
    st.subheader("Fluxo de decisão")
    st.code("""
Novo evento
  -> valida métricas
  -> normaliza vetor
  -> calcula anomalia
  -> busca eventos similares
  -> se fault é estado normal: não recomenda manutenção
  -> se fault é problema: busca documentação
  -> se não há documento: bloqueia recomendação
  -> se há documento: gera resposta somente com evidências
""", language="text")
    st.info("A solução foi desenhada para operação industrial com validação humana antes de qualquer intervenção física.")
