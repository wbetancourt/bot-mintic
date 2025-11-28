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
