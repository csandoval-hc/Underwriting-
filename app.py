from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Allow `import underwriting...` from ./src
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from auth import require_login, logout_button  # noqa: E402
from underwriting.infrastructure.config import load_settings  # noqa: E402
from underwriting.infrastructure.syntage_client import SyntageClient  # noqa: E402
from underwriting.application.sat_service import SatService  # noqa: E402
from underwriting.ui.sat_views import render_tax_status_cards  # noqa: E402
from underwriting.application.buro_service import obtener_buro_moffin_por_rfc  # noqa: E402


def _bootstrap_env_from_secrets() -> None:
    """Expose secrets as env vars so existing services keep working."""
    load_dotenv()

    for key in ["SYNTAGE_API_KEY", "SYNTAGE_BASE_URL", "MOFFIN_TOKEN"]:
        if key in st.secrets and st.secrets.get(key):
            os.environ[key] = str(st.secrets.get(key)).strip()


@st.cache_resource
def _get_sat_service() -> SatService:
    settings = load_settings()
    client = SyntageClient(settings=settings)
    return SatService(client)


def _money(x: float) -> str:
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "$0.00"


def _render_donut(df: pd.DataFrame, *, title: str, label_col: str, value_col: str) -> None:
    if df is None or df.empty:
        st.info("Sin datos")
        return

    import altair as alt

    d = df[[label_col, value_col]].copy()
    d[label_col] = d[label_col].astype(str)
    d[value_col] = pd.to_numeric(d[value_col], errors="coerce").fillna(0.0)

    if float(d[value_col].sum()) <= 0:
        st.info("Sin datos")
        return

    chart = (
        alt.Chart(d)
        .mark_arc(innerRadius=55)
        .encode(
            theta=alt.Theta(field=value_col, type="quantitative"),
            color=alt.Color(field=label_col, type="nominal", legend=None),
            tooltip=[alt.Tooltip(label_col, type="nominal"), alt.Tooltip(value_col, type="quantitative")],
        )
        .properties(title=title, height=260)
    )

    st.altair_chart(chart, use_container_width=True)


def sat_page() -> None:
    st.header("SAT")
    st.caption("Consulta de estatus fiscal (Syntage)")

    rfc = st.text_input("RFC", placeholder="AAA010101AAA").strip().upper()

    c1, c2 = st.columns([1, 3])
    with c1:
        run = st.button("Consultar", use_container_width=True)

    if not run:
        return

    if not rfc or len(rfc) not in (12, 13):
        st.warning("RFC inválido (debe tener 12 o 13 caracteres)")
        return

    service = _get_sat_service()

    with st.spinner("Consultando SAT..."):
        try:
            tax_status = service.get_tax_status(rfc)
        except Exception as e:
            st.error(f"Error consultando SAT: {e}")
            return

    st.subheader("Estatus")
    st.write(f"**RFC:** {tax_status.rfc}")
    st.write(f"**Status:** {tax_status.status or 'N/A'}")

    render_tax_status_cards(tax_status)

    st.divider()
    st.subheader("Señales de riesgo (si aplica)")

    with st.spinner("Consultando indicadores..."):
        try:
            risk = service.get_risk_indicators(rfc)
        except Exception:
            risk = None

    if not risk:
        st.info("No se pudieron obtener indicadores.")
        return

    cols = st.columns(3)
    items = list(risk.items())

    for i, (k, v) in enumerate(items[:9]):
        with cols[i % 3]:
            st.metric(k, "" if v is None else str(v))


def buro_page() -> None:
    st.header("Buró")
    st.caption("Buró de Crédito → Moffin (PF / PM)")

    rfc = st.text_input("RFC", placeholder="AAA010101AAA").strip().upper()
    run = st.button("Consultar", use_container_width=True)

    if not run:
        return

    if not rfc or len(rfc) not in (12, 13):
        st.warning("RFC inválido (debe tener 12 o 13 caracteres)")
        return

    with st.spinner("Consultando Buró..."):
        try:
            result = obtener_buro_moffin_por_rfc(rfc)
        except Exception as e:
            st.error(f"Error consultando Buró: {e}")
            return

    if isinstance(result, tuple) and len(result) == 2:
        df_buro, personas_pm = result
    else:
        df_buro, personas_pm = result, None

    if df_buro is None or getattr(df_buro, "empty", True):
        st.info("No hay información disponible.")
        return

    es_pm = len(rfc) == 12

    fecha_consulta = df_buro["Fecha Consulta"].iloc[0] if "Fecha Consulta" in df_buro.columns else "N/A"
    st.metric("Fecha de consulta", str(fecha_consulta))

    if personas_pm is not None:
        with st.expander("Personas (PM)", expanded=False):
            st.dataframe(personas_pm, use_container_width=True, hide_index=True)

    st.subheader("Detalle")
    st.dataframe(df_buro, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Underwriting (SAT + Buró)", layout="wide")

    _bootstrap_env_from_secrets()

    # SAFE LOGIN: allow app to run even if secrets not configured
    try:
        user = require_login()
    except Exception:
        user = "Guest"

    with st.sidebar:
        st.write(f"**Usuario:** {user}")
        logout_button()
        st.divider()
        page = st.radio("Módulo", ["SAT", "Buró"], index=0)

    if page == "SAT":
        sat_page()
    else:
        buro_page()


if __name__ == "__main__":
    main()
