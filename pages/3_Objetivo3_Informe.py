import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CSV_PATH = "Asset_Inventory_-_Public_20251119.csv"

@st.cache_data
def load_data():
    return pd.read_csv(CSV_PATH, encoding="utf-8")

df = load_data()


# ===============================================================
# CONFIGURACIÓN DE ESTILO (similar al demo stockpeers)
# ===============================================================

st.set_page_config(
    page_title="Informe Final – Datos Abiertos",
    layout="wide"
)

st.markdown("""
<style>
.big-title {
    font-size: 34px !important;
    font-weight: 700 !important;
}
.section-title {
    font-size: 26px !important;
    font-weight: 700 !important;
    margin-top: 20px !important;
}
</style>
""", unsafe_allow_html=True)



# ===============================================================
# TÍTULO GENERAL
# ===============================================================

st.markdown("<div class='big-title'>📘 Informe Final del Diagnóstico</div>", unsafe_allow_html=True)
st.write("Este informe consolida las métricas del inventario en un panel interactivo estilo 'dashboard'.")



# ===============================================================
# TABS (ESTILO DASHBOARD)
# ===============================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📄 Introducción",
    "📐 Completitud",
    "⏱ Actualización",
    "📊 Cobertura Temática"
])



# ===============================================================
# TAB 1 – INTRODUCCIÓN
# ===============================================================

with tab1:
    st.markdown("<div class='section-title'>Introducción</div>", unsafe_allow_html=True)
    st.markdown("""
    El análisis del inventario de activos de datos abiertos se construyó a partir de:

    - Completitud de metadatos  
    - Frecuencia de actualización  
    - Cobertura temática por sector  
    - Revisión general de consistencia  
    
    A continuación se presentan visualizaciones interactivas para profundizar en el estado real del inventario.
    """)



# ===============================================================
# TAB 2 – COMPLTITUD
# ===============================================================

with tab2:
    st.markdown("<div class='section-title'>1️⃣ Completitud de Metadatos</div>", unsafe_allow_html=True)

    completitud = (df.notna().mean() * 100).sort_values(ascending=False)
    tabla_completitud = completitud.reset_index()
    tabla_completitud.columns = ["Columna", "Completitud (%)"]

    st.dataframe(tabla_completitud, use_container_width=True)

    fig = px.bar(
        tabla_completitud,
        x="Columna",
        y="Completitud (%)",
        title="Completitud por Columna (%)",
        text="Completitud (%)",
        height=600
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)



# ===============================================================
# TAB 3 – FRECUENCIA DE ACTUALIZACIÓN
# ===============================================================

with tab3:

    st.markdown("<div class='section-title'>2️⃣ Frecuencia de Actualización</div>", unsafe_allow_html=True)

    # Columnas detectables
    update_cols = [
        "Fecha de última actualización de datos (UTC)",
        "Fecha de última actualización de metadatos (UTC)",
        "Common Core: Last Update"
    ]

    update_col = next((c for c in update_cols if c in df.columns), None)

    if update_col:
        st.success(f"Usando columna de actualización: **{update_col}**")

        df["fecha_upd"] = pd.to_datetime(df[update_col], errors="coerce")
        df["mes"] = df["fecha_upd"].dt.to_period("M").astype(str)

        conteo_mensual = df["mes"].value_counts().sort_index()

        fig2 = px.line(
            conteo_mensual,
            labels={"value": "N° de activos", "index": "Mes"},
            title="Línea de tiempo – Actualizaciones mensuales",
            markers=True
        )

        fig2.update_traces(line=dict(width=3))
        st.plotly_chart(fig2, use_container_width=True)

    else:
        st.error("⚠ No se detectó una columna de actualización válida.")



# ===============================================================
# TAB 4 – COBERTURA TEMÁTICA (SECTOR)
# ===============================================================

with tab4:

    st.markdown("<div class='section-title'>3️⃣ Cobertura Temática por Sector</div>", unsafe_allow_html=True)

    # Detectar cualquier columna que contenga "sector"
    sector_col = next((c for c in df.columns if "sector" in c.lower()), None)

    if sector_col:
        st.success(f"Columna temática detectada: **{sector_col}**")

        conteo_sector = df[sector_col].fillna("Sin sector").value_counts().reset_index()
        conteo_sector.columns = ["Sector", "Activos"]

        # Tabla
        st.dataframe(conteo_sector, use_container_width=True)

        # Gráfica estilo dashboard
        fig3 = px.bar(
            conteo_sector,
            x="Sector",
            y="Activos",
            title="Distribución de Activos por Sector",
            text="Activos",
            height=600
        )
        fig3.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig3, use_container_width=True)

        # Pie chart interactivo
        fig4 = px.pie(
            conteo_sector.head(10),
            names="Sector",
            values="Activos",
            title="Top 10 Sectores",
        )
        fig4.update_traces(textposition="inside")
        st.plotly_chart(fig4, use_container_width=True)

    else:
        st.error("⚠ No se detectó ninguna columna relacionada con 'sector'.")



# ===============================================================
# CONCLUSIONES AL FINAL DE LA PÁGINA
# ===============================================================

st.markdown("---")

st.markdown("<div class='section-title'>📝 Conclusiones Generales</div>", unsafe_allow_html=True)

completitud_prom = round(df.notna().mean().mean() * 100, 2)

st.markdown(f"""
- La completitud promedio de los metadatos es **{completitud_prom}%**.  
- Las columnas más débiles en completitud requieren priorización inmediata.  
- La distribución temática por sector permite identificar brechas de publicación.  
- La frecuencia de actualización evidencia tendencias sobre mantenimiento de activos.  

Este panel interactivo facilita la toma de decisiones orientadas a la gobernanza 
y mejora continua de los datos abiertos.
""")
