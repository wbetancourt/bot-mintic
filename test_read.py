import pandas as pd
import requests

url = "https://www.datos.gov.co/resource/uzcf-b9dh.json"
print("Probing URL:", url)
try:
    df = pd.read_json(url)
    print("Loaded with pd.read_json")
except Exception:
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        df = pd.json_normalize(data)
        print("Loaded with requests + pd.json_normalize")
    except Exception as e:
        print("Failed to load URL:", e)
        raise

print("Rows:", len(df))
print(df.head().to_string())
