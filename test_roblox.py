import sys
sys.path.insert(0, '.')
from friday.tools import open_roblox_game

# Test with the actual misspelling the user used
print("=== Test: open_roblox_game('blocks fruits') ===")
result = open_roblox_game("blocks fruits")
print(result)
print()

# Test with correct name
print("=== Test: open_roblox_game('blox fruits') ===")
result = open_roblox_game("blox fruits")
print(result)
print()

# Test the underlying search to debug
print("=== Debug: test search_engine ===")
from friday.web import WebScraper
scraper = WebScraper()
resp = scraper.search_engine("blox fruits roblox place id")
if resp.get("success"):
    for item in resp.get("results", [])[:5]:
        print(f"  Title: {item.get('title', '')}")
        print(f"  URL: {item.get('url', '')}")
        print(f"  Snippet: {item.get('snippet', '')[:100]}")
        print()
else:
    print("search_engine failed:", resp.get("error", "unknown"))
