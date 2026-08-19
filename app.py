import json
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

import requests
import streamlit as st


NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
LATITUD_VENTANAS = -1.44
LONGITUD_VENTANAS = -79.46
DIAS_ANALIZADOS = 7
DIAS_CONSULTADOS = 14
ZONA_HORARIA_ECUADOR = timezone(timedelta(hours=-5))


def evaluar_riesgo_siembra_maiz(
    humedad_relativa_promedio_pct: float,
    precipitacion_acumulada_mm: float,
) -> Tuple[str, str]:
    """Evalúa el riesgo de siembra mediante reglas determinísticas."""
    if (
        humedad_relativa_promedio_pct > 80
        or precipitacion_acumulada_mm > 30
    ):
        return "ALTO", "Postergar siembra"

    return "BAJO", "Condiciones óptimas"


def _es_valor_climatico_valido(valor: object, valor_faltante: float) -> bool:
    try:
        valor_numerico = float(valor)
    except (TypeError, ValueError):
        return False

    return math.isfinite(valor_numerico) and valor_numerico != valor_faltante


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_datos_climaticos_nasa_power() -> Dict[str, Any]:
    """Obtiene y resume las siete observaciones diarias válidas más recientes."""
    fecha_consulta = datetime.now(ZONA_HORARIA_ECUADOR)
    fecha_fin = fecha_consulta.date()
    fecha_inicio = fecha_fin - timedelta(days=DIAS_CONSULTADOS - 1)

    parametros = {
        "parameters": "PRECTOTCORR,RH2M",
        "community": "AG",
        "longitude": LONGITUD_VENTANAS,
        "latitude": LATITUD_VENTANAS,
        "start": fecha_inicio.strftime("%Y%m%d"),
        "end": fecha_fin.strftime("%Y%m%d"),
        "format": "JSON",
        "time-standard": "LST",
    }

    try:
        respuesta = requests.get(
            NASA_POWER_URL,
            params=parametros,
            timeout=(5, 30),
        )
        respuesta.raise_for_status()
        contenido = respuesta.json()
    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            "No fue posible consultar NASA POWER en este momento. "
            "Intenta nuevamente en unos minutos."
        ) from error
    except ValueError as error:
        raise RuntimeError(
            "NASA POWER devolvió una respuesta que no contiene JSON válido."
        ) from error

    try:
        series = contenido["properties"]["parameter"]
        precipitacion_diaria = series["PRECTOTCORR"]
        humedad_diaria = series["RH2M"]
    except (KeyError, TypeError) as error:
        raise RuntimeError(
            "La respuesta de NASA POWER no contiene las variables climáticas "
            "solicitadas."
        ) from error

    cabecera = contenido.get("header", {})
    try:
        valor_faltante = float(cabecera.get("fill_value", -999.0))
    except (AttributeError, TypeError, ValueError):
        valor_faltante = -999.0

    fechas_comunes = sorted(set(precipitacion_diaria) & set(humedad_diaria))
    observaciones_validas = []

    for fecha in fechas_comunes:
        valor_precipitacion = precipitacion_diaria[fecha]
        valor_humedad = humedad_diaria[fecha]

        if not (
            _es_valor_climatico_valido(valor_precipitacion, valor_faltante)
            and _es_valor_climatico_valido(valor_humedad, valor_faltante)
        ):
            continue

        observaciones_validas.append(
            {
                "fecha": datetime.strptime(fecha, "%Y%m%d").date().isoformat(),
                "precipitacion_corregida_mm_dia": float(valor_precipitacion),
                "humedad_relativa_2m_pct": float(valor_humedad),
            }
        )

    ultimas_observaciones = observaciones_validas[-DIAS_ANALIZADOS:]
    if len(ultimas_observaciones) < DIAS_ANALIZADOS:
        raise RuntimeError(
            "NASA POWER no dispone de siete días completos para realizar "
            "la evaluación agroclimática."
        )

    humedad_promedio = round(
        sum(
            observacion["humedad_relativa_2m_pct"]
            for observacion in ultimas_observaciones
        )
        / DIAS_ANALIZADOS,
        2,
    )
    precipitacion_acumulada = round(
        sum(
            observacion["precipitacion_corregida_mm_dia"]
            for observacion in ultimas_observaciones
        ),
        2,
    )

    return {
        "fuente": {
            "nombre": "NASA POWER",
            "endpoint": NASA_POWER_URL,
            "comunidad": "AG",
            "url_consulta": respuesta.url,
            "consultado_en_ecuador": fecha_consulta.isoformat(timespec="seconds"),
        },
        "ubicacion": {
            "localidad": "Ventanas, Los Ríos, Ecuador",
            "latitud": LATITUD_VENTANAS,
            "longitud": LONGITUD_VENTANAS,
        },
        "periodo_analizado": {
            "inicio": ultimas_observaciones[0]["fecha"],
            "fin": ultimas_observaciones[-1]["fecha"],
            "dias": DIAS_ANALIZADOS,
        },
        "humedad_relativa_promedio_pct": humedad_promedio,
        "precipitacion_acumulada_7_dias_mm": precipitacion_acumulada,
        "observaciones_diarias": ultimas_observaciones,
    }


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
    try:
        with st.spinner("Consultando datos reales de NASA POWER..."):
            datos_ambientales = obtener_datos_climaticos_nasa_power()
    except RuntimeError as error:
        st.error(str(error))
        st.stop()

    nivel_riesgo, recomendacion = evaluar_riesgo_siembra_maiz(
        datos_ambientales["humedad_relativa_promedio_pct"],
        datos_ambientales["precipitacion_acumulada_7_dias_mm"],
    )

    st.subheader("Datos ambientales actuales")
    columna_1, columna_2, columna_3 = st.columns(3)
    columna_1.metric(
        "Humedad relativa promedio",
        f"{datos_ambientales['humedad_relativa_promedio_pct']:.2f} %",
    )
    columna_2.metric(
        "Precipitación acumulada",
        f"{datos_ambientales['precipitacion_acumulada_7_dias_mm']:.2f} mm",
    )
    columna_3.metric(
        "Periodo analizado",
        f"{datos_ambientales['periodo_analizado']['dias']} días",
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
                "humedad_relativa_promedio_pct > 80 OR "
                "precipitacion_acumulada_7_dias_mm > 30"
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
