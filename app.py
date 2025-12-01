import streamlit as st
import pandas as pd
from openai import OpenAI
import os
import json
import matplotlib.pyplot as plt
import tempfile

# =====================================
# CONFIGURACIÓN
# =====================================

CSV_PATH = "Asset_Inventory_-_Public_20251119.csv"

# ⚠️ Reemplaza con tu API KEY
client = OpenAI(api_key="TU_API_KEY_AQUI")

# =====================================
# CARGA DE DATOS COMPLETOS (SIN LÍMITE)
# =====================================

@st.cache_data
def load_data():
    df = pd.read_csv(CSV_PATH, encoding="utf-8")
    return df

df = load_data()

# =====================================
# FUNCIÓN LLM → con muestra pequeña
# =====================================

def ask_llm(question):

    # Para evitar límites se envía SOLO:
    # - nombres de columnas
    # - 5 filas de muestra
    sample_df = df.head(5).to_dict(orient="records")

    prompt = f"""
Eres un asistente experto en análisis de datos.

INFORMACIÓN DEL DATASET REAL:
- Filas reales: {df.shape[0]}
- Columnas reales: {df.shape[1]}

Columnas disponibles:
{', '.join(df.columns)}

MUESTRA REAL DE 5 REGISTROS:
{sample_df}

REGLAS DE SALIDA:
-------------------------
1) Si el usuario solicita un gráfico:
{{
    "accion": "graficar",
    "tipo": "bar" | "line" | "pie",
    "x": "columna_x",
    "y": "columna_y",
    "agregacion": "count" | "sum" | "none"
}}

2) Si el usuario solicita una tabla:
{{
    "accion": "tabla",
    "columnas": ["col1", "col2"]
}}

3) Si solicita un filtro:
{{
    "accion": "filtrar",
    "columna": "nombre",
    "valor": "valor"
}}

4) Si NO necesita gráfico o tabla → responde SOLO en texto plano.

Pregunta del usuario:
{question}
"""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un asistente analítico experto en datos abiertos. Usa JSON válido SOLO cuando se requieran acciones."},
            {"role": "user", "content": prompt}
        ]
    )

    return completion.choices[0].message.content


# =====================================
# EJECUCIÓN DE INSTRUCCIONES JSON
# =====================================

def ejecutar_instruccion(instr):

    # Intentar cargar JSON. Si falla, es texto normal.
    try:
        instr = json.loads(instr)
    except:
        st.write(instr)
        return

    # ---- TABLA ----
    if instr.get("accion") == "tabla":
        columnas = instr.get("columnas", [])
        if all(col in df.columns for col in columnas):
            st.dataframe(df[columnas].head(20))
        else:
            st.error("Una o más columnas no existen.")
        return

    # ---- FILTRO ----
    if instr.get("accion") == "filtrar":
        col = instr.get("columna")
        val = instr.get("valor")
        if col not in df.columns:
            st.error("Columna no válida.")
            return
        filtrado = df[df[col] == val]
        st.write(f"Filas encontradas: {len(filtrado)}")
        st.dataframe(filtrado.head(50))
        return

    # ---- GRÁFICOS ----
    if instr.get("accion") == "graficar":
        tipo = instr.get("tipo")
        x = instr.get("x")
        y = instr.get("y")
        agg = instr.get("agregacion", "count")

        if x not in df.columns or y not in df.columns:
            st.error("Columnas del gráfico no válidas.")
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
st.write("Pregunta sobre el dataset, solicita gráficos o tablas.")


# ====================================================
# 🔊 PREGUNTAS POR VOZ
# ====================================================

st.subheader("🎤 Pregunta con tu voz")

audio_bytes = st.audio_input("Graba tu pregunta")

if audio_bytes is not None:
    with st.spinner("Procesando audio..."):

        # Guardar audio temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
            tmp_audio.write(audio_bytes)
            audio_path = tmp_audio.name

        # === Voz → Texto ===
        with open(audio_path, "rb") as f:
            transcripcion = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )

        texto_usuario = transcripcion.text
        st.success(f"🧍 Dijiste: **{texto_usuario}**")

        # Enviar al LLM
        respuesta_texto = ask_llm(texto_usuario)
        st.write("🤖 Respuesta:")
        ejecutar_instruccion(respuesta_texto)

        # === Texto → Voz ===
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=respuesta_texto
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_out:
            tmp_out.write(speech)
            audio_out_path = tmp_out.name

        with open(audio_out_path, "rb") as f:
            audio_bytes = f.read()

        st.audio(audio_bytes, format="audio/mp3")


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
