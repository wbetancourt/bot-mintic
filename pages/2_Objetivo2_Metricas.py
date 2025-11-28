import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

CSV_PATH = "Asset_Inventory_-_Public_20251119.csv"

@st.cache_data
def load_data():
    return pd.read_csv(CSV_PATH, encoding="utf-8")

df = load_data()

# ==========================================
# PÁGINA – OBJETIVO 2: MÉTRICAS
# ==========================================

st.title("📐 Objetivo 2 – Métricas de Completitud, Actualización y Cobertura Temática")
st.write("En esta sección calculamos métricas esenciales para evaluar la calidad del inventario de datos abiertos.")


# ==========================================
# 1) MÉTRICA DE COMPLETITUD
# ==========================================

st.header("1️⃣ Completitud de Metadatos")

completitud = df.notna().mean().sort_values(ascending=False)
tabla_completitud = (completitud * 100).round(2)

st.write("### Porcentaje de completitud por columna:")
st.dataframe(tabla_completitud.to_frame("Completitud (%)"))

fig1, ax1 = plt.subplots(figsize=(12,5))
tabla_completitud.plot(kind="bar", ax=ax1)
ax1.set_title("Completitud por columna (%)")
ax1.set_ylabel("Completitud (%)")
st.pyplot(fig1)


# ==========================================
# 2) FRECUENCIA DE ACTUALIZACIÓN
# ==========================================

st.header("2️⃣ Frecuencia de Actualización")

# Detectar columna correcta
possible_update_cols = [
    "Fecha de última actualización de datos (UTC)",
    "Fecha de última actualización de metadatos (UTC)",
    "Common Core: Last Update",
    "Fecha de creación (UTC)"
]

update_col = next((c for c in possible_update_cols if c in df.columns), None)

if update_col:
    st.success(f"Columna de actualización detectada: **{update_col}**")

    # Convertir fechas
    df["fecha_upd"] = pd.to_datetime(df[update_col], errors="coerce")

    # Mostrar estadísticas básicas
    st.write("### Estadísticas generales:")
    st.write(df["fecha_upd"].describe())

    # Gráfico de historial
    fechas = df["fecha_upd"].dt.to_period("M").value_counts().sort_index()

    fig2, ax2 = plt.subplots(figsize=(12,5))
    fechas.plot(kind="line", marker="o", ax=ax2)
    ax2.set_title("Cantidad de activos actualizados por mes")
    ax2.set_ylabel("Número de activos")
    ax2.set_xlabel("Mes")
    st.pyplot(fig2)

else:
    st.warning("⚠ No se encontró columna de fecha de actualización.")


# ==========================================
# 3) COBERTURA TEMÁTICA
# ==========================================

st.header("3️⃣ Cobertura Temática por Sector")

if "Información de la Entidad: Sector" in df.columns:
    sectores = df["Información de la Entidad: Sector"].fillna("Sin sector")
    conteo = sectores.value_counts()

    st.write("### Cantidad de activos por sector:")
    st.dataframe(conteo.to_frame("Activos"))

    fig3, ax3 = plt.subplots(figsize=(12,5))
    conteo.plot(kind="bar", ax=ax3)
    ax3.set_title("Distribución de activos por sector")
    ax3.set_ylabel("Número de activos")
    st.pyplot(fig3)

    # Gráfico PIE (solo top 10)
    fig4, ax4 = plt.subplots(figsize=(7,7))
    conteo.head(10).plot(kind="pie", ax=ax4, autopct="%1.1f%%")
    ax4.set_ylabel("")
    ax4.set_title("Top 10 Sectores")
    st.pyplot(fig4)

else:
    st.warning("⚠ La columna 'Sector' no existe en el inventario.")


# ==========================================
# RECOMENDACIONES DEL OBJETIVO 2
# ==========================================

st.header("📝 Conclusiones automáticas del Objetivo 2")

st.markdown(f"""
- Completitud media del dataset: **{round(completitud.mean() * 100, 2)}%**
- Columnas con peor completitud: **{', '.join(list(completitud.tail(5).index))}**
- Sector más frecuente: **{conteo.index[0] if 'Sector' in df.columns else 'N/A'}**
- Fecha más antigua detectada: **{df['fecha_upd'].min() if update_col else 'N/A'}**
- Fecha más reciente detectada: **{df['fecha_upd'].max() if update_col else 'N/A'}**
""")
