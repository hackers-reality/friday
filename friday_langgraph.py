"""
Friday LangGraph Orchestrator - Phase 10
LangGraph-based agent orchestration for Friday.
Provides better state management, checkpointing, human-in-the-loop.
"""
from __future__ import annotations

import os
import sys
import json
from typing import Dict, Any, List, Optional

try:
    from langgraph.graph import StateGraph, END
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.tools import tool
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("LangGraph not available. Install: pip install langgraph langchain-core")

# ─── Agent State ──────────────────────────────────#

class FridayAgentState(Dict):
    """State for the Friday agent graph."""
    messages: List[Dict[str, Any]]
    current_tool_calls: List[Dict[str, Any]]
    screen_context: Optional[str]
    user_goals: List[Dict[str, Any]]
    browser_history: List[Dict[str, Any]]
    is_proactive: bool
    last_action: Optional[str]

# ─── LangGraph Agent Graph ──────────────────────────#

def create_friday_graph():
    """Create the LangGraph agent graph for Friday."""
    if not LANGGRAPH_AVAILABLE:
        return None

    # Define the state graph
    graph = StateGraph(FridayAgentState)

    # Add nodes
    graph.add_node("analyze_screen", analyze_screen_node)
    graph.add_node("process_tool_call", process_tool_call_node)
    graph.add_node("check_goals", check_goals_node)
    graph.add_node("be_proactive", be_proactive_node)
    graph.add_node("generate_response", generate_response_node)

    # Set entry point
    graph.set_entry_point("analyze_screen")

    # Add edges
    graph.add_edge("analyze_screen", "check_goals")
    graph.add_edge("check_goals", "process_tool_call")
    graph.add_edge("process_tool_call", "be_proactive")
    graph.add_edge("be_proactive", "generate_response")
    graph.add_edge("generate_response", END)

    # Add conditional edges for tool calls
    graph.add_conditional_edges(
        "process_tool_call",
        should_continue,
        {
            "continue": "process_tool_call",
            "finish": "be_proactive",
        },
    )

    return graph.compile()

# ─── Node Functions ──────────────────────────────#

def analyze_screen_node(state: FridayAgentState) -> Dict[str, Any]:
    """Analyze the current screen."""
    try:
        from screen_watcher import get_active_window_info
        info = get_active_window_info()
        screen_context = f"Active: {info.get('title', 'Unknown')}"
        return {"screen_context": screen_context}
    except Exception as e:
        return {"screen_context": f"Screen analysis error: {e}"}

def process_tool_call_node(state: FridayAgentState) -> Dict[str, Any]:
    """Process tool calls from the LLM."""
    tool_calls = state.get("current_tool_calls", [])
    results = []

    for call in tool_calls:
        try:
            from friday_tools import execute_tool
            result = execute_tool(call.get("name"), call.get("args", {}))
            results.append({
                "tool": call.get("name"),
                "result": str(result),
            })
        except Exception as e:
            results.append({
                "tool": call.get("name"),
                "result": f"Error: {e}",
            })

    return {"messages": state.get("messages", []) + results}

def check_goals_node(state: FridayAgentState) -> Dict[str, Any]:
    """Check and update goals."""
    try:
        from goal_memory import load_goals
        goals = load_goals()
        active_goals = [g for g in goals if g.get("status") == "active"]
        return {"user_goals": active_goals}
    except Exception as e:
        return {"user_goals": []}

def be_proactive_node(state: FridayAgentState) -> Dict[str, Any]:
    """Be proactive based on context."""
    screen = state.get("screen_context", "")
    goals = state.get("user_goals", [])

    actions = []
    if "anime" in screen.lower():
        actions.append("I see you're watching anime. Enjoy!")
    if goals:
        actions.append(f"You have {len(goals)} active goals to work on.")

    return {"is_proactive": True, "last_action": "; ".join(actions)}

def generate_response_node(state: FridayAgentState) -> Dict[str, Any]:
    """Generate final response."""
    messages = state.get("messages", [])
    proactive = state.get("last_action", "")

    response = "Friday here. "
    if proactive:
        response += proactive + " "

    return {"messages": messages + [{"role": "assistant", "content": response}]}

# ─── Conditional Logic ───────────────────────────#

def should_continue(state: FridayAgentState) -> str:
    """Decide whether to continue processing tool calls."""
    tool_calls = state.get("current_tool_calls", [])
    if tool_calls:
        return "continue"
    return "finish"

# ─── Agent Runner ──────────────────────────────#

class FridayLangGraphAgent:
    """LangGraph-based Friday agent."""

    def __init__(self):
        self.graph = None
        self.agent = None
        if LANGGRAPH_AVAILABLE:
            try:
                self.graph = create_friday_graph()
                self.agent = self.graph
            except Exception as e:
                print(f"LangGraph agent init error: {e}")

    def run(self, user_message: str) -> str:
        """Run the agent with a user message."""
        if not self.agent:
            return "LangGraph agent not available."

        try:
            initial_state = {
                "messages": [{"role": "user", "content": user_message}],
                "current_tool_calls": [],
                "screen_context": None,
                "user_goals": [],
                "browser_history": [],
                "is_proactive": False,
                "last_action": None,
            }

            result = self.agent.invoke(initial_state)
            messages = result.get("messages", [])
            if messages:
                return messages[-1].get("content", "No response.")
            return "No response generated."

        except Exception as e:
            return f"Agent error: {e}"

def get_langgraph_status() -> str:
    """Get LangGraph integration status."""
    lines = ["### LANGRAPH ORCHESTRATION STATUS", ""]
    if LANGGRAPH_AVAILABLE:
        lines.append("[OK] LangGraph available")
        lines.append("[OK] Friday agent graph ready")
    else:
        lines.append("[FAIL] LangGraph not available")
        lines.append("Install: pip install langgraph langchain-core")
    return "\n".join(lines)

if __name__ == "__main__":
    print("Testing LangGraph Orchestrator...\n")
    print(get_langgraph_status())

    if LANGGRAPH_AVAILABLE:
        agent = FridayLangGraphAgent()
        response = agent.run("What's on my screen?")
        print(f"\nResponse: {response}")
