import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

CSV_PATH = "Asset_Inventory_-_Public_20251119.csv"

@st.cache_data
def load_data():
    return pd.read_csv(CSV_PATH, encoding="utf-8")

df = load_data()

# ==========================================
# PÁGINA – OBJETIVO 1: DIAGNÓSTICO GENERAL
# ==========================================

st.title("📊 Diagnóstico de Coherencia y Cobertura")
st.write("Objetivo 1: Diagnosticar la coherencia y la cobertura del inventario de activos de datos abiertos.")

st.header("1️⃣ Información General del Dataset")
st.write(f"- **Filas:** {df.shape[0]}")
st.write(f"- **Columnas:** {df.shape[1]}")
st.write("### Lista de columnas:")
st.write(list(df.columns))

# ------------------------------------------
# 2) COMPLETITUD POR COLUMNA
# ------------------------------------------

st.header("2️⃣ Completitud por Columna")

completitud = df.notna().mean().sort_values(ascending=False)
st.write(completitud.to_frame("Completitud (%)") * 100)

fig, ax = plt.subplots(figsize=(10,5))
(completitud * 100).plot(kind="bar", ax=ax)
ax.set_title("Porcentaje de Completitud por Columna")
ax.set_ylabel("Completitud (%)")
st.pyplot(fig)

# ------------------------------------------
# 3) COLUMNAS MÁS INCOMPLETAS
# ------------------------------------------

st.header("3️⃣ Columnas con Mayor Falta de Datos")

faltantes_top = (1 - completitud).sort_values(ascending=False).head(10)
st.write(faltantes_top.to_frame("Porcentaje de Faltantes") * 100)

fig2, ax2 = plt.subplots(figsize=(10,5))
(faltantes_top * 100).plot(kind="bar", ax=ax2, color="red")
ax2.set_title("Top 10 Columnas Más Incompletas")
ax2.set_ylabel("Faltantes (%)")
st.pyplot(fig2)

# ------------------------------------------
# 4) COBERTURA TEMÁTICA (si existe columna tema)
# ------------------------------------------

st.header("4️⃣ Cobertura Temática")

possible_theme_columns = ["sector", "tema", "category", "Categoría", "subject", "topic"]

theme_col = next((col for col in possible_theme_columns if col in df.columns), None)

if theme_col:
    st.success(f"Se detectó columna temática: **{theme_col}**")

    temas = df[theme_col].fillna("Sin Tema")
    conteo_temas = temas.value_counts()

    st.write("### Distribución por tema:")
    st.write(conteo_temas)

    fig3, ax3 = plt.subplots(figsize=(10,5))
    conteo_temas.head(10).plot(kind="bar", ax=ax3)
    ax3.set_title("Top 10 Temas Más Frecuentes")
    ax3.set_ylabel("Número de Activos")
    st.pyplot(fig3)

else:
    st.warning("⚠ No se encontró una columna de temas en el inventario.")

# ------------------------------------------
# 5) RECOMENDACIONES INICIALES
# ------------------------------------------

st.header("5️⃣ Recomendaciones del Diagnóstico")

col_incompletas = list(faltantes_top.index)
nulas_por_fila = df.isna().sum(axis=1).mean()

st.write("### 📝 Principales conclusiones automáticas:")

st.markdown(f"""
- El dataset tiene **{df.shape[1]} columnas** y **{df.shape[0]} registros**.  
- Las columnas con más faltantes son:  
  **{', '.join(col_incompletas)}**  
- Promedio de valores nulos por fila: **{round(nulas_por_fila,2)}**  
- Nivel de completitud general: **{round(completitud.mean()*100,2)}%**
""")

st.info("Este diagnóstico permite saber en qué columnas se debe priorizar la mejora de metadatos y si existen sesgos en la cobertura temática.")
