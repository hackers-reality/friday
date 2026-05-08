"""
Friday Desktop App Framework - Phase 6.2-6.4
PyTauri integration for native desktop app with UI.
"""
from __future__ import annotations

import os
import sys
import json
from typing import Optional, Dict, Any


# ─── Framework Selection ──────────────────────────────────────────

SUPPORTED_FRAMEWORKS = {
    "pytauri": {
        "name": "PyTauri",
        "description": "Rust+Tauri backend with Python bindings. Lightweight, native webview.",
        "pros": ["Lightweight (~10MB vs Electron's ~100MB)", "Native webview (no Chromium bundle)", 
                 "Rust security + Python ease", "PyPI package available", "Built-in freeze support"],
        "cons": ["Requires Rust compiler for custom plugins", "Newer framework, smaller community"],
        "recommended": True,
        "install": "pip install pytauri",
        "web": "https://pytauri.github.io/pytauri/",
    },
    "pywry": {
        "name": "PyWry",
        "description": "Cross-platform rendering engine with UI toolkit. Supports MCP, OpenAI, Anthropic.",
        "pros": ["MCP support built-in", "OpenAI/Anthropic providers", "AnyWidget support", 
                 "Build once, render anywhere (native/Jupyter/browser)", "Freeze support with pyinstaller"],
        "cons": ["Very new (2026)", "Small community (3 GitHub stars)"],
        "recommended": False,
        "install": "pip install 'pywry[all]'",
        "web": "https://deeleeramone.github.io/PyWry/",
    },
    "pyqt": {
        "name": "PyQt (PySide6)",
        "description": "Mature Qt bindings for Python. Full-featured but heavy.",
        "pros": ["Very mature, huge community", "Rich widget set", "Excellent docs", 
                 "Cross-platform"],
        "cons": ["Heavy (~50MB+)", "Commercial license required for proprietary apps", 
                 "No built-in webview (need PyQtWebEngine extra)"],
        "recommended": False,
        "install": "pip install PySide6",
        "web": "https://wiki.qt.io/Qt_for_Python",
    },
    "electron": {
        "name": "Electron (via pywebview or eel)",
        "description": "Node.js + Chromium. Heavy but full-featured web tech stack.",
        "pros": ["Full web ecosystem", "Huge community", "Easy to style with CSS"],
        "cons": ["Very heavy (~100MB+)", "Security concerns", "Not Python-native"],
        "recommended": False,
        "install": "pip install pywebview",
        "web": "https://pywebview.flowrl.com/",
    },
}


def get_framework_info(name: str) -> Dict[str, Any]:
    """Get info about a specific framework."""
    return SUPPORTED_FRAMEWORKS.get(name, {"error": f"Framework '{name}' not found"})


def list_frameworks() -> str:
    """List all supported frameworks with recommendations."""
    lines = ["### DESKTOP FRAMEWORK OPTIONS", ""]
    
    for key, info in SUPPORTED_FRAMEWORKS.items():
        rec = "[OK] RECOMMENDED" if info.get("recommended") else ""
        lines.append(f"**{info['name']}** {rec}")
        lines.append(f"  {info['description']}")
        lines.append(f"  Install: `{info['install']}`")
        lines.append("")
    
    lines.append("**Recommendation:** PyTauri - lightweight, secure, native webview.")
    return "\n".join(lines)


# ─── PyTauri Integration (Recommended) ────────────────────────────

def create_pytauri_app(
    app_name: str = "Friday",
    title: str = "Friday - Sovereign AI",
    width: int = 1200,
    height: int = 800,
) -> str:
    """
    Create a PyTauri app structure for Friday.
    Returns the path to the main app file.
    """
    try:
        import pytauri
        PYTAURI_AVAILABLE = True
    except ImportError:
        return "[FAIL] PyTauri not installed. Install: pip install pytauri"
    
    # Create app directory structure
    app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friday_desktop")
    os.makedirs(app_dir, exist_ok=True)
    
    # Main Python file
    main_py = os.path.join(app_dir, "main.py")
    with open(main_py, "w", encoding="utf-8") as f:
        f.write(f'''"""
Friday Desktop App - PyTauri
Native desktop application for Friday Sovereign AI.
"""
from __future__ import annotations

import os
import sys
import threading
import asyncio
from pathlib import Path

try:
    import pytauri
    from pytauri import Builder, WebviewWindow
    PYTAURI_AVAILABLE = True
except ImportError:
    PYTAURI_AVAILABLE = False
    print("PyTauri not available. Install: pip install pytauri")
    sys.exit(1)

# Import Friday components
sys.path.append(str(Path(__file__).parent.parent))

# ─── App State ──────────────────────────────────────────────

class FridayApp:
    def __init__(self):
        self.builder = None
        self.window = None
        self.chat_history = []
        self.goals = []
        self.settings = {{
            "theme": "dark",
            "voice_enabled": True,
            "screen_watch": True,
            "startup": True,
        }}
    
    def init_ui(self):
        """Initialize the UI."""
        if not PYTAURI_AVAILABLE:
            print("Cannot init UI: PyTauri not available")
            return
        
        self.builder = Builder()
        
        # Build the UI
        self.builder.init()
        
        # Main window
        self.window = WebviewWindow(
            title="{title}",
            width={width},
            height={height},
            resizable=True,
        )
        
        # Load the HTML UI
        html_path = Path(__file__).parent / "ui" / "index.html"
        if html_path.exists():
            self.window.load_file(str(html_path))
        else:
            # Load a simple default UI
            self.window.load_html(self._default_html())
        
        return self.window
    
    def _default_html(self) -> str:
        """Generate default HTML UI."""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a2e;
            color: #e0e0e0;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        .header {{
            background: #16213e;
            padding: 1rem;
            border-bottom: 1px solid #0f3460;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .chat-container {{
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
        }}
        .input-container {{
            padding: 1rem;
            border-top: 1px solid #0f3460;
            display: flex;
            gap: 0.5rem;
        }}
        input {{
            flex: 1;
            padding: 0.75rem;
            border: 1px solid #0f3460;
            border-radius: 0.5rem;
            background: #16213e;
            color: #e0e0e0;
            font-size: 1rem;
        }}
        button {{
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 0.5rem;
            background: #533483;
            color: white;
            cursor: pointer;
            font-size: 1rem;
        }}
        button:hover {{
            background: #6a4c93;
        }}
        .message {{
            margin-bottom: 1rem;
            padding: 0.75rem;
            border-radius: 0.5rem;
        }}
        .user-msg {{
            background: #16213e;
            margin-left: 20%;
        }}
        .friday-msg {{
            background: #0f3460;
            margin-right: 20%;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🤖 Friday - Sovereign AI</h2>
        <div>
            <button onclick="toggleSettings()">Settings</button>
            <button onclick="toggleGoals()">Goals</button>
        </div>
    </div>
    
    <div class="chat-container" id="chatContainer">
        <div class="message friday-msg">
            <strong>Friday:</strong> Ready to assist, Boss. How can I help you today?
        </div>
    </div>
    
    <div class="input-container">
        <input type="text" id="userInput" placeholder="Type your message..." 
               onkeydown="if(event.key==='Enter') sendMessage()">
        <button onclick="sendMessage()">Send</button>
    </div>
    
    <script>
        const chatContainer = document.getElementById('chatContainer');
        const userInput = document.getElementById('userInput');
        
        function sendMessage() {{
            const text = userInput.value.trim();
            if (!text) return;
            
            // Add user message
            addMessage(text, 'user');
            userInput.value = '';
            
            // TODO: Send to Friday backend via WebSocket or API
            // For now, simulate a response
            setTimeout(() => {{
                addMessage('Processing: ' + text, 'friday');
            }}, 500);
        }}
        
        function addMessage(text, sender) {{
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message ' + (sender === 'user' ? 'user-msg' : 'friday-msg');
            msgDiv.innerHTML = '<strong>' + (sender === 'user' ? 'You:' : 'Friday:') + '</strong> ' + text;
            chatContainer.appendChild(msgDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }}
        
        function toggleSettings() {{
            alert('Settings panel coming soon!');
        }}
        
        function toggleGoals() {{
            alert('Goals dashboard coming soon!');
        }}
    </script>
</body>
</html>"""
    
    def run(self):
        """Run the app."""
        if not self.window:
            self.init_ui()
        
        if self.window:
            self.window.show()
            pytauri.run()


def main():
    """Entry point for Friday Desktop App."""
    print("Starting Friday Desktop App...")
    
    app = FridayApp()
    
    # Start Friday backend in a separate thread
    def start_backend():
        try:
            from friday_live import friday_live_engine
            # This would integrate with the UI via WebSocket
            print("Friday backend started.")
        except Exception as e:
            print(f"Backend error: {{e}}")
    
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # Run UI
    app.run()


if __name__ == "__main__":
    main()
''')
    
    # Create UI directory and default HTML
    ui_dir = os.path.join(app_dir, "ui")
    os.makedirs(ui_dir, exist_ok=True)
    
    return f"[OK] PyTauri app created at: {main_py}"


# ─── Package as .exe (Phase 6.4) ──────────────────────────────

def create_spec_file(exe_name: str = "Friday") -> str:
    """Create PyInstaller spec file for freezing Friday."""
    spec_path = os.path.join(os.getcwd(), f"{exe_name}.spec")
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['friday.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('friday_tools.py', '.'),
        ('friday_live.py', '.'),
        ('friday_tools_rewritten.py', '.'),
        ('screen_watcher.py', '.'),
        ('browser_history_tools.py', '.'),
        ('goal_memory.py', '.'),
        ('file_generator.py', '.'),
        ('proactive_commentary.py', '.'),
        ('friday_graph.py', '.'),
        ('friday_mcp.py', '.'),
        ('startup_integration.py', '.'),
        ('sovereign_state.json', '.'),
        ('friday_memory', 'friday_memory'),
    ],
    hiddenimports=[
        'pywinctl', 'pycaw', 'psutil', 'browser_history',
        'langgraph', 'langchain', 'langchain_google_genai',
        'mcp', 'google.genai', 'PIL', 'pyautogui',
        'dotenv', 'requests', 'numpy', 'rich', 'pygame',
        'pvporcupine', 'pvrecorder', 'pyaudio', 'cv2',
        'opencli_integration', 'instagram_bot', 'llm_manager',
        'friday_github', 'command_chainer', 'autonomous_research',
        'trust_ml',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_no_prefer_symbolic_links=False,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zippeddata, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{exe_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False for GUI mode
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['friday.ico'],  # Add icon file if available
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{exe_name}',
)
'''
    
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    return f"[OK] Spec file created: {spec_path}\nBuild with: pyinstaller {exe_name}.spec"


# ─── Integration Tool ────────────────────────────────────────────

def desktop_app_tool(action: str = "info") -> str:
    """Friday tool to manage desktop app."""
    if action == "list_frameworks":
        return list_frameworks()
    
    if action == "create_pytauri":
        return create_pytauri_app()
    
    if action == "create_spec":
        return create_spec_file()
    
    if action == "info":
        info = SUPPORTED_FRAMEWORKS["pytauri"]
        return f"""### Friday Desktop App

**Recommended Framework:** {info['name']}
{info['description']}

Install: `{info['install']}`
Web: {info['web']}

To create the app: `desktop_app_tool('create_pytauri')`
To create spec file: `desktop_app_tool('create_spec')`
"""
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    # Test
    print("Testing Desktop App Framework...")
    print("\n" + list_frameworks())
    
    # Create PyTauri app
    # print("\n" + create_pytauri_app())
    
    # Create spec file
    # print("\n" + create_spec_file())
