import json
from typing import Mapping, Tuple

import streamlit as st


def evaluar_riesgo(datos_climaticos: Mapping[str, float]) -> Tuple[str, str]:
    """Evalúa el riesgo agroclimático mediante reglas determinísticas."""
    humedad_suelo = datos_climaticos["humedad_suelo_pct"]
    pronostico_lluvia = datos_climaticos["pronostico_lluvia_3_dias_mm"]

    if humedad_suelo > 80 or pronostico_lluvia > 30:
        return "ALTO", "Postergar siembra"

    return "BAJO", "Condiciones óptimas"


st.set_page_config(
    page_title="YIAKU AgroClima",
    page_icon="🌱",
    layout="centered",
)

st.title("🌱 YIAKU AgroClima")
st.write(
    "Prototipo TRL 4 para apoyar decisiones agronómicas mediante reglas "
    "agroclimáticas determinísticas, estructuradas y auditables."
)

st.sidebar.header("Contexto productivo")
provincia = st.sidebar.selectbox("Provincia", ["Los Ríos"])
canton = st.sidebar.selectbox("Cantón", ["Ventanas"])
cultivo = st.sidebar.selectbox("Cultivo", ["Maíz Duro Seco"])
etapa_fenologica = st.sidebar.selectbox(
    "Etapa fenológica",
    ["Pre-siembra", "Desarrollo vegetativo"],
    index=0,
)

consultar = st.sidebar.button(
    "Consultar Decisión Agroclimática",
    type="primary",
    use_container_width=True,
)

if consultar:
    datos_ambientales = {
        "humedad_suelo_pct": 85,
        "pronostico_lluvia_3_dias_mm": 45,
        "lluvia_acumulada_mm": 60,
    }

    nivel_riesgo, recomendacion = evaluar_riesgo(datos_ambientales)

    st.subheader("Datos ambientales actuales")
    columna_1, columna_2, columna_3 = st.columns(3)
    columna_1.metric(
        "Humedad del suelo",
        f"{datos_ambientales['humedad_suelo_pct']} %",
    )
    columna_2.metric(
        "Lluvia prevista (3 días)",
        f"{datos_ambientales['pronostico_lluvia_3_dias_mm']} mm",
    )
    columna_3.metric(
        "Lluvia acumulada",
        f"{datos_ambientales['lluvia_acumulada_mm']} mm",
    )

    st.subheader("Decisión agroclimática")
    if nivel_riesgo == "ALTO":
        st.error(f"Riesgo {nivel_riesgo}: {recomendacion}")
    else:
        st.success(f"Riesgo {nivel_riesgo}: {recomendacion}")

    salida_auditable = {
        "sistema": "YIAKU AgroClima",
        "nivel_madurez": "TRL 4",
        "contexto_productivo": {
            "provincia": provincia,
            "canton": canton,
            "cultivo": cultivo,
            "etapa_fenologica": etapa_fenologica,
        },
        "datos_ambientales": datos_ambientales,
        "decision": {
            "nivel_riesgo": nivel_riesgo,
            "recomendacion": recomendacion,
            "regla_aplicada": (
                "humedad_suelo_pct > 80 OR "
                "pronostico_lluvia_3_dias_mm > 30"
            ),
        },
    }

    with st.expander("Ver trazabilidad y JSON técnico"):
        st.code(
            json.dumps(salida_auditable, ensure_ascii=False, indent=2),
            language="json",
        )
else:
    st.info(
        "Selecciona el contexto productivo y presiona "
        "«Consultar Decisión Agroclimática»."
    )
