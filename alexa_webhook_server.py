
"""Friday Alexa Webhook Server

Run this on your machine (or any server) and expose it with ngrok.

Environment variables:
- FRIDAY_WEBHOOK_SECRET  required
- FRIDAY_ALLOWED_ORIGIN  optional, if you want to check a specific caller origin
"""

from __future__ import annotations

import os
import threading
from collections import deque

from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

app = Flask(__name__)

WEBHOOK_SECRET = os.environ["FRIDAY_WEBHOOK_SECRET"]

# Shared queue for commands coming from Alexa → Friday and Friday → Alexa
_alexa_command_queue: deque[dict] = deque()
_queue_lock = threading.Lock()


def _queue_command(source: str, command: str) -> None:
    with _queue_lock:
        _alexa_command_queue.append({"source": source, "command": command})


def _pop_all_commands() -> list[dict]:
    with _queue_lock:
        items = list(_alexa_command_queue)
        _alexa_command_queue.clear()
    return items


def _alexa_response(text: str, end_session: bool = True, reprompt: str | None = None):
    payload = {
        "version": "1.0",
        "response": {
            "outputSpeech": {"type": "PlainText", "text": text},
            "shouldEndSession": end_session,
        },
    }
    if reprompt and not end_session:
        payload["response"]["reprompt"] = {
            "outputSpeech": {"type": "PlainText", "text": reprompt}
        }
    return jsonify(payload)


@app.route("/alexa", methods=["POST"])
def alexa_handler():
    """Alexa skill endpoint."""
    body = request.get_json(silent=True) or {}
    request_type = body.get("request", {}).get("type", "")

    if request_type == "LaunchRequest":
        return _alexa_response(
            "Friday is online. What is the mission, Boss?",
            end_session=False,
            reprompt="Give me a command.",
        )

    if request_type == "IntentRequest":
        intent = body.get("request", {}).get("intent", {})
        intent_name = intent.get("name", "")
        slots = intent.get("slots", {})

        if intent_name == "FridayCommandIntent":
            command = slots.get("command", {}).get("value", "").strip()
            if command:
                _queue_command("alexa", command)
                return _alexa_response(f"Roger that. Executing: {command}")
            return _alexa_response("I did not catch that command, Boss.")

        if intent_name in {"AMAZON.StopIntent", "AMAZON.CancelIntent"}:
            return _alexa_response("Standing by.", end_session=True)

        if intent_name == "AMAZON.HelpIntent":
            return _alexa_response(
                "Try saying a Friday command like turn off the lights, or say stop to exit.",
                end_session=False,
                reprompt="What should I do?",
            )

    if request_type == "SessionEndedRequest":
        return jsonify({"version": "1.0", "response": {}})

    return _alexa_response("Ready for orders.")


@app.route("/friday/send", methods=["POST"])
def friday_send():
    """Friday posts here to queue a command for processing / logging."""
    auth = request.headers.get("X-Friday-Secret", "")
    if auth != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    if not request.is_json:
        return jsonify({"error": "Invalid content type"}), 400

    body = request.get_json(silent=True) or {}
    command = str(body.get("command", "")).strip()
    if not command:
        return jsonify({"error": "No command provided"}), 400

    _queue_command("friday", command)
    return jsonify({"status": "queued", "command": command})


@app.route("/friday/poll", methods=["GET"])
def friday_poll():
    """Friday polls this to retrieve commands queued from Alexa."""
    auth = request.headers.get("X-Friday-Secret", "")
    if auth != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify({"commands": _pop_all_commands()})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "online", "bridge": "active"})


if __name__ == "__main__":
    print("Friday Alexa Bridge — Online on port 5123")
    print("Expose with: ngrok http 5123")
    print("Set Alexa Skill endpoint to: https://<ngrok_url>/alexa")
    app.run(host="0.0.0.0", port=5123, debug=False)
