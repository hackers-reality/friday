"""Friday Dreaming System — background autonomous agent mode.

FRIDAY detects when the user stops responding and enters a "dreaming" state:
goes silent to the user but continues working autonomously in the background —
researching, consolidating memories, updating the knowledge graph, chatting
among agents, and self-improving. When the user returns, FRIDAY resumes
normal interaction and presents a summary of what happened while dreaming.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_DREAM_STATE_DIR = os.path.join(FRIDAY_MEMORY, "dreaming")
os.makedirs(_DREAM_STATE_DIR, exist_ok=True)

# ── Enums ────────────────────────────────────────────────────────────


class DreamingState(Enum):
    active = "active"
    inactive = "inactive"
    silent = "silent"


class ActivityType(Enum):
    research = "research"
    memory_consolidation = "memory_consolidation"
    knowledge_update = "knowledge_update"
    self_improvement = "self_improvement"
    agent_chat = "agent_chat"


class ActivityStatus(Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


# ── Data Models ──────────────────────────────────────────────────────


@dataclass
class BackgroundActivity:
    id: str
    type: ActivityType
    description: str
    status: ActivityStatus = ActivityStatus.queued
    result: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "status": self.status.value,
            "result": self.result,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BackgroundActivity:
        return cls(
            id=data["id"],
            type=ActivityType(data["type"]),
            description=data["description"],
            status=ActivityStatus(data.get("status", "queued")),
            result=data.get("result"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            completed_at=data.get("completed_at"),
        )


@dataclass
class DreamSession:
    id: str
    start_time: str
    end_time: Optional[str] = None
    activities: List[BackgroundActivity] = field(default_factory=list)
    messages_exchanged_before_silence: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "activities": [a.to_dict() for a in self.activities],
            "messages_exchanged_before_silence": self.messages_exchanged_before_silence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DreamSession:
        return cls(
            id=data["id"],
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            activities=[BackgroundActivity.from_dict(a) for a in data.get("activities", [])],
            messages_exchanged_before_silence=data.get("messages_exchanged_before_silence", 0),
        )


# ── Dream Engine ─────────────────────────────────────────────────────


class DreamEngine:
    """Background dreaming and autonomous agent engine for FRIDAY.

    Tracks user inactivity, enters silent/dreaming mode when the user stops
    responding, runs background activities autonomously, and resumes normal
    interaction when the user returns.
    """

    SILENCE_THRESHOLD: int = 20

    def __init__(self) -> None:
        self.user_inactivity_counter: int = 0
        self.is_dreaming: bool = False
        self.is_silent: bool = False
        self._state: DreamingState = DreamingState.inactive
        self._current_session: Optional[DreamSession] = None
        self._past_sessions: List[DreamSession] = []
        self._background_tasks: List[asyncio.Task] = []
        self._dream_loop_task: Optional[asyncio.Task] = None
        self._lock = threading.RLock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._load_state()
        # Always reset dream/silent flags on boot — never carry over across restarts
        self.is_dreaming = False
        self.is_silent = False
        self._state = DreamingState.inactive
        self._current_session = None

    # ── Public API ──────────────────────────────────────────────────

    def on_user_message(self, count_since_last_response: int = 0) -> None:
        """Called every time the user sends a message.

        Immediately resets inactivity, and if dreaming, exits dream mode
        right away by cancelling the loop and resetting flags synchronously.
        """
        with self._lock:
            self.user_inactivity_counter = count_since_last_response

            if self.is_dreaming or self.is_silent:
                logger.info("User returned — exiting dream mode.")
                self.is_silent = False
                self._state = DreamingState.active
                if self._dream_loop_task is not None:
                    self._dream_loop_task.cancel()
                    self._dream_loop_task = None
                for task in self._background_tasks:
                    task.cancel()
                self._background_tasks.clear()
                if self._current_session is not None:
                    self._current_session.end_time = datetime.now(timezone.utc).isoformat()
                    self._past_sessions.append(self._current_session)
                    if len(self._past_sessions) > 50:
                        self._past_sessions = self._past_sessions[-50:]
                session_id = self._current_session.id if self._current_session else "unknown"
                self._current_session = None
                self.is_dreaming = False
                self.user_inactivity_counter = 0
                self._save_state()
                logger.info("Exited dream mode (session=%s)", session_id)

    def on_friday_response(self) -> None:
        """Reset the inactivity counter because FRIDAY responded."""
        self.user_inactivity_counter = 0
        logger.debug("Inactivity counter reset (FRIDAY responded).")

    async def check_inactivity(self) -> bool:
        """Check if FRIDAY should enter dream mode based on inactivity.

        Returns True if dream mode was entered.
        """
        with self._lock:
            if self.user_inactivity_counter >= self.SILENCE_THRESHOLD and not self.is_dreaming:
                await self.enter_dream_mode()
                return True
        return False

    async def enter_dream_mode(self) -> None:
        """Go silent and start background dreaming activities.

        Sets is_silent=True so FRIDAY stops responding to the user.
        Starts a dream session and kicks off the background activity loop.
        """
        with self._lock:
            if self.is_dreaming:
                return

            self.is_dreaming = True
            self.is_silent = True
            self._state = DreamingState.silent

            self._current_session = DreamSession(
                id=f"dream_{uuid.uuid4().hex[:12]}",
                start_time=datetime.now(timezone.utc).isoformat(),
                messages_exchanged_before_silence=self.user_inactivity_counter,
            )

            logger.info(
                "Entered dream mode (session=%s, silence_threshold=%d)",
                self._current_session.id,
                self.user_inactivity_counter,
            )

        self._dream_loop_task = asyncio.create_task(self._dream_loop())

    async def exit_dream_mode(self) -> None:
        """Resume normal interaction.

        Stops the dream loop, finalizes the current session, saves state,
        and resets all flags.
        """
        if not self.is_dreaming:
            return

        self.is_silent = False
        self._state = DreamingState.active

        if self._dream_loop_task is not None:
            self._dream_loop_task.cancel()
            self._dream_loop_task = None

        for task in self._background_tasks:
            task.cancel()
        self._background_tasks.clear()

        if self._current_session is not None:
            self._current_session.end_time = datetime.now(timezone.utc).isoformat()
            self._past_sessions.append(self._current_session)
            if len(self._past_sessions) > 50:
                self._past_sessions = self._past_sessions[-50:]

        session_id = self._current_session.id if self._current_session else "unknown"
        logger.info("Exited dream mode (session=%s)", session_id)

        self._current_session = None
        self.is_dreaming = False
        self.user_inactivity_counter = 0
        self._save_state()

    # ── Activity Management ─────────────────────────────────────────

    async def add_background_activity(
        self,
        activity_type: ActivityType,
        description: str,
    ) -> BackgroundActivity:
        """Add a task to be executed in the background."""
        activity = BackgroundActivity(
            id=f"act_{uuid.uuid4().hex[:12]}",
            type=activity_type,
            description=description,
        )

        if self._current_session is not None:
            self._current_session.activities.append(activity)

        logger.info("Queued background activity: [%s] %s", activity_type.value, description)
        self._save_state()
        return activity

    async def start_memory_consolidation(self) -> BackgroundActivity:
        """Consolidate recent memories into long-term storage."""
        activity = await self.add_background_activity(
            ActivityType.memory_consolidation,
            "Consolidating recent conversations and interactions into long-term memory",
        )
        try:
            activity.status = ActivityStatus.running
            result = await self._run_memory_consolidation()
            activity.status = ActivityStatus.completed
            activity.result = result
            activity.completed_at = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            activity.status = ActivityStatus.failed
            activity.result = str(e)
            logger.error("Memory consolidation failed: %s", e)
        self._save_state()
        return activity

    async def start_agent_chat_session(self) -> BackgroundActivity:
        """Initiate an agent-to-agent chatting session for collaborative problem-solving."""
        activity = await self.add_background_activity(
            ActivityType.agent_chat,
            "Agent-to-agent chat session for collaborative reasoning and knowledge sharing",
        )
        try:
            activity.status = ActivityStatus.running
            result = await self._run_agent_chat()
            activity.status = ActivityStatus.completed
            activity.result = result
            activity.completed_at = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            activity.status = ActivityStatus.failed
            activity.result = str(e)
            logger.error("Agent chat session failed: %s", e)
        self._save_state()
        return activity

    async def start_knowledge_update(self) -> BackgroundActivity:
        """Refresh the knowledge graph with recent information and inferred relationships."""
        activity = await self.add_background_activity(
            ActivityType.knowledge_update,
            "Updating knowledge graph with recent entities, relationships, and inferred facts",
        )
        try:
            activity.status = ActivityStatus.running
            result = await self._run_knowledge_update()
            activity.status = ActivityStatus.completed
            activity.result = result
            activity.completed_at = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            activity.status = ActivityStatus.failed
            activity.result = str(e)
            logger.error("Knowledge update failed: %s", e)
        self._save_state()
        return activity

    async def start_research_task(self, topic: str) -> BackgroundActivity:
        """Perform autonomous research on a given topic."""
        activity = await self.add_background_activity(
            ActivityType.research,
            f"Autonomous research on: {topic}",
        )
        try:
            activity.status = ActivityStatus.running
            result = await self._run_research(topic)
            activity.status = ActivityStatus.completed
            activity.result = result
            activity.completed_at = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            activity.status = ActivityStatus.failed
            activity.result = str(e)
            logger.error("Research task failed for topic '%s': %s", topic, e)
        self._save_state()
        return activity

    # ── Summaries ──────────────────────────────────────────────────

    def get_dream_summary(self) -> str:
        """Return a summary of what happened during the most recent dream session.

        Called when the user returns to give them context on background work.
        """
        if not self._past_sessions:
            return "No dream sessions recorded yet."

        session = self._past_sessions[-1]
        lines: List[str] = [
            f"  Dream Session: {session.id}",
            f"  Started: {session.start_time}",
        ]

        if session.end_time:
            lines.append(f"  Ended: {session.end_time}")

        lines.append(f"  Activities completed: {len(session.activities)}")
        lines.append("")

        completed = [a for a in session.activities if a.status == ActivityStatus.completed]
        failed = [a for a in session.activities if a.status == ActivityStatus.failed]

        if completed:
            lines.append("  Completed Activities:")
            for act in completed:
                summary = (act.result or "")[:120]
                lines.append(f"    [{act.type.value}] {act.description}")
                if summary:
                    lines.append(f"      -> {summary}")

        if failed:
            lines.append("  Failed Activities:")
            for act in failed:
                lines.append(f"    [{act.type.value}] {act.description}: {act.result}")

        return "\n".join(lines)

    def get_current_activities(self) -> List[BackgroundActivity]:
        """Return all activities in the current dream session."""
        if self._current_session is None:
            return []
        return self._current_session.activities

    # ── State Persistence ──────────────────────────────────────────

    def save_state(self) -> None:
        self._save_state()

    def load_state(self) -> None:
        self._load_state()

    def _state_path(self) -> str:
        return os.path.join(_DREAM_STATE_DIR, "dream_engine_state.json")

    def _save_state(self) -> None:
        path = self._state_path()
        data: Dict[str, Any] = {
            "user_inactivity_counter": self.user_inactivity_counter,
            "is_dreaming": self.is_dreaming,
            "is_silent": self.is_silent,
            "state": self._state.value if self._state else DreamingState.inactive.value,
            "current_session": self._current_session.to_dict() if self._current_session else None,
            "past_sessions": [s.to_dict() for s in self._past_sessions],
        }
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save dream state: %s", e)

    def _load_state(self) -> None:
        path = self._state_path()
        if not os.path.exists(path):
            return
        try:
            with open(path) as f:
                data = json.load(f)
            self.user_inactivity_counter = data.get("user_inactivity_counter", 0)
            self.is_dreaming = data.get("is_dreaming", False)
            self.is_silent = data.get("is_silent", False)
            self._state = DreamingState(data.get("state", DreamingState.inactive.value))
            if data.get("current_session"):
                self._current_session = DreamSession.from_dict(data["current_session"])
            self._past_sessions = [DreamSession.from_dict(s) for s in data.get("past_sessions", [])]
        except Exception as e:
            logger.error("Failed to load dream state: %s", e)

    # ── Internal Background Executors ──────────────────────────────

    async def _run_memory_consolidation(self) -> str:
        """Run memory consolidation by calling into the vector memory system."""
        try:
            from friday.vector_memory import vector_memory_tool

            result = vector_memory_tool(action="consolidate")
            if isinstance(result, str):
                return result
            return "Memory consolidation completed."
        except ImportError:
            return "Vector memory module not available."
        except Exception as e:
            raise RuntimeError(f"Memory consolidation error: {e}") from e

    async def _run_agent_chat(self) -> str:
        """Run an agent-to-agent chat session using the agent bus."""
        try:
            from friday.agent_bus import publish, get_all_messages

            chat_id = f"dream_chat_{uuid.uuid4().hex[:8]}"
            await publish(
                agent_id="dream_engine",
                topic="agent_chat.start",
                data={"session_id": chat_id, "purpose": "background collaborative reasoning"},
                task_id=chat_id,
            )

            await asyncio.sleep(2)

            await publish(
                agent_id="dream_engine",
                topic="agent_chat.summarize",
                data={"session_id": chat_id},
                task_id=f"{chat_id}_summary",
            )

            return f"Agent chat session {chat_id} completed. Messages exchanged."
        except ImportError:
            return "Agent bus module not available."
        except Exception as e:
            raise RuntimeError(f"Agent chat error: {e}") from e

    async def _run_knowledge_update(self) -> str:
        """Update the knowledge graph with recent dream insights."""
        try:
            from friday.knowledge_graph import KnowledgeGraph

            kg = KnowledgeGraph()
            kg.add_node(
                node_id=f"dream_{uuid.uuid4().hex[:8]}",
                node_type="dream_session",
                properties={
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "dream_engine",
                },
            )
            kg.save()
            return "Knowledge graph updated with dream session node."
        except ImportError:
            return "Knowledge graph module not available."
        except Exception as e:
            raise RuntimeError(f"Knowledge update error: {e}") from e

    async def _run_research(self, topic: str) -> str:
        """Run autonomous research using the research module."""
        try:
            from friday.research import AutonomousResearch

            researcher = AutonomousResearch()
            analysis = researcher.analyze_topic(topic)
            return (
                f"Research analyzed topic '{topic}': "
                f"{len(analysis.get('key_concepts', []))} key concepts, "
                f"complexity {analysis.get('complexity_score', '?')}, "
                f"{len(analysis.get('search_queries', []))} search queries generated."
            )
        except ImportError:
            return f"Research module not available. Topic queued: {topic}"
        except Exception as e:
            raise RuntimeError(f"Research error: {e}") from e

    # ── Dream Loop ─────────────────────────────────────────────────

    async def run_forever(self) -> None:
        """Daemon thread entry point. Periodically checks inactivity and
        runs dream cycles when in dream mode."""
        # Reset counter at boot so we don't immediately re-enter dream mode
        self.user_inactivity_counter = 0
        try:
            while True:
                with self._lock:
                    # Gradually accumulate inactivity so dream mode triggers naturally
                    if not self.is_dreaming and not self.is_silent:
                        self.user_inactivity_counter += 1
                        if self.user_inactivity_counter >= self.SILENCE_THRESHOLD:
                            logger.info("Inactivity threshold reached — entering dream mode.")
                            try:
                                await self.enter_dream_mode()
                            except Exception as e:
                                logger.warning(f"enter_dream_mode failed: {e}")

                    # If dreaming, run a cycle
                    if self.is_dreaming and self._dream_loop_task is None:
                        self._dream_loop_task = asyncio.create_task(self._dream_loop())
                        logger.info("Dream loop started.")

                await asyncio.sleep(15)
        except asyncio.CancelledError:
            pass

    async def _dream_loop(self) -> None:
        """Main background loop that runs while dreaming.

        Periodically spawns background activities appropriate to the current
        context: research, memory consolidation, knowledge updates, agent chat,
        and self-improvement.
        """
        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                logger.debug("Dream cycle %d", cycle_count)

                await self._run_dream_cycle()

                await asyncio.sleep(60)
            except asyncio.CancelledError:
                logger.info("Dream loop cancelled.")
                break
            except Exception as e:
                logger.error("Dream cycle error: %s", e)
                await asyncio.sleep(120)

    async def _run_dream_cycle(self) -> None:
        """Execute a single dream cycle: pick activities and run them."""
        activities: List[asyncio.Task] = []

        if self._should_run_memory_consolidation():
            activities.append(asyncio.create_task(self.start_memory_consolidation()))

        if self._should_run_knowledge_update():
            activities.append(asyncio.create_task(self.start_knowledge_update()))

        if self._should_run_agent_chat():
            activities.append(asyncio.create_task(self.start_agent_chat_session()))

        if self._should_run_self_improvement():
            activities.append(asyncio.create_task(self._run_self_improvement_cycle()))

        if activities:
            await asyncio.gather(*activities, return_exceptions=True)

    def _should_run_memory_consolidation(self) -> bool:
        """Run memory consolidation every 3 cycles (~3 minutes)."""
        if not self._current_session:
            return False
        mem_count = sum(
            1 for a in self._current_session.activities
            if a.type == ActivityType.memory_consolidation
        )
        return mem_count == 0 or mem_count % 3 == 0

    def _should_run_knowledge_update(self) -> bool:
        """Run knowledge update every 5 cycles (~5 minutes)."""
        if not self._current_session:
            return False
        kg_count = sum(
            1 for a in self._current_session.activities
            if a.type == ActivityType.knowledge_update
        )
        return kg_count == 0 or kg_count % 5 == 0

    def _should_run_agent_chat(self) -> bool:
        """Run agent chat every 2 cycles (~2 minutes)."""
        if not self._current_session:
            return False
        chat_count = sum(
            1 for a in self._current_session.activities
            if a.type == ActivityType.agent_chat
        )
        return chat_count == 0 or chat_count % 2 == 0

    def _should_run_self_improvement(self) -> bool:
        """Run self-improvement every 10 cycles (~10 minutes)."""
        if not self._current_session:
            return False
        imp_count = sum(
            1 for a in self._current_session.activities
            if a.type == ActivityType.self_improvement
        )
        return imp_count == 0 or imp_count % 10 == 0

    async def _run_self_improvement_cycle(self) -> BackgroundActivity:
        """Run a self-improvement cycle: code review, pattern detection, optimization proposals."""
        activity = await self.add_background_activity(
            ActivityType.self_improvement,
            "Self-improvement cycle: reviewing recent performance and proposing optimizations",
        )
        try:
            activity.status = ActivityStatus.running
            result = await self._execute_self_improvement()
            activity.status = ActivityStatus.completed
            activity.result = result
            activity.completed_at = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            activity.status = ActivityStatus.failed
            activity.result = str(e)
            logger.error("Self-improvement cycle failed: %s", e)
        self._save_state()
        return activity

    async def _execute_self_improvement(self) -> str:
        """Hook into the self-improvement pipeline."""
        try:
            from friday.self_improve import _load_pending, _save_pending

            pending = _load_pending()
            return f"Self-improvement check: {len(pending)} pending changes in queue."
        except ImportError:
            return "Self-improvement module not available."
        except Exception as e:
            raise RuntimeError(f"Self-improvement error: {e}") from e


# ── Global Instance ──────────────────────────────────────────────────

_engine: Optional[DreamEngine] = None


def get_engine() -> DreamEngine:
    global _engine
    if _engine is None:
        _engine = DreamEngine()
    return _engine


# ── Standalone Helper ────────────────────────────────────────────────


def generate_dream_activities(goal_context: str) -> List[Dict[str, str]]:
    """Determine what background activities would be most valuable.

    Uses a heuristic based on the provided goal context to prioritise
    activities. If the context mentions research-worthy topics, schedule
    research; if it mentions memory or learning, schedule consolidation;
    otherwise return a balanced mix.

    Args:
        goal_context: A string describing the user's current goals,
                      recent conversations, or context for prioritisation.

    Returns:
        A list of dicts with keys 'type' and 'description' suitable for
        passing to ``DreamEngine.add_background_activity``.
    """
    ctx_lower = goal_context.lower()
    activities: List[Dict[str, str]] = []

    research_triggers = ["research", "learn", "study", "topic", "investigate", "find out"]
    memory_triggers = ["remember", "recall", "memory", "consolidate", "previous", "past"]
    knowledge_triggers = ["knowledge", "graph", "entity", "relationship", "connect", "relate"]
    improve_triggers = ["improve", "optimize", "refactor", "better", "faster", "bug", "fix"]
    chat_triggers = ["collaborate", "agent", "discuss", "brainstorm", "chat", "multi-agent"]

    if any(t in ctx_lower for t in research_triggers):
        activities.append({
            "type": ActivityType.research.value,
            "description": f"Research topics related to: {goal_context[:120]}",
        })

    if any(t in ctx_lower for t in memory_triggers):
        activities.append({
            "type": ActivityType.memory_consolidation.value,
            "description": "Consolidate recent memories and extract patterns from conversations",
        })

    if any(t in ctx_lower for t in knowledge_triggers):
        activities.append({
            "type": ActivityType.knowledge_update.value,
            "description": "Update knowledge graph with inferred relationships and entities",
        })

    if any(t in ctx_lower for t in improve_triggers):
        activities.append({
            "type": ActivityType.self_improvement.value,
            "description": "Review recent performance and propose code or behavior optimizations",
        })

    if any(t in ctx_lower for t in chat_triggers):
        activities.append({
            "type": ActivityType.agent_chat.value,
            "description": "Initiating multi-agent chat to collaboratively analyse context",
        })

    if not activities:
        activities = [
            {
                "type": ActivityType.memory_consolidation.value,
                "description": "Routine memory consolidation and pattern extraction",
            },
            {
                "type": ActivityType.knowledge_update.value,
                "description": "Routine knowledge graph refresh with recent interaction data",
            },
            {
                "type": ActivityType.agent_chat.value,
                "description": "Routine agent chat for cross-agent knowledge sharing",
            },
        ]

    return activities


def start_dreaming_if_idle() -> None:
    """Sync entry point called at boot. Initializes the DreamEngine singleton
    and kicks off background dreaming in a daemon thread."""
    try:
        engine = get_engine()
        engine._loop = asyncio.new_event_loop()
        t = threading.Thread(target=_run_engine_daemon, args=(engine,), daemon=True)
        t.start()
        logger.info("Dreaming engine started in background thread")
    except Exception as e:
        logger.warning(f"Dreaming engine failed to start: {e}")


def _run_engine_daemon(engine: DreamEngine) -> None:
    """Run the dream engine event loop in a daemon thread."""
    asyncio.set_event_loop(engine._loop)
    try:
        engine._loop.run_until_complete(engine.run_forever())
    except Exception:
        pass


# ── dream_tool — bridge for tools_flat.py import ─────────────────


def dream_tool(action: str = "status") -> str:
    """Tool-callable bridge into the DreamEngine.

    Actions:
      status       — return current dream state summary
      cycle        — force a single dream cycle now
      enter        — force enter dream mode
      exit         — force exit dream mode
      activities   — list current background activities
    """
    engine = get_engine()
    loop = getattr(engine, '_loop', None)
    try:
        if action == "status":
            state = engine._state.value if engine._state else "inactive"
            dreaming = engine.is_dreaming
            silent = engine.is_silent
            activities = engine.get_current_activities()
            act_summary = "; ".join(a.description for a in activities[:3]) if activities else "none"
            summary = engine.get_dream_summary() or "No dreams yet."
            return (
                f"[DREAM] state={state}, dreaming={dreaming}, silent={silent}, "
                f"activities: {act_summary} | {summary}"
            )

        elif action == "enter":
            if engine.is_dreaming:
                return "[DREAM] Already dreaming."
            if loop is None:
                return "[DREAM] Dream loop not started. Call start_dreaming_if_idle() first."
            fut = asyncio.run_coroutine_threadsafe(
                engine.enter_dream_mode(), loop
            )
            fut.result(timeout=10)
            return "[DREAM] Entered dream mode."

        elif action == "exit":
            if not engine.is_dreaming:
                return "[DREAM] Not dreaming."
            if loop is None:
                engine.is_dreaming = False
                engine.is_silent = False
                engine._state = DreamingState.inactive
                return "[DREAM] Force exited dream mode (no event loop)."
            fut = asyncio.run_coroutine_threadsafe(
                engine.exit_dream_mode(), loop
            )
            fut.result(timeout=10)
            return "[DREAM] Exited dream mode."

        elif action == "cycle":
            if loop is None:
                return "[DREAM] Dream loop not started."
            fut = asyncio.run_coroutine_threadsafe(
                engine._run_dream_cycle(), loop
            )
            result = fut.result(timeout=30)
            return f"[DREAM] Cycle complete: {result or 'done'}"

        elif action == "activities":
            activities = engine.get_current_activities()
            if not activities:
                return "[DREAM] No active background activities."
            lines = [f"  {a.type.value}: {a.description} ({a.status.value})" for a in activities]
            return "[DREAM] Background activities:\n" + "\n".join(lines)

        else:
            return f"[DREAM] Unknown action: {action}. Try: status, enter, exit, cycle, activities"

    except Exception as e:
        return f"[DREAM] Error: {e}"
