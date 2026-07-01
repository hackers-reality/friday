"""Benchmark all available NIM vision models: speed + UI element detection accuracy."""
import time
import os
import base64
import io
from dotenv import load_dotenv
load_dotenv()

from PIL import ImageGrab
from openai import OpenAI

key = (os.environ.get("NVIDIA_VISION_API_KEY") or
       os.environ.get("NVIDIA_NIM_API_KEY") or
       os.environ.get("NVIDIA_API_KEY") or
       os.environ.get("NIM_API_KEY"))

client = OpenAI(api_key=key, base_url="https://integrate.api.nvidia.com/v1", max_retries=0)

# Capture screen once for fair comparison
img = ImageGrab.grab()
img.thumbnail((1280, 720))
buf = io.BytesIO()
img.save(buf, format="JPEG", quality=80)
b64 = base64.b64encode(buf.getvalue()).decode()

prompt = (
    "List ALL visible UI elements on this screen — buttons, text fields, "
    "menu items, icons, tabs, scroll bars, the title bar. "
    "For each element return a [POINT:x,y:label] tag with its "
    "center coordinates and a precise label describing its function. "
    "Be thorough. Include at least 5 elements."
)

models = [
    "microsoft/phi-4-multimodal-instruct",
    "meta/llama-3.2-11b-vision-instruct",
    "nvidia/nemotron-nano-12b-v2-vl",
    "meta/llama-3.2-90b-vision-instruct",
]

results = []

for model in models:
    print(f"\n{'='*60}")
    print(f"Testing: {model}")
    print(f"{'='*60}")
    
    try:
        t0 = time.time()
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ]}],
            max_tokens=512,
            temperature=0.3,
            timeout=30,
        )
        elapsed = time.time() - t0
        text = r.choices[0].message.content.strip()
        
        # Count [POINT] tags
        import re
        tags = re.findall(r'\[POINT:[^\]]+\]', text)
        
        print(f"  Time: {elapsed:.1f}s | POINT tags: {len(tags)} | Length: {len(text)} chars")
        print(f"  Response preview: {text[:300]}")
        
        results.append((model, elapsed, len(tags), text))
        
    except Exception as e:
        print(f"  FAILED: {e}")

print(f"\n\n{'='*60}")
print(f"BENCHMARK SUMMARY")
print(f"{'='*60}")
for model, elapsed, tag_count, text in results:
    print(f"  {model:50s}  {elapsed:5.1f}s  {tag_count:2d} tags")
