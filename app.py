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
CSV_PATH = "Asset_Inventory_-_Public_20251119.csv"

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ======================================================
# CARGA DE DATOS
# ======================================================

@st.cache_data(ttl=3600)
def load_from_api():
    st.info("📥 Descargando datos desde datos.gov.co...")
    r = requests.get(API_URL)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    st.success(f"API cargada: {df.shape[0]} filas, {df.shape[1]} columnas.")
    return df

@st.cache_data()
def load_from_csv():
    st.info("📄 Cargando archivo CSV local...")
    df = pd.read_csv(CSV_PATH)
    st.success(f"CSV cargado: {df.shape[0]} filas, {df.shape[1]} columnas.")
    return df

# ======================================================
# SELECCIÓN DE FUENTE DE DATOS
# ======================================================

st.sidebar.header("⚙️ Configuración de Datos")

source = st.sidebar.radio(
    "Selecciona la fuente de datos:",
    ("API", "CSV local")
)

df = load_from_api() if source == "API" else load_from_csv()

# ======================================================
# FUNCIÓN LLM
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

    # TABLA
    if instr.get("accion") == "tabla":
        cols = instr.get("columnas", [])
        if all(c in df.columns for c in cols):
            st.dataframe(df[cols].head())
        else:
            st.error("Columnas no existen en el dataset.")
        return

    # FILTRO
    if instr.get("accion") == "filtrar":
        col = instr.get("columna")
        val = instr.get("valor")
        if col in df.columns:
            filtrado = df[df[col].astype(str) == str(val)]
            st.dataframe(filtrado.head())
        else:
            st.error(f"La columna '{col}' no existe.")
        return

    # GRAFICO
    if instr.get("accion") == "graficar":
        tipo = instr.get("tipo")
        x = instr.get("x")
        y = instr.get("y")
        agg = instr.get("agregacion", "count")

        if x not in df.columns or y not in df.columns:
            st.error("Columnas inválidas para graficar.")
            return

        dtemp = df.copy()

        if agg == "count":
            dtemp = dtemp.groupby(x)[y].count().reset_index(name="valor")
            y = "valor"
        elif agg == "sum":
            dtemp = dtemp.groupby(x)[y].sum().reset_index()

        # plotly
        if tipo == "bar":
            fig = px.bar(dtemp, x=x, y=y)
        elif tipo == "line":
            fig = px.line(dtemp, x=x, y=y)
        elif tipo == "pie":
            fig = px.pie(dtemp, names=x, values=y)
        else:
            st.error("Tipo de gráfico no reconocido.")
            return

        st.plotly_chart(fig, use_container_width=True)
        return

    st.write(instr)


# ======================================================
# INTERFAZ
# ======================================================

st.title("🤖 Chatbot Inteligente – Datos Abiertos MINTIC")
st.write("Pregunta por texto o por voz sobre el dataset seleccionado.")

# ---------------------- Pregunta por Texto ------------------------

query = st.text_area("Escribe tu pregunta:")

if st.button("Enviar pregunta"):
    if query.strip() == "":
        st.warning("Escribe una pregunta.")
    else:
        resp = ask_llm(query)
        ejecutar_instruccion(resp)

# ---------------------- Pregunta por Voz ------------------------

st.subheader("🎤 Habla con el Chatbot")

audio_data = st.audio_input("Graba tu pregunta:")

if audio_data is not None:
    with st.spinner("Procesando audio..."):

        # Guardar archivo de audio correctamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_data.getbuffer())
            audio_path = tmp.name

        # WHISPER → texto
        with open(audio_path, "rb") as f:
            transcripcion = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )

        user_text = transcripcion.text
        st.success(f"🧍 Dijiste: **{user_text}**")

        respuesta = ask_llm(user_text)

        st.write("🤖 Respuesta:")
        ejecutar_instruccion(respuesta)

        # TTS → voz
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=respuesta
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_out:
            tmp_out.write(speech)
            audio_output_path = tmp_out.name

        with open(audio_output_path, "rb") as f:
            st.audio(f.read(), format="audio/mp3")
