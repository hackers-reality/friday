"""
Friday Memory Import System - Import chat history from Claude, ChatGPT, Gemini.
Audits all data to build a detailed user profile.
"""
from __future__ import annotations
from friday._paths import FRIDAY_MEMORY

import os
import re
import json
import glob
import zipfile
import tempfile
import shutil
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

_MEMORY_DIR = FRIDAY_MEMORY
_PROFILE_FILE = os.path.join(_MEMORY_DIR, "user_profile.json")
_PROFILE_MD = os.path.join(_MEMORY_DIR, "user_profile.md")
_RAW_IMPORTS_DIR = os.path.join(_MEMORY_DIR, "imported_chats")
_AUDIT_LOG = os.path.join(_MEMORY_DIR, "audit_log.json")

os.makedirs(_MEMORY_DIR, exist_ok=True)
os.makedirs(_RAW_IMPORTS_DIR, exist_ok=True)

# ─── Raw Text Parsing ──────────────────────────────────────

def _parse_conversation_text(text: str) -> List[Dict[str, str]]:
    """Split a conversation by speaker turns (User:, Human:, You:, Assistant:, AI:, Claude:, etc)."""
    turns = []
    pattern = r'(?:(?:^|\n)(?:Human|User|You|Me)\s*[:\-–—]\s*)(.*?)(?=\n(?:Human|User|You|Me|Assistant|AI|Claude|ChatGPT|Gemini)\s*[:\-–—]\s*|\n*$)'
    results = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    if results:
        for r in results:
            turns.append({"role": "user", "content": r.strip()})
    # Get assistant turns
    pattern2 = r'(?:(?:^|\n)(?:Assistant|AI|Claude|ChatGPT|Gemini|Chat AI)\s*[:\-–—]\s*)(.*?)(?=\n(?:Human|User|You|Me|Assistant|AI|Claude|ChatGPT|Gemini)\s*[:\-–—]\s*|\n*$)'
    results2 = re.findall(pattern2, text, re.DOTALL | re.IGNORECASE)
    for r in results2:
        turns.append({"role": "assistant", "content": r.strip()})
    return turns or [{"role": "unknown", "content": text.strip()}]

def _fix_json(json_str: str) -> str:
    """Attempt to fix common JSON issues in exports."""
    s = json_str.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
    return s

# ─── Import Functions ──────────────────────────────────────

def import_from_text_file(filepath: str) -> Dict[str, Any]:
    """Import a plain text conversation export."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    turns = _parse_conversation_text(text)
    return {
        "source": os.path.basename(filepath),
        "source_type": "text",
        "imported_at": datetime.now().isoformat(),
        "conversations": [{"title": "Imported Text", "turns": turns}],
        "raw_text_snippet": text[:2000],
    }

def import_from_json_file(filepath: str) -> Dict[str, Any]:
    """Import a JSON export. Auto-detects format (ChatGPT, Claude, Gemini, generic)."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    data = json.loads(_fix_json(raw))
    source_type = "unknown_json"

    conversations = []

    if isinstance(data, list):
        # Claude-style: list of conversation objects
        for item in data:
            if isinstance(item, dict) and "name" in item and "chat_messages" in item:
                source_type = "claude"
                title = item.get("name", "Untitled")
                turns = []
                for msg in item.get("chat_messages", []):
                    if not isinstance(msg, dict):
                        continue
                    role = "user" if msg.get("sender") in ("human", "user") else "assistant"
                    text = msg.get("text", "") or _parse_claude_content(msg.get("content", ""))
                    if text:
                        turns.append({"role": role, "content": text})
                conversations.append({"title": title, "turns": turns})
            elif isinstance(item, dict) and "message" in item:
                source_type = "chatgpt"
                title = item.get("title", item.get("message", {}).get("content", {}).get("parts", [""])[0])[:80]
                mapping = item.get("mapping", {})
                turns = []
                for node_id, node in mapping.items():
                    msg = node.get("message", {})
                    if msg:
                        role = msg.get("author", {}).get("role", "user")
                        role = "user" if role == "user" else "assistant"
                        parts = msg.get("content", {}).get("parts", [])
                        text = " ".join(p for p in parts if isinstance(p, str))
                        if text:
                            turns.append({"role": role, "content": text})
                if turns:
                    conversations.append({"title": title, "turns": turns})

    elif isinstance(data, dict):
        # Gemini-style or ChatGPT single conversation
        if "conversations" in data:
            for item in data["conversations"]:
                source_type = "chatgpt"
                turns = []
                for msg in item.get("messages", []):
                    role = msg.get("role", "user")
                    role = "user" if role == "user" else "assistant"
                    text = msg.get("content", msg.get("text", ""))
                    if isinstance(text, list):
                        text = " ".join(t for t in text if isinstance(t, str))
                    if text:
                        turns.append({"role": role, "content": text})
                conversations.append({"title": item.get("title", "Untitled"), "turns": turns})
        elif "messages" in data:
            source_type = "generic_json"
            turns = []
            for msg in data["messages"]:
                role = msg.get("role", "user")
                text = msg.get("content", msg.get("text", ""))
                if isinstance(text, list):
                    text = " ".join(t for t in text if isinstance(t, str))
                if text:
                    turns.append({"role": role, "content": text})
            conversations.append({"title": "Imported Conversation", "turns": turns})
        elif "name" in data:
            source_type = "claude"
            title = data.get("name", "Untitled")
            turns = []
            for msg in data.get("chat_messages", data.get("messages", [])):
                role = "user" if msg.get("sender") in ("human", "user") else "assistant"
                turns.append({"role": role, "content": msg.get("text", msg.get("content", ""))})
            conversations.append({"title": title, "turns": turns})

    if not conversations:
        conversations.append({"title": "Raw JSON Import", "turns": [{"role": "unknown", "content": raw[:2000]}]})

    return {
        "source": os.path.basename(filepath),
        "source_type": source_type,
        "imported_at": datetime.now().isoformat(),
        "conversations": conversations,
        "raw_json_snippet": raw[:2000],
    }

def import_from_directory(directory: str) -> List[Dict[str, Any]]:
    """Auto-import all supported files from a directory."""
    results = []
    supported = ["*.txt", "*.json", "*.md", "*.csv"]
    for pattern in supported:
        for filepath in glob.glob(os.path.join(directory, pattern)):
            try:
                if filepath.endswith(".json"):
                    data = import_from_json_file(filepath)
                else:
                    data = import_from_text_file(filepath)
                if data["conversations"]:
                    # Save a copy to imports dir
                    copy_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(filepath)}"
                    copy_path = os.path.join(_RAW_IMPORTS_DIR, copy_name)
                    with open(copy_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    data["saved_copy"] = copy_path
                    results.append(data)
            except Exception as e:
                print(f"[MemoryImport] Skipping {filepath}: {e}")
    return results

# ─── Claude Memories JSON ─────────────────────────────────

def _parse_claude_content(content_field) -> str:
    """Parse Claude content field which can be a string or list of content parts."""
    if isinstance(content_field, str):
        return content_field
    if isinstance(content_field, list):
        parts = []
        for part in content_field:
            if isinstance(part, dict):
                if "text" in part:
                    parts.append(part["text"])
                elif "type" in part and part["type"] == "text" and "text" in part:
                    parts.append(part["text"])
            elif isinstance(part, str):
                parts.append(part)
        return "\n".join(parts)
    return str(content_field) if content_field else ""


def import_from_claude_memories(memories_data: List[Dict]) -> Dict[str, Any]:
    """Parse Claude memories.json: extracts conversations_memory and project_memories."""
    all_text = ""
    account_count = 0
    project_count = 0

    for entry in memories_data:
        if not isinstance(entry, dict):
            continue
        account_count += 1
        cm = entry.get("conversations_memory", "")
        if isinstance(cm, str) and cm.strip():
            all_text += f"\n{cm}\n"
        pm = entry.get("project_memories", {})
        if isinstance(pm, dict):
            for proj_id, proj_text in pm.items():
                if isinstance(proj_text, str) and proj_text.strip():
                    all_text += f"\n[Project {proj_id}]\n{proj_text}\n"
                    project_count += 1

    return {
        "source": "claude_memories.json",
        "source_type": "claude_memories",
        "imported_at": datetime.now().isoformat(),
        "conversations": [{"title": "Claude Memories", "turns": [{"role": "assistant", "content": all_text.strip()}]}],
        "account_count": account_count,
        "project_count": project_count,
        "raw_text_snippet": all_text[:2000],
    }


def import_from_claude_conversations(convs_data: List[Dict]) -> Dict[str, Any]:
    """Parse Claude conversations.json. Each entry has uuid, name, summary, chat_messages etc."""
    conversations = []
    for item in convs_data:
        if not isinstance(item, dict):
            continue
        title = item.get("name") or item.get("summary", "Untitled Claude Chat") or "Untitled"
        summary = item.get("summary", "")
        turns = []
        for msg in item.get("chat_messages", []):
            if not isinstance(msg, dict):
                continue
            role = "user" if msg.get("sender") in ("human", "user") else "assistant"
            text = msg.get("text", "") or _parse_claude_content(msg.get("content", ""))
            if text:
                turns.append({"role": role, "content": text})
        if summary and (not turns or turns[0].get("role") != "system"):
            turns.insert(0, {"role": "system", "content": f"Summary: {summary}"})
        conversations.append({"title": title[:200], "turns": turns})

    return {
        "source": "claude_conversations.json",
        "source_type": "claude_conversations",
        "imported_at": datetime.now().isoformat(),
        "conversations": conversations,
        "conversation_count": len(conversations),
    }


# ─── Gemini Workspace TXT ──────────────────────────────────

def import_from_gemini_workspace(data: Dict) -> Dict[str, Any]:
    """Parse Gemini Workspace conversation JSON (from Takeout TXT files).
    Structure: {title, conversation_turns: [{user_turn: {prompt}, model_turn: {response}}]}"""
    title = data.get("title", "Gemini Conversation")
    turns = []
    for turn in data.get("conversation_turns", []):
        if not isinstance(turn, dict):
            continue
        user_turn = turn.get("user_turn")
        if isinstance(user_turn, dict):
            prompt = user_turn.get("prompt", "")
            if prompt:
                turns.append({"role": "user", "content": prompt})
        model_turn = turn.get("model_turn")
        if isinstance(model_turn, dict):
            response = model_turn.get("response", "")
            if response:
                turns.append({"role": "assistant", "content": response})

    return {
        "source": f"gemini_workspace_{title[:30]}",
        "source_type": "gemini_workspace",
        "imported_at": datetime.now().isoformat(),
        "conversations": [{"title": title[:200], "turns": turns}],
        "turn_count": len(turns),
    }


# ─── ZIP Import ────────────────────────────────────────────

_DOWNLOADS_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
# Also check E:\downloads
_E_DOWNLOADS = r"E:\downloads"


def import_from_zip_file(zip_path: str) -> List[Dict[str, Any]]:
    """Auto-detect and import data from a zip file (in-memory, no disk extraction).
    Handles Claude exports and Google Takeout zips."""
    results = []
    if not zipfile.is_zipfile(zip_path):
        return results

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            names = z.namelist()
            basenames = {os.path.basename(n) for n in names}

            # Claude export: memories.json + conversations.json
            if "memories.json" in basenames and "conversations.json" in basenames:
                try:
                    mem_data = json.loads(z.read("memories.json"))
                    if isinstance(mem_data, list):
                        result = import_from_claude_memories(mem_data)
                        copy_path = os.path.join(_RAW_IMPORTS_DIR, f"claude_memories_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                        with open(copy_path, "w", encoding="utf-8") as f:
                            json.dump(result, f, indent=4)
                        result["saved_copy"] = copy_path
                        results.append(result)
                except Exception as e:
                    print(f"[MemoryImport] Claude memories error: {e}")

                try:
                    conv_data = json.loads(z.read("conversations.json"))
                    if isinstance(conv_data, list) and conv_data and "chat_messages" in conv_data[0]:
                        result = import_from_claude_conversations(conv_data)
                        copy_path = os.path.join(_RAW_IMPORTS_DIR, f"claude_convs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                        with open(copy_path, "w", encoding="utf-8") as f:
                            json.dump(result, f, indent=4)
                        result["saved_copy"] = copy_path
                        results.append(result)
                except Exception as e:
                    print(f"[MemoryImport] Claude conversations error: {e}")

                # Also handle individual project files
                for n in names:
                    if n.startswith("projects/") and n.endswith(".json"):
                        try:
                            proj_data = json.loads(z.read(n))
                            proj_result = import_from_json_file_raw("projects", proj_data)
                            if proj_result and proj_result.get("conversations"):
                                results.append(proj_result)
                        except Exception:
                            pass

            # Google Takeout: Gemini in Workspace TXT files
            for n in names:
                if n.endswith(".txt") and "conversation_" in n:
                    try:
                        raw = z.read(n).decode("utf-8", errors="replace")
                        data = json.loads(raw)
                        if isinstance(data, dict) and "conversation_turns" in data:
                            result = import_from_gemini_workspace(data)
                            base_name = os.path.basename(n).replace(".txt", "")
                            copy_path = os.path.join(_RAW_IMPORTS_DIR, f"gemini_{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                            with open(copy_path, "w", encoding="utf-8") as f:
                                json.dump(result, f, indent=4)
                            result["saved_copy"] = copy_path
                            results.append(result)
                    except Exception as e:
                        print(f"[MemoryImport] Gemini TXT error {n}: {e}")

        return results
    except Exception as e:
        print(f"[MemoryImport] Zip import error for {zip_path}: {e}")
        return results


def import_from_json_file_raw(source_name: str, data) -> Optional[Dict[str, Any]]:
    """Parse raw JSON data (already loaded) as conversation, without file path.
    Used for in-memory zip contents."""
    source_type = "unknown_json"
    conversations = []

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "chat_messages" in item:
                source_type = "claude"
                title = item.get("name", item.get("summary", "Untitled"))
                turns = []
                for msg in item.get("chat_messages", []):
                    if not isinstance(msg, dict):
                        continue
                    role = "user" if msg.get("sender") in ("human", "user") else "assistant"
                    text = msg.get("text", "") or _parse_claude_content(msg.get("content", ""))
                    if text:
                        turns.append({"role": role, "content": text})
                conversations.append({"title": title[:200], "turns": turns})

    if not conversations and isinstance(data, dict):
        if "conversations" in data:
            for item in data["conversations"]:
                source_type = "chatgpt"
                turns = []
                for msg in item.get("messages", []):
                    role = msg.get("role", "user")
                    role = "user" if role == "user" else "assistant"
                    text = msg.get("content", msg.get("text", ""))
                    if isinstance(text, list):
                        text = " ".join(t for t in text if isinstance(t, str))
                    if text:
                        turns.append({"role": role, "content": text})
                conversations.append({"title": item.get("title", "Untitled"), "turns": turns})

    if not conversations:
        return None

    return {
        "source": source_name,
        "source_type": source_type,
        "imported_at": datetime.now().isoformat(),
        "conversations": conversations,
    }


def import_exports(exports_dir: str = None) -> List[Dict[str, Any]]:
    """Scan a directory for supported zip files and import all of them.
    Defaults to checking both ~/Downloads and E:\\downloads."""
    results = []
    directories = []

    if exports_dir:
        directories = [exports_dir]
    else:
        if os.path.isdir(_DOWNLOADS_DIR):
            directories.append(_DOWNLOADS_DIR)
        if os.path.isdir(_E_DOWNLOADS):
            directories.append(_E_DOWNLOADS)

    seen_zips = set()
    for d in directories:
        for fname in os.listdir(d):
            fpath = os.path.join(d, fname)
            if not fname.endswith(".zip") or not os.path.isfile(fpath):
                continue
            # Skip non-data zips
            if not any(kw in fname.lower() for kw in ["data-", "takeout-", "export"]):
                continue
            if fpath in seen_zips:
                continue
            seen_zips.add(fpath)
            print(f"[MemoryImport] Importing {fname}...")
            try:
                imported = import_from_zip_file(fpath)
                results.extend(imported)
                print(f"[MemoryImport]  -> {len(imported)} result(s)")
            except Exception as e:
                print(f"[MemoryImport]  -> FAIL: {e}")

    return results


# ─── Audit Engine ──────────────────────────────────────────

def _extract_name(text: str) -> Optional[str]:
    _GENERIC_NAMES = {"account", "user", "human", "assistant", "claude", "chatgpt", "gemini", "customer", "client", "student", "teacher", "admin", "guest", "default", "person", "someone", "nobody", "none"}
    patterns = [
        r"(?:my name is|call me|I'm|I am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:name['\u2019s]?s?\s*(?::|is|-)\s*)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            name = m.group(1).strip()
            if name.lower() not in _GENERIC_NAMES:
                return name
    return None

def _extract_age_grade(text: str) -> Optional[str]:
    patterns = [
        r"(?:I\s+am|I'm)\s+(\d+)\s*(?:years?\s*old|y\.?o\.?|yo)",
        r"(?:age|aged?)\s*(?::|is|-)\s*(\d+)",
        r"(?:(?:in|in\s+the?)?\s*(?:class|grade|standard|std)\s*)(?::|is|-|\s+)(\d+)(?:\s*(?:th|st|nd|rd)\s*(?:grade|standard|class)?)?",
        r"(\d+)(?:th|st|nd|rd)\s*(?:grade|class|standard)",
        r"(?:college|university|school)\s*(?:student)?",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return None

def _extract_education(text: str) -> List[str]:
    details = []
    patterns = [
        r"(?:studying|studied|pursuing|doing|taking)\s+([A-Za-z\s]{4,50}?)(?:at|in|from|,|\.)",
        r"(?:school|college|university|academy|institute)\s*(?::|is|-|\s+)([A-Za-z\s]{4,60}?)(?:\.|,|$)",
        r"(\d+)(?:th|st|nd|rd)\s*(?:grade|class|standard)\s*(?:at|in|,)?\s*([A-Za-z\s]{4,40}?)(?:\.|,|$)",
        r"(?:10th|12th|CBSE|ICSE|state\s*board|JEE|NEET|GATE|UPSC|IIT|NIT|IIIT)\s*(?:[A-Za-z]{3,30})?(?:\s*\d+[\.,]?\d*)?",
        r"(?:percentage|score|marks|grade|GPA|CGPA)\s*(?::|is|-|\s+)(\d+[\.,]?\d*\s*%?)",
    ]
    for p in patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                m = " ".join(part for part in m if part).strip()
            else:
                m = m.strip()
            if len(m) > 3 and m not in details:
                details.append(m)
    return details

def _extract_projects(text: str) -> List[str]:
    projects = []
    patterns = [
        r"(?:project|building|working\s*on|creating|developed|made)\s+(?:a|an|the|my)?\s*([A-Za-z0-9\s_\-]{3,60}?)(?:\.|,|$|using|with|for)",
        r"(?:github\.com|gitlab\.com|bitbucket\.org)/([A-Za-z0-9_\-]+/[A-Za-z0-9_\-]+)",
        r"(?:repo|repository)\s*(?::|is|-|\s+)([A-Za-z0-9_\-/]{3,60})",
    ]
    for p in patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            m = m.strip().rstrip(".,;")
            if len(m) > 3 and m not in projects:
                projects.append(m)
    return projects

def _extract_preferences(text: str) -> Dict[str, List[str]]:
    prefs = {"browsers": [], "apps": [], "music": [], "anime": [], "games": [], "food": [], "other": []}

    patterns = {
        "browsers": [r"(?:use|using|browser)\s*(?::|is|-|\s+)(Chrome|Firefox|Edge|Brave|Opera|Safari)"],
        "apps":    [r"(?:use|using|app|application|software)\s*(?::|is|-|\s+)([A-Za-z\s]{2,30}?)(?:\.|,|$|for|to)"],
        "anime":   [r"(?:watching|watch|seen|anime)\s*(?::|is|-|\s+)([A-Za-z0-9\s]{2,40}?)(?:\.|,|$|episode|season)"],
        "games":   [r"(?:playing|play|game|gaming)\s*(?::|is|-|\s+)([A-Za-z0-9\s]{2,30}?)(?:\.|,|$|on|with)"],
        "food":    [r"(?:like|love|eat|eating|food|cuisine)\s*(?::|is|-|\s+)([A-Za-z\s]{2,30}?)(?:\.|,|$)"],
    }

    for category, pat_list in patterns.items():
        for p in pat_list:
            matches = re.findall(p, text, re.IGNORECASE)
            for m in matches:
                m = m.strip().rstrip(".,;")
                if len(m) > 2 and m not in prefs[category]:
                    prefs[category].append(m)

    # Check for music services
    music_services = ["spotify", "youtube music", "apple music", "soundcloud", "wynk", "gaana", "jiosaavn"]
    for svc in music_services:
        if svc in text.lower():
            if svc not in prefs["music"]:
                prefs["music"].append(svc)

    return prefs

def _extract_relationships(text: str) -> List[str]:
    people = []
    patterns = [
        r"(?:my friend|friend named|friend called|best friend|my sister|my brother|my mom|my dad|my mother|my father)\s+([A-Z][a-z]+)",
        r"(?:with|to|for)\s+([A-Z][a-z]+)\s+(?:on|about|regarding|yesterday|today|tomorrow)",
    ]
    for p in patterns:
        matches = re.findall(p, text)
        for m in matches:
            if m not in people:
                people.append(m)
    return people

def _extract_goals(text: str) -> List[str]:
    goals = []
    patterns = [
        r"(?:want to|need to|planning to|going to|aim to|goal is|aspire to|trying to)\s+([A-Za-z\s]{4,60}?)(?:\.|,|$|so that|because)",
        r"(?:goal|target|aim|dream|ambition)\s*(?::|is|-|\s+)([A-Za-z\s]{4,60}?)(?:\.|,|$)",
        r"(?:preparing|study|prepare|give|appear)\s+(?:for|in)\s+([A-Za-z0-9\s]{3,30}?)(?:\.|,|$|next|this|exam)",
    ]
    for p in patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            m = m.strip().rstrip(".,;")
            if len(m) > 5 and m not in goals:
                goals.append(m)
    return goals

def _extract_location(text: str) -> Optional[str]:
    patterns = [
        r"(?:live in|from|based in|located in|stay in|reside in)\s+([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)?)",
        r"(?:city|town|place|area)\s*(?::|is|-|\s+)([A-Z][a-z]+)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return None

def _extract_tech_stack(text: str) -> List[str]:
    techs = []
    known_techs = [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "react", "angular", "vue", "node", "django", "flask", "fastapi",
        "tensorflow", "pytorch", "keras", "opencv", "llm", "gpt", "gemini",
        "docker", "kubernetes", "aws", "gcp", "azure", "linux", "git",
        "html", "css", "sql", "mongodb", "redis", "postgresql",
        "tailwind", "bootstrap", "next.js", "svelte", "jquery",
        "electron", "tauri", "flutter", "react native", "swift",
    ]
    lower = text.lower()
    for tech in known_techs:
        if tech in lower:
            if tech not in techs:
                techs.append(tech)
    return techs

def audit_all_text(text: str) -> Dict[str, Any]:
    """Run all audit extractors on text and return structured data."""
    return {
        "name": _extract_name(text),
        "age_grade": _extract_age_grade(text),
        "education": _extract_education(text),
        "projects": _extract_projects(text),
        "preferences": _extract_preferences(text),
        "relationships": _extract_relationships(text),
        "goals": _extract_goals(text),
        "location": _extract_location(text),
        "tech_stack": _extract_tech_stack(text),
        "audited_at": datetime.now().isoformat(),
    }

def audit_imported_data(imported: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Audit all imported conversations and aggregate findings."""
    all_text = ""
    conversation_count = 0

    for item in imported:
        for conv in item.get("conversations", []):
            for turn in conv.get("turns", []):
                all_text += turn.get("content", "") + "\n"
            conversation_count += 1

    return {
        "conversations_audited": conversation_count,
        "sources_imported": len(imported),
        "audited_at": datetime.now().isoformat(),
        "findings": audit_all_text(all_text),
    }

# ─── Profile Management ────────────────────────────────────

def load_profile() -> Dict[str, Any]:
    if os.path.exists(_PROFILE_FILE):
        try:
            with open(_PROFILE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"name": None, "version": 1, "audits": [], "last_updated": None}

def save_profile(profile: Dict[str, Any]) -> None:
    with open(_PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=4)

def update_profile_with_audit(audit_result: Dict[str, Any]) -> Dict[str, Any]:
    """Merge audit findings into the user profile. Only adds NEW information."""
    profile = load_profile()
    findings = audit_result.get("findings", {})

    # Track what changed
    changes = {}

    for key in ["name", "age_grade", "location"]:
        val = findings.get(key)
        if val and val != profile.get(key):
            changes[key] = {"old": profile.get(key), "new": val}
            profile[key] = val

    for list_key in ["education", "projects", "relationships", "goals", "tech_stack"]:
        existing = set(profile.get(list_key, []))
        new_items = [item for item in findings.get(list_key, []) if item not in existing]
        if new_items:
            changes[list_key] = {"added": new_items}
            profile.setdefault(list_key, []).extend(new_items)

    prefs = findings.get("preferences", {})
    existing_prefs = profile.get("preferences", {})
    for cat in ["browsers", "apps", "music", "anime", "games", "food", "other"]:
        existing = set(existing_prefs.get(cat, []))
        new_items = [item for item in prefs.get(cat, []) if item not in existing]
        if new_items:
            if "preferences" not in changes:
                changes["preferences"] = {}
            changes["preferences"][cat] = new_items
            profile.setdefault("preferences", {}).setdefault(cat, []).extend(new_items)

    profile.setdefault("audits", []).append({
        "timestamp": audit_result.get("audited_at", datetime.now().isoformat()),
        "conversations_audited": audit_result.get("conversations_audited", 0),
        "changes_found": len(changes),
    })
    profile["last_updated"] = datetime.now().isoformat()
    profile["version"] = profile.get("version", 1) + 1 if changes else profile.get("version", 1)

    save_profile(profile)
    return changes

def generate_profile_markdown() -> str:
    """Generate a detailed user profile markdown from all accumulated data."""
    profile = load_profile()

    md = f"""# User Profile - Friday Memory System

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Profile Version: {profile.get('version', 1)}*
*Total Audits: {len(profile.get('audits', []))}*

---

## Basic Information

| Field | Value |
|-------|-------|
"""

    md += f"| Name | {profile.get('name', 'Unknown')} |\n"
    md += f"| Age/Grade | {profile.get('age_grade', 'Unknown')} |\n"
    md += f"| Location | {profile.get('location', 'Unknown')} |\n"

    education = profile.get("education", [])
    if education:
        md += "\n## Education\n\n"
        for item in education:
            md += f"- {item}\n"

    projects = profile.get("projects", [])
    if projects:
        md += "\n## Projects\n\n"
        for item in projects:
            md += f"- {item}\n"

    tech_stack = profile.get("tech_stack", [])
    if tech_stack:
        md += "\n## Technology Stack\n\n"
        for item in tech_stack:
            md += f"- {item}\n"

    goals = profile.get("goals", [])
    if goals:
        md += "\n## Goals & Aspirations\n\n"
        for item in goals:
            md += f"- {item}\n"

    relationships = profile.get("relationships", [])
    if relationships:
        md += "\n## Relationships\n\n"
        for item in relationships:
            md += f"- {item}\n"

    prefs = profile.get("preferences", {})
    if any(prefs.values()):
        md += "\n## Preferences\n\n"
        for cat in ["browsers", "apps", "music", "anime", "games", "food", "other"]:
            items = prefs.get(cat, [])
            if items:
                md += f"### {cat.capitalize()}\n\n"
                for item in items:
                    md += f"- {item}\n"
                md += "\n"

    recent_audits = profile.get("audits", [])[-5:]
    if recent_audits:
        md += "\n## Recent Audits\n\n"
        md += "| # | Date | Conversations | Changes |\n"
        md += "|---|------|--------------|--------|\n"
        for i, audit in enumerate(reversed(recent_audits), 1):
            md += f"| {i} | {audit.get('timestamp', '?')[:10]} | {audit.get('conversations_audited', 0)} | {audit.get('changes_found', 0)} |\n"

    md += "\n---\n*This profile is automatically maintained by Friday's Memory Import System.*\n"

    with open(_PROFILE_MD, "w", encoding="utf-8") as f:
        f.write(md)

    return md

# ─── Memory Import Tool ────────────────────────────────────

def memory_import_tool(action: str = "status", **kwargs) -> str:
    """
    Friday tool for importing and auditing chat history.
    Actions: status, import_file, import_dir, import_zip, import_exports, profile, audit
    """
    if action == "status":
        profile = load_profile()
        audits = profile.get("audits", [])
        total_convs = sum(a.get("conversations_audited", 0) for a in audits)
        return (
            f"### MEMORY IMPORT STATUS\n\n"
            f"Profile Version: {profile.get('version', 1)}\n"
            f"Total Audits Run: {len(audits)}\n"
            f"Total Conversations Processed: {total_convs}\n"
            f"Last Updated: {profile.get('last_updated', 'Never')}\n"
            f"Known Name: {profile.get('name', 'Not yet known')}\n"
            f"Known Education: {', '.join(profile.get('education', [])) or 'Not yet known'}\n"
            f"Known Projects: {len(profile.get('projects', []))}\n"
            f"Profile MD: {_PROFILE_MD}"
        )

    if action == "import_file":
        filepath = kwargs.get("path") or kwargs.get("filepath") or kwargs.get("file")
        if not filepath or not os.path.exists(filepath):
            return f"[FAIL] File not found: {filepath}"
        try:
            if filepath.endswith(".json"):
                data = import_from_json_file(filepath)
            else:
                data = import_from_text_file(filepath)
            conv_count = len(data.get("conversations", []))
            # Save copy to imports dir for audit
            copy_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(filepath)}.json"
            copy_path = os.path.join(_RAW_IMPORTS_DIR, copy_name)
            with open(copy_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return f"[OK] Imported {conv_count} conversation(s) from {os.path.basename(filepath)}\nSource Type: {data.get('source_type', 'text')}"
        except Exception as e:
            return f"[FAIL] Import failed: {e}"

    if action == "import_dir":
        directory = kwargs.get("dir") or kwargs.get("directory") or kwargs.get("path", ".")
        if not os.path.exists(directory):
            return f"[FAIL] Directory not found: {directory}"
        results = import_from_directory(directory)
        if not results:
            return f"[FAIL] No supported files found in {directory}"
        total_convs = sum(len(r.get("conversations", [])) for r in results)
        return f"[OK] Imported {len(results)} files ({total_convs} conversations) from {directory}"

    if action == "audit":
        # Re-audit all stored imports
        stored = []
        for filepath in glob.glob(os.path.join(_RAW_IMPORTS_DIR, "*.json")):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    stored.append(json.load(f))
            except Exception:
                pass
        if not stored:
            return "[FAIL] No imported data to audit. Import files first using 'import_file' or 'import_dir'."

        audit_result = audit_imported_data(stored)
        changes = update_profile_with_audit(audit_result)
        md = generate_profile_markdown()

        if changes:
            lines = [f"### AUDIT COMPLETE - New Information Found\n"]
            for key, val in changes.items():
                if isinstance(val, dict):
                    if "added" in val:
                        lines.append(f"  📝 {key}: Added {', '.join(val['added'])}")
                    elif "old" in val:
                        lines.append(f"  📝 {key}: {val['old']} → {val['new']}")
                    else:
                        lines.append(f"  📝 {key}: Updated")
                else:
                    lines.append(f"  📝 {key}: {val}")
            lines.append(f"\n[OK] Profile version {audit_result.get('findings', {}).get('audited_at', '?')[:10]}")
            return "\n".join(lines)
        else:
            return f"[OK] Audit complete. No new information found. ({audit_result.get('conversations_audited', 0)} conversations analyzed)"

    if action == "profile":
        md = generate_profile_markdown()
        # Return summary
        profile = load_profile()
        return (
            f"### USER PROFILE\n\n"
            f"Name: {profile.get('name', 'Unknown')}\n"
            f"Age/Grade: {profile.get('age_grade', 'Unknown')}\n"
            f"Education: {', '.join(profile.get('education', [])) or 'Unknown'}\n"
            f"Projects: {', '.join(profile.get('projects', [])) or 'Unknown'}\n"
            f"Goals: {', '.join(profile.get('goals', [])) or 'Unknown'}\n"
            f"Tech Stack: {', '.join(profile.get('tech_stack', [])) or 'Unknown'}\n"
            f"\nFull profile: {_PROFILE_MD}"
        )

    if action == "import_zip":
        zip_path = kwargs.get("path") or kwargs.get("zip") or kwargs.get("filepath")
        if not zip_path or not os.path.exists(zip_path):
            return f"[FAIL] Zip not found: {zip_path}"
        if not zipfile.is_zipfile(zip_path):
            return f"[FAIL] Not a valid zip: {zip_path}"
        results = import_from_zip_file(zip_path)
        if not results:
            return f"[FAIL] No importable data found in zip."
        total_convs = sum(len(r.get("conversations", [])) for r in results)
        sources = ", ".join(r.get("source_type", "?") for r in results)
        return f"[OK] Imported {len(results)} data source(s) ({total_convs} conversations) from zip\nSources: {sources}"

    if action == "import_exports":
        exports_dir = kwargs.get("dir") or kwargs.get("directory") or kwargs.get("path")
        results = import_exports(exports_dir)
        if not results:
            return f"[FAIL] No supported export zips found."
        total_convs = sum(len(r.get("conversations", [])) for r in results)
        sources = ", ".join(set(r.get("source_type", "?") for r in results))
        return f"[OK] Imported {len(results)} data source(s) ({total_convs} conversations) from exports\nSources: {sources}"

    return f"Unknown action: {action}. Available: status, import_file, import_dir, import_zip, import_exports, audit, profile"


if __name__ == "__main__":
    print("Testing Memory Import System...\n")

    # Test 1: Status
    print("--- Status ---")
    print(memory_import_tool("status"))

    # Test 2: Profile (empty)
    print("\n--- Profile ---")
    print(memory_import_tool("profile"))
