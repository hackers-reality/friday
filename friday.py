# -*- coding: utf-8 -*-
"""Friday AI — Sovereign Agent entry point."""
import os
import sys
import time
from dotenv import load_dotenv
load_dotenv()

from friday.live import friday_live_engine

if __name__ == "__main__":
    import asyncio
    max_restarts = 5
    restarts = 0
    while restarts < max_restarts:
        try:
            asyncio.run(friday_live_engine())
            # If we get here cleanly (intentional shutdown), break
            break
        except KeyboardInterrupt:
            print("\n[Friday] Shutting down.")
            break
        except Exception as e:
            restarts += 1
            print(f"\n[Friday] Unexpected error (attempt {restarts}/{max_restarts}): {e}")
            if restarts < max_restarts:
                print("[Friday] Restarting in 3 seconds...")
                time.sleep(3)
            else:
                print("[Friday] Max restarts reached. Exiting.")
                raise
