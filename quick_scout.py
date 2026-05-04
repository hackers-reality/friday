import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path="e:/open-interpreter/.env")
api_key = os.environ.get("GOOGLE_API_KEY")

def scout_requests():
    for version in ['v1alpha', 'v1beta']:
        url = f"https://generativelanguage.googleapis.com/{version}/models?key={api_key}"
        print(f"--- FETCHING {version} ---")
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if "models" in data:
                for m in data["models"]:
                    name = m["name"]
                    methods = m.get("supportedGenerationMethods", [])
                    if "bidiGenerateContent" in methods:
                        print(f"✅ LIVE: {name}")
                    elif "2.5" in name or "flash" in name.lower():
                        print(f"   Model: {name} ({methods})")
            else:
                print(f"   No models or error: {data}")
        except Exception as e:
            print(f"   Failed: {e}")

if __name__ == "__main__":
    scout_requests()
