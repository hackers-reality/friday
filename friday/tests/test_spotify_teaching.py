"""FRIDAY Teaching Demo: Spotify

Flow:
  1. Open Spotify
  2. analyze_screen → NIM tags everything → FRIDAY points to logo
  3. analyze_screen → FRIDAY teaches search (point to search bar)
  4. User types, hits enter → analyze_screen again for results
  5. FRIDAY points to song result, guides click play
"""

import sys
import os
import time
import subprocess
import re

sys.path.insert(0, r"E:\open-interpreter")
os.chdir(r"E:\open-interpreter")
os.environ["FRIDAY_MODE"] = "cli"

from dotenv import load_dotenv
load_dotenv()


def narrate(role: str, text: str):
    print(f"\n{'=' * 60}")
    print(f"  [{role}]")
    print(f"{'=' * 60}")
    # Simulate streaming TTS narration
    print(f'  "{text}"')
    print()


def say_and_annotate(text: str, overlay_fn=None, *args, **kwargs):
    """FRIDAY narrates AND annotates simultaneously."""
    narrate("FRIDAY", text)
    if overlay_fn and args:
        try:
            desc = kwargs.pop("desc", text[:40])
            print(f"  [OVERLAY] → {overlay_fn.__name__}{args}  # {desc}")
            overlay_fn(*args, **kwargs)
        except Exception as e:
            print(f"  [OVERLAY SKIP] {e}")


print("=" * 60)
print("  FRIDAY SPOTIFY TEACHING DEMO")
print("=" * 60)

# ── Step 0: Open Spotify ──
narrate("FRIDAY", "Let me open Spotify for you!")
narrate("SYSTEM", "Launching Spotify...")
try:
    subprocess.Popen(["cmd", "/c", "start", "spotify:"], shell=True)
    time.sleep(5)
except Exception:
    # Fallback: try Spotify executable path
    try:
        os.startfile(r"C:\Users\admin\AppData\Roaming\Spotify\Spotify.exe")
        time.sleep(5)
    except Exception as e:
        narrate("WARN", f"Could not launch Spotify: {e}")
        narrate("INFO", "Make sure Spotify is installed or launch it manually.")

# ── Step 1: Analyze Spotify's main screen ──
from friday.pointing_agent import analyze_screen, parse_point_tags
from friday.visual_overlay import (
    show_pointer, show_text, clear_overlays,
    start_teaching, stop_teaching, teaching_move_to,
    teaching_click, teaching_highlight
)

narrate("FRIDAY", "Let me look at Spotify and understand the interface...")

result = analyze_screen(
    question="List ALL elements in the Spotify window: logo, search bar, navigation sidebar (Home, Search, Library), playlist items, play/pause button, skip buttons, volume slider, your library. Return [POINT:x,y:label] tags for each."
)
targets, cleaned = parse_point_tags(result)
narrate("FRIDAY", f"I can see {len(targets)} elements on the Spotify screen!")
print()
for i, t in enumerate(targets):
    print(f"  #{i+1}: [POINT:{t.x:.0f},{t.y:.0f}] {t.label}")

if not targets:
    narrate("FRIDAY", "I can see Spotify but couldn't identify individual elements. Here's what I see:")
    print(f"  {result[:500]}")
    sys.exit(0)

# ── Step 2: Point to Spotify logo ──
say_and_annotate(
    "First, let me show you where the Spotify logo is at the top of the app!",
    point_at, targets[0].x, targets[0].y, targets[0].label
)
time.sleep(1)

# ── Step 3: Find + point to search bar ──
search_targets = [t for t in targets if "search" in t.label.lower() or "search" in t.label.lower()]
if search_targets:
    st = search_targets[0]
    say_and_annotate(
        f"Here's the Search bar at ({st.x:.0f}, {st.y:.0f}). Click here to search for any song, artist, or album!",
        teaching_move_to, st.x, st.y, "Search bar"
    )
    time.sleep(1)

# ── Step 4: Teach the search flow ──
narrate("FRIDAY", "Now, here's how to search for a song step-by-step:")

# Step 4a: Click search bar
say_and_annotate(
    "Step 1: Click on the Search bar. I'll highlight it.",
    teaching_highlight, search_targets[0].x - 80, search_targets[0].y - 15, 160, 30, "Click here to search"
)
time.sleep(1)

# Step 4b: Type in search
narrate("FRIDAY", 'Step 2: Type the song name, like "Bohemian Rhapsody" and press Enter.')
narrate("SYSTEM", "[User types 'Bohemian Rhapsody' and hits Enter]")
time.sleep(1)

# ── Step 5: Analyze search results ──
narrate("FRIDAY", "Let me check what appeared on screen after your search...")

result2 = analyze_screen(
    question="Show me the search results on screen now. Point to each song/album/artist result with [POINT:x,y:label] tags. Also identify the play button if visible."
)
targets2, cleaned2 = parse_point_tags(result2)

if targets2:
    narrate("FRIDAY", f"I found {len(targets2)} elements in the search results!")
    for i, t in enumerate(targets2[:5]):
        print(f"  #{i+1}: [POINT:{t.x:.0f},{t.y:.0f}] {t.label}")

    if targets2:
        say_and_annotate(
            f"Step 3: Here's the first search result — '{targets2[0].label}'. Click to open it!",
            point_at, targets2[0].x, targets2[0].y, targets2[0].label
        )
        time.sleep(1)

# ── Step 6: Click play ──
play_targets = [t for t in targets2 if "play" in t.label.lower()]
if play_targets:
    pt = play_targets[0]
    say_and_annotate(
        f"Step 4: Finally, click the Play button to start your song!",
        teaching_click, pt.x, pt.y, "Play"
    )
elif targets2:
    # Just click the first result
    say_and_annotate(
        "Step 4: Click on the song to play it. Enjoy your music! 🎵",
        teaching_click, targets2[0].x, targets2[0].y, targets2[0].label
    )
else:
    narrate("FRIDAY", "Let me point you to what I can see and you can click the song you want!")
    if targets:
        say_and_annotate(
            "Here's what's on your screen — pick a song and I'll guide you through playing it!",
            point_at, targets[0].x, targets[0].y, targets[0].label
        )

narrate("FRIDAY", "That's it! You've just searched and played a song on Spotify using my guidance!")
narrate("FRIDAY", "You can ask me to teach you any other part of Spotify — creating playlists, adjusting the equalizer, finding new music, or anything else!")
