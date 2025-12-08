import streamlit as st
import pandas as pd
import requests
from openai import OpenAI
import json
import plotly.express as px
import tempfile
import os

# ======================================================
# CONFIGURACIÓN GENERAL
# ======================================================

CSV_PATH = "Asset_Inventory_-_Public_20251119.csv"
API_URL = "https://www.datos.gov.co/resource/uzcf-b9dh.json?$limit=50000"

# OPENAI API KEY (usar secrets en Streamlit Cloud)
API_KEY = None
if "OPENAI_API_KEY" in st.secrets:
    API_KEY = st.secrets["OPENAI_API_KEY"]
else:
    API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    st.error("⚠ No se encontró OPENAI_API_KEY (ni en st.secrets ni en variables de entorno).")
    st.stop()

client = OpenAI(api_key=API_KEY)

# ======================================================
# SELECCIÓN DE FUENTE DE DATOS (CSV vs API)
# ======================================================

st.sidebar.title("⚙ Configuración de datos")
data_source = st.sidebar.radio(
    "Selecciona la fuente de datos:",
    ("CSV local", "API datos.gov.co")
)

# ======================================================
# CARGA DE DATOS
# ======================================================

@st.cache_data(ttl=3600, show_spinner=True)
def load_data_from_csv():
    if not os.path.exists(CSV_PATH):
        st.error(f"❌ No se encontró el archivo CSV: {CSV_PATH}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(CSV_PATH, encoding="utf-8")
        return df
    except Exception as e:
        st.error(f"❌ Error leyendo el CSV: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=True)
def load_data_from_api():
    try:
        st.info("📥 Descargando datos desde datos.gov.co...")
        r = requests.get(API_URL, timeout=30)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data)
        st.success(f"✅ Datos API cargados: {df.shape[0]} filas, {df.shape[1]} columnas.")
        return df
    except Exception as e:
        st.error(f"❌ Error al cargar datos desde la API: {e}")
        return pd.DataFrame()


# Cargar según selección
if data_source == "CSV local":
    df = load_data_from_csv()
else:
    df = load_data_from_api()

if df.empty:
    st.error("No hay datos disponibles. Revisa la fuente seleccionada.")
    st.stop()

# ======================================================
# FUNCIÓN LLM
# ======================================================

def ask_llm(question: str) -> str:
    """
    Envía la pregunta al modelo y devuelve texto (puede ser JSON).
    """

    columnas = ", ".join(df.columns.astype(str))

    prompt = f"""
Eres un asistente experto en análisis de datos.
Tienes un dataset con {df.shape[0]} filas y {df.shape[1]} columnas.

Columnas disponibles (usa SOLO estos nombres exactamente):
{columnas}

Reglas:
1) Si el usuario pide un GRÁFICO → responde SOLO JSON:
{{
  "accion": "graficar",
  "tipo": "bar"|"line"|"pie",
  "x": "nombre_columna_existente",
  "y": "nombre_columna_existente_o_vacio",
  "agregacion": "count"|"sum"|"none"
}}

   - Para "count" puedes dejar "y" vacío o cualquiera, el backend contará registros.

2) Si el usuario pide una TABLA → responde SOLO JSON:
{{
  "accion": "tabla",
  "columnas": ["col1", "col2", ...]  // deben existir en el dataset
}}

3) Si el usuario pide FILTROS → responde SOLO JSON:
{{
  "accion": "filtrar",
  "columna": "nombre_columna_existente",
  "valor": "valor_a_filtrar"
}}

4) Si es una pregunta normal (explicación, descripción, etc.) → responde en texto plano.

Pregunta del usuario:
{question}
"""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Eres un asistente analítico. Cuando se piden gráficos o tablas, respondes con JSON válido."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return completion.choices[0].message.content


# ======================================================
# EJECUTAR INSTRUCCIONES JSON
# ======================================================

def ejecutar_instruccion(instr: str):
    """
    Si la respuesta es JSON con 'accion', ejecuta tabla/filtro/grafico.
    Si no es JSON válido, muestra el texto tal cual.
    """
    try:
        obj = json.loads(instr)
    except Exception:
        # No era JSON → mostrar como texto normal
        st.write(instr)
        return

    accion = obj.get("accion")

    # ----------------- TABLA -----------------
    if accion == "tabla":
        columnas = obj.get("columnas", [])
        columnas_validas = [c for c in columnas if c in df.columns]
        if not columnas_validas:
            st.warning("Las columnas indicadas no existen o están vacías.")
            return
        st.dataframe(df[columnas_validas].head())
        return

    # ----------------- FILTRO -----------------
    if accion == "filtrar":
        col = obj.get("columna")
        val = obj.get("valor")

        if col not in df.columns:
            st.warning(f"La columna '{col}' no existe en el dataset.")
            return

        filtrado = df[df[col] == val]
        st.dataframe(filtrado.head())
        st.caption(f"Filas filtradas donde {col} == {val} (mostrando primeras 5).")
        return

    # ----------------- GRAFICO -----------------
    if accion == "graficar":
        tipo = obj.get("tipo")
        x = obj.get("x")
        y = obj.get("y")
        agg = obj.get("agregacion", "count")

        if x not in df.columns:
            st.warning(f"La columna de eje X '{x}' no existe en el dataset.")
            return

        dtemp = df.copy()

        # Manejo robusto para 'count' aunque 'y' no exista o venga vacío
        if agg == "count":
            dtemp = dtemp.groupby(x).size().reset_index(name="valor")
            y_col = "valor"
        elif agg == "sum":
            if y not in df.columns:
                st.warning(f"La columna '{y}' no existe para agregación 'sum'.")
                return
            dtemp = dtemp.groupby(x)[y].sum().reset_index()
            y_col = y
        else:  # none
            if y not in df.columns:
                st.warning(f"La columna '{y}' no existe.")
                return
            dtemp = dtemp[[x, y]]
            y_col = y

        # Crear gráfico con Plotly
        if tipo == "bar":
            fig = px.bar(dtemp, x=x, y=y_col)
        elif tipo == "line":
            fig = px.line(dtemp, x=x, y=y_col)
        elif tipo == "pie":
            fig = px.pie(dtemp, names=x, values=y_col)
        else:
            st.warning(f"Tipo de gráfico desconocido: {tipo}")
            st.write(obj)
            return

        st.plotly_chart(fig, use_container_width=True)
        return

    # Si no coincide con nada, mostramos el JSON crudo
    st.write(obj)


# ======================================================
# INTERFAZ PRINCIPAL
# ======================================================

st.title("🤖 Chatbot Inteligente – Datos Abiertos MINTIC")

st.markdown(
    f"**Fuente de datos actual:** `{data_source}` &nbsp;&nbsp; "
    f"({df.shape[0]} filas, {df.shape[1]} columnas)"
)

with st.expander("Ver columnas del dataset"):
    st.write(list(df.columns))

st.markdown("---")

# ---------------------- Pregunta por TEXTO ------------------------
st.subheader("💬 Pregunta por texto")

query = st.text_area("Escribe tu pregunta:")

if st.button("Enviar pregunta"):
    if query.strip() == "":
        st.warning("Escribe una pregunta.")
    else:
        resp = ask_llm(query)
        ejecutar_instruccion(resp)

# ---------------------- Pregunta por VOZ ------------------------
st.subheader("🎤 Habla con el Chatbot")

audio_file = st.audio_input("Graba tu pregunta:")

if audio_file is not None:
    try:
        with st.spinner("Procesando audio..."):
            # audio_input devuelve un UploadedFile → usar getvalue()
            audio_bytes = audio_file.getvalue()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                tmp_audio.write(audio_bytes)
                audio_path = tmp_audio.name

            # WHISPER → voz a texto
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

            # TTS → texto a voz
            try:
                speech_resp = client.audio.speech.create(
                    model="gpt-4o-mini-tts",
                    voice="alloy",
                    input=respuesta_texto
                )

                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_out:
                    # En SDK nuevo, hay que usar .read()
                    if hasattr(speech_resp, "read"):
                        tmp_out.write(speech_resp.read())
                    else:
                        # por si la respuesta ya son bytes
                        tmp_out.write(speech_resp)
                    audio_out_path = tmp_out.name

                with open(audio_out_path, "rb") as f:
                    st.audio(f.read(), format="audio/mp3")
            except Exception as e:
                st.warning(f"No se pudo generar audio de respuesta (TTS): {e}")

    except Exception as e:
        st.error(f"Error procesando el audio: {e}")
