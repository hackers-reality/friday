"""Test that all major imports work."""
import sys
errors = []

modules = [
    "fastapi",
    "uvicorn",
    "httpx",
    "jwt",
    "websockets",
    "apscheduler",
    "rapidfuzz",
    "yaml",
    "redis",
]

for mod in modules:
    try:
        __import__(mod)
        print(f"[OK] {mod}")
    except Exception as e:
        print(f"[FAIL] {mod}: {e}")
        errors.append(mod)

# Test FRIDAY module imports
friday_modules = [
    ("friday.nim_client", "InferenceClient"),
    ("friday.nim_router", "resolve_model, classify_task_type"),
    ("friday.base_agent", "BaseAgent, AgentTask, AgentDef"),
    ("friday.agent_registry", "AgentRegistry"),
    ("friday.name_resolver", "resolve, extract_mentions"),
    ("friday.context_bus", "ContextBus, get_bus"),
    ("friday.orchestrator", "Orchestrator"),
    ("friday.sidecar", "router, send_command, get_registry, generate_token"),
    ("friday.sidecar_legacy", "sidecar_tool, register_sidecar"),
    ("friday.camera_manager", "CameraManager"),
    ("friday.frame_buffer", "FrameBuffer, FrameEntry, CVLabels"),
    ("friday.cv_pipeline", "CVPipeline"),
    ("friday.vision_query_handler", "VisionQueryHandler"),
    ("friday.proactive_monitor", "ProactiveMonitor"),
    ("friday.content_analyzer", "analyze_comments"),
    ("friday.metadata_generator", "generate_metadata"),
    ("friday.startup", "launch_all"),
]

for mod_path, names in friday_modules:
    try:
        __import__(mod_path)
        print(f"[OK] {mod_path}")
    except Exception as e:
        print(f"[FAIL] {mod_path}: {e}")
        errors.append(mod_path)

if errors:
    print(f"\n[{len(errors)} ERRORS]")
    sys.exit(1)
else:
    print("\n[ALL OK] All imports pass")
