"""
Friday Package - Phase 6.4
Package Friday as standalone .exe using PyInstaller with spec file.
"""
from __future__ import annotations__

import os
import sys
import shutil
from pathlib import Path


SPEC_CONTENT = '''# -*- mode: python ; coding: utf-8 -*-

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
        ('desktop_app.py', '.'),
        ('sovereign_state.json', '.'),
        ('friday_memory', 'friday_memory'),
        ('templates', 'templates'),
        ('ui', 'ui'),
    ],
    hiddenimports=[
        'pywinctl', 'pycaw', 'psutil', 'browser_history',
        'langgraph', 'langchain', 'langchain_google_genai',
        'mcp', 'google.genai', 'PIL', 'pyautogui',
        'dotenv', 'requests', 'numpy', 'rich', 'pygame',
        'pvporcupine', 'pvrecorder', 'pyaudio', 'cv2',
        'opencli_integration', 'instagram_bot', 'llm_manager',
        'friday_github', 'command_chainer', 'autonomous_research',
        'trust_ml', 'screen_watcher', 'browser_history_tools',
        'goal_memory', 'file_generator', 'proactive_commentary',
        'friday_graph', 'friday_mcp', 'startup_integration',
        'desktop_app', 'json', 'sqlite3', 'ctypes', 'psutil',
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

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    exclude_binaries=True,
    name='Friday',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for GUI mode
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
    name='Friday',
)
'''


def create_spec_file() -> str:
    """Create PyInstaller spec file for Friday."""
    spec_path = os.path.join(os.getcwd(), "Friday.spec")
    
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(SPEC_CONTENT)
    
    return f"✅ Spec file created: {spec_path}"


def build_exe() -> str:
    """Build the executable using PyInstaller."""
    try:
        import PyInstaller.__main__
        
        spec_path = os.path.join(os.getcwd(), "Friday.spec")
        if not os.path.exists(spec_path):
            create_spec_file()
        
        # Run PyInstaller
        from PyInstaller import __main__ as pyinstaller_main
        sys.argv = ['pyinstaller', '--clean', 'Friday.spec']
        pyinstaller_main.run()
        
        return "✅ Build complete! Check dist/Friday/ directory."
    
    except ImportError:
        return "❌ PyInstaller not installed. Install: pip install pyinstaller"
    except Exception as e:
        return f"❌ Build error: {str(e)}"


def create_simple_batch() -> str:
    """Create a simple batch file to run Friday."""
    batch_path = os.path.join(os.getcwd(), "Run_Friday.bat")
    
    bat_content = f'''@echo off
echo Starting Friday - Sovereign AI...
"{sys.executable}" "{os.path.abspath("friday.py")}"
pause
'''
    
    with open(batch_path, "w") as f:
        f.write(bat_content)
    
    return f"✅ Batch file created: {batch_path}"


def create_requirements() -> str:
    """Create requirements.txt for easy setup."""
    req_path = os.path.join(os.getcwd(), "requirements.txt")
    
    requirements = [
        "langgraph>=1.1.0",
        "langchain>=1.2.0",
        "langchain-google-genai",
        "mcp",
        "browser-history>=0.5.0",
        "pywinctl>=0.4.0",
        "pycaw",
        "psutil",
        "Pillow",
        "numpy",
        "rich",
        "python-dotenv",
        "requests",
        "google-generativeai",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "pyautogui",
        "pyperclip",
        "pvporcupine",
        "pvrecorder",
        "pyaudio",
        "opencv-python",
        "pygame",
        "PyInstaller",
    ]
    
    with open(req_path, "w") as f:
        f.write("\n".join(requirements))
    
    return f"✅ Requirements file created: {req_path}"


if __name__ == "__main__":
    print("Friday Packaging Tool")
    print("=" * 40)
    
    # Create spec file
    print(create_spec_file())
    
    # Create batch file
    print(create_simple_batch())
    
    # Create requirements
    print(create_requirements())
    
    print("\nTo build: pyinstaller Friday.spec")
    print("Or run: python package_friday.py build")
