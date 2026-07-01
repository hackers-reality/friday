"""Debug SVG generation - why is it returning empty?"""
import sys, asyncio, textwrap
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(str(Path(__file__).parent.parent / ".env"))
from friday.nim_client import InferenceClient
from friday.nim_router import resolve_model

async def main():
    client = InferenceClient()
    model = resolve_model("code_gen")
    
    # Test with a VERY simple SVG prompt
    prompt = "Write Python code that writes '<svg width=\"200\" height=\"100\"><text x=\"10\" y=\"50\">FRIDAY</text></svg>' to a file named 'test.svg'. ONLY Python code."
    
    resp = await client.chat(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.1, max_tokens=500)
    code = resp.content.strip()
    print(f"Response length: {len(code)} chars")
    print(f"Response: {code[:500]}")
    
    if not code:
        print("EMPTY RESPONSE - checking model availability")
        # Test basic chat
        resp2 = await client.chat(model=model, messages=[{"role": "user", "content": "Say hello"}], temperature=0.1, max_tokens=50)
        print(f"Basic chat test: {resp2.content.strip()[:100]}")

if __name__ == "__main__":
    asyncio.run(main())
