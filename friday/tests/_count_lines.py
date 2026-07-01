from pathlib import Path
f = Path("E:/open-interpreter/friday/agent_profiles.py")
print(f"Lines: {len(f.read_text(encoding='utf-8').splitlines())}")
