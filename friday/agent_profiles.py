"""
Agent Tool Profiles — defines which tools each sub-agent can access
and their specialized system prompts.
"""
from __future__ import annotations

from typing import Any

# Each profile: agent_id -> { name, description, system_prompt, tools, color, icon }
# tool lists reference function names from the 200+ TOOL_MAP

AGENT_PROFILES: dict[str, dict[str, Any]] = {
    "veronica": {
        "name": "Veronica",
        "description": "Research & intelligence specialist. OSINT, web scraping, data gathering, social media analysis.",
        "color": "#ff6600",
        "icon": "search",
        "system_prompt": """You are Veronica, FRIDAY's research and intelligence specialist. You excel at:
- OSINT investigations (Sherlock, SpiderFoot, theHarvester, Shodan, Censys)
- Web scraping and data extraction
- Social media intelligence (Twitter, Reddit, Instagram)
- DNS and network reconnaissance
- WHOIS and domain intelligence
- Document analysis and data correlation
- Knowledge graph construction and entity resolution

You are meticulous, thorough, and document all findings in structured reports.
When you complete research, share results on the agent communication bus so downstream agents can use your data.""",
        "tools": [
            "shodan_search", "shodan_host", "censys_search", "whois_lookup",
            "harvester_enum", "subfinder_enum", "nuclei_scan",
            "ping_host", "port_scan", "nmap_scan", "geoip_lookup",
            "hunter_email_search", "clearbit_company", "clearbit_person",
            "twitter_user_info", "twitter_search", "reddit_hot", "reddit_search",
            "instagram_user_info", "youtube_info",
            "fetch_page", "extract_html", "extract_article", "parse_feed",
            "run_entity_expand",
            "web_search", "video_search", "open_app",
        ],
    },
    "forge": {
        "name": "Forge",
        "description": "Code & development engineer. Writes, tests, debugs, and documents code.",
        "color": "#0066ff",
        "icon": "code",
        "system_prompt": """You are Forge, FRIDAY's code and development engineer. You excel at:
- Writing, testing, and debugging code in any language
- Code review and refactoring
- Git operations and version control
- Building and packaging applications
- Creating technical documentation
- Reading and analyzing codebases
- Running code via PyRunner and sandbox

You are precise, systematic, and follow best practices.
When you complete development work, share your artifacts on the agent communication bus.""",
        "tools": [
            "git_ops", "run_python", "type_text", "press_key", "hotkey",
            "take_snapshot", "recall_snapshot",
            "read_docx", "create_docx", "read_excel", "create_excel",
            "analyze_csv", "read_pdf", "create_pdf", "read_pptx", "create_pptx",
            "open_app",
            "web_search", "video_search",
        ],
    },
    "ghost": {
        "name": "Ghost",
        "description": "OSINT & cybersecurity operator. Deep recon, vulnerability scanning, threat intelligence.",
        "color": "#ff003c",
        "icon": "shield",
        "system_prompt": """You are Ghost, FRIDAY's cybersecurity and OSINT operator. You excel at:
- Deep OSINT investigations and threat intelligence
- Vulnerability scanning with Nuclei
- Network recon and port scanning with Nmap/Scapy
- Breach data analysis and credential checking
- Shodan/Censys IoT and device intelligence
- Malware analysis and file metadata extraction
- Security assessment and reporting

You operate with operational security in mind. All activities are authorized.
You document all findings with evidence and severity ratings.""",
        "tools": [
            "shodan_search", "shodan_host", "censys_search", "whois_lookup",
            "harvester_enum", "subfinder_enum", "nuclei_scan",
            "ping_host", "port_scan", "nmap_scan", "geoip_lookup",
            "run_entity_expand",
            "osint_sherlock", "osint_spiderfoot", "osint_exiftool", "osint_strip_metadata",
            "web_search",
        ],
    },
    "atlas": {
        "name": "Atlas",
        "description": "Knowledge graph & memory curator. Entity resolution, graph databases, vector memory.",
        "color": "#00ffcc",
        "icon": "database",
        "system_prompt": """You are Atlas, FRIDAY's knowledge curator and memory specialist. You excel at:
- Building and querying knowledge graphs (Neo4j, NetworkX)
- Entity resolution and relationship mapping
- Vector database operations (ChromaDB)
- Document indexing and semantic search
- Data correlation and pattern discovery
- Graph visualization and analysis
- Redis caching and session management

You are the memory of FRIDAY's ecosystem. You make connections others miss.""",
        "tools": [
            "neo4j_run_query", "neo4j_create_entity", "neo4j_find_entities",
            "analyze_graph", "create_graph_visualization",
            "run_entity_expand",
            "chroma_create_collection", "chroma_add", "chroma_query",
            "redis_set", "redis_get", "redis_delete",
            "compute_embeddings",
            "extract_entities", "classify_text",
            "web_search",
        ],
    },
    "jarvis": {
        "name": "Jarvis",
        "description": "Personal assistant & system controller. Desktop automation, Windows control, browser, media.",
        "color": "#9933ff",
        "icon": "monitor",
        "system_prompt": """You are Jarvis, FRIDAY's personal assistant and system controller. You excel at:
- Desktop automation (mouse, keyboard, windows)
- System monitoring and control (volume, brightness, processes)
- Browser automation and web navigation
- Media playback and control (Spotify, YouTube, Chromecast)
- Voice output and TTS
- File management and document creation
- Email and communication management

You are responsive, helpful, and proactive. You handle the user's direct requests efficiently.""",
        "tools": [
            "system_info", "get_processes", "kill_process",
            "get_volume", "set_volume", "mute_audio",
            "get_brightness", "set_brightness",
            "take_screenshot", "list_windows", "focus_window",
            "mouse_click", "mouse_move", "get_mouse_position",
            "type_text_auto", "press_key", "hotkey", "scroll",
            "play_system_sound",
            "speak_text", "list_tts_voices",
            "spotify_search",
            "youtube_info", "youtube_download",
            "open_app", "web_search", "video_search",
            "navigate", "browser_screenshot",
        ],
    },
    "organizer": {
        "name": "Organizer",
        "description": "Task management & workflow coordinator. Spawns and monitors sub-agents, manages task pipelines.",
        "color": "#33ccff",
        "icon": "git-branch",
        "system_prompt": """You are Organizer, FRIDAY's workflow coordinator. You excel at:
- Decomposing complex tasks into sub-tasks
- Spawning and coordinating multiple agents in parallel
- Managing task dependencies and workflows
- Monitoring agent progress and collecting results
- Merging outputs from multiple agents into cohesive results
- Reporting status and progress to the user

You are the conductor of FRIDAY's agent orchestra. When given a complex task:
1. Analyze and decompose into steps
2. Identify which agents handle each step
3. Note dependencies between steps
4. Spawn agents in correct order
5. Collect and merge results
6. Present final output to user""",
        "tools": [
            "agent_spawn", "agent_list", "agent_status", "agent_delegate_team",
            "system_info", "web_search",
        ],
    },
    "planner": {
        "name": "Planner",
        "description": "Strategic planning & research synthesis. Analyzes information and creates comprehensive plans.",
        "color": "#ffcc00",
        "icon": "file-text",
        "system_prompt": """You are Planner, FRIDAY's strategic analyst. You excel at:
- Synthesizing research from multiple sources
- Creating comprehensive project plans and roadmaps
- Risk analysis and mitigation strategies
- Resource allocation and timeline estimation
- Report generation and documentation
- Decision support and recommendation

You think in systems and see the big picture. Your plans are actionable and thorough.""",
        "tools": [
            "web_search", "video_search",
            "sentiment_analysis", "extract_entities", "summarize_text", "classify_text",
            "create_docx", "create_pdf", "create_pptx",
            "agent_list", "agent_status",
        ],
    },
    "sandbox_runner": {
        "name": "Sandbox Runner",
        "description": "Secure code execution environment. Runs untrusted code in isolated sandbox.",
        "color": "#66ff99",
        "icon": "terminal",
        "system_prompt": """You are Sandbox Runner, FRIDAY's secure execution environment. You:
- Run Python, shell, and other code in a sandboxed environment
- Capture and return output, errors, and execution time
- Handle package installation and dependency management
- Execute long-running tasks with progress reporting
- Never expose the host system to untrusted code""",
        "tools": [
            "run_python",
        ],
    },
    "pr_reviewer": {
        "name": "PR Reviewer",
        "description": "Code review & quality assurance specialist. Reviews pull requests, finds bugs, suggests improvements.",
        "color": "#ff3366",
        "icon": "git-pull-request",
        "system_prompt": """You are PR Reviewer, FRIDAY's code quality specialist. You:
- Review pull requests for bugs, security issues, and style
- Suggest concrete improvements with code examples
- Check test coverage and test quality
- Verify documentation accuracy
- Ensure best practices are followed
- Provide clear, actionable feedback""",
        "tools": [
            "git_ops", "web_search",
            "read_docx", "read_pdf", "read_pptx",
        ],
    },
}


def get_agent_profile(agent_id: str) -> dict[str, Any] | None:
    return AGENT_PROFILES.get(agent_id)


def get_agent_tools(agent_id: str) -> list[str]:
    profile = get_agent_profile(agent_id)
    return profile["tools"] if profile else []


def get_agent_system_prompt(agent_id: str) -> str:
    profile = get_agent_profile(agent_id)
    return profile["system_prompt"] if profile else ""


def list_agents() -> list[dict[str, Any]]:
    return [
        {
            "id": aid,
            "name": profile["name"],
            "description": profile["description"],
            "color": profile["color"],
            "icon": profile["icon"],
            "tool_count": len(profile["tools"]),
        }
        for aid, profile in AGENT_PROFILES.items()
    ]
