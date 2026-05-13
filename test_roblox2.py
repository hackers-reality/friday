import sys, time
sys.path.insert(0, '.')

# First, test the Roblox API directly (this should be fast)
print("=== Test Roblox API ===")
import requests, urllib.parse
try:
    r = requests.get(
        "https://games.roblox.com/v1/games/search?keyword=" + urllib.parse.quote("blox fruits") + "&limit=5",
        timeout=10
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        for g in data.get("data", [])[:5]:
            print(f"  {g.get('name')} -> placeId={g.get('placeId')}")
    else:
        print(f"Response: {r.text[:200]}")
except Exception as e:
    print(f"API Error: {e}")

print()

# Now test web search with a short timeout
print("=== Test WebScraper ===")
try:
    from friday.web import WebScraper
    scraper = WebScraper()
    t0 = time.time()
    resp = scraper.search_engine("blox fruits roblox")
    elapsed = time.time() - t0
    print(f"Elapsed: {elapsed:.1f}s")
    if resp.get("success"):
        for item in resp.get("results", [])[:3]:
            print(f"  Title: {item.get('title','')}")
            print(f"  URL: {item.get('url','')}")
            print()
    else:
        print(f"Failed: {resp.get('error', 'no error msg')}")
except Exception as e:
    print(f"WebScraper Error: {e}")
