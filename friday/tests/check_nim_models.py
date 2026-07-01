"""Check what models are available on the NIM API endpoint."""
import urllib.request, json

r = urllib.request.urlopen("https://integrate.api.nvidia.com/v1/models", timeout=10)
models = json.loads(r.read())

keywords = ["vision", "florence", "phi-4", "llava", "vlm", "nemotron", "vl", "cog", "intern", "fuyu", "adept"]
vision = [m["id"] for m in models["data"] if any(k in m["id"].lower() for k in keywords)]

print("Vision-related models:")
for v in vision:
    print(f"  {v}")
print(f"\nTotal models: {len(models['data'])}")

# Also check for llava or meta vision models
llm = [m["id"] for m in models["data"] if "llama" in m["id"].lower() and "vision" in m["id"].lower()]
print(f"\nLLaMA vision models:")
for v in llm:
    print(f"  {v}")
