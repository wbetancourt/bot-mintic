# Chatbot de Datos Abiertos – MINTIC

Instrucciones para desarrollo local y despliegue en Streamlit Cloud.

## Resumen

Este proyecto es una aplicación Streamlit que utiliza la API de OpenAI para analizar y visualizar un dataset CSV. Por seguridad, la clave de OpenAI no debe subirse al repositorio. En producción se recomienda usar el Secrets Manager de Streamlit Cloud.

## Opciones para la API Key

- Streamlit Cloud (recomendado para despliegue):
  1. Ve a tu app en Streamlit Cloud → Settings → Secrets.
  2. Añade la clave como `OPENAI_API_KEY=sk-...`.
  3. Despliega — la app leerá `st.secrets['OPENAI_API_KEY']`.

- Desarrollo local con `.env`:
  1. Crear un archivo `.env` en la raíz (no subirlo al repo).
     ```powershell
     'OPENAI_API_KEY=sk-<tu-clave-aqui>' | Out-File -FilePath .env -Encoding utf8
     ```
  2. Instalar dependencias y ejecutar:
     ```powershell
     pip install -r requirements.txt
     streamlit run .\app.py
     ```

## Archivos importantes

- `app.py`: aplicación Streamlit. Lee `st.secrets` primero, luego `OPENAI_API_KEY` desde `.env` o la variable de entorno.
- `.env.example`: ejemplo con placeholder (no contiene la clave real).
- `.gitignore`: ya incluye `.env` para que no se suba.

## Dependencias

Instala las dependencias listadas en `requirements.txt`.

## Notas de seguridad

- Nunca comprometas tu clave en el repositorio público.
- Usa Streamlit Cloud Secrets para producción.

Si quieres, puedo crear el commit con estos cambios y preparar el repositorio para subirlo a GitHub.
## Usar un dataset remoto con `CSV_URL`

La aplicación puede cargar un dataset desde una URL pública (CSV o JSON) usando la variable `CSV_URL`. Esto es útil si no quieres subir archivos grandes al repositorio.

- Streamlit Cloud (recomendado):
  1. Ve a tu app en Streamlit Cloud → Settings → Secrets.
  2. Añade una entrada `CSV_URL` con la URL pública, por ejemplo:
    ```text
    CSV_URL=https://www.datos.gov.co/resource/uzcf-b9dh.json
    ```
  3. Guarda y redepliega la app; `app.py` leerá `st.secrets['CSV_URL']` automáticamente.

- Desarrollo local (opcional):
  1. Crea/edita tu archivo `.env` en la raíz del proyecto (ya está en `.gitignore`) y añade:
    ```powershell
    'CSV_URL=https://www.datos.gov.co/resource/uzcf-b9dh.json' | Out-File -FilePath .env -Encoding utf8
    ```
  2. Asegúrate de tener `python-dotenv` instalado (está en `requirements.txt`). El código carga `.env` automáticamente.
  3. Ejecuta la app desde la misma terminal:
    ```powershell
    streamlit run .\app.py
    ```

- Nota: la app intenta cargar primero CSV, luego JSON con `pd.read_json`, y por último usa `requests` + `pd.json_normalize`.

Si prefieres que añada `CSV_URL` a `st.secrets` en Streamlit Cloud, dímelo y te guío paso a paso.
