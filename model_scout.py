import os
from google import genai
from dotenv import load_dotenv

# Load credentials
load_dotenv(dotenv_path="e:/open-interpreter/.env")
api_key = os.environ.get("GOOGLE_API_KEY")

def list_and_verify_models():
    print(f"--- FETCHING MODELS FOR KEY: {api_key[:5]}...{api_key[-4:]} ---")
    try:
        # Check both v1alpha and v1beta as some models are version-specific
        for version in ['v1alpha', 'v1beta']:
            print(f"\n[API VERSION: {version}]")
            client = genai.Client(api_key=api_key, http_options={'api_version': version})
            models = client.models.list()
            for m in models:
                # Look for Live/Bidi support
                if 'bidiGenerateContent' in m.supported_generation_methods:
                    print(f"✅ FOUND LIVE MODEL: {m.name}")
                    print(f"   Methods: {m.supported_generation_methods}")
                elif 'flash' in m.name.lower() or 'live' in m.name.lower():
                    print(f"   Potential Model: {m.name} (Methods: {m.supported_generation_methods})")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_and_verify_models()
