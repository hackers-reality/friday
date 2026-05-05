"""
Friday Tools - Utility functions and helpers.
File operations, text processing, data conversion, system utilities.
"""
from __future__ import annotations__

import os
import sys
import json
import time
import re
import math
import hashlib
import base64
import mimetypes
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
import csv
import xml.etree.ElementTree as ET


# ─── Text Processing ────────────────────────────#

class TextProcessor:
    """Advanced text processing utilities."""
    
    @staticmethod
    def word_count(text: str) -> Dict[str, int]:
        """Count words, characters, sentences."""
        words = len(re.findall(r'\b\w+\b', text))
        chars = len(text)
        chars_no_spaces = len(text.replace(" ", ""))
        sentences = len(re.findall(r'[.!?]+', text))
        
        return {
            "words": words,
            "characters": chars,
            "characters_no_spaces": chars_no_spaces,
            "sentences": sentences,
            "paragraphs": len([p for p in text.split("\n\n") if p.strip()]),
        }
    
    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """Extract email addresses."""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.findall(pattern, text)
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract URLs."""
        pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(pattern, text)
    
    @staticmethod
    def extract_phone_numbers(text: str) -> List[str]:
        """Extract phone numbers (simplified)."""
        pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
        return re.findall(pattern, text)
    
    @staticmethod
    def slugify(text: str) -> str:
        """Convert text to URL-friendly slug."""
        # Remove special characters, replace spaces with hyphens
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[\s_-]+', '-', slug)
        slug = re.sub(r'^-+|-+$', '', slug)
        return slug
    
    @staticmethod
    def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def similarity(text1: str, text2: str) -> float:
        """Calculate text similarity (Jaccard index)."""
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0


# ─── Data Conversion ────────────────────────────#

class DataConverter:
    """Convert between data formats."""
    
    @staticmethod
    def json_to_xml(json_data: Dict) -> str:
        """Convert JSON to XML (simplified)."""
        def dict_to_xml(element, data):
            if isinstance(data, dict):
                for key, value in data.items():
                    child = ET.SubElement(element, key)
                    dict_to_xml(child, value)
            elif isinstance(data, list):
                for item in data:
                    item_elem = ET.SubElement(element, "item")
                    dict_to_xml(item_elem, item)
            else:
                element.text = str(data)
        
        root = ET.Element("root")
        dict_to_xml(root, json_data)
        return ET.tostring(root, encoding="unicode")
    
    @staticmethod
    def xml_to_json(xml_string: str) -> Dict:
        """Convert XML to JSON (simplified)."""
        def element_to_dict(element):
            result = {}
            
            for child in element:
                child_data = element_to_dict(child)
                if child.tag in result:
                    if not isinstance(result[child.tag], list):
                        result[child.tag] = [result[child.tag]]
                    result[child.tag].append(child_data)
                else:
                    result[child.tag] = child_data
            
            if not result:
                result = element.text or ""
            
            return result
        
        root = ET.fromstring(xml_string)
        return {root.tag: element_to_dict(root)}
    
    @staticmethod
    def csv_to_json(csv_string: str) -> List[Dict]:
        """Convert CSV to JSON."""
        lines = csv_string.strip().split("\n")
        if not lines:
            return []
        
        reader = csv.DictReader(lines)
        return list(reader)
    
    @staticmethod
    def json_to_csv(data: List[Dict]) -> str:
        """Convert JSON to CSV."""
        if not data:
            return ""
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue()
    
    @staticmethod
    def base64_encode(data: str) -> str:
        """Encode string to base64."""
        return base64.b64encode(data.encode()).decode()
    
    @staticmethod
    def base64_decode(encoded: str) -> str:
        """Decode base64 string."""
        return base64.b64decode(encoded).decode()


# ─── File Utilities ────────────────────────────#

class FileUtils:
    """File operation utilities."""
    
    @staticmethod
    def read_file(file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Read file content."""
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            return {
                "success": True,
                "content": content,
                "size": len(content),
                "encoding": encoding,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def write_file(file_path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Write content to file."""
        try:
            with open(file_path, "w", encoding=encoding) as f:
                f.write(content)
            return {"success": True, "path": file_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """Get file information."""
        try:
            stat = os.stat(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            
            return {
                "success": True,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "mime_type": mime_type or "application/octet-stream",
                "extension": Path(file_path).suffix,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def list_directory(directory: str, pattern: str = "*") -> Dict[str, Any]:
        """List directory contents."""
        try:
            path = Path(directory)
            if not path.exists():
                return {"success": False, "error": "Directory not found."}
            
            items = []
            for item in path.glob(pattern):
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "is_file": item.is_file(),
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                })
            
            return {
                "success": True,
                "items": items,
                "count": len(items),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def create_archive(source: str, output: str = None) -> Dict[str, Any]:
        """Create ZIP archive."""
        try:
            import zipfile
            
            source_path = Path(source)
            output = output or f"{source_path.name}.zip"
            
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipf:
                if source_path.is_file():
                    zipf.write(source_path, source_path.name)
                else:
                    for file_path in source_path.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(source_path.parent)
                            zipf.write(file_path, arcname)
            
            return {"success": True, "archive": output}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def extract_archive(archive: str, destination: str = None) -> Dict[str, Any]:
        """Extract ZIP archive."""
        try:
            import zipfile
            
            destination = destination or Path(archive).stem
            
            with zipfile.ZipFile(archive, "r") as zipf:
                zipf.extractall(destination)
            
            return {"success": True, "destination": destination}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── System Utilities ────────────────────────────#

class SystemUtils:
    """System utility functions."""
    
    @staticmethod
    def get_env(var_name: str, default: str = None) -> str:
        """Get environment variable."""
        return os.getenv(var_name, default)
    
    @staticmethod
    def set_env(var_name: str, value: str) -> Dict[str, Any]:
        """Set environment variable (current process only)."""
        try:
            os.environ[var_name] = value
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get system information."""
        import platform
        
        return {
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }
    
    @staticmethod
    def get_timestamp(format_: str = "iso") -> str:
        """Get current timestamp."""
        now = datetime.now()
        if format_ == "iso":
            return now.isoformat()
        elif format_ == "unix":
            return str(int(now.timestamp()))
        elif format_ == "readable":
            return now.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return now.isoformat()
    
    @staticmethod
    def sleep(seconds: float):
        """Sleep for specified seconds."""
        time.sleep(seconds)
    
    @staticmethod
    def execute_command(command: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute system command."""
        try:
            import subprocess
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Math Utilities ────────────────────────────#

class MathUtils:
    """Math utility functions."""
    
    @staticmethod
    def calculate(expression: str) -> Dict[str, Any]:
        """Safely evaluate a math expression."""
        try:
            # Only allow safe operations
            allowed = {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "pi": math.pi,
                "e": math.e,
            }
            
            result = eval(expression, {"__builtins__": {}}, allowed)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def statistics(data: List[float]) -> Dict[str, Any]:
        """Calculate statistics."""
        if not data:
            return {"success": False, "error": "No data provided."}
        
        sorted_data = sorted(data)
        n = len(data)
        
        mean = sum(data) / n
        median = sorted_data[n // 2] if n % 2 else (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
        variance = sum((x - mean) ** 2 for x in data) / n
        std_dev = variance ** 0.5
        
        return {
            "success": True,
            "count": n,
            "mean": mean,
            "median": median,
            "min": min(data),
            "max": max(data),
            "variance": variance,
            "std_dev": std_dev,
        }


# ─── Tools Tool for Friday ────────────────────────────#

def tools_tool(
    action: str = "status",
    data: str = None,
    format_from: str = None,
    format_to: str = None,
) -> str:
    """
    Friday tool for utility operations.
    Actions: status, wordcount, extract_emails, extract_urls, slugify,
            convert, file_read, file_write, file_info, math_calc, sys_info
    """
    if action == "status":
        lines = ["### TOOLS STATUS", ""]
        lines.append("**Available Utilities**:")
        lines.append("  - Text processing (word count, extract emails/URLs)")
        lines.append("  - Data conversion (JSON, XML, CSV, Base64)")
        lines.append("  - File operations (read, write, info, archive)")
        lines.append("  - System utilities (env vars, system info)")
        lines.append("  - Math utilities (calculate, statistics)")
        return "\n".join(lines)
    
    if action == "wordcount":
        if not data:
            return "❌ Text required."
        result = TextProcessor.word_count(data)
        return f"### WORD COUNT\n\n{json.dumps(result, indent=2)}"
    
    if action == "extract_emails":
        if not data:
            return "❌ Text required."
        emails = TextProcessor.extract_emails(data)
        return f"### EXTRACTED EMAILS\n\n{json.dumps(emails, indent=2)}"
    
    if action == "extract_urls":
        if not data:
            return "❌ Text required."
        urls = TextProcessor.extract_urls(data)
        return f"### EXTRACTED URLS\n\n{json.dumps(urls, indent=2)}"
    
    if action == "slugify":
        if not data:
            return "❌ Text required."
        slug = TextProcessor.slugify(data)
        return f"### SLUGIFY\n\n**Original**: {data}\n**Slug**: {slug}"
    
    if action == "convert":
        if not data or not format_from or not format_to:
            return "❌ Data, from format, and to format required."
        
        try:
            if format_from == "json" and format_to == "xml":
                result = DataConverter.json_to_xml(json.loads(data))
                return f"### CONVERT JSON->XML\n\n{result}"
            elif format_from == "xml" and format_to == "json":
                result = DataConverter.xml_to_json(data)
                return f"### CONVERT XML->JSON\n\n{json.dumps(result, indent=2)}"
            elif format_from == "csv" and format_to == "json":
                result = DataConverter.csv_to_json(data)
                return f"### CONVERT CSV->JSON\n\n{json.dumps(result, indent=2)}"
            elif format_from == "base64" and format_to == "text":
                result = DataConverter.base64_decode(data)
                return f"### CONVERT BASE64->TEXT\n\n{result}"
            elif format_from == "text" and format_to == "base64":
                result = DataConverter.base64_encode(data)
                return f"### CONVERT TEXT->BASE64\n\n{result}"
            else:
                return f"❌ Unsupported conversion: {format_from} to {format_to}"
        except Exception as e:
            return f"❌ Conversion error: {e}"
    
    if action == "file_read":
        if not data:
            return "❌ File path required."
        result = FileUtils.read_file(data)
        if result["success"]:
            return f"### FILE READ\n\n{result['content'][:500]}..."
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    if action == "file_write":
        # Data should be JSON with path and content
        try:
            params = json.loads(data) if data else {}
            path = params.get("path")
            content = params.get("content", "")
            if not path:
                return "❌ Path required."
            result = FileUtils.write_file(path, content)
            return f"### FILE WRITE\n\n{'✅ Written' if result['success'] else '❌ Error'}"
        except Exception as e:
            return f"❌ Error: {e}"
    
    if action == "file_info":
        if not data:
            return "❌ File path required."
        result = FileUtils.get_file_info(data)
        if result["success"]:
            return f"### FILE INFO\n\n{json.dumps(result, indent=2)}"
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    if action == "math_calc":
        if not data:
            return "❌ Expression required."
        result = MathUtils.calculate(data)
        if result["success"]:
            return f"### CALCULATION\n\n**Expression**: {data}\n**Result**: {result['result']}"
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    if action == "sys_info":
        info = SystemUtils.get_system_info()
        return f"### SYSTEM INFO\n\n{json.dumps(info, indent=2)}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Tools...\n")
    
    # Test word count
    print("--- Word Count ---")
    print(tools_tool("wordcount", data="Hello world! This is a test."))
    
    # Test math
    print("\n--- Math Calculation ---")
    print(tools_tool("math_calc", data="2 + 2 * 3"))
    
    # Test system info
    print("\n--- System Info ---")
    print(tools_tool("sys_info"))
