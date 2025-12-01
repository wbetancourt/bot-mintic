import streamlit as st
import pandas as pd
import requests
import openai
import json
import re
import matplotlib.pyplot as plt
import os

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA API DE OPENAI
# ---------------------------------------------------------
openai.api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

if not openai.api_key:
    st.error("❌ Falta la variable OPENAI_API_KEY. Debes agregarla en Streamlit Secrets.")
    st.stop()

# ---------------------------------------------------------
# URL OFICIAL DE LA API
# ---------------------------------------------------------
API_URL = "https://www.datos.gov.co/resource/uzcf-b9dh.json"

# ---------------------------------------------------------
# CARGA DE DATOS DESDE LA API
# ---------------------------------------------------------
@st.cache_data(show_spinner=True)
def load_data():
    try:
        response = requests.get(API_URL, timeout=15)

        if response.status_code != 200:
            st.error(f"Error al consultar API: {response.status_code}")
            return pd.DataFrame()

        data = response.json()
        df = pd.DataFrame(data)

        return df

    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return pd.DataFrame()

# ---------------------------------------------------------
# MOSTRAR DATAFRAME
# ---------------------------------------------------------
st.title("📊 BOT – Datos Abiertos MINTIC")
st.subheader("📥 Datos cargados desde la API oficial")

df = load_data()

if df.empty:
    st.warning("⚠ No se pudieron cargar datos desde la API.")
    st.stop()

st.dataframe(df, use_container_width=True)

# ---------------------------------------------------------
# CHATBOT
# ---------------------------------------------------------
st.subheader("🤖 Chatbot Inteligente")

pregunta = st.text_input("Escribe tu pregunta:")

def extract_json(text):
    """Extrae JSON válido desde una respuesta del modelo."""
    try:
        return json.loads(text)
    except:
        pass

    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.S)
    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except:
        return None


if st.button("Enviar") and pregunta.strip():

    prompt = f"""
Eres un analista experto. El dataset tiene {df.shape[0]} filas y {df.shape[1]} columnas.

Columnas disponibles:
{', '.join(df.columns)}

Si el usuario pide:
1) TABLA → responde SOLO:
{{
  "accion": "tabla",
  "columnas": ["columna1", "columna2"]
}}

2) FILTRAR →
{{
  "accion": "filtrar",
  "columna": "col",
  "valor": "valor"
}}

3) GRAFICAR →
{{
  "accion": "graficar",
  "tipo": "bar" | "line" | "pie",
  "x": "",
  "y": "",
  "agregacion": "count" | "sum" | "none"
}}

Si NO es instrucción, responde en texto normal.
Pregunta:
{pregunta}
"""

    try:
        respuesta = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente experto en análisis de datos."},
                {"role": "user", "content": prompt}
            ]
        )

        texto = respuesta.choices[0].message.content
        st.success(texto)

        # Intentar interpretar JSON
        parsed = extract_json(texto)

        if isinstance(parsed, dict):
            accion = parsed.get("accion")

            # TABLA
            if accion == "tabla":
                cols = parsed.get("columnas", [])
                if cols:
                    st.write(df[cols].head())
                else:
                    st.warning("JSON sin columnas válidas.")

            # FILTRO
            elif accion == "filtrar":
                col = parsed.get("columna")
                val = parsed.get("valor")
                st.write(df[df[col] == val].head())

            # GRAFICAR
            elif accion == "graficar":
                tipo = parsed.get("tipo")
                x = parsed.get("x")
                y = parsed.get("y")
                agg = parsed.get("agregacion", "count")

                try:
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

                except Exception as e:
                    st.error(f"No se pudo graficar: {e}")

    except Exception as e:
        st.error(f"Error al generar respuesta: {str(e)}")
