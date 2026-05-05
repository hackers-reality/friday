"""
Friday LangGraph Integration - Phase 1.1
StateGraph with persistent SQLite checkpoints for Friday's agent loop.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional, TypedDict, Annotated

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI

import warnings
warnings.filterwarnings("ignore")


# ─── Agent State Definition ────────────────────────────────────────────────────

class FridayState(TypedDict):
    """State container for Friday's LangGraph agent."""
    messages: Annotated[List, "The conversation messages"]
    user_input: str
    tool_results: Dict[str, Any]
    current_tool: Optional[str]
    needs_tool: bool
    goal_context: Dict[str, Any]
    active_window: str
    vision_context: Optional[str]


# ─── Persistent Checkpoint Setup ──────────────────────────────────────────────

_CHECKPOINT_DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "friday_memory",
    "langgraph_checkpoints.db"
)

def get_checkpointer():
    """Get or create SQLite-based checkpointer for persistent state."""
    os.makedirs(os.path.dirname(_CHECKPOINT_DB), exist_ok=True)
    return SqliteSaver.from_conn_string(_CHECKPOINT_DB)


# ─── Tool Registry for LangGraph ──────────────────────────────────────────────

def register_tools_to_langchain():
    """Convert Friday's tools to LangChain Tool format for LangGraph."""
    import friday_tools as ft
    
    tool_mapping = {
        "stark_doctor": ft.stark_doctor,
        "spotify_play": ft.spotify_play,
        "spotify_pause": ft.spotify_pause,
        "open_app": ft.open_app,
        "web_search": ft.web_search,
        "video_search": ft.video_search,
        "see_screen": ft.see_screen,
        "open_url": ft.open_url,
        "run_cmd": ft.run_cmd,
        "safe_run_cmd": ft.safe_run_cmd,
        "memory_store": ft.memory_store,
        "memory_retrieve": ft.memory_retrieve,
        "get_time": ft.get_time,
        "system_info": ft.system_info,
        "deep_research": ft.deep_research,
        "type_text": ft.type_text,
        "click": ft.click,
        "double_click": ft.double_click,
        "right_click": ft.right_click,
        "move_mouse": ft.move_mouse,
        "drag": ft.drag,
        "hotkey": ft.hotkey,
        "press_key": ft.press_key,
        "scroll": ft.scroll,
        "read_file": ft.read_file,
        "write_file": ft.write_file,
        "list_files": ft.list_files,
        "find_files": ft.find_files,
        "copy_file": ft.copy_file,
        "move_file": ft.move_file,
        "delete_file": ft.delete_file,
        "clipboard_get": ft.clipboard_get,
        "clipboard_set": ft.clipboard_set,
        "climb_codebase": ft.climb_codebase,
        "situational_awareness": ft.situational_awareness,
        "git_ops": ft.git_ops,
        "take_snapshot": ft.take_snapshot,
        "recall_snapshot": ft.recall_snapshot,
    }
    
    tools = []
    for name, func in tool_mapping.items():
        try:
            import inspect
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            
            tool = Tool(
                name=name,
                func=func,
                description=func.__doc__ or f"Execute {name}",
            )
            tools.append(tool)
        except Exception as e:
            print(f"[LangGraph] Failed to register tool {name}: {e}")
    
    return tools


# ─── Graph Nodes ──────────────────────────────────────────────────────────────

def process_input(state: FridayState) -> Dict[str, Any]:
    """Process user input and determine if tools are needed."""
    user_input = state.get("user_input", "")
    
    # Build messages for LLM
    messages = state.get("messages", [])
    
    # Add system instruction
    from friday_live import SYSTEM_INSTRUCTION
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages.insert(0, SystemMessage(content=SYSTEM_INSTRUCTION))
    
    # Add user message
    messages.append(HumanMessage(content=user_input))
    
    return {
        "messages": messages,
        "user_input": user_input,
        "needs_tool": False,
        "current_tool": None,
    }


def call_llm(state: FridayState) -> Dict[str, Any]:
    """Call the LLM to generate a response or tool call."""
    messages = state.get("messages", [])
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    
    if not api_key:
        return {
            "messages": messages + [AIMessage(content="Error: GOOGLE_API_KEY not configured.")],
        }
    
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.1,
            convert_system_message_to_human=True,
        )
        
        # Get tools
        tools = register_tools_to_langchain()
        if tools:
            llm_with_tools = llm.bind_tools(tools)
            response = llm_with_tools.invoke(messages)
        else:
            response = llm.invoke(messages)
        
        messages.append(response)
        
        # Check if tool calls are needed
        needs_tool = bool(response.tool_calls)
        current_tool = response.tool_calls[0]["name"] if needs_tool else None
        
        return {
            "messages": messages,
            "needs_tool": needs_tool,
            "current_tool": current_tool,
        }
    except Exception as e:
        error_msg = AIMessage(content=f"LLM Error: {str(e)}")
        return {
            "messages": messages + [error_msg],
            "needs_tool": False,
        }


def execute_tool(state: FridayState) -> Dict[str, Any]:
    """Execute a tool call and add result to messages."""
    messages = state.get("messages", [])
    tool_results = state.get("tool_results", {})
    
    # Get the last message with tool calls
    last_msg = None
    for msg in reversed(messages):
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            last_msg = msg
            break
    
    if not last_msg:
        return {"tool_results": tool_results}
    
    new_messages = []
    import friday_tools as ft
    
    for tool_call in last_msg.tool_calls:
        name = tool_call["name"]
        args = tool_call.get("args", {})
        
        try:
            func = getattr(ft, name, None)
            if func:
                if isinstance(args, dict):
                    result = func(**args)
                else:
                    result = func(args) if args else func()
                tool_results[name] = result
                new_messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )
            else:
                result = f"Unknown tool: {name}"
                tool_results[name] = result
                new_messages.append(
                    ToolMessage(content=result, tool_call_id=tool_call["id"])
                )
        except Exception as e:
            result = f"Tool {name} error: {str(e)}"
            tool_results[name] = result
            new_messages.append(
                ToolMessage(content=result, tool_call_id=tool_call["id"])
            )
    
    return {
        "messages": messages + new_messages,
        "tool_results": tool_results,
        "needs_tool": False,
    }


def should_continue(state: FridayState) -> str:
    """Conditional edge: determine next step."""
    if state.get("needs_tool"):
        return "execute_tool"
    return END


def get_final_response(state: FridayState) -> str:
    """Extract the final text response from the state."""
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not hasattr(msg, 'tool_calls'):
            return msg.content
    return "No response generated."


# ─── Build the Graph ──────────────────────────────────────────────────────────

def build_friday_graph():
    """Build and return the Friday LangGraph agent."""
    checkpointer = get_checkpointer()
    
    # Create the graph
    graph = StateGraph(FridayState)
    
    # Add nodes
    graph.add_node("process_input", process_input)
    graph.add_node("call_llm", call_llm)
    graph.add_node("execute_tool", execute_tool)
    
    # Set entry point
    graph.set_entry_point()
    
    # Add edges
    graph.add_edge("process_input", "call_llm")
    
    # Conditional edges from call_llm
    graph.add_conditional_edges(
        "call_llm",
        should_continue,
        {
            "execute_tool": "execute_tool",
            END: END,
        }
    )
    
    # After tool execution, go back to LLM
    graph.add_edge("execute_tool", "call_llm")
    
    # Compile with checkpointing
    return graph.compile(checkpointer=checkpointer)


# ─── Agent Class ─────────────────────────────────────────────────────────────

class FridayAgent:
    """Friday agent powered by LangGraph with persistent state."""
    
    def __init__(self):
        self.graph = build_friday_graph()
        self.thread_id = "friday_main"
        self.config = {"configurable": {"thread_id": self.thread_id}}
    
    def chat(self, user_input: str) -> str:
        """Send a message and get response."""
        initial_state = {
            "messages": [],
            "user_input": user_input,
            "tool_results": {},
            "current_tool": None,
            "needs_tool": False,
            "goal_context": {},
            "active_window": "unknown",
            "vision_context": None,
        }
        
        try:
            result = self.graph.invoke(initial_state, config=self.config)
            return get_final_response(result)
        except Exception as e:
            return f"Agent error: {str(e)}"
    
    def chat_stream(self, user_input: str):
        """Stream responses from the agent."""
        initial_state = {
            "messages": [],
            "user_input": user_input,
            "tool_results": {},
            "current_tool": None,
            "needs_tool": False,
            "goal_context": {},
            "active_window": "unknown",
            "vision_context": None,
        }
        
        try:
            for chunk in self.graph.stream(initial_state, config=self.config):
                if "call_llm" in chunk:
                    state = chunk["call_llm"]
                    messages = state.get("messages", [])
                    for msg in reversed(messages):
                        if isinstance(msg, AIMessage) and msg.content and not hasattr(msg, 'tool_calls'):
                            yield {"type": "message", "content": msg.content}
                            break
                elif "execute_tool" in chunk:
                    state = chunk["execute_tool"]
                    tool_results = state.get("tool_results", {})
                    if tool_results:
                        last_tool = list(tool_results.keys())[-1]
                        yield {
                            "type": "tool_result",
                            "tool": last_tool,
                            "result": tool_results[last_tool],
                        }
        except Exception as e:
            yield {"type": "error", "content": str(e)}
    
    def get_state(self) -> Dict[str, Any]:
        """Get current agent state."""
        try:
            state = self.graph.get_state(self.config)
            return state.values if state else {}
        except Exception:
            return {}
    
    def reset(self):
        """Reset the conversation state."""
        self.thread_id = f"friday_{len(os.urandom(8))}"
        self.config = {"configurable": {"thread_id": self.thread_id}}


# ─── Singleton Instance ───────────────────────────────────────────────────────

_agent_instance: Optional[FridayAgent] = None
_agent_lock = threading.Lock()

def get_agent() -> FridayAgent:
    """Get or create the singleton agent instance."""
    global _agent_instance
    with _agent_lock:
        if _agent_instance is None:
            _agent_instance = FridayAgent()
        return _agent_instance


if __name__ == "__main__":
    # Quick test
    print("Testing Friday LangGraph Agent...")
    agent = get_agent()
    
    response = agent.chat("What time is it?")
    print(f"Response: {response}")
    
    response = agent.chat("What's my system info?")
    print(f"Response: {response}")
