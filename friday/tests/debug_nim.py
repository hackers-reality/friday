"""Debug NIM vision failure in analyze_screen."""
from dotenv import load_dotenv
load_dotenv()
import os
from openai import OpenAI

key = os.environ.get("NVIDIA_VISION_API_KEY") or os.environ.get("NVIDIA_NIM_API_KEY")
print(f"Key loaded: {key[:10] if key else 'MISSING'}...")

from friday.pointing_agent import capture_all_monitors, parse_point_tags

# Step 1: Capture
monitors = capture_all_monitors()
print(f"Captured {len(monitors)} monitor(s)")
for m in monitors:
    print(f'  {m["label"]}: {m["w"]}x{m["h"]}')

# Step 2: Build request same way as analyze_screen
client = OpenAI(api_key=key, base_url="https://integrate.api.nvidia.com/v1", max_retries=0)

prompt = (
    "You are looking at the user's screen. "
    "Identify and describe every visible UI element, button, text field, icon, "
    "and interactive element. For each element, include a [POINT:x,y:label] tag "
    "with its approximate center coordinates and a short label.\n\n"
    "Format example:\n"
    "There is a [POINT:320,240:Submit button] at the bottom right of the form. "
    "The [POINT:100,50:Search bar] is at the top.\n\n"
    "Return ALL visible elements with their coordinates."
)

content = [{"type": "text", "text": prompt}]
for m in monitors:
    content.append({
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{m['b64']}"},
    })
    content.append({"type": "text", "text": f"--- {m['label']} ---"})

print(f"\nContent parts: {len(content)}")
print(f"Total image size: ~{sum(len(m['b64']) for m in monitors) // 1024} KB base64\n")

for model in ["nvidia/nemotron-nano-12b-v2-vl", "meta/llama-3.2-11b-vision-instruct"]:
    try:
        print(f"Testing {model}...")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            max_tokens=1024,
            temperature=0.3,
            timeout=30,
        )
        text = response.choices[0].message.content.strip()
        print(f"SUCCESS ({len(text)} chars)")
        targets, cleaned = parse_point_tags(text)
        print(f"POINT tags found: {len(targets)}")
        print(f"Preview: {text[:400]}")
        break
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
