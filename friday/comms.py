"""
FRIDAY Communication Broker — Thread-safe messaging queues
linking the background voice engine and the FastAPI dashboard server.
"""
from __future__ import annotations
import queue

# Queue for text commands sent from the dashboard chat UI to the Gemini Live session
dashboard_to_live_queue: queue.Queue[str] = queue.Queue()

# Queue for transcripts, tokens, tool results, and other updates from the Live engine to uvicorn websockets
live_to_dashboard_queue: queue.Queue[dict] = queue.Queue()
