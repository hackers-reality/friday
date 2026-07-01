from pathlib import Path
base = Path("E:/open-interpreter/friday/skills")
for f in sorted(base.rglob("SKILL*.md")):
    try:
        text = f.read_text(encoding="utf-8")
        lines = len(text.splitlines())
        chars = len(text)
        print(f"{str(f.relative_to(base)):40s} {lines:5d} lines  {chars:6d} chars")
    except Exception as e:
        print(f"{str(f.relative_to(base)):40s} ERROR: {e}")
