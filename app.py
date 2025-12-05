import streamlit as st
import pandas as pd
<<<<<<< HEAD
from openai import OpenAI
import os
import json
import matplotlib.pyplot as plt
import tempfile

# =====================================
# CONFIGURACIÓN
# =====================================

CSV_PATH = "Asset_Inventory_-_Public_20251119.csv"

client = OpenAI(api_key="TU_API_KEY_AQUI")  # REEMPLAZAR

# =====================================
# CARGA DE DATOS SEGURA
# =====================================

@st.cache_data
def load_data():
    if not os.path.exists(CSV_PATH):
        st.error(f"❌ ERROR: No se encuentra el archivo CSV:\n**{CSV_PATH}**")
        st.stop()

    try:
        df = pd.read_csv(CSV_PATH, encoding="utf-8")
        return df
    except Exception as e:
        st.error("❌ ERROR leyendo el archivo CSV.")
        st.error(str(e))
        st.stop()

df = load_data()

# =====================================
# FUNCIÓN LLM
# =====================================
=======
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
>>>>>>> temp-save

def ask_llm(question):

    prompt = f"""
    Eres un asistente experto en análisis de datos.
    Dataset cargado con {df.shape[0]} filas y {df.shape[1]} columnas.

    Columnas disponibles:
    {', '.join(df.columns)}
<<<<<<< HEAD

    FORMATO RESPUESTA OBLIGATORIO:
    --------------------------------------
    1) Si piden GRÁFICOS → responde SOLO JSON así:
    {{
        "accion": "graficar",
        "tipo": "bar" | "line" | "pie",
        "x": "columna_x",
        "y": "columna_y",
        "agregacion": "count" | "sum" | "none"
    }}

    2) Si piden TABLAS →
    {{
        "accion": "tabla",
        "columnas": ["col1", "col2"]
    }}

    3) Si piden FILTROS →
    {{
        "accion": "filtrar",
        "columna": "columna",
        "valor": "valor"
    }}

    4) Si es solo una pregunta →
        responde texto plano.
    """

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un asistente analítico que devuelve JSON válido cuando el usuario pide gráficos o tablas."},
            {"role": "user", "content": prompt + "\n\nPregunta: " + question}
        ]
    )

    return completion.choices[0].message.content


# =====================================
# EJECUCIÓN DEL JSON DEL LLM
# =====================================

def ejecutar_instruccion(instr):
    try:
        instr = json.loads(instr)
    except:
        st.write(instr)
        return

    # TABLA
    if instr.get("accion") == "tabla":
        columnas = instr.get("columnas", [])
        st.dataframe(df[columnas].head())
        return

    # FILTRO
    if instr.get("accion") == "filtrar":
        col = instr.get("columna")
        val = instr.get("valor")
        filtrado = df[df[col] == val]
        st.dataframe(filtrado.head())
        return

    # GRÁFICO
    if instr.get("accion") == "graficar":
        tipo = instr.get("tipo")
        x = instr.get("x")
        y = instr.get("y")
        agg = instr.get("agregacion", "count")

        if x not in df.columns or y not in df.columns:
            st.error("Las columnas indicadas no existen.")
            return

        if agg == "count":
            data = df.groupby(x)[y].count()
        elif agg == "sum":
            data = df.groupby(x)[y].sum()
        else:
            data = df.set_index(x)[y]

        fig, ax = plt.subplots(figsize=(10, 5))

        if tipo == "bar":
            data.plot(kind="bar", ax=ax)
        elif tipo == "line":
            data.plot(kind="line", ax=ax)
        elif tipo == "pie":
            data.plot(kind="pie", ax=ax, autopct="%1.1f%%")

        st.pyplot(fig)
        return

    st.write(instr)

# =====================================
# INTERFAZ STREAMLIT
# =====================================

st.title("🤖 Chatbot de Datos Abiertos – MINTIC")
st.write("Pregunta sobre el dataset, o solicita gráficos/tablas.")

# =====================================
# SECCIÓN DE VOZ
# =====================================

st.subheader("🎤 Habla con el Chatbot")

audio_bytes = st.audio_input("Graba tu pregunta:")

if audio_bytes is not None:
    with st.spinner("Procesando..."):

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
            tmp_audio.write(audio_bytes)
            audio_path = tmp_audio.name

        # WHISPER
        with open(audio_path, "rb") as f:
            transcripcion = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )

        texto_usuario = transcripcion.text
        st.success(f"🧍 Dijiste: **{texto_usuario}**")

        respuesta_texto = ask_llm(texto_usuario)

        st.write("🤖 Respuesta:")
        ejecutar_instruccion(respuesta_texto)

        # TTS
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=respuesta_texto
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_out:
            tmp_out.write(speech)
            audio_out_path = tmp_out.name

        with open(audio_out_path, "rb") as f:
            st.audio(f.read(), format="audio/mp3")

# =====================================
# TEXTO NORMAL
# =====================================

query = st.text_area("O escribe tu pregunta:")

if st.button("Preguntar por texto"):
    if not query.strip():
        st.warning("Escribe una pregunta.")
    else:
        respuesta = ask_llm(query)
        ejecutar_instruccion(respuesta)

# =====================================
# ENDPOINT PARA N8N
# =====================================

st.markdown("---")
st.subheader("🌐 Endpoint para n8n")

if "http_request" in st.session_state:
    data = st.session_state.http_request
    msg = data.get("msg", "")
    if msg:
        resp = ask_llm(msg)
        st.json({"reply": resp})
=======

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

>>>>>>> temp-save
