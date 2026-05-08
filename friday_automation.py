"""
Friday Automation - Advanced automation capabilities.
Browser automation, file automation, system automation, scheduled tasks, RPA.
"""
from __future__ import annotations

import os
import sys
import json
import time
import threading
import subprocess
import shutil
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
import glob
import re
import schedule
import tempfile


# ─── Browser Automation ────────────────────────────#

class BrowserAutomation:
    """Browser automation using Selenium or Playwright."""
    
    def __init__(self):
        self.driver = None
        self.available = False
        self.backend = None
        self._initialize()
        
    def _initialize(self):
        """Initialize browser automation."""
        # Try Selenium
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            self.available = True
            self.backend = "selenium"
            self.selenium = {
                "webdriver": webdriver,
                "By": By,
                "WebDriverWait": WebDriverWait,
                "EC": EC,
            }
        except ImportError:
            # Try Playwright
            try:
                from playwright.sync_api import sync_playwright
                self.available = True
                self.backend = "playwright"
                self.playwright = sync_playwright
            except ImportError:
                self.available = False
    
    def start_browser(self, headless: bool = False) -> Dict[str, Any]:
        """Start browser."""
        if not self.available:
            return {
                "success": False,
                "error": "Browser automation not available. Install: pip install selenium or playwright",
            }
        
        try:
            if self.backend == "selenium":
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                
                options = Options()
                if headless:
                    options.add_argument("--headless")
                
                self.driver = webdriver.Chrome(options=options)
                
            elif self.backend == "playwright":
                from playwright.sync_api import sync_playwright
                self.playwright_instance = sync_playwright().start()
                self.browser = self.playwright_instance.chromium.launch(headless=headless)
                self.page = self.browser.new_page()
            
            return {
                "success": True,
                "backend": self.backend,
                "error": None,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to URL."""
        if not self.driver and not hasattr(self, "page"):
            return {"success": False, "error": "Browser not started."}
        
        try:
            if self.backend == "selenium" and self.driver:
                self.driver.get(url)
                return {"success": True, "url": self.driver.current_url}
            
            elif self.backend == "playwright" and hasattr(self, "page"):
                self.page.goto(url)
                return {"success": True, "url": self.page.url}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def find_element(self, selector: str, by: str = "css") -> Dict[str, Any]:
        """Find element on page."""
        if not self.driver and not hasattr(self, "page"):
            return {"success": False, "error": "Browser not started."}
        
        try:
            if self.backend == "selenium" and self.driver:
                by_map = {
                    "css": self.selenium["By"].CSS_SELECTOR,
                    "xpath": self.selenium["By"].XPATH,
                    "id": self.selenium["By"].ID,
                    "class": self.selenium["By"].CLASS_NAME,
                }
                element = self.driver.find_element(by_map.get(by, by_map["css"]), selector)
                return {
                    "success": True,
                    "text": element.text,
                    "tag": element.tag_name,
                    "found": True,
                }
            
            elif self.backend == "playwright" and hasattr(self, "page"):
                element = self.page.query_selector(selector)
                if element:
                    return {
                        "success": True,
                        "text": element.inner_text(),
                        "tag": element.evaluate("el => el.tagName"),
                        "found": True,
                    }
                else:
                    return {"success": False, "error": "Element not found."}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def click(self, selector: str) -> Dict[str, Any]:
        """Click element."""
        if not self.driver and not hasattr(self, "page"):
            return {"success": False, "error": "Browser not started."}
        
        try:
            if self.backend == "selenium" and self.driver:
                from selenium.webdriver.common.by import By
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                element.click()
                return {"success": True}
            
            elif self.backend == "playwright" and hasattr(self, "page"):
                self.page.click(selector)
                return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into element."""
        if not self.driver and not hasattr(self, "page"):
            return {"success": False, "error": "Browser not started."}
        
        try:
            if self.backend == "selenium" and self.driver:
                from selenium.webdriver.common.by import By
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                element.clear()
                element.send_keys(text)
                return {"success": True}
            
            elif self.backend == "playwright" and hasattr(self, "page"):
                self.page.fill(selector, text)
                return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def screenshot(self, output_file: str = None) -> Dict[str, Any]:
        """Take screenshot."""
        if not self.driver and not hasattr(self, "page"):
            return {"success": False, "error": "Browser not started."}
        
        try:
            output_file = output_file or f"screenshot_{int(time.time())}.png"
            
            if self.backend == "selenium" and self.driver:
                self.driver.save_screenshot(output_file)
            
            elif self.backend == "playwright" and hasattr(self, "page"):
                self.page.screenshot(path=output_file)
            
            return {"success": True, "file": output_file}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def close(self):
        """Close browser."""
        try:
            if self.backend == "selenium" and self.driver:
                self.driver.quit()
            elif self.backend == "playwright" and hasattr(self, "browser"):
                self.browser.close()
                self.playwright_instance.stop()
        except:
            pass


# ─── File Automation ────────────────────────────#

class FileAutomation:
    """Automate file operations."""
    
    @staticmethod
    def watch_directory(
        directory: str,
        callback: Callable = None,
        patterns: List[str] = None,
        timeout: int = 10,
    ) -> Dict[str, Any]:
        """Watch directory for file changes (simplified)."""
        import time
        from pathlib import Path
        
        directory = Path(directory)
        if not directory.exists():
            return {"success": False, "error": "Directory not found."}
        
        patterns = patterns or ["*"]
        initial_files = {f.name: f.stat().st_mtime for f in directory.glob("*")}
        
        # Simple polling (in production, use watchdog library)
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_files = {f.name: f.stat().st_mtime for f in directory.glob("*")}
            
            # Check for new files
            new_files = set(current_files.keys()) - set(initial_files.keys())
            if new_files:
                if callback:
                    callback(new_files)
                return {"success": True, "new_files": list(new_files)}
            
            time.sleep(0.5)
        
        return {"success": True, "new_files": []}
    
    @staticmethod
    def batch_rename(
        directory: str,
        pattern: str = None,
        replacement: str = None,
        prefix: str = None,
        suffix: str = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Batch rename files in directory."""
        from pathlib import Path
        
        directory = Path(directory)
        if not directory.exists():
            return {"success": False, "error": "Directory not found."}
        
        renamed = []
        
        for file_path in directory.iterdir():
            if file_path.is_file():
                new_name = file_path.name
                
                if pattern and replacement is not None:
                    new_name = re.sub(pattern, replacement, new_name)
                
                if prefix:
                    new_name = prefix + new_name
                
                if suffix:
                    # Add suffix before extension
                    stem = file_path.stem
                    ext = file_path.suffix
                    new_name = stem + suffix + ext
                
                if new_name != file_path.name:
                    new_path = file_path.parent / new_name
                    
                    if not dry_run:
                        file_path.rename(new_path)
                    
                    renamed.append({
                        "old": file_path.name,
                        "new": new_name,
                    })
        
        return {
            "success": True,
            "renamed": renamed,
            "dry_run": dry_run,
        }
    
    @staticmethod
    def organize_files(directory: str, by: str = "extension") -> Dict[str, Any]:
        """Organize files into subdirectories."""
        from pathlib import Path
        
        directory = Path(directory)
        if not directory.exists():
            return {"success": False, "error": "Directory not found."}
        
        organized = {}
        
        for file_path in directory.iterdir():
            if file_path.is_file():
                if by == "extension":
                    ext = file_path.suffix.lower() or "no_extension"
                    target_dir = directory / ext
                elif by == "date":
                    import datetime
                    mtime = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                    target_dir = directory / mtime.strftime("%Y-%m")
                else:
                    continue
                
                if not target_dir.exists():
                    target_dir.mkdir(exist_ok=True)
                
                try:
                    shutil.move(str(file_path), str(target_dir / file_path.name))
                    organized[file_path.name] = str(target_dir)
                except Exception as e:
                    organized[file_path.name] = f"Error: {e}"
        
        return {"success": True, "organized": organized}
    
    @staticmethod
    def find_duplicates(directory: str) -> Dict[str, Any]:
        """Find duplicate files by content hash."""
        from pathlib import Path
        import hashlib
        
        directory = Path(directory)
        if not directory.exists():
            return {"success": False, "error": "Directory not found."}
        
        hashes = {}
        duplicates = {}
        
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                try:
                    with open(file_path, "rb") as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()
                    
                    if file_hash in hashes:
                        if file_hash not in duplicates:
                            duplicates[file_hash] = [hashes[file_hash]]
                        duplicates[file_hash].append(str(file_path))
                    else:
                        hashes[file_hash] = str(file_path)
                except:
                    pass
        
        return {"success": True, "duplicates": duplicates}


# ─── System Automation ────────────────────────────#

class SystemAutomation:
    """Automate system operations."""
    
    @staticmethod
    def run_command(
        command: str,
        shell: bool = True,
        timeout: int = 30,
        capture: bool = True,
    ) -> Dict[str, Any]:
        """Run system command."""
        try:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=capture,
                text=True,
                timeout=timeout,
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout if capture else "",
                "stderr": result.stderr if capture else "",
                "command": command,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def schedule_task(
        task_func: Callable,
        interval: str = "daily",
        at_time: str = "09:00",
    ) -> str:
        """Schedule a task (simplified)."""
        import schedule
        
        if interval == "daily":
            schedule.every().day.at(at_time).do(task_func)
        elif interval == "hourly":
            schedule.every().hour.do(task_func)
        elif interval == "minutes":
            schedule.every(int(at_time)).minutes.do(task_func)
        
        # Return task ID (simplified)
        return f"task_{int(time.time())}"
    
    @staticmethod
    def get_running_tasks() -> List[Dict]:
        """Get running scheduled tasks."""
        import schedule
        return [
            {"job": str(job), "next_run": str(job.next_run)}
            for job in schedule.jobs
        ]
    
    @staticmethod
    def kill_process(process_name: str) -> Dict[str, Any]:
        """Kill process by name."""
        try:
            if os.name == "nt":  # Windows
                result = subprocess.run(
                    f"taskkill /F /IM {process_name}",
                    shell=True,
                    capture_output=True,
                    text=True,
                )
            else:  # Unix
                result = subprocess.run(
                    f"pkill -f {process_name}",
                    shell=True,
                    capture_output=True,
                    text=True,
                )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout or result.stderr,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def monitor_resources(interval: int = 5, duration: int = 30) -> Dict[str, Any]:
        """Monitor system resources (CPU, memory)."""
        import psutil
        
        stats = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            
            stats.append({
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "disk_percent": disk.percent,
            })
            
            time.sleep(interval)
        
        return {"success": True, "stats": stats}


# ─── RPA (Robotic Process Automation) ────────────────────────────#

class RPA:
    """Robotic Process Automation workflows."""
    
    def __init__(self):
        self.browser = BrowserAutomation()
        self.file_auto = FileAutomation()
        self.system = SystemAutomation()
        self.workflows: Dict[str, Dict] = {}
        
    def create_workflow(self, name: str, steps: List[Dict]) -> Dict[str, Any]:
        """Create an RPA workflow."""
        self.workflows[name] = {
            "name": name,
            "steps": steps,
            "created": datetime.now().isoformat(),
        }
        return {"success": True, "workflow": name}
    
    def run_workflow(self, name: str) -> Dict[str, Any]:
        """Run an RPA workflow."""
        if name not in self.workflows:
            return {"success": False, "error": f"Workflow '{name}' not found."}
        
        workflow = self.workflows[name]
        results = []
        
        for step in workflow["steps"]:
            action = step.get("action")
            params = step.get("params", {})
            
            if action == "navigate":
                result = self.browser.navigate(params.get("url"))
            elif action == "click":
                result = self.browser.click(params.get("selector"))
            elif action == "type":
                result = self.browser.type_text(
                    params.get("selector"),
                    params.get("text")
                )
            elif action == "screenshot":
                result = self.browser.screenshot(params.get("output"))
            elif action == "command":
                result = self.system.run_command(params.get("command"))
            elif action == "wait":
                time.sleep(params.get("seconds", 1))
                result = {"success": True, "action": "wait"}
            else:
                result = {"success": False, "error": f"Unknown action: {action}"}
            
            results.append({
                "action": action,
                "result": result,
            })
            
            if not result.get("success", True):
                break
        
        return {
            "success": True,
            "workflow": name,
            "results": results,
        }


# ─── Automation Tool for Friday ────────────────────────────#

def automation_tool(
    action: str = "status",
    target: str = None,
    params: Dict = None,
) -> str:
    """
    Friday tool for automation.
    Actions: status, browser_start, browser_navigate, browser_click, browser_screenshot,
            file_rename, file_organize, file_duplicates, system_command, system_monitor,
            rpa_create, rpa_run
    """
    params = params or {}
    
    if action == "status":
        browser = BrowserAutomation()
        lines = ["### AUTOMATION STATUS", ""]
        lines.append(f"**Browser Automation**: {'[OK] Available' if browser.available else '[FAIL] Not available'}")
        lines.append(f"**Backend**: {browser.backend or 'None'}")
        return "\n".join(lines)
    
    if action == "browser_start":
        browser = BrowserAutomation()
        result = browser.start_browser(headless=params.get("headless", False))
        if result["success"]:
            return "### BROWSER\n\n[OK] Started"
        else:
            return f"### BROWSER\n\n[FAIL] {result.get('error', 'Unknown')}"
    
    if action == "browser_navigate":
        if not target:
            return "[FAIL] URL required."
        browser = BrowserAutomation()
        if not browser.driver and not hasattr(browser, "page"):
            browser.start_browser()
        result = browser.navigate(target)
        if result["success"]:
            return "### NAVIGATE\n\n[OK] Navigated"
        else:
            return f"### NAVIGATE\n\n[FAIL] {result.get('error', 'Unknown')}"
    
    if action == "browser_click":
        if not target:
            return "[FAIL] Selector required."
        browser = BrowserAutomation()
        result = browser.click(target)
        if result["success"]:
            return "### CLICK\n\n[OK] Clicked"
        else:
            return f"### CLICK\n\n[FAIL] {result.get('error', 'Unknown')}"
    
    if action == "browser_screenshot":
        browser = BrowserAutomation()
        result = browser.screenshot(target)
        if result["success"]:
            return f"### SCREENSHOT\n\n[OK] Saved to {result.get('file', 'unknown')}"
        else:
            return f"### SCREENSHOT\n\n[FAIL] {result.get('error', 'Unknown')}"
    
    if action == "file_rename":
        if not target:
            return "[FAIL] Directory required."
        file_auto = FileAutomation()
        result = file_auto.batch_rename(
            target,
            pattern=params.get("pattern"),
            replacement=params.get("replacement"),
            prefix=params.get("prefix"),
            suffix=params.get("suffix"),
            dry_run=params.get("dry_run", True),
        )
        return f"### BATCH RENAME\n\nRenamed {len(result['renamed'])} files (dry_run={result['dry_run']})"
    
    if action == "file_organize":
        if not target:
            return "[FAIL] Directory required."
        file_auto = FileAutomation()
        result = file_auto.organize_files(target, by=params.get("by", "extension"))
        return f"### ORGANIZE\n\nOrganized {len(result['organized'])} files"
    
    if action == "file_duplicates":
        if not target:
            return "[FAIL] Directory required."
        file_auto = FileAutomation()
        result = file_auto.find_duplicates(target)
        return f"### DUPLICATES\n\nFound {len(result['duplicates'])} duplicate groups"
    
    if action == "system_command":
        if not target:
            return "[FAIL] Command required."
        system = SystemAutomation()
        result = system.run_command(target)
        if result["success"]:
            return f"### COMMAND\n\n[OK] Success\n{result.get('stdout', '')}"
        else:
            return f"### COMMAND\n\n[FAIL] Failed\n{result.get('error', '')}"
    
    if action == "system_monitor":
        system = SystemAutomation()
        result = system.monitor_resources(
            interval=params.get("interval", 5),
            duration=params.get("duration", 30),
        )
        return f"### MONITOR\n\nCollected {len(result['stats'])} data points"
    
    if action == "rpa_create":
        if not target:
            return "[FAIL] Workflow name required."
        rpa = RPA()
        result = rpa.create_workflow(target, params.get("steps", []))
        if result["success"]:
            return "### RPA CREATE\n\n[OK] Created"
        else:
            return f"### RPA CREATE\n\n[FAIL] {result.get('error', 'Unknown')}"
    
    if action == "rpa_run":
        if not target:
            return "[FAIL] Workflow name required."
        rpa = RPA()
        result = rpa.run_workflow(target)
        return f"### RPA RUN\n\nCompleted {len(result.get('results', []))} steps"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Automation...\n")
    
    # Test file operations
    print("--- File Automation ---")
    print(automation_tool("file_duplicates", target="."))
    
    # Test system command
    print("\n--- System Command ---")
    print(automation_tool("system_command", target="echo Hello from Friday"))
