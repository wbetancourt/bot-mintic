import streamlit as st
import pandas as pd
import requests
from openai import OpenAI
import json
import plotly.express as px
import tempfile
import os

# ======================================================
# CONFIGURACIÓN
# ======================================================

API_URL = "https://www.datos.gov.co/resource/uzcf-b9dh.json?$limit=50000"

# OpenAI API KEY desde secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ======================================================
# CARGA DE DATOS DESDE API JSON
# ======================================================

@st.cache_data(ttl=3600)
def load_data():
    st.info("Descargando datos desde datos.gov.co...")

    r = requests.get(API_URL)
    r.raise_for_status()   

    data = r.json()

    df = pd.DataFrame(data)

    st.success(f"Datos cargados correctamente: {df.shape[0]} filas, {df.shape[1]} columnas.")
    return df

df = load_data()

# ======================================================
# FUNCION LLM
# ======================================================

def ask_llm(question):

    prompt = f"""
    Eres un asistente experto en análisis de datos.
    Dataset cargado con {df.shape[0]} filas y {df.shape[1]} columnas.

    Columnas disponibles:
    {', '.join(df.columns)}

    Reglas:
    1) Si piden gráficos → responde SOLO JSON:
    {{
        "accion": "graficar",
        "tipo": "bar"|"line"|"pie",
        "x": "columna",
        "y": "columna",
        "agregacion": "count"|"sum"|"none"
    }}

    2) Si piden tabla → responde SOLO JSON:
    {{
        "accion": "tabla",
        "columnas": ["col1", "col2"]
    }}

    3) Si piden filtros → responde SOLO JSON:
    {{
        "accion": "filtrar",
        "columna": "col",
        "valor": "valor"
    }}

    4) Si es pregunta normal → responde texto plano.

    Pregunta:
    {question}
    """

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un asistente analítico que responde con JSON válido cuando es necesario."},
            {"role": "user", "content": prompt}
        ]
    )

    return completion.choices[0].message.content

# ======================================================
# EJECUTAR INSTRUCCIONES JSON
# ======================================================

def ejecutar_instruccion(instr):

    try:
        instr = json.loads(instr)
    except:
        st.write(instr)
        return

    # ----------------- TABLA -----------------
    if instr.get("accion") == "tabla":
        columnas = instr.get("columnas", [])
        st.dataframe(df[columnas].head())
        return

    # ----------------- FILTRO -----------------
    if instr.get("accion") == "filtrar":
        col = instr.get("columna")
        val = instr.get("valor")
        filtrado = df[df[col] == val]
        st.dataframe(filtrado.head())
        return

    # ----------------- GRAFICO -----------------
    if instr.get("accion") == "graficar":
        tipo = instr.get("tipo")
        x = instr.get("x")
        y = instr.get("y")
        agg = instr.get("agregacion", "count")

        dtemp = df.copy()

        if agg == "count":
            dtemp = dtemp.groupby(x)[y].count().reset_index(name="valor")
            y = "valor"

        elif agg == "sum":
            dtemp = dtemp.groupby(x)[y].sum().reset_index()

        # Plotly
        if tipo == "bar":
            fig = px.bar(dtemp, x=x, y=y)
        elif tipo == "line":
            fig = px.line(dtemp, x=x, y=y)
        elif tipo == "pie":
            fig = px.pie(dtemp, names=x, values=y)

        st.plotly_chart(fig, use_container_width=True)
        return

    st.write(instr)

# ======================================================
# INTERFAZ
# ======================================================

st.title("🤖 Chatbot Inteligente – Datos Abiertos MINTIC")
st.write("Pregunta por texto o por voz sobre el dataset descargado de datos.gov.co")

# ---------------------- Pregunta por Texto ------------------------
query = st.text_area("Escribe tu pregunta:")

if st.button("Enviar pregunta"):
    if query.strip() == "":
        st.warning("Escribe una pregunta.")
    else:
        resp = ask_llm(query)
        ejecutar_instruccion(resp)

