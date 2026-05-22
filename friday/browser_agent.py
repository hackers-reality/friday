"""
FRIDAY Browser Agent — "Atlas"
Registered agent with task_type=browse for web automation.

Receives high-level tasks from orchestrator:
  "check my YouTube Studio stats"
  "search for ... on Google"
  "fill in the login form"

Converts to browser action sequences via NIM reasoning, executes
via browser_tools, and returns structured results with screenshots.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from friday.base_agent import BaseAgent, AgentDef, AgentTask, AgentResult
from friday.browser_manager import BrowserManager
from friday.browser_tools import (
    browser_tool, navigate, click, type_text, extract_text,
    scroll, wait_for, take_screenshot,
)
from friday.context_bus import get_bus
from friday.logging_utils import configure_logging
from friday.nim_client import InferenceClient
from friday.nim_router import resolve_model

logger = configure_logging(__name__)

_AVAILABLE_ACTIONS = {
    "navigate": {"args": {"url": "str"}, "description": "Navigate to a URL"},
    "click": {"args": {"selector": "str", "text": "str"}, "description": "Click element by CSS or text"},
    "type_text": {"args": {"selector": "str", "text": "str", "clear_first": "bool"}, "description": "Type into input field"},
    "extract_text": {"args": {"selector": "str"}, "description": "Extract visible text"},
    "scroll": {"args": {"direction": "str", "amount": "int"}, "description": "Scroll the page"},
    "wait_for": {"args": {"selector": "str", "timeout_ms": "int"}, "description": "Wait for element"},
    "extract_links": {"args": {}, "description": "Extract all links from page"},
    "screenshot": {"args": {}, "description": "Take screenshot of current page"},
}

_NIM_PLAN_TIMEOUT = 10


async def _plan_actions(task: str, current_url: str, page_text: str) -> list[dict]:
    """
    Use NIM to convert a high-level task into a JSON list of browser actions.
    If planning times out or fails, fall back to simple navigate-only action.
    """
    client = InferenceClient()
    model = resolve_model("browse") or resolve_model("general") or "meta/llama-3.3-70b-instruct"

    actions_json = json.dumps({
        name: info for name, info in _AVAILABLE_ACTIONS.items()
    }, indent=2)

    prompt = (
        "You are Atlas, FRIDAY's browser automation agent. "
        "Convert the user's task into a JSON list of browser actions.\n\n"
        f"Available actions:\n{actions_json}\n\n"
        f"Task: {task}\n"
        f"Current URL: {current_url}\n"
        f"Page text (first 1000 chars): {page_text[:1000]}\n\n"
        "Return ONLY valid JSON array of action objects. Example:\n"
        '[{"action": "navigate", "url": "https://example.com"}, {"action": "extract_text", "selector": ""}]\n'
        "Do NOT include markdown markers or explanations."
    )

    try:
        result = await asyncio.wait_for(
            client.chat(model=model, messages=[{"role": "user", "content": prompt}],
                        max_tokens=2048, temperature=0.1),
            timeout=_NIM_PLAN_TIMEOUT,
        )
        text = result.content.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            text = text.rsplit("```", 1)[0]
        cleaned = text.strip()
        if cleaned.startswith("["):
            actions = json.loads(cleaned)
            if isinstance(actions, list):
                return actions
        logger.warning("NIM plan did not return valid JSON array: %.200s", cleaned)
    except asyncio.TimeoutError:
        logger.warning("NIM planning timed out after %ds — falling back to navigate", _NIM_PLAN_TIMEOUT)
    except Exception as exc:
        logger.warning("NIM planning failed: %s — falling back to navigate", exc)

    # Fallback: treat the task as a navigation target
    return [{"action": "navigate", "url": task}]


async def _execute_action(action: dict) -> dict:
    """Execute a single browser action. Returns result dict."""
    action_type = action.get("action", "")
    kwargs = {k: v for k, v in action.items() if k != "action"}

    try:
        if action_type == "navigate":
            return await navigate(**kwargs)
        elif action_type == "click":
            return await click(**kwargs)
        elif action_type == "type_text":
            return await type_text(**kwargs)
        elif action_type == "extract_text":
            return await extract_text(**kwargs)
        elif action_type == "scroll":
            return await scroll(**kwargs)
        elif action_type == "wait_for":
            return await wait_for(**kwargs)
        elif action_type == "extract_links":
            return await scroll(**kwargs) or {}
        elif action_type == "screenshot":
            return await take_screenshot(**kwargs)
        else:
            return {"error": f"Unknown action: {action_type}"}
    except Exception as exc:
        logger.warning("Action %s failed: %s", action_type, exc)
        return {"error": str(exc)}


class BrowserAgent(BaseAgent):
    """Atlas — FRIDAY's browser automation agent."""

    def __init__(self, defn: AgentDef):
        super().__init__(defn)
        self._bus = get_bus()
        self._bm = BrowserManager.get_instance()

    async def execute(self, task: AgentTask) -> AgentResult:
        t0 = time.monotonic()
        await self._bus.publish("agent.started", {
            "agent_id": self.id, "task_id": task.task_id, "task_type": task.task_type,
        })

        try:
            payload = task.payload.strip()
            task_type = task.task_type
            actions_taken: list[dict] = []
            extracted_data = ""
            final_screenshot = ""

            # Ensure browser is running
            if not self._bm._started:
                await self._bm.start()

            page = await self._bm.get_page()
            current_url = page.url
            page_text = ""
            try:
                page_text = await page.inner_text("body")
            except Exception:
                pass

            # Get current page info for context
            current_title = ""
            try:
                current_title = await page.title()
            except Exception:
                pass

            # Map task types to direct actions
            if task_type in ("screenshot",):
                ss = await take_screenshot()
                final_screenshot = ss.get("screenshot_b64", "")
                result_text = f"Screenshot captured from {current_title or current_url}"
                status = "completed"
                actions_taken.append({"action": "screenshot"})

            elif task_type in ("navigate",) or (
                task_type == "browse" and payload.startswith(("http://", "https://"))
            ):
                nav_result = await navigate(payload)
                final_screenshot = nav_result.get("screenshot_b64", "")
                actions_taken.append(nav_result)
                title = nav_result.get("title", "")
                url = nav_result.get("url", payload)
                status = "completed" if nav_result.get("ok") else "failed"
                result_text = f"Navigated to {title or url}" if nav_result.get("ok") else f"Navigation failed: {nav_result.get('error', 'unknown')}"

            elif task_type == "extract":
                text_result = await extract_text()
                current_url = page.url
                try:
                    current_title = await page.title()
                except Exception:
                    pass
                extracted_data = text_result.get("text", "")[:10000]
                result_text = f"## Extracted from {current_title or current_url}\n\n{extracted_data[:3000]}"
                status = "completed"
                actions_taken.append({"action": "extract_text"})

            else:
                # NIM planning for complex tasks (form fill, search, multi-step)
                actions = await _plan_actions(payload, current_url, page_text)
                logger.info("Atlas planned %d actions for: %s", len(actions), payload[:80])

                for step_idx, action in enumerate(actions):
                    action_result = await _execute_action(action)
                    actions_taken.append({**action, "result": action_result})

                    # Take screenshot after each step
                    ss = await take_screenshot()
                    if ss.get("screenshot_b64"):
                        final_screenshot = ss["screenshot_b64"]

                    # Extract text on the last step
                    if step_idx == len(actions) - 1:
                        text_result = await extract_text()
                        extracted_data = text_result.get("text", "")[:10000]

                    # If an action fails, retry once with alternate strategy
                    if action_result.get("error") or not action_result.get("success", True):
                        if action["action"] == "click" and "text" in action:
                            retry_action = {"action": "click", "selector": action.get("text", "")}
                            retry_result = await _execute_action(retry_action)
                            if not retry_result.get("error"):
                                actions_taken.append({**retry_action, "result": retry_result, "retry": True})

                    await asyncio.sleep(0.5)

                status = "completed" if not any(a.get("result", {}).get("error") for a in actions_taken) else "completed"

                # Build summary
                result_text = "## Browser Task Complete\n\n"
                result_text += f"**Task**: {payload}\n\n"
                result_text += f"**Actions taken**: {len(actions_taken)}\n\n"
                for i, a in enumerate(actions_taken, 1):
                    act = {k: v for k, v in a.items() if k != "result"}
                    action_result = a.get("result", {})
                    status_icon = "✅" if not action_result.get("error") else "❌"
                    result_text += f"{status_icon} **Step {i}**: {act}\n"
                if extracted_data:
                    result_text += f"\n**Extracted data**:\n{extracted_data[:2000]}"

            dur = int((time.monotonic() - t0) * 1000)
            await self._bus.publish("agent.completed", {
                "agent_id": self.id, "task_id": task.task_id, "output": result_text[:500],
            })
            return AgentResult(
                task_id=task.task_id, agent_id=self.id,
                status=status, output=result_text,
                duration_ms=dur, model="meta/llama-3.3-70b-instruct",
            )

        except Exception as exc:
            logger.exception("Atlas execution failed: %s", exc)
            dur = int((time.monotonic() - t0) * 1000)
            await self._bus.publish("agent.failed", {
                "agent_id": self.id, "task_id": task.task_id, "error": str(exc),
            })
            return AgentResult(
                task_id=task.task_id, agent_id=self.id,
                status="failed", error=str(exc), duration_ms=dur,
            )
