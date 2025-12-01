# app.py (versión corregida)
import streamlit as st
import pandas as pd
import requests
import os
import json
import re
import matplotlib.pyplot as plt

# Intento de importar cliente OpenAI moderno (usa `from openai import OpenAI`)
# Si no está instalado, el bloque LLM quedará desactivado y la app seguirá funcionando
try:
    from openai import OpenAI
    OPENAI_INSTALLED = True
except Exception:
    OPENAI_INSTALLED = False

# ============================
# CONFIG
# ============================
CSV_PATH = "Asset_Inventory_-_Public_20251119.csv"
API_URL_DEFAULT = "https://www.datos.gov.co/resource/uzcf-b9dh.json"

# Intentar obtener la clave OpenAI desde Streamlit secrets o variables de entorno
API_KEY = None
try:
    if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
        API_KEY = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass

if not API_KEY:
    API_KEY = os.getenv("OPENAI_API_KEY")

# Inicializar cliente LLM solo si la lib está disponible y hay clave
client = None
if OPENAI_INSTALLED and API_KEY:
    try:
        client = OpenAI(api_key=API_KEY)
    except Exception as e:
        client = None
        st.warning(f"Advertencia: no se pudo inicializar OpenAI client: {e}")

# ============================
# CARGA DE DATOS
# ============================
@st.cache_data(show_spinner=True)
def load_data():
    """
    Preferencia:
     1) CSV local si existe (CSV_PATH)
     2) CSV_URL en st.secrets o variable CSV_URL
     3) API_URL_DEFAULT (JSON)
    Devuelve DataFrame (puede ser vacío si falla).
    """
    # 1) CSV local
    if os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH, encoding="utf-8")
            return df
        except Exception:
            # intentar sin encoding explícito
            try:
                return pd.read_csv(CSV_PATH)
            except Exception:
                st.warning("No se pudo leer el CSV local correctamente.")
                return pd.DataFrame()

    # 2) CSV_URL en secrets o entorno
    csv_url = None
    try:
        if hasattr(st, "secrets") and "CSV_URL" in st.secrets:
            csv_url = st.secrets["CSV_URL"]
    except Exception:
        pass
    if not csv_url:
        csv_url = os.getenv("CSV_URL", None)

    # 3) Usar csv_url si está, sino API por defecto
    url_to_use = csv_url if csv_url else API_URL_DEFAULT

    # Intentar leer JSON o CSV desde url
    try:
        # intentar read_json directo
        try:
            df = pd.read_json(url_to_use)
            return df
        except Exception:
            # fallback: requests + json_normalize
            resp = requests.get(url_to_use, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                df = pd.json_normalize(data)
            else:
                # si viene dict con claves, intentar normalizar
                df = pd.json_normalize([data])
            return df
    except Exception as e:
        st.error(f"No se pudieron cargar datos desde `{url_to_use}`: {e}")
        return pd.DataFrame()

# ============================
# UTIL: extraer JSON de texto
# ============================
def extract_json_from_text(text):
    """
    Busca la primera estructura JSON (objeto o lista) en un texto y devuelve el objeto Python.
    """
    m = re.search(r"(\{(?:.|\n)*\}|\[(?:.|\n)*\])", text, flags=re.S)
    if not m:
        return None
    candidate = m.group(1)
    try:
        return json.loads(candidate)
    except Exception:
        return None

# ============================
# LLM: preguntar (si está disponible)
# ============================
def ask_llm(question, df):
    """
    Devuelve texto (respuesta del LLM). Si no hay client, devuelve None.
    """
    if client is None:
        return None

    # Construir prompt (incluir un resumen mínimo de columnas)
    cols_preview = ", ".join(df.columns[:50]) if not df.empty else "sin datos"
    prompt = f"""
Eres un asistente experto en análisis de datos.
Dataset cargado con {0 if df.empty else df.shape[0]} filas y {0 if df.empty else df.shape[1]} columnas.
Columnas disponibles: {cols_preview}

Cuando el usuario solicite:
1) GRÁFICOS → devuelve JSON:
{{"accion":"graficar","tipo":"bar"|"line"|"pie","x":"col_x","y":"col_y","agregacion":"count"|"sum"|"none"}}
2) TABLAS → JSON:
{{"accion":"tabla","columnas":["col1","col2"]}}
3) FILTROS → JSON:
{{"accion":"filtrar","columna":"col","valor":"val"}}
Si no pide alguna de las anteriores, responde en texto.
Pregunta: {question}
"""

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente analítico. Devuelves JSON válido cuando se piden gráficos/tablas."},
                {"role": "user", "content": prompt}
            ],
        )
        # Algunos SDKs devuelven choices... adaptamos al patrón que ya usabas
        return completion.choices[0].message.content
    except Exception as e:
        st.warning(f"Error al consultar LLM: {e}")
        return None

# ============================
# Ejecutar instrucciones JSON
# ============================
def ejecutar_instruccion(instr, df):
    """
    instr puede ser dict (ya parseado) o texto.
    """
    if isinstance(instr, str):
        # intentar extraer JSON
        parsed = None
        try:
            parsed = json.loads(instr)
        except Exception:
            parsed = extract_json_from_text(instr)
        if parsed is None:
            st.write(instr)
            return
    else:
        parsed = instr

    if not isinstance(parsed, dict):
        st.write(parsed)
        return

    accion = parsed.get("accion")
    if accion == "tabla":
        cols = parsed.get("columnas", [])
        if not cols:
            st.warning("No se especificaron columnas para la tabla.")
            return
        # seguridad: filtrar columnas existentes
        cols_ok = [c for c in cols if c in df.columns]
        st.dataframe(df[cols_ok].head(50))
        return

    if accion == "filtrar":
        col = parsed.get("columna")
        val = parsed.get("valor")
        if not col or col not in df.columns:
            st.warning("Columna de filtro inválida.")
            return
        filtrado = df[df[col].astype(str) == str(val)]
        st.dataframe(filtrado.head(200))
        return

    if accion == "graficar":
        tipo = parsed.get("tipo")
        x = parsed.get("x")
        y = parsed.get("y")
        agg = parsed.get("agregacion", "count")
        if x not in df.columns or (y is not None and y not in df.columns):
            st.warning("Columnas para graficar inválidas.")
            return
        try:
            if agg == "count":
                data = df.groupby(x)[x].count()
            elif agg == "sum" and y:
                data = df.groupby(x)[y].sum()
            else:
                data = df.set_index(x)[y] if y else df.groupby(x)[x].count()
            fig, ax = plt.subplots(figsize=(10, 4))
            if tipo == "bar":
                data.plot(kind="bar", ax=ax)
            elif tipo == "line":
                data.plot(kind="line", ax=ax)
            elif tipo == "pie":
                data.plot(kind="pie", ax=ax, autopct="%1.1f%%")
            st.pyplot(fig)
        except Exception as e:
            st.warning(f"No se pudo generar el gráfico: {e}")
        return

    st.write(parsed)

# ============================
# INTERFAZ STREAMLIT
# ============================
st.title("🤖 Chatbot de Datos Abiertos – MINTIC")
st.write("Este app usa el dataset público. Si no tienes OPENAI_API_KEY, la app seguirá funcionando en modo limitado (sin LLM).")

st.subheader("📊 Cargando datos")
df = load_data()

if df.empty:
    st.warning("No se pudieron cargar datos (DataFrame vacío). Asegúrate del endpoint o sube un CSV.")
else:
    st.caption(f"Dataset cargado: {df.shape[0]} filas × {df.shape[1]} columnas")
    with st.expander("Ver primeras filas"):
        st.dataframe(df.head(50))

# Mostrar lista corta de columnas
if not df.empty:
    with st.expander("Columnas del dataset"):
        st.write(list(df.columns))

# =================================
# Preguntas / Chat
# =================================
st.subheader("🤖 Pregunta al bot")

pregunta = st.text_area("Escribe tu pregunta aquí (ej: '¿Cuántas columnas tiene el dataset?')", height=120)

if st.button("Enviar pregunta"):
    if not pregunta.strip():
        st.warning("Escribe una pregunta antes.")
    else:
        # 1) Si no hay client LLM, responder con capacidades locales
        if client is None:
            q = pregunta.lower()
            # respuestas útiles sin LLM
            if "cuánt" in q or "cuantos" in q or "cuántas" in q:
                st.info(f"El dataset tiene {0 if df.empty else df.shape[1]} columnas.")
                st.write(list(df.columns))
            elif "filas" in q or "registros" in q:
                st.info(f"El dataset tiene {0 if df.empty else df.shape[0]} filas.")
            elif "mostrar columnas" in q or "columnas" in q:
                st.write(list(df.columns))
            else:
                st.info("LLM no está disponible (no hay API key). Puedo responder preguntas simples sobre tamaño/columnas/filtrado.")
        else:
            # preguntar al LLM
            respuesta = ask_llm(pregunta, df)
            if respuesta is None:
                st.warning("No se obtuvo respuesta del LLM.")
            else:
                # intentar ejecutar si LLM devolvió JSON
                parsed = None
                try:
                    parsed = json.loads(respuesta)
                except Exception:
                    parsed = extract_json_from_text(respuesta)
                if isinstance(parsed, dict):
                    ejecutar_instruccion(parsed, df)
                else:
                    st.write(respuesta)

# =================================
# Endpoint simple para n8n (opcional)
# =================================
st.markdown("---")
st.subheader("🌐 Endpoint para n8n (opcional)")
st.write("Si necesitas exponer este bot a un workflow (n8n), usa la UI o implementa un endpoint en la capa que despliegues (este Streamlit no expone endpoint HTTP por defecto).")

# FIN
