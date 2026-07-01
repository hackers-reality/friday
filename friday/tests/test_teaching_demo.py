"""FRIDAY Teaching Demo — Full Pipeline: NIM Vision → [POINT] tags → Overlay Annotation → Narration

Simulates how FRIDAY (Gemini Live) would:
  1. Look at an app via analyze_screen()
  2. Get [POINT:x,y:label] tags for every UI element
  3. Narrate what she sees + annotate each element on screen
  4. Walk through a multi-step teaching flow
"""

import sys
import os
import time

sys.path.insert(0, r"E:\open-interpreter")
os.chdir(r"E:\open-interpreter")
os.environ["FRIDAY_MODE"] = "cli"

from dotenv import load_dotenv
load_dotenv()


def narrate(role: str, text: str):
    print(f"\n{'=' * 60}")
    print(f"  [{role}]")
    print(f"{'=' * 60}")
    # Simulate the streaming voice narration
    print(f"  {text}")


def simulate_friday_teaching(target_app: str, question: str):
    """Simulate FRIDAY's full teaching pipeline."""
    narrate("FRIDAY", f"Let me look at {target_app} and identify everything I can see...")

    # ── Step 1: NIM Vision analysis ──
    from friday.pointing_agent import analyze_screen, parse_point_tags

    narrate("SYSTEM", f"Calling analyze_screen('{question}') → NVIDIA NIM Vision")
    
    result = analyze_screen(question)
    
    if result.startswith("[FAIL]"):
        narrate("ERROR", f"NIM vision failed: {result}")
        return

    # ── Step 2: Parse [POINT] tags ──
    targets, cleaned = parse_point_tags(result)
    
    narrate("FRIDAY", f"I found {len(targets)} elements on screen!")
    print()
    
    for i, t in enumerate(targets):
        abs_x, abs_y = t.x, t.y
        print(f"  🔹 Element #{i+1}: [POINT:{abs_x:.0f},{abs_y:.0f}] — {t.label}")

    if not targets:
        narrate("FRIDAY", f"Hmm, I can see the screen but didn't find specific UI elements. Here's what I see:\n{result[:500]}")
        return

    # ── Step 3: Annotate on overlay ──
    from friday.visual_overlay import (
        start_overlay, show_text, point_at, draw_line,
        clear_overlays
    )

    narrate("FRIDAY", "Let me show you what I found! I'll annotate everything on your screen.")
    narrate("SYSTEM", "Starting overlay engine...")
    
    try:
        start_overlay()
        time.sleep(0.5)
    except Exception as e:
        pass  # Overlay may not work in headless CLI
    
    for i, t in enumerate(targets):
        abs_x, abs_y = t.x, t.y
        label = t.label or f"Element {i+1}"
        
        # FRIDAY narrates as she annotates each element
        narrate("FRIDAY", f"There's a {label} at position ({abs_x:.0f}, {abs_y:.0f}). Let me point to it!")
        narrate("SYSTEM", f"  → point_at({abs_x:.0f}, {abs_y:.0f}, '{label}')")
        
        try:
            point_at(abs_x, abs_y, label)
            show_text(abs_x + 50, abs_y - 10, label)
        except Exception:
            pass
        
        time.sleep(0.3)
    
    # ── Step 4: Multi-step teaching demo ──
    if len(targets) >= 2:
        narrate("FRIDAY", f"Now let me walk you through how to use these elements step by step!")
        
        from friday.visual_overlay import (
            start_teaching, stop_teaching,
            teaching_move_to, teaching_click, teaching_highlight
        )
        
        try:
            start_teaching()
            time.sleep(0.3)
        except Exception:
            pass
        
        # Teaching walkthrough
        t1 = targets[0]
        t2 = targets[1]
        
        narrate("FRIDAY", f"Step 1: First, let's look at '{t1.label}'. Clicking here will show you options.")
        narrate("SYSTEM", f"  → teaching_move_to({t1.x:.0f}, {t1.y:.0f}, '{t1.label}')")
        try:
            teaching_move_to(t1.x, t1.y, t1.label)
            teaching_highlight(t1.x - 30, t1.y - 15, 60, 30, t1.label)
        except Exception:
            pass
        time.sleep(0.3)
        
        narrate("FRIDAY", f"Step 2: Now, '{t2.label}' is where you'll perform the next action.")
        narrate("SYSTEM", f"  → teaching_click({t2.x:.0f}, {t2.y:.0f}, '{t2.label}')")
        try:
            teaching_click(t2.x, t2.y, t2.label)
        except Exception:
            pass
        time.sleep(0.3)
        
        if len(targets) >= 3:
            t3 = targets[2]
            narrate("FRIDAY", f"Step 3: Finally, drag here or click '{t3.label}' to complete the action.")
            narrate("SYSTEM", f"  → draw_line({t2.x:.0f}, {t2.y:.0f}, {t3.x:.0f}, {t3.y:.0f})")
            try:
                draw_line(t2.x, t2.y, t3.x, t3.y)
            except Exception:
                pass
            time.sleep(0.3)
        
        try:
            stop_teaching()
        except Exception:
            pass
    
    narrate("FRIDAY", f"That's everything I found in {target_app}! I can guide you through any of these step by step. Just tell me what you want to do!")


if __name__ == "__main__":
    target = "Notepad"
    question = (
        "List EVERY visible UI element in this Notepad window: "
        "menu items (File, Edit, Format, View, Help), toolbar buttons, "
        "the text editing area, the status bar, scroll bars, the title bar, "
        "minimize/maximize/close buttons. "
        "For each element, return a [POINT:x,y:label] tag with the "
        "center coordinates of each clickable/interactive element. "
        "Be thorough and don't miss anything."
    )
    simulate_friday_teaching(target, question)
