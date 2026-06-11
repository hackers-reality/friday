"""
Agent Tool Profiles — defines which tools each sub-agent can access
and their specialized system prompts.
"""
from __future__ import annotations

from typing import Any

# Each profile: agent_id -> { name, description, system_prompt, tools, color, icon }
# tool lists reference function names from TOOL_MAP (live.py) + auto-registered tools
# Philosophy: use APIs where available, browser-use/desktop-use only as fallback

AGENT_PROFILES: dict[str, dict[str, Any]] = {
    "veronica": {
        "name": "Veronica",
        "description": "Deep research & intelligence specialist. API-first OSINT, browser fallback for deep research.",
        "color": "#ff6600",
        "icon": "search",
        "system_prompt": """You are Veronica, FRIDAY's deep research and intelligence specialist.
You use APIs FIRST (Shodan, Censys, Hunter, Clearbit, Twitter, Reddit, etc.).
Only fall back to browser-use for multi-step deep research when no API exists.
You excel at OSINT, web scraping, social media intelligence, DNS recon, WHOIS.
Document all findings in structured reports and share on the agent bus.""",
        "tools": [
            "run_browser_task", "browser_navigate", "browser_extract_content", "browser_search",
            "browser_use_navigate", "browser_use_extract", "browser_use_screenshot",
            "browser_use_get_dom_state", "browser_use_extract_text", "browser_use_extract_html",
            "browser_use_extract_links", "browser_use_scroll", "browser_use_click", "browser_use_type",
            "shodan_search", "shodan_host", "censys_search", "whois_lookup",
            "harvester_enum", "subfinder_enum", "nuclei_scan",
            "ping_host", "port_scan", "nmap_scan", "geoip_lookup",
            "hunter_email_search", "clearbit_company", "clearbit_person",
            "twitter_user_info", "twitter_search", "reddit_hot", "reddit_search",
            "instagram_user_info", "youtube_info", "youtube_download",
            "fetch_page", "extract_html", "extract_article", "parse_feed",
            "web_search", "video_search", "open_app",
            "nlp_extract_entities", "nlp_analyze_sentiment", "nlp_classify_content",
            "agent_delegate_with_terminal", "agent_spawn_and_track",
        ],
    },
    "forge": {
        "name": "Forge",
        "description": "Code & development engineer. Writes, tests, debugs, documents code.",
        "color": "#0066ff",
        "icon": "code",
        "system_prompt": """You are Forge, FRIDAY's code and development engineer.
You write, test, debug, and document code in any language.
Use APIs for git, linting, code analysis.
Use browser-use for documentation research and web app testing.
Use desktop-use for IDE control when APIs aren't available.
You are precise, systematic, and follow best practices.""",
        "tools": [
            "git_ops", "run_python",
            "read_docx", "create_docx", "read_excel", "create_excel",
            "analyze_csv", "read_pdf", "create_pdf", "read_pptx", "create_pptx",
            "open_app", "web_search", "video_search",
            "browser_navigate", "browser_extract_content", "browser_search",
            "run_browser_task",
            "browser_use_navigate", "browser_use_extract", "browser_use_screenshot",
            "browser_use_get_dom_state", "browser_use_scroll", "browser_use_click", "browser_use_type",
            "desktop_list_windows", "desktop_focus_window", "desktop_type_text", "desktop_click",
            "desktop_screenshot", "desktop_launch_app",
            "lint_code", "format_code", "search_code", "search_ast", "parse_code", "type_check",
            "run_precommit", "analyze_git_repo", "audit_dependencies",
            "type_text", "press_key", "hotkey", "scroll",
            "take_snapshot", "recall_snapshot",
            "generate_file", "write_file", "read_file", "list_files", "find_files",
        ],
    },
    "ghost": {
        "name": "Ghost",
        "description": "Full-spectrum cybersecurity operator. API-first OSINT, pentesting, vuln scanning, browser recon fallback.",
        "color": "#ff003c",
        "icon": "shield",
        "system_prompt": """You are Ghost, FRIDAY's full-spectrum cybersecurity and OSINT operator.
You use APIs FIRST (Shodan, Censys, VirusTotal, HIBP, URLScan, etc.).
Fall back to browser-use for website recon and surface-level inspection.
You excel at:
- OSINT & threat intelligence (Sherlock, SpiderFoot, Maigret, Holehe)
- Vulnerability scanning (Nuclei, Nmap, port scan)
- WiFi security assessment (handshake capture, profile audit)
- Metasploit (search exploits, launch modules, manage sessions)
- DNS enumeration, email security analysis, breach checks
- Full pentesting: SSL, CORS, headers, whatweb, Wappalyzer
Document all findings with evidence, severity, and remediation steps.""",
        "tools": [
            "run_browser_task", "browser_navigate", "browser_extract_content", "browser_search",
            "browser_use_navigate", "browser_use_extract", "browser_use_screenshot",
            "browser_use_get_dom_state", "browser_use_extract_text", "browser_use_extract_html",
            "browser_use_extract_links", "browser_use_scroll", "browser_use_click", "browser_use_type",
            "shodan_search", "shodan_host", "shodan_search_count", "shodan_ports",
            "censys_search", "whois_lookup", "geoip_lookup", "ping_host", "port_scan", "nmap_scan",
            "harvester_enum", "subfinder_enum", "nuclei_scan",
            "wifi_list_profiles", "wifi_show_password", "wifi_scan", "wifi_connection_status",
            "network_connections", "arp_table", "traceroute",
            "dns_lookup", "dns_reverse_lookup", "dns_mx_lookup", "dns_enumeration",
            "dns_enum", "dns_bruteforce", "dns_zone_transfer", "dns_reverse",
            "ssl_certificate_check", "hibp_breach_check",
            "metasploit_connect", "metasploit_status", "metasploit_exploit",
            "metasploit_scan", "metasploit_post_exploit", "metasploit_payload_gen",
            "msf_search", "msf_workspace_create", "msf_workspace_list",
            "msf_hosts_list", "msf_vulns_list", "msf_creds_list", "msf_sessions_list",
            "analyze_email_headers", "trace_email_path", "detect_email_spoofing",
            "spf_check", "dkim_check", "dmarc_check", "mx_lookup",
            "email_security_score", "email_security_report", "email_full_analysis",
            "verify_email_smtp", "verify_email_domain", "email_disposable_check",
            "forensic_investigate", "forensic_phishing_detection", "forensic_url_analysis",
            "whatweb", "whatcms", "security_headers", "cors_check", "hsts_check",
            "cdn_detect", "web_server_headers", "robots_txt_check",
            "urlscan_submit", "urlscan_result",
            "virus_total_url", "virus_total_domain",
            "wayback_snapshots", "wayback_urls", "wayback_latest",
            "web_crawl", "email_extractor", "meta_extractor", "page_text_extractor",
            "social_analyzer", "instagram_osint", "twitter_osint", "facebook_osint",
            "linkedin_osint", "tiktok_osint", "telegram_osint", "reddit_osint",
            "holehe_check", "email_rep", "username_search",
            "phone_lookup", "phone_format", "phone_breach_check",
            "leak_check", "intelx_search", "dehashed_search",
            "ip_abuse_report", "ip_threat_intel", "ip_reverse_dns",
            "ip_asn_info", "ip_blacklist_check", "ip_geolocate_full", "ip_range_expand",
            "domain_similar", "domain_history", "certificate_transparency",
            "btc_address_lookup", "eth_address_lookup",
            "format_osint_for_report", "summarize_osint_findings", "osint_to_markdown",
            "web_search",
        ],
    },
    "atlas": {
        "name": "Atlas",
        "description": "Knowledge graph & memory curator. Neo4j, ChromaDB, Redis, vector memory.",
        "color": "#00ffcc",
        "icon": "database",
        "system_prompt": """You are Atlas, FRIDAY's knowledge curator and memory specialist.
You use APIs FIRST for all database operations (Neo4j, ChromaDB, Redis).
Use browser-use only when researching data to enrich the knowledge graph.
You excel at entity resolution, vector search, graph analysis, and making connections.""",
        "tools": [
            "run_browser_task", "browser_navigate", "browser_extract_content",
            "browser_use_navigate", "browser_use_extract", "browser_use_screenshot",
            "neo4j_run_query", "neo4j_create_entity", "neo4j_find_entities",
            "analyze_graph", "create_graph_visualization",
            "chroma_create_collection", "chroma_add", "chroma_query", "chroma_list_collections",
            "redis_set", "redis_get", "redis_delete", "redis_list_keys",
            "vm_add", "vm_search", "vm_stats", "vm_delete", "vm_clear",
            "compute_embeddings",
            "nlp_extract_entities", "nlp_classify_content",
            "web_search",
            "knowledge_graph_tool",
        ],
    },
    "jarvis": {
        "name": "Jarvis",
        "description": "Personal assistant & system controller. Desktop automation, Windows control, browser, media.",
        "color": "#9933ff",
        "icon": "monitor",
        "system_prompt": """You are Jarvis, FRIDAY's personal assistant and system controller.
You use Windows APIs FIRST (system_info, get_volume, get_brightness, etc.).
Use desktop-use bridge for UI automation (click, type, focus windows) when APIs aren't enough.
Use browser-use for web tasks the user asks you to do.
You handle: system monitoring, media control, voice, email, files, notifications.""",
        "tools": [
            "system_info", "system_cpu", "system_memory", "system_disk", "system_network", "system_processes",
            "get_processes", "kill_process",
            "get_volume", "set_volume", "mute_audio",
            "get_brightness", "set_brightness",
            "take_screenshot", "list_windows", "focus_window",
            "mouse_click", "mouse_move", "get_mouse_position",
            "type_text", "type_text_auto", "press_key", "hotkey", "scroll",
            "play_system_sound", "read_registry",
            "speak_text", "list_tts_voices",
            "spotify_play", "spotify_pause", "spotify_current", "spotify_next", "spotify_prev", "spotify_volume",
            "open_app", "web_search", "video_search",
            "run_browser_task", "browser_navigate", "browser_extract_content", "browser_search",
            "browser_use_navigate", "browser_use_extract", "browser_use_screenshot",
            "browser_use_get_dom_state", "browser_use_extract_text",
            "browser_use_click", "browser_use_type", "browser_use_scroll",
            "desktop_use_status", "desktop_list_windows", "desktop_get_active_window", "desktop_focus_window",
            "desktop_click", "desktop_type_text", "desktop_extract_text", "desktop_screenshot",
            "desktop_launch_app", "desktop_scroll", "desktop_press_key", "desktop_get_element_tree",
            "send_notification", "read_emails", "send_email",
            "clipboard_get", "clipboard_set",
            "read_file", "write_file", "list_files", "find_files", "generate_file",
            "vision_click",
        ],
    },
    "organizer": {
        "name": "Organizer",
        "description": "Task management & workflow coordinator. Spawns and monitors sub-agents.",
        "color": "#33ccff",
        "icon": "git-branch",
        "system_prompt": """You are Organizer, FRIDAY's workflow coordinator.
You decompose complex tasks and delegate to specialist agents.
Use agent_use_* APIs to spawn, delegate, and monitor sub-agents.
Use agent_spawn_and_track for long-running parallel tasks.
Only use browser-use if you need to research how to organize a workflow.
You are the conductor — delegate don't do.""",
        "tools": [
            "agent_spawn_and_track", "agent_delegate_with_terminal",
            "friday_parse_and_delegate", "friday_multi_agent_task",
            "friday_quick_delegate", "agent_bus_status",
            "agent_use_status", "agent_use_list_agents", "agent_use_spawn",
            "agent_use_delegate", "agent_use_workflow",
            "system_info", "web_search",
            "run_browser_task",
            "create_and_run_workflow", "get_workflow", "get_workflow_status_text",
            "get_task_status", "list_agents",
            "close_all_agent_resources",
        ],
    },
    "planner": {
        "name": "Planner",
        "description": "Strategic planning & research synthesis. Analyzes and creates comprehensive plans.",
        "color": "#ffcc00",
        "icon": "file-text",
        "system_prompt": """You are Planner, FRIDAY's strategic analyst.
You synthesize research from multiple sources into actionable plans.
Use web_search, NLP APIs for analysis, and document APIs for reports.
Use browser only when you need to research specific topics for planning.
You create PDF, DOCX, and PPTX reports with your findings.""",
        "tools": [
            "web_search", "video_search",
            "browser_navigate", "browser_extract_content", "browser_search",
            "nlp_analyze_sentiment", "nlp_extract_entities", "nlp_classify_content",
            "sentiment_analysis", "extract_entities", "summarize_text", "classify_text",
            "create_docx", "create_pdf", "create_pptx",
            "read_docx", "read_pdf", "read_pptx",
            "generate_file", "write_file", "read_file",
        ],
    },
    "sandbox_runner": {
        "name": "Sandbox Runner",
        "description": "Secure code execution environment. Runs untrusted code in isolated sandbox.",
        "color": "#66ff99",
        "icon": "terminal",
        "system_prompt": """You are Sandbox Runner, FRIDAY's secure execution environment.
You run Python, shell, and other code in a sandboxed environment.
Capture and return output, errors, and execution time.
Handle package installation and dependency management.
Use lint/format tools for code quality checks.""",
        "tools": [
            "run_python",
            "lint_code", "format_code", "type_check",
            "search_code", "parse_code",
        ],
    },
    "pr_reviewer": {
        "name": "PR Reviewer",
        "description": "Code review & quality assurance. Reviews pull requests, finds bugs.",
        "color": "#ff3366",
        "icon": "git-pull-request",
        "system_prompt": """You are PR Reviewer, FRIDAY's code quality specialist.
You review PRs for bugs, security, style, test coverage, and documentation.
Use git_ops API for all git operations. Use lint/audit tools for analysis.
Use browser only to reference documentation or best practices.""",
        "tools": [
            "git_ops", "web_search",
            "browser_navigate", "browser_extract_content", "browser_search",
            "read_docx", "read_pdf", "read_pptx",
            "lint_code", "format_code", "search_code", "parse_code", "type_check",
            "analyze_git_repo", "run_precommit", "audit_dependencies",
            "deep_code_review", "code_review_report",
            "github_list_files", "github_read_file", "github_get_contents",
            "github_list_prs", "github_pr_diff", "github_pr_files", "github_pr_comment",
            "github_review_pr", "github_commit_history",
        ],
    },
    "pentester": {
        "name": "Pentester",
        "description": "Full-spectrum pentesting specialist using all offensive security tools.",
        "color": "#cc0000",
        "icon": "zap",
        "system_prompt": """You are Pentester, FRIDAY's offensive cybersecurity operator.
You are a full-spectrum penetration testing specialist.
You excel at:
- WiFi security assessment (handshake capture, cracking, deauth detection)
- Metasploit automation (install, RPC, scan, exploit, auto-pwn, EternalBlue)
- Full pentesting chain: scan, enumerate, exploit, report
- Smart wordlist generation and management
- DNS enumeration, Shodan recon, port scanning
Document all findings with evidence, severity scores, and step-by-step remediation.""",
        "tools": [
            "wifi_smart_crack", "wifi_capture_handshake", "wifi_crack_handshake",
            "download_wordlist", "wordlist_stats",
            "wifi_detect_deauth",
            "msf_auto_install", "msf_ensure_rpc", "msf_quick_scan",
            "msf_find_exploits", "msf_auto_exploit", "msf_auto_pwn",
            "msf_exploit_eternalblue",
            "pentest_scan_target", "pentest_enumerate", "pentest_exploit",
            "pentest_full_chain", "pentest_generate_report", "pentest_tools_check",
            "pentest_wifi_assessment", "pentest_plan",
            "generate_smart_wordlist", "wifi_crack",
            "dns_enum", "shodan_search", "port_scan",
        ],
    },
    "ecosystem": {
        "name": "Ecosystem Controller",
        "description": "Unified ecosystem control across smart home, desktop, browser, media, calendar.",
        "color": "#00cc66",
        "icon": "cpu",
        "system_prompt": """You are Ecosystem Controller, FRIDAY's unified environment orchestrator.
You control and coordinate every aspect of the digital and physical ecosystem.
You excel at:
- Smart home control (lights, thermostat, locks, sensors)
- Desktop automation (windows, apps, files, clipboard)
- Browser automation (navigation, extraction, form filling)
- Media control (Spotify, volume, playback)
- Calendar management (events, schedules, reminders)
- Cross-domain automation routines and triggers
Use APIs FIRST, desktop-use/browser-use as needed for UI-level control.""",
        "tools": [
            "ecosystem_status", "ecosystem_execute", "ecosystem_schedule_action",
            "ecosystem_automation", "ecosystem_routines", "ecosystem_context",
            "ecosystem_discover",
            "desktop_use_status", "browser_use_status", "voice_use_status",
            "calendar_list_events",
            "spotify_play",
            "system_info",
        ],
    },
    "investigator": {
        "name": "OSINT Investigator",
        "description": "Deep OSINT investigation specialist with knowledge graph and multi-agent correlation.",
        "color": "#0066cc",
        "icon": "search",
        "system_prompt": """You are OSINT Investigator, FRIDAY's deep intelligence analyst.
You are a thorough and methodical investigator specializing in open-source intelligence.
You excel at:
- Knowledge graph construction and entity relationship analysis
- Multi-agent investigation coordination
- Timeline reconstruction and event correlation
- Attack surface mapping and continuous monitoring
- Social media analysis, username/email lookup, DNS/WHOIS recon
- Shodan, GeoIP, and infrastructure intelligence
Cross-reference all findings, build evidence chains, and produce comprehensive reports.""",
        "tools": [
            "osint_knowledge_graph", "osint_multi_agent", "osint_timeline",
            "osint_correlation", "osint_report", "osint_continuous_monitor",
            "osint_attack_surface",
            "social_analyzer", "username_search", "email_rep",
            "dns_enum", "whois_lookup", "shodan_search", "geoip_lookup",
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
