"""Test: LLM drives the overlay to explain Pythagoras visually."""
import sys, time, json, os, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from friday.overlay_engine import get_engine
eng = get_engine()
eng.start()
eng.show_buddy(True)
time.sleep(0.5)

import pyautogui
sw, sh = pyautogui.size()
cx, cy = sw // 2, sh // 2

tools_def = [
    {
        "name": "draw_line",
        "description": "Draw a straight line between two points (no arrowhead). Buddy follows along as line draws. One line at a time.",
        "parameters": {
            "type": "object",
            "properties": {
                "x1": {"type": "integer"}, "y1": {"type": "integer"},
                "x2": {"type": "integer"}, "y2": {"type": "integer"},
                "color": {"type": "string"},
                "duration": {"type": "number"}
            },
            "required": ["x1", "y1", "x2", "y2"]
        }
    },
    {
        "name": "show_text",
        "description": "Show text at screen coordinates (black text on white background)",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"}, "y": {"type": "integer"},
                "text": {"type": "string"}, "duration": {"type": "number"}
            },
            "required": ["x", "y", "text"]
        }
    },
    {
        "name": "fly_to",
        "description": "Animate cursor to screen coordinates with label",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"}, "y": {"type": "integer"},
                "label": {"type": "string"}
            },
            "required": ["x", "y"]
        }
    },
]

prompt = (
    f"Screen is {sw}x{sh}px. Center is ({cx},{cy}). "
    "Explain Pythagoras theorem by drawing a 3-4-5 right triangle on screen. "
    "Draw ONE line at a time with draw_line (base, then height, then hypotenuse). "
    "Use show_text for labels (a, b, c) and the formula a²+b²=c². "
    "Use fly_to to point at each side and explain it."
)

api_key = os.environ.get("GOOGLE_API_KEY", "")
resp = requests.post(
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
    headers={"Content-Type": "application/json"},
    params={"key": api_key},
    json={
        "system_instruction": {"parts": [{"text": "You are a visual teacher. Always use tool calls to draw and explain. Draw one element at a time."}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"function_declarations": tools_def}]
    },
    timeout=30
)
data = resp.json()
for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
    if "functionCall" in part:
        fn = part["functionCall"]
        name, args = fn["name"], fn.get("args", {})
        print(f"LLM calls: {name}({json.dumps(args)})")
        if name == "draw_line":
            eng.draw_line(args["x1"], args["y1"], args["x2"], args["y2"],
                          color=args.get("color", "#3B82F6"),
                          duration=args.get("duration", 5.0))
            time.sleep(2)
        elif name == "show_text":
            eng.show_text(args["x"], args["y"], args["text"],
                          duration=args.get("duration", 10.0))
        elif name == "fly_to":
            eng.fly_to(args["x"], args["y"], label=args.get("label", ""))
            time.sleep(2)
    elif "text" in part:
        print(f"LLM: {part['text'][:300]}")

time.sleep(5)
eng.clear_all()
eng.stop()
print("Done")
