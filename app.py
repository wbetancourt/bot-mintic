import streamlit as st
import pandas as pd
from openai import OpenAI
import os
import json
import matplotlib.pyplot as plt
import tempfile

# Cargar .env en desarrollo si python-dotenv está disponible
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# =====================================

# CONFIGURACIÓN
# =====================================

CSV_PATH = "Asset_Inventory_-_Public_20251119.csv"
# Obtener la API key: preferir `st.secrets` (Streamlit Cloud), luego variable de entorno y .env
API_KEY = None
if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
    API_KEY = st.secrets["OPENAI_API_KEY"]
else:
    API_KEY = os.getenv("OPENAI_API_KEY")

# Si no hay API_KEY, mostramos un error claro y detenemos la app.
if not API_KEY:
    st.error("No se encontró la variable de entorno `OPENAI_API_KEY`. Define esta variable antes de ejecutar la app (ej.: usar Streamlit Cloud Secrets o un archivo .env local).")
    st.stop()

# Inicializar cliente usando la clave desde la variable de entorno
client = OpenAI(api_key=API_KEY)
# =====================================
# CARGA DE DATOS
# =====================================

@st.cache_data
def load_data():
    df = pd.read_csv(CSV_PATH, encoding="utf-8")
    return df

df = load_data()

# =====================================
# FUNCIÓN LLM → devuelve JSON o texto
# =====================================

def ask_llm(question):

    prompt = f"""
    Eres un asistente experto en análisis de datos.
    Dataset cargado con {df.shape[0]} filas y {df.shape[1]} columnas.

    Columnas disponibles:
    {', '.join(df.columns)}

    Cuando el usuario solicite:
    --------------------------------------
    1) GRÁFICOS → responde SOLO JSON así:
    {{
        "accion": "graficar",
        "tipo": "bar" | "line" | "pie",
        "x": "columna_x",
        "y": "columna_y",
        "agregacion": "count" | "sum" | "none"
    }}

    2) TABLAS → responde SOLO JSON así:
    {{
        "accion": "tabla",
        "columnas": ["columna1", "columna2"]
    }}

    3) FILTROS → JSON así:
    {{
        "accion": "filtrar",
        "columna": "nombre_columna",
        "valor": "valor_a_filtrar"
    }}

    4) SI ES SOLO UNA PREGUNTA NORMAL → responde texto plano.

    Pregunta del usuario:
    {question}
    """

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un asistente analítico. Devuelves JSON válido cuando se te piden gráficos o tablas."},
            {"role": "user", "content": prompt}
        ]
    )

    return completion.choices[0].message.content


# =====================================
# FUNCIÓN PARA EJECUTAR LAS ACCIONES JSON
# =====================================

def ejecutar_instruccion(instr):

    # Intentar JSON
    try:
        instr = json.loads(instr)
    except:
        st.write(instr)
        return

    # ---- TABLA ----
    if instr.get("accion") == "tabla":
        columnas = instr.get("columnas", [])
        st.write(df[columnas].head())
        return

    # ---- FILTRO ----
    if instr.get("accion") == "filtrar":
        col = instr.get("columna")
        val = instr.get("valor")
        filtrado = df[df[col] == val]
        st.write(filtrado.head())
        return

    # ---- GRÁFICOS ----
    if instr.get("accion") == "graficar":
        tipo = instr.get("tipo")
        x = instr.get("x")
        y = instr.get("y")
        agg = instr.get("agregacion", "count")

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
st.write("Pregunta sobre el dataset, solicita gráficos o tablas.")


# ====================================================
# 🔊 SECCIÓN DE VOZ (CORREGIDA)
# ====================================================

st.subheader("🎤 Habla con el Chatbot")

audio_file = st.audio_input("Graba tu pregunta por voz")

if audio_file is not None:
    with st.spinner("Procesando audio..."):

        # Extraer bytes del archivo subido
        audio_bytes = audio_file.getvalue()

        # Guardar audio temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
            tmp_audio.write(audio_bytes)
            audio_path = tmp_audio.name

        # === Whisper (voz → texto) ===
        with open(audio_path, "rb") as f:
            transcripcion = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )

        texto_usuario = transcripcion.text
        st.success(f"🧍 Dijiste: **{texto_usuario}**")

        # === Mandar al chatbot ===
        respuesta_texto = ask_llm(texto_usuario)

        st.write("🤖 Respuesta:")
        ejecutar_instruccion(respuesta_texto)

        # === Texto → Voz (TTS) ===
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=respuesta_texto
        )

        # Guardar respuesta de voz
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_out:
            tmp_out.write(speech)
            audio_out_path = tmp_out.name

        with open(audio_out_path, "rb") as f:
            audio_reply = f.read()

        st.audio(audio_reply, format="audio/mp3")



# ====================================================
# TEXTO NORMAL
# ====================================================

query = st.text_area("O escribe tu pregunta:")

if st.button("Preguntar por texto"):
    if not query.strip():
        st.warning("Escribe una pregunta primero")
    else:
        respuesta = ask_llm(query)
        ejecutar_instruccion(respuesta)


# =====================================
# ENDPOINT PARA N8N
# =====================================

st.markdown("---")
st.subheader("🌐 Endpoint para n8n (POST /bot)")

if "http_request" in st.session_state:
    data = st.session_state.http_request
    msg = data.get("msg", "")

    if msg:
        resp = ask_llm(msg)
        st.json({"reply": resp})
