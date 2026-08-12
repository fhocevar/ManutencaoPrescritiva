import json
import os
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st


API_URL = os.getenv("API_URL", "http://localhost:8000")

BASE_DIR = Path(__file__).resolve().parents[1]
BANNER_CSV = BASE_DIR / "data" / "banner.csv"


st.set_page_config(
    page_title="Manutenção Prescritiva Enterprise",
    page_icon="🛠️",
    layout="wide",
)

st.title("Manutenção Prescritiva Enterprise")
st.caption(
    "API + PostgreSQL/pgvector + ML + RAG + Evidências Documentais"
)


# ============================================================
# API
# ============================================================

def api_get(path: str):
    try:
        return httpx.get(
            f"{API_URL}{path}",
            timeout=20,
        )
    except Exception as exc:
        st.error(
            f"Falha ao conectar na API: {exc}"
        )
        return None


def api_post(path: str, **kwargs):
    try:
        return httpx.post(
            f"{API_URL}{path}",
            timeout=180,
            **kwargs,
        )
    except Exception as exc:
        st.error(
            f"Falha ao conectar na API: {exc}"
        )
        return None


# ============================================================
# DATASET / CENÁRIOS
# ============================================================

def normalize_fault(value: Any) -> str:
    return (
        str(value)
        .strip()
        .lower()
    )


def python_value(value: Any):
    """
    Converte tipos pandas/numpy para tipos JSON serializáveis.
    """
    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


@st.cache_data(show_spinner=False)
def load_banner(csv_path: str) -> pd.DataFrame:
    path = Path(csv_path)

    if not path.exists():
        return pd.DataFrame()

    frame = pd.read_csv(
        path,
        low_memory=False,
    )

    if "fault" in frame.columns:
        frame["fault_normalized"] = (
            frame["fault"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

    if "created_at" in frame.columns:
        frame["created_at"] = pd.to_datetime(
            frame["created_at"],
            utc=True,
            errors="coerce",
        )

    return frame


def find_real_event(
    frame: pd.DataFrame,
    aliases: list[str],
) -> dict:
    """
    Procura um registro real no banner.csv usando aliases de fault.
    """
    if frame.empty:
        return {}

    if "fault_normalized" not in frame.columns:
        return {}

    normalized_aliases = {
        normalize_fault(alias)
        for alias in aliases
    }

    # Primeiro tenta correspondência exata.
    matches = frame[
        frame["fault_normalized"].isin(
            normalized_aliases
        )
    ]

    # Caso não encontre, tenta correspondência parcial.
    if matches.empty:
        mask = pd.Series(
            False,
            index=frame.index,
        )

        for alias in normalized_aliases:
            mask = mask | (
                frame["fault_normalized"]
                .str.contains(
                    alias,
                    regex=False,
                    na=False,
                )
            )

        matches = frame[mask]

    if matches.empty:
        return {}

    # Usa um registro intermediário em vez do primeiro.
    # Isso reduz a chance de pegar algum registro de transição.
    row = matches.iloc[
        len(matches) // 2
    ]

    payload = {}

    for column, value in row.items():
        if column == "fault_normalized":
            continue

        converted = python_value(value)

        if converted is not None:
            payload[column] = converted

    return payload


def build_demo_scenarios(
    frame: pd.DataFrame,
) -> dict[str, dict]:
    scenarios: dict[str, dict] = {}

    # --------------------------------------------------------
    # Rotor inclinado
    # --------------------------------------------------------

    cocked = find_real_event(
        frame,
        [
            "cocked_rotor_2",
            "cocked_rotor",
        ],
    )

    if cocked:
        scenarios[
            "Rotor inclinado — evento real"
        ] = cocked

    # --------------------------------------------------------
    # Desalinhamento
    # --------------------------------------------------------

    misalignment = find_real_event(
        frame,
        [
            "desalinhado",
            "desalinhamento",
            "misalignment",
        ],
    )

    if misalignment:
        scenarios[
            "Desalinhamento — evento real"
        ] = misalignment

    # --------------------------------------------------------
    # Desbalanceamento
    # --------------------------------------------------------

    imbalance = find_real_event(
        frame,
        [
            "desbalanceado",
            "desbalanceamento",
            "desabalanceado",
            "imbalance",
        ],
    )

    if imbalance:
        scenarios[
            "Desbalanceamento — evento real"
        ] = imbalance

    # --------------------------------------------------------
    # Normal
    # --------------------------------------------------------

    normal = find_real_event(
        frame,
        [
            "normal",
            "baseline",
        ],
    )

    if normal:
        scenarios[
            "Condição normal — evento real"
        ] = normal

    # --------------------------------------------------------
    # Falha sem documentação
    #
    # Usa métricas REAIS, mas altera propositalmente o fault.
    # Serve para provar a regra anti-alucinação.
    # --------------------------------------------------------

    base_unsupported = (
        cocked
        or misalignment
        or imbalance
        or normal
    )

    if base_unsupported:
        unsupported = (
            base_unsupported.copy()
        )

        unsupported["fault"] = (
            "falha_sem_documentacao_demo"
        )

        scenarios[
            "Falha sem documentação — teste anti-alucinação"
        ] = unsupported

    return scenarios


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("Operação")

    health = api_get(
        "/health/ready"
    )

    if health and health.is_success:
        st.success("API pronta")
    else:
        st.warning("API indisponível")

    stats = api_get(
        "/api/v1/stats"
    )

    if stats and stats.is_success:
        stats_data = stats.json()

        st.metric(
            "Eventos",
            stats_data.get(
                "events",
                0,
            ),
        )

        st.metric(
            "Documentos",
            stats_data.get(
                "documents",
                0,
            ),
        )

        st.metric(
            "Chunks",
            stats_data.get(
                "document_chunks",
                0,
            ),
        )

        st.metric(
            "Análises",
            stats_data.get(
                "analyses",
                0,
            ),
        )

    st.divider()

    st.header(
        "Base documental"
    )

    uploaded = st.file_uploader(
        "Adicionar documento",
        type=[
            "pdf",
            "txt",
            "md",
        ],
    )

    if uploaded and st.button(
        "Indexar documento",
        use_container_width=True,
    ):
        with st.spinner(
            "Extraindo, vetorizando e indexando..."
        ):
            response = api_post(
                "/api/v1/documents/upload",
                files={
                    "file": (
                        uploaded.name,
                        uploaded.getvalue(),
                        uploaded.type,
                    ),
                },
            )

        if (
            response
            and response.is_success
        ):
            st.success(
                "Documento indexado em "
                f"{response.json()['chunks']} "
                "trechos."
            )

        elif response:
            st.error(
                response.text
            )


# ============================================================
# ABAS
# ============================================================

tab_event, tab_chat, tab_stats, tab_arch = st.tabs(
    [
        "Análise de evento",
        "Chat documental",
        "Indicadores",
        "Arquitetura",
    ]
)


# ============================================================
# ABA — ANÁLISE DE EVENTO
# ============================================================

with tab_event:
    st.subheader(
        "Análise de evento"
    )

    st.caption(
        "Selecione um cenário baseado em um registro real "
        "do banner.csv ou informe manualmente o JSON."
    )

    banner = load_banner(
        str(BANNER_CSV)
    )

    scenarios = build_demo_scenarios(
        banner
    )

    scenario_options = (
        list(scenarios.keys())
        + [
            "JSON manual / vazio",
        ]
    )

    selected_scenario = st.selectbox(
        "Cenário de análise",
        options=scenario_options,
        key="analysis_scenario",
    )

    if (
        selected_scenario
        == "JSON manual / vazio"
    ):
        selected_payload = {}

        st.info(
            "Modo manual: informe um JSON "
            "completo para executar a análise."
        )

    else:
        selected_payload = scenarios[
            selected_scenario
        ]

        scenario_fault = (
            selected_payload.get(
                "fault",
                "N/D",
            )
        )

        scenario_id = (
            selected_payload.get(
                "id",
                "N/D",
            )
        )

        scenario_date = (
            selected_payload.get(
                "created_at",
                "N/D",
            )
        )

        c1, c2, c3 = st.columns(
            3
        )

        c1.metric(
            "Fault original",
            scenario_fault,
        )

        c2.metric(
            "ID",
            scenario_id,
        )

        c3.metric(
            "Data",
            str(scenario_date)[
                :19
            ],
        )

        if (
            selected_scenario
            == (
                "Falha sem documentação — "
                "teste anti-alucinação"
            )
        ):
            st.warning(
                "Este cenário utiliza métricas de "
                "um evento real, mas substitui "
                "propositalmente o campo fault por "
                "'falha_sem_documentacao_demo'. "
                "O objetivo é provar que o sistema "
                "não inventa uma recomendação quando "
                "não encontra documentação adequada."
            )

        else:
            st.success(
                "As métricas deste cenário foram "
                "extraídas diretamente do banner.csv."
            )

    default_json = json.dumps(
        selected_payload,
        indent=2,
        ensure_ascii=False,
    )

    event_text = st.text_area(
        "JSON do evento",
        value=default_json,
        height=390,
        key=(
            "event_json_"
            + selected_scenario
        ),
    )

    if st.button(
        "Analisar evento",
        type="primary",
        use_container_width=True,
        key="analyze_event_button",
    ):
        try:
            payload = json.loads(
                event_text
            )

        except json.JSONDecodeError as exc:
            st.error(
                f"JSON inválido: {exc}"
            )
            st.stop()

        if not payload:
            st.warning(
                "Informe um evento antes "
                "de executar a análise."
            )
            st.stop()

        with st.spinner(
            "Analisando histórico, anomalia, "
            "similaridade e documentação..."
        ):
            response = api_post(
                "/api/v1/events/analyze",
                json=payload,
            )

        if (
            not response
            or not response.is_success
        ):
            st.error(
                response.text
                if response
                else "Sem resposta"
            )
            st.stop()

        result = response.json()

        col1, col2, col3, col4, col5 = (
            st.columns(5)
        )

        col1.metric(
            "Defeito",
            result[
                "detected_fault"
            ],
        )

        col2.metric(
            "É problema?",
            (
                "Sim"
                if result[
                    "is_problem"
                ]
                else "Não"
            ),
        )

        col3.metric(
            "Similares",
            result[
                "similar_events_count"
            ],
        )

        col4.metric(
            "Freq./mês",
            result[
                "frequency_per_month"
            ],
        )

        anomaly = result[
            "anomaly_score"
        ]

        col5.metric(
            "Score de anomalia",
            (
                "N/D"
                if anomaly is None
                else f"{anomaly:.2%}"
            ),
        )

        # ----------------------------------------------------
        # RECOMENDAÇÃO
        # ----------------------------------------------------

        recommendation = result[
            "recommendation"
        ]

        status = recommendation[
            "status"
        ]

        if status == "supported":
            st.success(
                recommendation[
                    "summary"
                ]
            )

        elif status == "unsupported":
            st.warning(
                recommendation[
                    "summary"
                ]
            )

        else:
            st.info(
                recommendation[
                    "summary"
                ]
            )

        st.subheader(
            "Ações prescritivas"
        )

        steps = recommendation.get(
            "steps",
            [],
        )

        if steps:
            for index, step in enumerate(
                steps,
                start=1,
            ):
                st.write(
                    f"**{index}.** {step}"
                )
        else:
            st.info(
                "Nenhuma ação prescritiva "
                "foi retornada."
            )

        # ----------------------------------------------------
        # EVENTOS SIMILARES
        # ----------------------------------------------------

        similar = pd.DataFrame(
            result.get(
                "similar_events",
                [],
            )
        )

        if not similar.empty:
            similar[
                "created_at"
            ] = pd.to_datetime(
                similar[
                    "created_at"
                ]
            )

            left, right = (
                st.columns(2)
            )

            with left:
                counts = similar.groupby(
                    similar[
                        "created_at"
                    ]
                    .dt.to_period(
                        "M"
                    )
                    .astype(str)
                ).size()

                chart_df = (
                    counts
                    .rename(
                        "ocorrencias"
                    )
                    .reset_index()
                )

                chart_df.columns = [
                    "mes",
                    "ocorrencias",
                ]

                st.plotly_chart(
                    px.bar(
                        chart_df,
                        x="mes",
                        y="ocorrencias",
                        title=(
                            "Distribuição "
                            "temporal"
                        ),
                    ),
                    use_container_width=True,
                )

            with right:
                fault_counts = (
                    similar
                    .groupby(
                        "fault"
                    )
                    .size()
                    .rename(
                        "ocorrencias"
                    )
                    .reset_index()
                )

                st.plotly_chart(
                    px.pie(
                        fault_counts,
                        names="fault",
                        values=(
                            "ocorrencias"
                        ),
                        title=(
                            "Falhas "
                            "similares"
                        ),
                    ),
                    use_container_width=True,
                )

            st.plotly_chart(
                px.scatter(
                    similar,
                    x="created_at",
                    y="distance",
                    color="fault",
                    title=(
                        "Distância dos "
                        "eventos similares"
                    ),
                ),
                use_container_width=True,
            )

            display_columns = [
                column
                for column in [
                    "external_id",
                    "created_at",
                    "fault",
                    "distance",
                ]
                if column
                in similar.columns
            ]

            st.dataframe(
                similar[
                    display_columns
                ],
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Nenhum evento dentro "
                "do limiar de similaridade."
            )

        # ----------------------------------------------------
        # EVIDÊNCIAS
        # ----------------------------------------------------

        evidence = recommendation.get(
            "evidence",
            [],
        )

        if evidence:
            st.subheader(
                "Evidências documentais"
            )

            for item in evidence:
                filename = item.get(
                    "filename",
                    "Documento",
                )

                similarity = item.get(
                    "similarity",
                    0,
                )

                with st.expander(
                    f"{filename} — "
                    f"similaridade "
                    f"{similarity:.1%}"
                ):
                    st.write(
                        item.get(
                            "content",
                            "",
                        )
                    )

        else:
            st.info(
                "Nenhuma evidência documental "
                "retornada."
            )

        # ----------------------------------------------------
        # FEEDBACK HUMANO
        # ----------------------------------------------------

        with st.expander(
            "Registrar feedback humano"
        ):
            rating = st.slider(
                "Nota da recomendação",
                1,
                5,
                4,
                key=(
                    "rating_"
                    + result[
                        "event_id"
                    ]
                ),
            )

            comment = st.text_area(
                "Comentário",
                key=(
                    "comment_"
                    + result[
                        "event_id"
                    ]
                ),
            )

            if st.button(
                "Enviar feedback",
                key=(
                    "feedback_"
                    + result[
                        "event_id"
                    ]
                ),
            ):
                fb = api_post(
                    "/api/v1/feedback",
                    json={
                        "event_id": (
                            result[
                                "event_id"
                            ]
                        ),
                        "rating": rating,
                        "comment": (
                            comment
                        ),
                    },
                )

                if (
                    fb
                    and fb.is_success
                ):
                    st.success(
                        "Feedback registrado."
                    )

                elif fb:
                    st.error(
                        fb.text
                    )


# ============================================================
# ABA — CHAT DOCUMENTAL
# ============================================================

with tab_chat:
    st.subheader(
        "Chat com base documental"
    )

    st.caption(
        "Consulte os procedimentos técnicos "
        "indexados no PostgreSQL/pgvector."
    )

    stats_response = api_get(
        "/api/v1/stats"
    )

    seeded_faults = []

    if (
        stats_response
        and stats_response.is_success
    ):
        stats_data = (
            stats_response.json()
        )

        seeded_faults = [
            item.get(
                "fault"
            )
            for item
            in stats_data.get(
                "top_faults",
                [],
            )
            if item.get(
                "fault"
            )
        ]

    fallback_faults = [
        "cocked_rotor_2",
        "desalinhado",
        "desbalanceado",
    ]

    normal_states = {
        "normal",
        "baseline",
        "teste",
        "acelerando",
        "motor_desligado",
        "healthy",
        "ok",
        "sem_falha",
        "sem falha",
        "no_fault",
    }

    available_faults = sorted(
        {
            *fallback_faults,
            *seeded_faults,
        }
        - normal_states
    )

    demo_faults = [
        "",
        *available_faults,
    ]

    fault_labels = {
        "": "Sem filtro de defeito",

        "cocked_rotor_2":
            "Rotor inclinado "
            "(cocked_rotor_2)",

        "cocked_rotor":
            "Rotor inclinado "
            "(cocked_rotor)",

        "desalinhado":
            "Desalinhamento",

        "desalinhamento":
            "Desalinhamento",

        "desbalanceado":
            "Desbalanceamento",

        "desbalanceamento":
            "Desbalanceamento",

        "imbalance":
            "Desbalanceamento "
            "(imbalance)",

        "misalignment":
            "Desalinhamento "
            "(misalignment)",

        "bearing_fault":
            "Falha de rolamento "
            "(bearing_fault)",

        "bearing":
            "Falha de rolamento "
            "(bearing)",
    }

    fault = st.selectbox(
        "Defeito / contexto",
        options=demo_faults,
        format_func=lambda value: (
            fault_labels.get(
                value,
                value
                .replace(
                    "_",
                    " ",
                )
                .strip()
                .title(),
            )
        ),
        key="chat_fault",
    )

    default_questions = {
        "cocked_rotor_2": (
            "Qual procedimento devo seguir "
            "para diagnosticar e corrigir "
            "um rotor inclinado?"
        ),

        "cocked_rotor": (
            "Qual procedimento devo seguir "
            "para diagnosticar e corrigir "
            "um rotor inclinado?"
        ),

        "desalinhado": (
            "Qual procedimento de inspeção "
            "e correção devo seguir para "
            "desalinhamento?"
        ),

        "desalinhamento": (
            "Qual procedimento de inspeção "
            "e correção devo seguir para "
            "desalinhamento?"
        ),

        "misalignment": (
            "Qual procedimento de inspeção "
            "e correção devo seguir para "
            "desalinhamento?"
        ),

        "desbalanceado": (
            "Como devo diagnosticar e "
            "corrigir um problema de "
            "desbalanceamento?"
        ),

        "desbalanceamento": (
            "Como devo diagnosticar e "
            "corrigir um problema de "
            "desbalanceamento?"
        ),

        "imbalance": (
            "Como devo diagnosticar e "
            "corrigir um problema de "
            "desbalanceamento?"
        ),

        "bearing_fault": (
            "Qual procedimento devo seguir "
            "para diagnosticar e corrigir "
            "uma falha de rolamento?"
        ),

        "bearing": (
            "Qual procedimento devo seguir "
            "para diagnosticar e corrigir "
            "uma falha de rolamento?"
        ),

        "": (
            "Qual procedimento de "
            "inspeção devo seguir?"
        ),
    }

    default_question = (
        default_questions.get(
            fault,
            (
                "Qual procedimento técnico "
                "devo seguir para diagnosticar "
                "e corrigir a falha "
                f"'{fault.replace('_', ' ')}'?"
                if fault
                else (
                    "Qual procedimento de "
                    "inspeção devo seguir?"
                )
            ),
        )
    )

    question = st.text_area(
        "Pergunta",
        value=default_question,
        height=100,
        key=(
            "chat_question_"
            + (
                fault
                if fault
                else "all"
            )
        ),
    )

    if st.button(
        "Consultar documentação",
        use_container_width=True,
        type="primary",
        key="chat_button",
    ):
        with st.spinner(
            "Buscando evidências "
            "na base vetorial..."
        ):
            response = api_post(
                "/api/v1/chat",
                json={
                    "question": question,
                    "fault": (
                        fault
                        or None
                    ),
                },
            )

        if (
            response
            and response.is_success
        ):
            result = response.json()

            status = result.get(
                "status"
            )

            if status == "supported":
                st.success(
                    result[
                        "answer"
                    ]
                )
            else:
                st.warning(
                    result[
                        "answer"
                    ]
                )

            steps = result.get(
                "steps",
                [],
            )

            if steps:
                st.subheader(
                    "Procedimento sugerido"
                )

                for index, step in enumerate(
                    steps,
                    start=1,
                ):
                    st.write(
                        f"**{index}.** "
                        f"{step}"
                    )

            evidence = result.get(
                "evidence",
                [],
            )

            if evidence:
                st.subheader(
                    "Evidências documentais"
                )

                for ev in evidence:
                    filename = ev.get(
                        "filename",
                        "Documento",
                    )

                    similarity = ev.get(
                        "similarity",
                        0,
                    )

                    with st.expander(
                        f"{filename} — "
                        f"{similarity:.1%}"
                    ):
                        st.write(
                            ev.get(
                                "content",
                                "",
                            )
                        )

            else:
                st.info(
                    "Nenhuma evidência "
                    "documental foi retornada."
                )

        elif response:
            st.error(
                response.text
            )


# ============================================================
# ABA — INDICADORES
# ============================================================

with tab_stats:
    st.subheader(
        "Indicadores gerais"
    )

    response = api_get(
        "/api/v1/stats"
    )

    if (
        response
        and response.is_success
    ):
        data = response.json()

        cols = st.columns(4)

        cols[0].metric(
            "Eventos",
            data[
                "events"
            ],
        )

        cols[1].metric(
            "Documentos",
            data[
                "documents"
            ],
        )

        cols[2].metric(
            "Chunks",
            data[
                "document_chunks"
            ],
        )

        cols[3].metric(
            "Análises",
            data[
                "analyses"
            ],
        )

        top = pd.DataFrame(
            data.get(
                "top_faults",
                [],
            )
        )

        if not top.empty:
            st.plotly_chart(
                px.bar(
                    top,
                    x="fault",
                    y="total",
                    title=(
                        "Top falhas / "
                        "estados"
                    ),
                ),
                use_container_width=True,
            )

        else:
            st.info(
                "Sem dados ainda."
            )

    else:
        st.info(
            "Sem dados ainda."
        )


# ============================================================
# ABA — ARQUITETURA
# ============================================================

with tab_arch:
    st.subheader(
        "Fluxo de decisão"
    )

    st.code(
        """
+-----------------------------------+
| Novo evento                       |
+-----------------+-----------------+
                  |
                  v
+-----------------------------------+
| Validação das métricas            |
+-----------------+-----------------+
                  |
                  v
+-----------------------------------+
| StandardScaler                    |
| Isolation Forest                  |
+-----------------+-----------------+
                  |
                  v
+-----------------------------------+
| Busca de eventos similares        |
| PostgreSQL + pgvector             |
+-----------------+-----------------+
                  |
                  v
+-----------------------------------+
| Estado operacional normal?        |
+-----------+-----------------------+
            |
       +----+----+
       |         |
      SIM       NÃO
       |         |
       v         v
+-------------+  +------------------+
| Não         |  | Busca            |
| recomenda   |  | documentação     |
| manutenção  |  +---------+--------+
+-------------+            |
                           v
                 +------------------+
                 | Documento        |
                 | encontrado?      |
                 +-----+-------+----+
                       |       |
                      NÃO     SIM
                       |       |
                       v       v
               +---------+  +---------+
               | Bloqueia|  | RAG     |
               | resposta|  | +       |
               |         |  | Evidence|
               +---------+  +---------+
""",
        language="text",
    )

    st.info(
        "A solução foi desenhada para "
        "operação industrial com validação "
        "humana antes de qualquer "
        "intervenção física."
    )