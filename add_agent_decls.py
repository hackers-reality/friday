content = open('friday/live.py', encoding='utf-8').read()

# Find the closing: "        ])\n    ]\n\nTOOL_MAP = {"
marker = "        ])\n    ]\n\nTOOL_MAP = {"
last_idx = content.rfind(marker)

if last_idx >= 0:
    agent_decls = """            # ── Agent Spawning Tools ──
            types.FunctionDeclaration(
                name="agent_spawn",
                description="Spawn a sub-agent for delegated task execution. Creates an agent instance that runs independently and reports back.",
                parameters=types.Schema(type="OBJECT", properties={
                    "agent_id": {"type": "STRING", "description": "Agent ID to spawn: research_agent (Veronica), code_agent (Forge), osint_agent (Ghost), browser_agent (Atlas), communicator_agent (Jarvis), organizer_agent (Nova), planner_agent (Athena), sandbox_runner_agent (Devin), pr_reviewer_agent (Sentinel)."},
                    "task": {"type": "STRING", "description": "Task description for the agent to execute."},
                    "task_type": {"type": "STRING", "description": "Type of task: research, code_gen, osint, browse, summarization, reasoning, general."},
                }),
            ),
            types.FunctionDeclaration(
                name="agent_list",
                description="List all available agents and their current status (idle/running/completed/failed)."
            ),
            types.FunctionDeclaration(
                name="agent_status",
                description="Get detailed status of a specific agent by ID.",
                parameters=types.Schema(type="OBJECT", properties={
                    "agent_id": {"type": "STRING", "description": "Agent ID to check status for."},
                }),
            ),
            types.FunctionDeclaration(
                name="agent_delegate_team",
                description="Split a complex task across multiple specialist sub-agents (Veronica, Forge, Ghost, Atlas, Jarvis) for parallel execution.",
                parameters=types.Schema(type="OBJECT", properties={
                    "task": {"type": "STRING", "description": "The complex task to split across agents."},
                    "agents": {"type": "STRING", "description": "Optional comma-separated list of agent IDs to include (default: all suitable agents)."},
                }),
            ),
"""
    content = content[:last_idx] + agent_decls + content[last_idx:]
    open('friday/live.py', 'w', encoding='utf-8').write(content)
    print(f"OK - agent declarations inserted at {last_idx}")
else:
    print("Marker not found")
