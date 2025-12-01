import streamlit as st
import pandas as pd
import requests
import openai
import os
# 4. FUNCIÓN PARA CARGAR LOS DATOS DESDE LA API (actualizada)
# ---------------------------------------------------------
def load_data():
    """
    Carga el dataset desde la API pública JSON.
    Si hay un `CSV_URL` en `st.secrets` o en la variable `CSV_URL` de entorno,
    se usa en su lugar.
    """

    # URL por defecto (reemplaza el CSV local)
    default_url = "https://www.datos.gov.co/resource/uzcf-b9dh.json"

    # Preferir `CSV_URL` en secretos/entorno si está presente
    csv_url = None
    try:
        if hasattr(st, "secrets") and "CSV_URL" in st.secrets:
            csv_url = st.secrets["CSV_URL"]
    except Exception:
        pass

    if not csv_url:
        csv_url = os.getenv("CSV_URL", default_url)

    # Intentar leer como JSON/CSV; preferimos JSON para este endpoint
    try:
        try:
            return pd.read_json(csv_url)
        except Exception:
            # fallback: requests + json_normalize
            resp = requests.get(csv_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return pd.json_normalize(data)
    except Exception as e:
        st.error(f"No se pudo cargar los datos desde la URL `{csv_url}`: {e}")
        st.stop()
# 3. URL OFICIAL DE LA API
# ---------------------------------------------------------
API_URL = "https://www.datos.gov.co/resource/uzcf-b9dh.json"

# ---------------------------------------------------------
# 4. FUNCIÓN PARA CARGAR LOS DATOS DESDE LA API
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
# 5. CARGAR DATAFRAME
# ---------------------------------------------------------
st.subheader("📊 Datos cargados desde la API")
df = load_data()

if df.empty:
    st.warning("⚠ No se pudieron cargar datos desde la API.")
else:
    st.dataframe(df)

# ---------------------------------------------------------
# 6. CHATBOT MODEL
# ---------------------------------------------------------
st.subheader("🤖 Chatbot Mintic")

pregunta = st.text_input("Escribe tu pregunta:")

if st.button("Enviar") and pregunta.strip():
    try:
        respuesta = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente experto en análisis de datos."},
                {"role": "user", "content": pregunta}
            ]
        )

        st.success(respuesta.choices[0].message.content)

    except Exception as e:
        st.error(f"Error al generar respuesta: {str(e)}")
