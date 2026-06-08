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
import math
import zipfile
import tempfile
import shutil
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
from collections import Counter

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
# Also check alternative downloads directories
_E_DOWNLOADS = None
def _get_alt_downloads():
    global _E_DOWNLOADS
    if _E_DOWNLOADS is None:
        from friday.paths import get_downloads_dir
        _E_DOWNLOADS = str(get_downloads_dir())
    return _E_DOWNLOADS


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

            # Google Takeout: NotebookLM — extract notes and artifacts as text
            for n in names:
                if "NotebookLM" in n and n.endswith((".md", ".html")):
                    try:
                        raw = z.read(n).decode("utf-8", errors="replace")
                        # Clean HTML tags for HTML files
                        if n.endswith(".html"):
                            raw = re.sub(r"<[^>]+>", " ", raw)
                            raw = re.sub(r"\s+", " ", raw).strip()
                        title = os.path.splitext(os.path.basename(n))[0]
                        if len(raw) > 50:
                            result = {
                                "source": f"notebooklm_{title[:40]}",
                                "source_type": "notebooklm",
                                "imported_at": datetime.now().isoformat(),
                                "conversations": [{"title": f"NotebookLM: {title[:100]}", "turns": [{"role": "assistant", "content": raw[:5000]}]}],
                            }
                            copy_path = os.path.join(_RAW_IMPORTS_DIR, f"notebooklm_{title[:30]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                            with open(copy_path, "w", encoding="utf-8") as f:
                                json.dump(result, f, indent=4)
                            result["saved_copy"] = copy_path
                            results.append(result)
                    except Exception:
                        pass

            # Google Takeout: YouTube — extract watch history, subscriptions as profile data
            for n in names:
                if "youtube" in n.lower() and n.endswith(".json"):
                    try:
                        raw = z.read(n).decode("utf-8", errors="replace")
                        yt = json.loads(raw)
                        texts = []
                        if isinstance(yt, list):
                            for entry in yt:
                                if isinstance(entry, dict):
                                    title = entry.get("title", "") or entry.get("snippet", {}).get("title", "")
                                    if title:
                                        texts.append(f"[YouTube] {title}")
                        elif isinstance(yt, dict):
                            for key in ["items", "videos", "playlists"]:
                                for entry in yt.get(key, []):
                                    t = entry.get("title", "") or entry.get("snippet", {}).get("title", "")
                                    if t:
                                        texts.append(f"[YouTube] {t}")
                        if texts:
                            result = {
                                "source": "youtube_takeout",
                                "source_type": "youtube_takeout",
                                "imported_at": datetime.now().isoformat(),
                                "conversations": [{"title": "YouTube History", "turns": [{"role": "user", "content": "\n".join(texts[:200])}]}],
                            }
                            copy_path = os.path.join(_RAW_IMPORTS_DIR, f"youtube_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                            with open(copy_path, "w", encoding="utf-8") as f:
                                json.dump(result, f, indent=4)
                            result["saved_copy"] = copy_path
                            results.append(result)
                    except Exception:
                        pass

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
        alt_dl = _get_alt_downloads()
        if os.path.isdir(alt_dl) and alt_dl != _DOWNLOADS_DIR:
            directories.append(alt_dl)

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


# ─── Auto-Import Any File ──────────────────────────────────

_SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".log"}

def import_from_any_file(filepath: str) -> Optional[Dict[str, Any]]:
    """Auto-import any supported file: zip, json, text, md, csv.
    Detects format automatically."""
    if not os.path.isfile(filepath):
        return None
    try:
        # Zip files
        if filepath.endswith(".zip") and zipfile.is_zipfile(filepath):
            results = import_from_zip_file(filepath)
            if results:
                # Merge all results into one
                merged = {
                    "source": os.path.basename(filepath),
                    "source_type": "zip_multi",
                    "imported_at": datetime.now().isoformat(),
                    "conversations": [],
                }
                for r in results:
                    merged["conversations"].extend(r.get("conversations", []))
                return merged
            return None
        # JSON files
        if filepath.endswith(".json"):
            return import_from_json_file(filepath)
        # Text/md/csv files
        if filepath.endswith((".txt", ".md", ".csv", ".log")):
            return import_from_text_file(filepath)
        return None
    except Exception as e:
        print(f"[MemoryImport] import_from_any_file error {filepath}: {e}")
        return None


def import_from_memory_folder() -> List[Dict[str, Any]]:
    """Scan memory folder + downloads for ANY new file and import it.
    Tracks already-imported files via a processed_files set."""
    processed_file = os.path.join(_MEMORY_DIR, ".processed_files.json")
    seen = set()
    if os.path.exists(processed_file):
        try:
            with open(processed_file, "r") as f:
                seen = set(json.load(f))
        except Exception:
            pass

    results = []
    scan_dirs = [_RAW_IMPORTS_DIR, _MEMORY_DIR]
    if os.path.isdir(_DOWNLOADS_DIR):
        scan_dirs.append(_DOWNLOADS_DIR)
    alt_dl = _get_alt_downloads()
    if os.path.isdir(alt_dl) and alt_dl != _DOWNLOADS_DIR:
        scan_dirs.append(alt_dl)

    for d in scan_dirs:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            fpath = os.path.join(d, fname)
            if not os.path.isfile(fpath):
                continue
            if fpath in seen:
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in _SUPPORTED_EXTENSIONS and ext != ".zip":
                continue
            # Skip processed JSON copies (already imported)
            if ext == ".json" and d == _RAW_IMPORTS_DIR and fname.startswith(("claude_", "gemini_", "notebooklm_", "youtube_")):
                seen.add(fpath)
                continue

            print(f"[MemoryImport] Auto-importing {fname}...")
            imported = import_from_any_file(fpath)
            if imported and imported.get("conversations"):
                # Save processed copy
                copy_name = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{fname.replace('.','_')}.json"
                copy_path = os.path.join(_RAW_IMPORTS_DIR, copy_name)
                with open(copy_path, "w", encoding="utf-8") as f:
                    json.dump(imported, f, indent=4)
                imported["saved_copy"] = copy_path
                results.append(imported)
            seen.add(fpath)

    # Save updated processed set
    try:
        with open(processed_file, "w") as f:
            json.dump(sorted(seen), f, indent=2)
    except Exception:
        pass

    return results


# ─── LLM Deep Audit ────────────────────────────────────────

def _llm_deep_audit(all_text: str) -> Optional[Dict[str, Any]]:
    """Use Gemini to extract structured profile data from all conversation text.
    Returns dict with validated fields or None."""
    import requests as _requests
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        # Truncate text to fit context window (flash-lite: 1M tokens ≈ ~500K chars)
        text_sample = all_text[:300000]
        prompt = f"""Extract real, verified personal information from this conversation archive. Only include information that is explicitly stated multiple times or confirmed. Return a JSON object with ONLY fields that have high-confidence data:

{{
  "name": "Full name or null",
  "age": "Age or null",
  "location": "City, Country or null",
  "education": ["list of schools/colleges/exams"],
  "occupation": "Job title/role or null",
  "skills": ["confirmed skills"],
  "goals": ["stated goals/aspirations"],
  "tech_stack": ["confirmed technologies used"],
  "languages_spoken": ["languages"],
  "projects": ["confirmed project names"],
  "personality": ["self-described traits"]
}}

Do NOT infer. Only extract explicitly stated information. Return ONLY valid JSON."""

        r = _requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": prompt + "\n\n---CONVERSATIONS---\n" + text_sample[:200000]}]}]},
            timeout=60,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        # Extract JSON from markdown fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        print(f"[MemoryImport] LLM audit error: {e}")
        return None


# ─── Audit Engine ──────────────────────────────────────────
# Utility helpers

_WORD_BOUNDARY = r"(?<![a-zA-Z])"
_WORD_END = r"(?![a-zA-Z])"
_GENERIC_NAMES = {"account", "user", "human", "assistant", "claude", "chatgpt", "gemini", "customer", "client", "student", "teacher", "admin", "guest", "default", "person", "someone", "nobody", "none", "test", "demo"}

def _wb(pattern: str) -> str:
    """Wrap pattern with word-boundary-aware guards."""
    return _WORD_BOUNDARY + pattern + _WORD_END

_NOISE_WORDS = {"the", "this", "that", "these", "those", "there", "their", "them", "they",
    "what", "which", "where", "when", "how", "all", "each", "every", "some", "any", "none",
    "both", "either", "neither", "here", "there", "then", "than", "just", "also", "very",
    "too", "much", "more", "most", "many", "such", "only", "even", "still", "already",
    "about", "above", "after", "again", "almost", "along", "always", "among", "another",
    "around", "because", "before", "being", "below", "between", "beyond", "might", "could",
    "would", "should", "shall", "must", "need", "dare", "ought", "used", "while", "whether",
    "without", "through", "during", "within", "across", "against", "behind", "though"}

def _is_noise(item: str) -> bool:
    """Fast filter: True if item is almost certainly garbage/unreal."""
    item = item.strip()
    if len(item) < 4:
        return True
    # Pure number or punctuation
    if re.match(r'^[\d\s.,;:\-_\'"]+$', item):
        return True
    # Single letter with punctuation
    if re.match(r'^[A-Za-z]\s*[.,;:\-]$', item):
        return True
    # Starts with generic filler
    first = item.split()[0].lower() if item.split() else ""
    if first in _NOISE_WORDS and len(item) < 10:
        return True
    # Contains suspicious fragments (likely partial word matches)
    suspicious_endings = ["ing ", "ion ", "tion ", "ment ", "ness ", "less ", "ful ", "ous "]
    if len(item) < 8 and any(item.endswith(s.strip()) for s in suspicious_endings if len(s.strip()) < len(item)):
        # Single verb/noun fragment with no context
        if not item[0].isupper():
            return True
    return False


def _filter_items(items: List[str], text: str, min_score: float = 0.4) -> List[str]:
    """Universal filter for extracted items: noise check + quality score."""
    result = []
    for item in items:
        if _is_noise(item):
            continue
        score = _score_item_quality(item, text)
        if score >= min_score:
            result.append(item)
    return _deduplicate(result)


def _score_item_quality(item: str, context: str) -> float:
    """Score extracted item quality 0-1 based on length, repetition, and context."""
    if len(item) < 4:
        return 0.0
    # Very long items are likely garbage
    if len(item) > 100:
        return 0.1
    # Check if it looks like a sentence fragment vs named entity
    caps_ratio = sum(1 for c in item if c.isupper()) / max(len(item), 1)
    # Items with no capital letters that aren't common words are suspicious
    if caps_ratio < 0.05 and len(item) > 5:
        # Lowercase-only long string — check if it's a real phrase
        common_words = {"the", "this", "that", "and", "for", "with", "from", "want", "need", "have", "has", "was", "are", "can", "could", "would", "should", "about", "there", "their", "what", "when", "where", "which", "your", "some", "them", "they", "been", "into", "more", "than", "very", "just", "also", "does", "make", "come", "take", "know", "like", "look", "work", "year", "life", "back", "even", "well", "down", "over", "only", "new", "each", "other", "many", "then"}
    if caps_ratio < 0.05 and len(item) > 8:
        words = item.lower().split()
        real_words = sum(1 for w in words if w in common_words or len(w) > 2)
        if real_words / max(len(words), 1) < 0.3:
            return 0.15  # Likely random letters

    # Count occurrences in context (higher = more likely real)
    count = context.lower().count(item.lower())
    frequency_bonus = min(count / 10, 1.0) * 0.2

    base = 0.6
    if item[0].isupper():
        base += 0.15  # Named entities more likely real
    if 4 <= len(item) <= 50:
        base += 0.1
    if count >= 2:
        base += 0.1

    return min(base + frequency_bonus, 1.0)


def _deduplicate(items: List[str], threshold: float = 0.8) -> List[str]:
    """Deduplicate items using simple similarity."""
    if not items:
        return []
    result = []
    for item in items:
        item_lower = item.strip().lower()
        is_dup = False
        for existing in result:
            if item_lower == existing.lower():
                is_dup = True
                break
            # Check if one is substring of the other (meaningful overlap)
            short, long = (item_lower, existing.lower()) if len(item_lower) < len(existing.lower()) else (existing.lower(), item_lower)
            if len(short) > 5 and short in long:
                is_dup = True
                break
        if not is_dup:
            result.append(item.strip())
    return result


def _extract_name(text: str) -> Optional[str]:
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
        _wb(r"(?:class|grade|standard|std)\s*(?::|is|-|\s+)(\d+)(?:\s*(?:th|st|nd|rd)\s*(?:grade|standard|class)?)?"),
        _wb(r"(\d+)(?:th|st|nd|rd)\s*(?:grade|class|standard)"),
        r"(?:(?:in\s+)?(?:class|grade|standard)\s+)(\d+)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            # Return just the number with unit, not the full match text
            val = m.group(1).strip() if m.lastindex >= 1 else m.group(0).strip()
            # Must be a short numeric age/grade string
            val_clean = val.rstrip(".,;:")
            if val_clean.isdigit():
                n = int(val_clean)
                if 3 <= n <= 25:
                    return f"{n} years old" if n > 12 else f"Grade {n}"
                # Age < 3 or > 25 is suspicious
                continue
            if len(val_clean) < 10 and len(val_clean) > 0:
                return val_clean
    return None


def _extract_education(text: str) -> List[str]:
    _EDU_FALSE_POSITIVES = {
        "the", "this", "that", "these", "those", "there", "it", "them",
        "i", "you", "he", "she", "we", "they", "my", "your", "his", "her",
        "a", "an", "in", "on", "at", "to", "for", "of", "with", "by", "from",
        "and", "or", "but", "so", "if", "because", "when", "where",
        "what", "which", "who", "how", "all", "some", "any", "many",
        "more", "most", "other", "such", "only", "just", "also", "very",
        "can", "will", "may", "should", "would", "could", "must", "need",
        "does", "has", "have", "had", "was", "were", "been", "being",
        "get", "got", "make", "made", "take", "took", "give", "gave",
        "see", "saw", "know", "knew", "think", "thought", "want", "wanted",
        "come", "came", "go", "went", "use", "used", "find", "found",
        "tell", "told", "ask", "asked", "work", "worked", "study", "learn",
        "learn", "call", "called", "try", "tried", "feel", "felt",
        "leave", "left", "put", "set", "bring", "brought", "begin", "began",
        "keep", "kept", "hold", "held", "write", "wrote", "stand", "stood",
        "hear", "heard", "let", "mean", "meant", "run", "ran",
    }
    details = []
    patterns = [
        _wb(r"(?:school|college|university|academy|institute|institution)\s+(?:of\s+)?(?:is\s+)?(?:at\s+|in\s+)?([A-Z][A-Za-z\s.'&-]{3,60}?)(?:\.|,|$)"),
        r"(?:studying|studied|pursuing|enrolled|doing|taking)\s+([A-Za-z\s]{4,50}?)\s+(?:at|in|from|,|\.)",
        r"(\d+)(?:th|st|nd|rd)\s*(?:grade|class|standard)\s+(?:at|in|,)?\s*([A-Z][A-Za-z\s]{3,40}?)(?:\.|,|$)",
        _wb(r"(?:CBSE|ICSE|IB)\s+(?:board\s+)?(?:[A-Z][A-Za-z\s]{3,30})?"),
        _wb(r"(IIT|NIT|IIIT|JEE|NEET|GATE|UPSC|CAT|GMAT|GRE|TOEFL|IELTS|SAT)\s*(?:[A-Za-z]{2,30})?(?:\s*\d+[\.,]?\d*)?"),
        r"(?:percentage|score|marks|grade|GPA|CGPA|aggregate)\s*(?::|is|-|\s+)(\d+[\.,]?\d*\s*%?)",
    ]
    for p in patterns:
        if p.startswith(_WORD_BOUNDARY):
            matches = re.findall(p, text, re.IGNORECASE)
        else:
            matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                m = " ".join(part for part in m if part).strip()
            else:
                m = m.strip()
            if len(m) > 3 and len(m) < 100 and m not in details:
                # Reject if it's just a stop word or fragment
                m_lower = m.lower().strip()
                if m_lower in _EDU_FALSE_POSITIVES:
                    continue
                if len(m.split()) == 1 and m_lower in _EDU_FALSE_POSITIVES:
                    continue
                # Reject single short words that aren't proper nouns
                if len(m.split()) == 1 and len(m) < 5 and not m[0].isupper():
                    continue
                # Reject items that look like URLs or file paths
                if re.search(r'https?://|www\.|\.com|\.org|\.net|\.io|\\|/', m):
                    continue
                score = _score_item_quality(m, text)
                if score > 0.35:
                    details.append(m)
    return _deduplicate(details)


def _extract_projects(text: str) -> List[str]:
    _PROJECT_FALSE_POSITIVES = {
        "a", "an", "the", "my", "your", "this", "that", "it", "i", "we",
        "them", "their", "its", "our", "some", "any", "all", "each", "every",
        "both", "few", "more", "most", "other", "such", "no", "not", "only",
        "own", "same", "so", "too", "very", "just", "also", "even", "still",
        "already", "always", "never", "often", "sometimes", "usually",
        "here", "there", "then", "now", "here", "where", "which", "while",
        "project", "app", "tool", "system", "site", "platform", "software",
        "assistant", "bot", "script", "module", "package", "library",
        "thing", "stuff", "work", "code", "something", "anything",
    }
    projects = []
    patterns = [
        r"(?:project|building|working\s*on|creating|developed|created|made|designing)\s+(?:a|an|the|my|this)?\s*([A-Z][A-Za-z0-9\s_\-'&]{3,60}?)(?:\.|,|$|using|with|for|which|that)",
        r"(?:github\.com|gitlab\.com|bitbucket\.org)/([A-Za-z0-9_\-]+/[A-Za-z0-9_\-]+)",
        r"(?:github|gitlab|bitbucket)\s+(?:at|@|:)\s*([A-Za-z0-9_\-]+/[A-Za-z0-9_\-]+)",
        _wb(r"(?:repo|repository)\s*(?::|is|-|\s+)([A-Za-z0-9_\-/]{3,60})"),
        r"(?:called|named|titled)\s+['\u201c]?([A-Z][A-Za-z0-9\s_\-'&]{3,60}?)['\u201d]?\s+(?:project|app|tool|system|site|platform|bot|assistant)",
        r"(?:project|app|tool|system|site|platform|software|assistant)\s+(?:called|named|titled)\s+['\u201c]?([A-Z][A-Za-z0-9\s_\-'&]{3,60}?)['\u201d]?",
    ]
    for p in patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            m = m.strip().rstrip(".,;:'\"")
            m_lower = m.lower()
            if m_lower in _PROJECT_FALSE_POSITIVES:
                continue
            if len(m.split()) == 1 and len(m) < 4:
                continue
            if len(m) > 3 and len(m) < 80 and m not in projects:
                score = _score_item_quality(m, text)
                if score > 0.35:
                    projects.append(m)
    return _deduplicate(projects)


def _extract_preferences(text: str) -> Dict[str, List[str]]:
    prefs = {"browsers": [], "apps": [], "music": [], "anime": [], "games": [], "food": [], "other": []}

    known_browsers = ["Chrome", "Firefox", "Edge", "Brave", "Opera", "Safari", "Vivaldi", "Tor"]
    known_apps = ["Figma", "Spotify", "VS Code", "Discord", "Slack", "Notion", "Obsidian", "Telegram", "WhatsApp", "Instagram", "Twitter", "GitHub Desktop", "Postman", "Docker Desktop", "Photoshop", "Premiere Pro", "Fusion 360", "Blender"]
    known_music = ["Spotify", "YouTube Music", "Apple Music", "SoundCloud", "Gaana", "Wynk", "JioSaavn", "Amazon Music"]
    known_anime = ["Naruto", "One Piece", "Attack on Titan", "Demon Slayer", "Jujutsu Kaisen", "Death Note", "Fullmetal Alchemist", "My Hero Academia", "Dragon Ball", "Tokyo Ghoul", "One Punch Man", "Sword Art Online"]
    known_games = ["Minecraft", "Roblox", "Fortnite", "Valorant", "GTA", "Call of Duty", "Apex Legends", "Elden Ring", "Red Dead Redemption", "The Legend of Zelda", "Pokemon", "Among Us", "Bloons TD", "Chess"]
    known_food = ["Pizza", "Biryani", "Sushi", "Pasta", "Burger", "Tacos", "Dosa", "Samosa", "Chocolate", "Ice Cream", "Coffee", "Tea", "Noodles", "Ramen", "Butter Chicken", "Paneer"]

    lower = text.lower()

    # All known-item checks with word boundaries, no string containment
    def _in_text(term: str) -> bool:
        return bool(re.search(_wb(re.escape(term.lower())), lower))

    for b in known_browsers:
        if _in_text(b) and b not in prefs["browsers"]:
            prefs["browsers"].append(b)

    for a in known_apps:
        if _in_text(a) and a not in prefs["apps"]:
            prefs["apps"].append(a)

    for m in known_music:
        if _in_text(m) and m not in prefs["music"]:
            prefs["music"].append(m)

    for a in known_anime:
        if _in_text(a) and a not in prefs["anime"]:
            prefs["anime"].append(a)

    for g in known_games:
        if _in_text(g) and g not in prefs["games"]:
            prefs["games"].append(g)

    for f in known_food:
        if _in_text(f) and f not in prefs["food"]:
            prefs["food"].append(f)

    return prefs


def _extract_relationships(text: str) -> List[str]:
    people = []
    patterns = [
        r"(?:my friend|friend named|friend called|best friend|my sister|my brother|my mom|my dad|my mother|my father|my cousin|my uncle|my aunt|my colleague|my partner|my teammate)\s+([A-Z][a-z]+)",
        r"(?:with|to|for)\s+([A-Z][a-z]+)\s+(?:on|about|regarding|yesterday|today|tomorrow|next)",
    ]
    stop_words = {"the", "this", "that", "these", "those", "there", "their", "them", "they", "what", "which", "where", "when", "how", "all", "each", "every", "some", "any", "none", "both", "either", "neither", "here", "there"}
    for p in patterns:
        matches = re.findall(p, text)
        for m in matches:
            if m and m.lower() not in stop_words:
                people.append(m)
    return _deduplicate(people)


def _extract_goals(text: str) -> List[str]:
    _GOAL_FALSE_POSITIVES = {
        "it", "this", "that", "the", "a", "an", "do", "make", "get", "have",
        "be", "go", "see", "know", "find", "use", "take", "come", "work",
        "look", "want", "give", "tell", "help", "keep", "let", "start",
        "show", "hear", "play", "run", "move", "live", "believe", "hold",
        "bring", "happen", "write", "provide", "sit", "stand", "lose", "pay",
        "meet", "include", "continue", "set", "learn", "change", "lead",
        "understand", "watch", "follow", "stop", "create", "speak", "read",
        "allow", "add", "spend", "grow", "open", "walk", "win", "offer",
        "remember", "love", "consider", "appear", "buy", "wait", "serve",
        "build", "stay", "reach", "remain", "suggest", "raise", "pass",
        "sell", "require", "report", "decide", "pull", "push", "draw",
        "break", "ask", "call", "try", "feel", "leave", "put", "bring",
        "begin", "keep", "hold", "write", "stand", "hear", "let", "mean",
        "run", "cut", "hit", "beat", "sing", "choose", "drive", "fly",
    }
    goals = []
    patterns = [
        r"(?:want to|need to|planning to|going to|aim to|goal is|aspire to|trying to|hoping to|looking to)\s+([A-Za-z\s]{5,80}?)(?:\.|,|$|so that|because|and|but)",
        _wb(r"(?:goal|target|aim|dream|ambition|objective)\s*(?::|is|-|\s+)([A-Za-z\s]{5,80}?)(?:\.|,|$)"),
        r"(?:preparing|studying|study|prepare|give|appear|sit)\s+(?:for|in)\s+([A-Za-z0-9\s]{3,40}?)(?:\.|,|$|next|this|exam|test|competition)",
    ]
    for p in patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                m = " ".join(part for part in m if part).strip()
            else:
                m = m.strip().rstrip(".,;")
            if not m or len(m) < 5 or len(m) > 80:
                continue
            first_word = m.split()[0].lower() if m.split() else ""
            if first_word in _GOAL_FALSE_POSITIVES:
                continue
            # Reject if it's just punctuation or whitespace
            if re.match(r'^[\s.,;:\-_\'"]+$', m):
                continue
            # Reject single-word "goals"
            if len(m.split()) == 1:
                continue
            if m not in goals:
                score = _score_item_quality(m, text)
                if score > 0.35:
                    goals.append(m)
    return _deduplicate(goals)


def _extract_location(text: str) -> Optional[str]:
    _KNOWN_NON_LOCATIONS = {
        "google", "microsoft", "amazon", "apple", "meta", "netflix", "spotify",
        "github", "gitlab", "docker", "slack", "notion", "figma", "discord",
        "youtube", "twitter", "linkedin", "instagram", "reddit", "whatsapp",
        "chrome", "firefox", "safari", "edge", "linux", "windows", "macos",
        "android", "ios", "ubuntu", "debian", "python", "react", "node",
        "the", "this", "that", "here", "there", "where", "some", "any", "all",
        "home", "school", "college", "university", "work", "office", "online",
        "everywhere", "nowhere", "somewhere", "default", "none", "null",
        "india", "usa", "uk", "australia", "canada",  # Too vague without more context
    }
    patterns = [
        r"(?:live in|from|based in|located in|stay in|reside in|hailing from)\s+([A-Z][a-z]+(?:[, ]+\s*[A-Z][a-z]+)?(?:[, ]+\s*[A-Z][a-z]+)?)",
        r"(?:city|town|village|place|area|region)\s*(?::|is|-|\s+)([A-Z][a-z]+(?:[, ]+\s*[A-Z][a-z]+)?)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            loc = m.group(1).strip().rstrip(".,")
            loc_lower = loc.lower()
            if loc_lower in _KNOWN_NON_LOCATIONS:
                continue
            if loc_lower in {"the", "this", "that", "here", "there", "where"}:
                continue
            if len(loc) > 2:
                return loc
    return None


def _extract_tech_stack(text: str) -> List[str]:
    known_techs = [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "react", "angular", "vue", "svelte", "node", "node.js", "deno", "bun",
        "django", "flask", "fastapi", "express", "next.js", "nuxt", "remix",
        "tensorflow", "pytorch", "keras", "opencv", "scikit-learn", "pandas", "numpy",
        "llm", "gpt", "gemini", "claude", "ollama", "langchain", "huggingface",
        "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "firebase", "vercel", "netlify",
        "linux", "git", "github", "gitlab",
        "html", "css", "sass", "tailwind", "bootstrap", "material-ui", "chakra",
        "sql", "mysql", "postgresql", "sqlite", "mongodb", "redis", "supabase",
        "electron", "tauri", "flutter", "react native", "swift", "kotlin",
        "graphql", "rest", "grpc", "websocket", "rabbitmq", "kafka",
        "ansible", "terraform", "jenkins", "github actions", "ci/cd",
    ]
    techs = set()
    lower = text.lower()
    for tech in known_techs:
        if re.search(_wb(re.escape(tech)), lower):
            techs.add(tech)
    return sorted(techs)


# ─── New Comprehensive Extractors ──────────────────────────

def _extract_interests_hobbies(text: str) -> Dict[str, List[str]]:
    """Extract interests, hobbies, and activities."""
    result = {"hobbies": [], "activities": [], "topics_of_interest": []}
    patterns = {
        "hobbies": [
            r"(?:my hobby|hobbies|love to|enjoy|i like)\s+(?:is|are|:)?\s*([A-Za-z\s]{4,40}?)(?:\.|,|$|and|but)",
        ],
        "activities": [
            r"(?:i\s+(?:like|love|enjoy|do|practice|play|go)\s+)([A-Za-z\s]{4,40}?)(?:\.|,|$|every|on|in|with|for|when)",
        ],
    }
    for category, pat_list in patterns.items():
        for p in pat_list:
            matches = re.findall(p, text, re.IGNORECASE)
            for m in matches:
                m = m.strip().rstrip(".,;")
                if len(m) > 3 and len(m) < 50:
                    result[category].append(m)

    # Deduplicate
    for k in result:
        result[k] = _deduplicate(result[k])

    return result


def _extract_skills(text: str) -> List[str]:
    """Extract general skills (not just tech)."""
    known_skills = [
        # Design
        "ui/ux", "ui design", "ux design", "graphic design", "motion design", "3d modeling",
        "video editing", "photo editing", "illustration", "animation", "wireframing",
        "prototyping", "figma", "photoshop", "blender", "fusion 360", "canva",
        # Writing
        "content writing", "copywriting", "technical writing", "creative writing",
        "blogging", "editing", "proofreading", "storytelling",
        # Communication
        "public speaking", "presentation", "communication", "negotiation",
        "leadership", "team management", "project management", "mentoring",
        "teaching", "training", "coaching",
        # Business
        "entrepreneurship", "marketing", "seo", "social media", "community building",
        "product management", "business development", "sales",
        # Music / Arts
        "singing", "guitar", "piano", "drums", "music production", "djing",
        "painting", "drawing", "photography", "cooking",
        # Sports / Fitness
        "yoga", "meditation", "running", "swimming", "cycling", "gym", "workout",
        "basketball", "football", "cricket", "badminton", "tennis", "chess",
        # General
        "problem solving", "critical thinking", "analytical", "research",
        "data analysis", "data science", "machine learning", "deep learning",
    ]
    found = set()
    lower = text.lower()
    for skill in known_skills:
        if re.search(_wb(skill.lower()), lower):
            found.add(skill)
    return sorted(found)


def _extract_social_media(text: str) -> Dict[str, List[str]]:
    """Extract social media handles, emails, URLs."""
    result = {"email": [], "github": [], "twitter": [], "linkedin": [], "discord": [], "other": []}
    # Emails
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    for e in emails:
        skip = {"example.com", "test.com", "domain.com", "email.com", "@gmail.com", "@yahoo.com", "@outlook.com", "@hotmail.com"}
        domain = e.split("@")[1] if "@" in e else ""
        if domain not in skip and e not in result["email"]:
            result["email"].append(e)
    # GitHub
    gh = re.findall(r"github\.com/([A-Za-z0-9_-]+)", text)
    for g in gh:
        if g not in result["github"]:
            result["github"].append(g)
    # Twitter
    tw = re.findall(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)", text)
    for t in tw:
        if t not in result["twitter"]:
            result["twitter"].append(t)
    # LinkedIn
    li = re.findall(r"linkedin\.com/(?:in|company)/([A-Za-z0-9_-]+)", text)
    for l in li:
        if l not in result["linkedin"]:
            result["linkedin"].append(l)
    return result


def _extract_languages(text: str) -> List[str]:
    """Extract natural languages mentioned."""
    known = [
        "english", "hindi", "marathi", "bengali", "tamil", "telugu", "kannada", "malayalam",
        "gujarati", "punjabi", "urdu", "sanskrit", "odia", "assamese",
        "spanish", "french", "german", "chinese", "japanese", "korean", "arabic",
        "russian", "portuguese", "italian", "dutch", "turkish", "vietnamese",
        "thai", "swedish", "norwegian", "danish", "finnish", "polish",
    ]
    found = set()
    lower = text.lower()
    for lang in known:
        if re.search(_wb(lang), lower):
            found.add(lang.capitalize())
    return sorted(found)


def _extract_devices_os(text: str) -> Dict[str, List[str]]:
    """Extract devices, operating systems, hardware mentions."""
    result = {"os": [], "devices": [], "hardware": []}
    lower = text.lower()
    # OS
    oss = ["windows 11", "windows 10", "windows", "macos", "linux", "ubuntu", "debian", "fedora", "arch", "kali", "android", "ios", "ipados"]
    for os_name in oss:
        if re.search(_wb(os_name), lower):
            if os_name.capitalize() not in result["os"]:
                result["os"].append(os_name.capitalize() if os_name[0].islower() else os_name)
    # Devices
    devices = ["iphone", "ipad", "macbook", "macbook pro", "macbook air", "imac", "mac mini",
               "samsung galaxy", "oneplus", "pixel", "xiaomi", "dell xps", "thinkpad",
               "surface pro", "surface laptop", "raspberry pi", "arduino", "esp32", "esp8266"]
    for d in devices:
        if re.search(_wb(d), lower):
            if d.title() not in result["devices"]:
                result["devices"].append(d.title() if "_" not in d else d)
    # Hardware
    hardware = ["rtx 3060", "rtx 3070", "rtx 3080", "rtx 3090", "rtx 4060", "rtx 4070", "rtx 4080", "rtx 4090",
                "intel i5", "intel i7", "intel i9", "amd ryzen 5", "amd ryzen 7", "amd ryzen 9",
                "16gb ram", "32gb ram", "64gb ram", "ssd", "nvidia", "amd"]
    for h in hardware:
        if re.search(_wb(h), lower):
            result["hardware"].append(h.upper() if h.isupper() else h.title())
    return result


def _extract_achievements(text: str) -> List[str]:
    """Extract accomplishments, awards, milestones."""
    achievements = []
    patterns = [
        r"(?:won|achieved|earned|received|awarded|completed|accomplished|successfully)\s+(.{5,80}?)(?:\.|,|$|\band\b|\bin\b|\bat\b|\bby\b|\bfor\b|\bas\b|\bon\b)",
        r"(?:award|prize|medal|trophy|certificate|certification|badge)\s*(?::|is|-|\s+)(.{5,60}?)(?:\.|,|$)",
        r"(?:ranked|rank|scored|secured|placed)\s+(.{5,60}?)(?:\.|,|$|\bin\b|\bat\b|\bby\b|\bfor\b)",
    ]
    for p in patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            m = m.strip().rstrip(".,;")
            if 5 <= len(m) <= 80 and m not in achievements:
                score = _score_item_quality(m, text)
                if score > 0.4:
                    achievements.append(m)
    return _deduplicate(achievements)


def _extract_challenges(text: str) -> List[str]:
    """Extract problems, obstacles, pain points."""
    challenges = []
    patterns = [
        r"(?:struggling with|struggled with|facing|faced|dealing with|dealt with|issue with|problem with|bug|error is|stuck on|stuck with)\s+(.{5,80}?)(?:\.|,|$|\band\b|\bbut\b|\bfor\b|\bin\b|\bwhen\b|\bbecause\b)",
        r"(?:difficult|hard|challenging|tough|complex|complicated)\s+(.{5,60}?)(?:\.|,|$|\bbut\b|\band\b|\bhowever\b)",
        r"(?:doesn't work|not working|broken|failed|crashing|crash|error\s+)\s*(.{5,80}?)(?:\.|,|$|\bwhen\b|\bif\b|\bbecause\b)",
    ]
    for p in patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            m = m.strip().rstrip(".,;")
            if 5 <= len(m) <= 80 and m not in challenges:
                score = _score_item_quality(m, text)
                if score > 0.3:
                    challenges.append(m)
    return _deduplicate(challenges)


def _extract_learning(text: str) -> Dict[str, List[str]]:
    """Extract courses, books, resources mentioned."""
    result = {"courses": [], "books": [], "resources": []}
    # Books
    books = re.findall(r"(?:book|reading|read)\s+(?:called|named|:)?\s*['\"]?([A-Z][A-Za-z0-9\s_\-'&]{3,60}?)['\"]?(?:\s+(?:by|from|about|\.|,))", text, re.IGNORECASE)
    for b in books:
        b = b.strip().rstrip(".,;")
        if b and b not in result["books"]:
            result["books"].append(b)
    # Courses
    courses = re.findall(r"(?:course|class|tutorial|workshop|bootcamp|training)\s+(?:on|in|about|of|:)?\s*([A-Za-z0-9\s_\-'&]{4,60}?)(?:\.|,|$|by|from|which)", text, re.IGNORECASE)
    for c in courses:
        c = c.strip().rstrip(".,;")
        if len(c) > 3 and c not in result["courses"]:
            result["courses"].append(c)
    return result


def _extract_entertainment(text: str) -> Dict[str, List[str]]:
    """Extract specific movies, shows, anime, music genres."""
    result = {"shows": [], "movies": [], "anime": [], "music_genres": []}
    known_anime = ["naruto", "one piece", "attack on titan", "demon slayer", "jujutsu kaisen",
                   "death note", "fullmetal alchemist", "my hero academia", "dragon ball",
                   "tokyo ghoul", "one punch man", "sword art online", "bleach", "hunter x hunter",
                   "cowboy bebop", "steins;gate", "re:zero", "vinland saga", "chainsaw man",
                   "spy x family", "haikyuu", "code geass", "evangelion"]
    known_genres = ["pop", "rock", "hip hop", "rap", "jazz", "classical", "electronic",
                    "edm", "lofi", "phonk", "metal", "punk", "reggae", "blues", "r&b",
                    "indie", "folk", "country", "k-pop", "j-pop", "anime ost",
                    "bollywood", "bhajan", "qawwali", "ghazal", "sufi"]
    lower = text.lower()
    for a in known_anime:
        if re.search(_wb(a), lower):
            result["anime"].append(a.title())
    for g in known_genres:
        if re.search(_wb(g), lower):
            result["music_genres"].append(g.capitalize())
    # Show/movie titles in quotes
    quoted = re.findall(r"""["\u201c\u201d]([A-Za-z0-9\s_\-'&]{3,50}?)["\u201c\u201d]""", text)
    for q in quoted:
        q = q.strip()
        if len(q) > 3 and q not in result["shows"]:
            result["shows"].append(q)
    return result


def _extract_personality_traits(text: str) -> List[str]:
    """Extract self-described personality traits and communication style cues."""
    traits = []
    patterns = [
        r"(?:i'm|i am|i tend to be|i consider myself|i'm very|i am very)\s+([A-Za-z\s]{3,30}?)(?:\.|,|$|person|individual|and|but)",
        r"(?:personality|nature|temperament)\s*(?::|is|-|\s+)([A-Za-z\s]{4,40}?)(?:\.|,|$)",
    ]
    known_traits = ["perfectionist", "lazy", "hardworking", "creative", "analytical", "curious",
                    "patient", "impatient", "organized", "messy", "social", "introvert", "extrovert",
                    "ambitious", "focused", "distracted", "calm", "anxious", "confident", "shy",
                    "optimistic", "pessimistic", "realistic", "practical", "theoretical", "detail-oriented",
                    "big picture", "logical", "emotional", "intuitive", "systematic", "spontaneous",
                    "planner", "improviser", "independent", "team player", "leader", "follower",
                    "morning person", "night owl", "nerd", "geek", "bookworm", "gamer"]
    lower = text.lower()
    for trait in known_traits:
        if re.search(_wb(trait), lower):
            traits.append(trait.capitalize())
    # Extract from explicit sentences
    for p in patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            m = m.strip()
            if len(m) > 3 and len(m) < 40 and m not in traits:
                traits.append(m.capitalize())
    return _deduplicate(traits)


def _extract_career(text: str) -> Dict[str, List[str]]:
    """Extract career-related information: roles, industries, work type."""
    result = {"roles": [], "industries": [], "work_types": []}
    patterns = {
        "roles": [
            r"(?:i\s+am\s+a|i'm\s+a|i\s+work\s+as\s+a|i\s+work\s+as\s+an|working\s+as\s+a|role\s+is)\s+([A-Za-z/\s&-]{5,50}?)(?:\.|,|$|at|in|for|with)",
        ],
        "industries": [
            r"(?:work in|working in|industry|sector|field\s+of)\s+([A-Za-z\s]{5,50}?)(?:\.|,|$)",
        ],
    }
    for category, pat_list in patterns.items():
        for p in pat_list:
            matches = re.findall(p, text, re.IGNORECASE)
            for m in matches:
                m = m.strip().rstrip(".,;")
                if len(m) > 3 and m not in result[category]:
                    result[category].append(m)
    return result


def _extract_health_wellness(text: str) -> Dict[str, List[str]]:
    """Extract health, fitness, sleep, wellness mentions."""
    result = {"fitness": [], "sleep": [], "health_mentions": []}
    lower = text.lower()
    # Fitness activities
    fitness_keywords = ["yoga", "meditation", "gym", "workout", "running", "jogging", "swimming",
                         "cycling", "walking", "exercise", "stretching", "pilates", "calisthenics",
                         "weight lifting", "cardio", "hiit", "sports", "cricket", "football",
                         "basketball", "badminton", "tennis", "martial arts", "boxing"]
    for f in fitness_keywords:
        if re.search(_wb(f), lower):
            result["fitness"].append(f.capitalize())
    # Sleep
    sleep_patterns = [r"(?:sleep|slept|insomnia|awake|tired|exhausted)\s*(.{3,50}?)(?:\.|,|$)"]
    for p in sleep_patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            m = m.strip()
            if m and m not in result["sleep"]:
                result["sleep"].append(m[:60])
    return result


# ─── TF-IDF Analysis ─────────────────────────────────────

_STOPWORDS: set = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was",
    "one", "our", "out", "has", "have", "been", "some", "them", "than", "its", "over",
    "such", "that", "this", "with", "will", "what", "which", "when", "where", "how",
    "who", "why", "does", "doing", "done", "about", "into", "just", "also", "very",
    "would", "could", "should", "after", "then", "there", "their", "they", "were",
    "been", "being", "does", "doing", "done", "having", "making", "getting", "using",
    "need", "know", "want", "think", "like", "look", "make", "take", "give", "work",
    "try", "tell", "feel", "call", "find", "keep", "let", "ask", "seem", "help",
    "talk", "turn", "start", "show", "hear", "play", "run", "move", "live", "believe",
    "hold", "bring", "happen", "write", "provide", "sit", "stand", "lose", "pay",
    "meet", "include", "continue", "set", "learn", "change", "lead", "understand",
    "watch", "follow", "stop", "create", "speak", "read", "allow", "add", "spend",
    "grow", "open", "walk", "win", "offer", "remember", "love", "consider", "appear",
    "buy", "wait", "serve", "die", "send", "expect", "build", "stay", "fall", "cut",
    "reach", "kill", "remain", "suggest", "raise", "pass", "sell", "require", "report",
    "decide", "pull", "push", "draw", "break", "stuff", "thing", "things", "something",
    "anything", "nothing", "everything", "someone", "anyone", "everyone", "somebody",
    "anybody", "everybody", "way", "ways", "lot", "lots", "bit", "little", "much",
    "many", "more", "most", "few", "less", "enough", "good", "bad", "great", "big",
    "small", "new", "old", "first", "last", "long", "right", "high", "different",
    "same", "next", "important", "able", "sure", "real", "hard", "easy", "best",
    "better", "worst", "worse", "okay", "ok", "yes", "no", "yeah", "sure", "thanks",
    "please", "sorry", "hello", "hi", "hey", "well", "so", "now", "then", "here",
    "there", "actually", "basically", "really", "pretty", "quite", "maybe", "perhaps",
    "probably", "always", "never", "often", "sometimes", "usually", "already", "still",
    "even", "just", "only", "also", "too", "very", "quite", "rather", "kind", "sort",
    "type", "like", "example", "mean", "going", "got", "get", "got", "gotten",
    "let", "lets", "let's", "dont", "don't", "doesnt", "doesn't", "didnt", "didn't",
    "wont", "won't", "wouldnt", "wouldn't", "couldnt", "couldn't", "shouldnt", "shouldn't",
    "cant", "can't", "isnt", "isn't", "arent", "aren't", "wasnt", "wasn't", "werent",
    "weren't", "hasnt", "hasn't", "havent", "haven't", "hadnt", "hadn't", "im", "i'm",
    "ive", "i've", "id", "i'd", "ill", "i'll", "youre", "you're", "youve", "you've",
    "youd", "you'd", "youll", "you'll", "hes", "he's", "shes", "she's", "its", "it's",
    "we're", "weve", "we've", "wed", "we'd", "well", "we'll", "theyd", "they'd",
    "theyre", "they're", "theyve", "they've", "theyll", "they'll", "there's", "theres",
    "thats", "that's", "whats", "what's", "whos", "who's", "whove", "who've",
    "wheres", "where's", "whens", "when's", "whys", "why's", "hows", "how's",
}
"""Common English stopwords for TF-IDF filtering."""


def _tokenize(text: str) -> List[str]:
    """Tokenize text: lowercase, keep alpha tokens >= 3 chars, exclude stopwords."""
    tokens = re.findall(r'[a-zA-Z][a-zA-Z0-9]{2,}', text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


def compute_tfidf(documents: List[str]) -> List[Dict[str, float]]:
    """
    Full TF-IDF computation over a list of documents.
    
    Steps:
      1. Tokenize each document (lowercase, min 3 chars, stopwords removed).
      2. Compute Term Frequency (TF) = raw count per document.
      3. Compute Inverse Document Frequency (IDF) using smoothed formula:
             idf(t) = log((1 + N) / (1 + df(t))) + 1
         where N = total documents, df(t) = docs containing term t.
      4. Compute TF-IDF = TF * IDF for each term in each document.
      5. Normalize TF by max TF per document so longer docs don't dominate.
    
    Returns list of {term: tfidf_score} dicts, one per document.
    """
    tokenized = [_tokenize(doc) for doc in documents]
    N = len(tokenized)
    
    # --- Step 3: IDF ---
    doc_freq: Counter = Counter()
    for doc_tokens in tokenized:
        for term in set(doc_tokens):
            doc_freq[term] += 1
    
    idf: Dict[str, float] = {}
    for term, df in doc_freq.items():
        idf[term] = math.log((1.0 + N) / (1.0 + df)) + 1.0  # smoothed
    
    # --- Step 4 & 5: TF-IDF per document ---
    results = []
    for doc_tokens in tokenized:
        tf = Counter(doc_tokens)
        max_tf = float(max(tf.values())) if tf else 1.0
        tfidf: Dict[str, float] = {}
        for term, freq in tf.items():
            tf_norm = freq / max_tf
            tfidf[term] = round(tf_norm * idf.get(term, 1.0), 6)
        results.append(tfidf)
    
    return results


def extract_top_tfidf_terms(
    tfidf_results: List[Dict[str, float]],
    top_n: int = 25,
) -> Dict[str, Any]:
    """
    Extract top-N terms per document and overall from TF-IDF results.
    
    Steps:
      1. Sort each document's terms by score descending, take top-N.
      2. Aggregate scores across documents (sum) for overall importance.
      3. Return structured dict with per-document and overall lists.
    """
    per_doc = []
    all_scores: Dict[str, float] = {}
    
    for doc_scores in tfidf_results:
        sorted_terms = sorted(doc_scores.items(), key=lambda x: -x[1])
        top = [{"term": t, "score": round(s, 4)} for t, s in sorted_terms[:top_n]]
        per_doc.append(top)
        for item in top:
            t = item["term"]
            s = item["score"]
            all_scores[t] = all_scores.get(t, 0.0) + s
    
    overall = sorted(all_scores.items(), key=lambda x: -x[1])[:top_n]
    overall_clean = [{"term": t, "score": round(s, 4)} for t, s in overall]
    
    return {
        "per_document": per_doc,
        "overall_top_terms": overall_clean,
    }


# Heuristic keyword sets for TF-IDF topic classification
_TECH_INDICATORS: set = {
    "python", "javascript", "typescript", "react", "node", "nodejs", "docker",
    "kubernetes", "k8s", "api", "rest", "graphql", "backend", "frontend", "fullstack",
    "database", "sql", "nosql", "postgresql", "mysql", "mongodb", "redis",
    "linux", "bash", "shell", "git", "github", "aws", "azure", "gcp", "cloud",
    "cli", "framework", "library", "sdk", "npm", "pip", "yarn", "bun",
    "package", "module", "deploy", "ci", "cd", "pipeline", "microservice",
    "container", "vm", "server", "client", "middleware", "cache", "queue",
    "websocket", "http", "tcp", "udp", "ssl", "tls", "oauth", "jwt",
    "agile", "scrum", "devops", "mlops", "automation", "scripting",
    "tensorflow", "pytorch", "llm", "ai", "ml", "nlp", "neural", "deep",
    "learning", "transformer", "gpt", "bert", "embedding", "vector",
    "android", "ios", "flutter", "swift", "kotlin", "dart", "reactnative",
    "html", "css", "tailwind", "bootstrap", "sass", "webpack", "vite",
    "rust", "golang", "go", "java", "cplusplus", "cpp", "csharp", "ruby",
    "php", "scala", "haskell", "elixir", "lua", "assembly", "wasm",
    "vim", "neovim", "vscode", "intellij", "pycharm", "ide", "emacs",
    "jupyter", "notebook", "colab", "databricks", "spark", "hadoop",
    "algorithm", "datastructure", "leetcode", "hackerrank", "codeforces",
    "testing", "unittest", "pytest", "jest", "cypress", "selenium",
    "debugging", "profiling", "logging", "monitoring", "grafana", "prometheus",
    "blockchain", "crypto", "web3", "solidity", "smart", "contract",
    "socket", "async", "concurrency", "parallel", "multithreading",
    "regex", "serialization", "encryption", "hashing", "compression",
}

_INTEREST_INDICATORS: set = {
    "music", "gaming", "reading", "writing", "design", "art", "photo",
    "photography", "video", "editing", "travel", "cooking", "baking", "sports",
    "anime", "manga", "movies", "films", "fitness", "gym", "yoga", "meditation",
    "drawing", "painting", "singing", "dancing", "guitar", "piano", "instrument",
    "hiking", "camping", "fishing", "gardening", "craft", "diy", "fashion",
    "makeup", "skincare", "beauty", "food", "coffee", "tea", "cooking",
    "podcast", "streaming", "twitch", "youtube", "tiktok", "instagram",
    "comics", "books", "novel", "poetry", "chess", "puzzle", "board",
    "cars", "bike", "motorcycle", "drone", "rc", "model", "train",
}

_SKILL_INDICATORS: set = {
    "leadership", "management", "communication", "teamwork", "problem",
    "solving", "critical", "thinking", "creativity", "adaptability",
    "organization", "planning", "research", "analysis", "writing",
    "editing", "public", "speaking", "presentation", "negotiation",
    "mentoring", "teaching", "coaching", "design", "drawing", "coding",
    "programming", "typing", "data", "entry", "cold", "calling", "sales",
    "marketing", "seo", "sem", "analytics", "accounting", "bookkeeping",
    "investing", "trading", "stock", "crypto", "tax", "legal", "medical",
    "nursing", "teaching", "tutoring", "counseling", "therapy",
}


def classify_tfidf_terms(tfidf_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify TF-IDF top terms into tech, interests, skills, and general topics.
    
    Uses keyword heuristics against the aggregated top terms to suggest
    profile fields the regex extractors may have missed.
    """
    top_terms = [t["term"] for t in tfidf_data.get("overall_top_terms", [])]
    
    discovered = {
        "tech_terms": [],
        "interest_terms": [],
        "skill_terms": [],
        "topic_suggestions": [],
    }
    
    for term in top_terms:
        if term in _TECH_INDICATORS:
            discovered["tech_terms"].append(term)
        if term in _INTEREST_INDICATORS:
            discovered["interest_terms"].append(term)
        if term in _SKILL_INDICATORS:
            discovered["skill_terms"].append(term)
        # Suggest longer terms not already categorized as potential topics
        if len(term) > 5 and term not in _TECH_INDICATORS and term not in _INTEREST_INDICATORS and term not in _SKILL_INDICATORS:
            discovered["topic_suggestions"].append(term)
    
    # De-duplicate
    for key in discovered:
        discovered[key] = sorted(set(discovered[key]))
    
    return discovered


# ─── Aggregation ───────────────────────────────────────────

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
        "interests_hobbies": _extract_interests_hobbies(text),
        "skills": _extract_skills(text),
        "social_media": _extract_social_media(text),
        "languages": _extract_languages(text),
        "devices_os": _extract_devices_os(text),
        "achievements": _extract_achievements(text),
        "challenges": _extract_challenges(text),
        "learning": _extract_learning(text),
        "entertainment": _extract_entertainment(text),
        "personality_traits": _extract_personality_traits(text),
        "career": _extract_career(text),
        "health_wellness": _extract_health_wellness(text),
        "audited_at": datetime.now().isoformat(),
    }

def audit_imported_data(imported: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Audit all imported conversations and aggregate findings.

    Also runs TF-IDF analysis over individual conversations to discover
    important topics, validate extracted items, and suggest new entries
    the regex extractors may have missed.
    """
    all_text = ""
    conversation_count = 0
    documents: List[str] = []

    for item in imported:
        for conv in item.get("conversations", []):
            conv_text = ""
            for turn in conv.get("turns", []):
                content = turn.get("content", "")
                all_text += content + "\n"
                conv_text += content + "\n"
            if conv_text.strip():
                documents.append(conv_text)
            conversation_count += 1

    # --- TF-IDF analysis over individual conversations ---
    tfidf_analysis: Dict[str, Any] = {"enabled": False, "conversations_analyzed": 0}
    if len(documents) >= 2:
        try:
            tfidf_scores = compute_tfidf(documents)
            tfidf_data = extract_top_tfidf_terms(tfidf_scores)
            classified = classify_tfidf_terms(tfidf_data)
            tfidf_analysis = {
                "enabled": True,
                "conversations_analyzed": len(documents),
                "top_terms_per_conversation": tfidf_data["per_document"],
                "overall_top_terms": tfidf_data["overall_top_terms"],
                "classified": classified,
            }
        except Exception as e:
            tfidf_analysis = {"enabled": False, "error": str(e)}

    return {
        "conversations_audited": conversation_count,
        "sources_imported": len(imported),
        "audited_at": datetime.now().isoformat(),
        "findings": audit_all_text(all_text),
        "tfidf_analysis": tfidf_analysis,
    }

# ─── Profile Management ────────────────────────────────────

_PROFILE_BAK = _PROFILE_FILE + ".bak"


def load_profile() -> Dict[str, Any]:
    if os.path.exists(_PROFILE_FILE):
        try:
            with open(_PROFILE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # Attempt to load backup
            if os.path.exists(_PROFILE_BAK):
                try:
                    with open(_PROFILE_BAK, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
    return {"name": None, "version": 1, "audits": [], "last_updated": None}


def save_profile(profile: Dict[str, Any]) -> None:
    """Atomically write profile to disk with .bak backup."""
    os.makedirs(os.path.dirname(_PROFILE_FILE), exist_ok=True)
    # Write to temp file first
    tmp = _PROFILE_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=4)
        # Verify we can read it back
        with open(tmp, "r", encoding="utf-8") as f:
            json.load(f)
        # Backup existing file
        if os.path.exists(_PROFILE_FILE):
            try:
                os.replace(_PROFILE_FILE, _PROFILE_BAK)
            except Exception:
                pass
        # Atomic replace
        os.replace(tmp, _PROFILE_FILE)
    except Exception:
        # Clean up temp on failure
        try:
            os.remove(tmp)
        except Exception:
            pass
        raise

    # Regenerate markdown after every save
    try:
        generate_profile_markdown(profile)
    except Exception:
        pass


# ─── Profile Validation & Cleaning ──────────────────────

_SUSPICIOUS_SCALARS: Dict[str, set] = {
    "location": {
        "google", "microsoft", "amazon", "apple", "meta", "netflix",
        "github", "gitlab", "docker", "slack", "notion", "figma",
        "youtube", "twitter", "linkedin", "reddit", "whatsapp",
        "chrome", "firefox", "safari", "edge", "linux", "windows",
        "macos", "android", "ios", "ubuntu", "debian", "python",
        "react", "node", "the", "this", "that", "here", "there",
        "where", "some", "any", "all", "home", "school", "college",
        "university", "work", "office", "online", "everywhere",
        "nowhere", "somewhere", "default", "none", "null",
        "india", "usa", "uk", "canada", "australia",
    },
    "age_grade": set(),
    "name": {"account", "user", "human", "assistant", "claude", "chatgpt",
             "gemini", "customer", "client", "student", "teacher", "admin",
             "guest", "default", "person", "someone", "nobody", "none",
             "test", "demo", "null", "undefined"},
}

_BAD_LIST_PATTERNS = [
    re.compile(r'https?://\S+', re.IGNORECASE),
    re.compile(r'www\.\S+', re.IGNORECASE),
    re.compile(r'[\\/]'),  # file paths
    re.compile(r'^[\s.,;:\-_\'"!?]+$'),
    re.compile(r'^\d+$'),  # pure numbers
    re.compile(r'^\d+[\.\,]\d+$'),  # floating point numbers
    re.compile(r'^[A-Za-z]\s*[.,;:\-]$'),  # single letter with punct
]

_FRAGMENT_PATTERNS = [
    re.compile(r'^(?:the|this|that|these|those|it|they|we|you|he|she)\s', re.IGNORECASE),
    re.compile(r'^\s*(?:and|or|but|so|if|because|when|while|where|which|who|that)\s', re.IGNORECASE),
    re.compile(r'^(?:also|then|here|there|now|just|very|too|only|even|still|already)\s', re.IGNORECASE),
    re.compile(r'^(?:is|are|was|were|has|have|had|been|being|do|does|did|will|would|can|could|shall|should|may|might|must)\s', re.IGNORECASE),
]

_TECH_LOWERCASE: Dict[str, str] = {
    "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
    "reactjs": "React", "react.js": "React", "react": "React",
    "nodejs": "Node.js", "node.js": "Node.js", "node": "Node.js",
    "nextjs": "Next.js", "next.js": "Next.js",
    "vuejs": "Vue.js", "vue.js": "Vue.js",
    "expressjs": "Express.js", "express.js": "Express.js",
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    "mysql": "MySQL", "mongodb": "MongoDB", "sqlite": "SQLite",
    "redis": "Redis", "github": "GitHub", "gitlab": "GitLab",
    "github actions": "GitHub Actions", "ci/cd": "CI/CD",
    "graphql": "GraphQL", "rest api": "REST API", "restapi": "REST API",
    "k8s": "Kubernetes", "kubernetes": "Kubernetes",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch",
    "scikit-learn": "scikit-learn", "scikit learn": "scikit-learn",
    "opencv": "OpenCV", "huggingface": "Hugging Face",
    "langchain": "LangChain", "webpack": "Webpack", "vite": "Vite",
    "tailwind": "Tailwind CSS", "tailwindcss": "Tailwind CSS",
    "bootstrap": "Bootstrap", "material ui": "Material UI", "materialui": "Material UI",
    "chakra": "Chakra UI", "fastapi": "FastAPI",
    "flask": "Flask", "django": "Django",
    "postman": "Postman", "figma": "Figma",
    "vs code": "VS Code", "vscode": "VS Code",
    "pycharm": "PyCharm", "intellij": "IntelliJ",
    "vim": "Vim", "neovim": "Neovim",
    "jupyter": "Jupyter", "html": "HTML", "css": "CSS",
    "docker": "Docker", "aws": "AWS", "gcp": "GCP", "azure": "Azure",
    "linux": "Linux", "git": "Git",
    "rust": "Rust", "golang": "Go", "go": "Go",
    "java": "Java", "kotlin": "Kotlin", "swift": "Swift",
    "flutter": "Flutter", "react native": "React Native", "reactnative": "React Native",
    "android": "Android", "ios": "iOS",
    "sql": "SQL", "nosql": "NoSQL",
    "api": "API", "rest": "REST", "graphql": "GraphQL",
    "llm": "LLM", "ai": "AI", "ml": "ML", "nlp": "NLP",
    "cli": "CLI", "sdk": "SDK", "ide": "IDE",
}

_LANG_LOWERCASE: Dict[str, str] = {
    "English": "English", "Hindi": "Hindi", "Marathi": "Marathi",
    "Bengali": "Bengali", "Tamil": "Tamil", "Telugu": "Telugu",
    "Kannada": "Kannada", "Malayalam": "Malayalam", "Gujarati": "Gujarati",
    "Punjabi": "Punjabi", "Urdu": "Urdu", "Sanskrit": "Sanskrit",
    "Odia": "Odia", "Assamese": "Assamese",
    "Spanish": "Spanish", "French": "French", "German": "German",
    "Chinese": "Chinese", "Japanese": "Japanese", "Korean": "Korean",
    "Arabic": "Arabic", "Russian": "Russian", "Portuguese": "Portuguese",
    "Italian": "Italian", "Dutch": "Dutch", "Turkish": "Turkish",
    "Vietnamese": "Vietnamese", "Thai": "Thai",
}


def _is_suspicious_list_item(item: str) -> bool:
    """Return True if item looks like garbage / fragment / URL / bad extraction."""
    if not item or len(item) < 3:
        return True
    for pat in _BAD_LIST_PATTERNS:
        if pat.search(item):
            return True
    # Grammatical fragment — starts with conjunction/preposition/verb
    stripped = item.strip()
    if len(stripped.split()) >= 2:
        for pat in _FRAGMENT_PATTERNS:
            if pat.search(stripped):
                return True
    # Single word, not capitalized, shorter than 5 = likely fragment
    if len(stripped.split()) == 1 and len(stripped) < 5 and not stripped[0].isupper():
        return True
    # Looks like command output or error
    if re.match(r'^(Traceback|Error|Warning|Info|DEBUG|INFO|WARNING|ERROR|CRITICAL)', stripped):
        return True
    # Contains unbalanced punctuation
    if stripped.count('(') != stripped.count(')'):
        return True
    if stripped.count('[') != stripped.count(']'):
        return True
    return False


def _normalize_item(item: str, key: str) -> str:
    """Normalize casing for tech stack and languages (case-insensitive)."""
    if key == "tech_stack":
        key_lower = item.lower()
        normalized = _TECH_LOWERCASE.get(key_lower)
        if normalized:
            return normalized
        # Fallback: preserve original if it looks reasonable
        if item[0].isupper() and len(item) > 1:
            return item
        return item.title() if len(item) > 2 else item
    if key == "languages":
        key_lower = item.lower()
        for k, v in _LANG_LOWERCASE.items():
            if k.lower() == key_lower:
                return v
        return item
    return item


def validate_profile(profile: dict) -> dict:
    """Validate profile structure, returning issues found.

    Returns:
        Dict with keys:
        - "invalid_fields": scalar fields with suspicious values
        - "missing": fields expected but absent
        - "warnings": structural issues
    """
    issues: Dict[str, list] = {"invalid_fields": [], "missing": [], "warnings": []}

    if not isinstance(profile, dict):
        issues["warnings"].append("Profile is not a dict")
        return issues

    # Check scalar fields
    for key in _SCALAR_KEYS:
        val = profile.get(key)
        if val:
            val_lower = str(val).strip().lower()
            suspected = _SUSPICIOUS_SCALARS.get(key, set())
            if val_lower in suspected:
                issues["invalid_fields"].append(key)
            # Check if value looks like a URL or code
            if re.search(r'https?://|www\.|\.com|\.org|\.io', str(val)):
                issues["invalid_fields"].append(key)

    # Check for required structure
    if "version" not in profile:
        issues["warnings"].append("Missing version field")
    if "audits" not in profile:
        issues["warnings"].append("Missing audits field")

    return issues


def clean_profile(profile: dict) -> tuple[dict, dict]:
    """Clean profile in place, removing garbage data.

    Returns:
        (cleaned_profile, change_report) where change_report has:
        - "removed": {list_key: [removed_items]}
        - "normalized": {list_key: [(old, new)]}
        - "suspicious": [scalar_key]
    """
    report: Dict[str, Any] = {"removed": {}, "normalized": {}, "suspicious": [], "scalar_reset": []}

    # Validate and reset suspicious scalar fields
    for key in _SCALAR_KEYS:
        val = profile.get(key)
        if not val:
            continue
        val_str = str(val).strip()
        val_lower = val_str.lower()
        suspected = _SUSPICIOUS_SCALARS.get(key, set())

        should_reset = False
        if val_lower in suspected:
            should_reset = True
        if re.search(r'https?://|www\.|\.com|\.org|\.io|\\|/', val_str):
            should_reset = True
        # Location that is just a first name, company, or platform
        if key == "location" and len(val_str.split()) <= 2:
            if val_lower in suspected:
                should_reset = True
        # Age/grade that looks like "Standard 64" (random word + number, not a real age)
        if key == "age_grade":
            digits = re.findall(r'\d+', val_str)
            if not digits:
                should_reset = True  # No number at all
            else:
                n = int(digits[0])
                # Educational grade context: max 12 (grade/class/standard)
                grade_keywords = ["grade", "class", "standard", "std"]
                age_keywords = ["year", "old", "age", "yo"]
                is_grade = any(kw in val_lower for kw in grade_keywords)
                is_age = any(kw in val_lower for kw in age_keywords)
                if is_grade and n > 12:
                    should_reset = True  # "Standard 64" etc.
                elif is_age and (n < 1 or n > 120):
                    should_reset = True  # Impossible age
                elif not is_grade and not is_age:
                    # Bare number - must be in reasonable range
                    if n < 3 or n > 80:
                        should_reset = True
                # Check if the text is mostly non-age context
                age_keywords = ["year", "grade", "class", "standard", "age", "old"]
                has_age_context = any(kw in val_lower for kw in age_keywords)
                if not has_age_context and len(val_str.split()) > 2:
                    should_reset = True

        if should_reset:
            report["scalar_reset"].append(key)
            report["suspicious"].append(key)
            profile[key] = None

    # Clean list fields
    for key in _LIST_KEYS:
        items = profile.get(key, [])
        if not isinstance(items, list):
            continue
        kept = []
        removed = []
        for item in items:
            if not isinstance(item, str):
                removed.append(str(item))
                continue
            if _is_suspicious_list_item(item):
                removed.append(item)
                continue
            # Field-specific checks
            if key == "goals":
                if len(item.split()) < 2:  # Single-word "goals" are useless
                    removed.append(item)
                    continue
                # Generic verb-only goals
                if item.strip().lower() in {"learn", "build", "create", "make", "get", "have", "do", "be", "go", "work", "study", "start", "finish", "complete", "improve"}:
                    removed.append(item)
                    continue
            if key == "projects":
                # Single short generic words
                if len(item) < 4 or (len(item.split()) == 1 and len(item) < 5 and item[0].islower()):
                    removed.append(item)
                    continue
            if key == "education":
                if len(item) < 4:
                    removed.append(item)
                    continue
                if item.lower() in {"the", "a", "an", "in", "at", "on", "for", "to"}:
                    removed.append(item)
                    continue
            # Normalize
            normalized = _normalize_item(item, key)
            if normalized != item:
                report["normalized"].setdefault(key, []).append((item, normalized))
                item = normalized
            kept.append(item)
        if removed:
            report["removed"][key] = removed
        profile[key] = _deduplicate(kept)

    # Clean dict-of-list fields
    for key in _DICT_KEYS:
        subdict = profile.get(key, {})
        if not isinstance(subdict, dict):
            continue
        for subkey, items in subdict.items():
            if not isinstance(items, list):
                continue
            kept = []
            removed = []
            for item in items:
                if not isinstance(item, str):
                    removed.append(str(item))
                    continue
                if _is_suspicious_list_item(item):
                    removed.append(item)
                    continue
                normalized = _normalize_item(item, subkey)
                kept.append(normalized)
            if removed:
                report["removed"].setdefault(f"{key}.{subkey}", []).extend(removed)
            subdict[subkey] = _deduplicate(kept)

    return profile, report


# ─── Confidence Scoring ─────────────────────────────────

def _score_scalar_confidence(profile: dict) -> dict:
    """Compute confidence scores for scalar fields.

    Returns dict like {"name": 0.95, "location": 0.35, "age_grade": 0.2}
    """
    conf: Dict[str, float] = {}

    # Name confidence
    name = profile.get("name")
    if name and isinstance(name, str):
        name = name.strip()
        if name.lower() in _SUSPICIOUS_SCALARS.get("name", set()):
            conf["name"] = 0.1
        elif len(name) >= 3 and name[0].isupper() and " " not in name.strip():
            conf["name"] = 0.95  # Single capitalized name
        elif len(name) >= 3 and name[0].isupper():
            conf["name"] = 0.9  # Full name
        else:
            conf["name"] = 0.3
    else:
        conf["name"] = 0.0

    # Location confidence
    loc = profile.get("location")
    if loc and isinstance(loc, str):
        loc = loc.strip()
        loc_lower = loc.lower()
        bad = _SUSPICIOUS_SCALARS.get("location", set())
        if loc_lower in bad:
            conf["location"] = 0.0
        elif len(loc) > 3 and loc[0].isupper() and "," in loc:
            conf["location"] = 0.85  # "City, Country" format
        elif len(loc) > 3 and loc[0].isupper():
            conf["location"] = 0.6  # Single place name
        else:
            conf["location"] = 0.2
    else:
        conf["location"] = 0.0

    # Age/grade confidence
    age = profile.get("age_grade")
    if age and isinstance(age, str):
        digits = re.findall(r'\d+', age)
        if digits:
            n = int(digits[0])
            if 5 <= n <= 25:
                conf["age_grade"] = 0.8  # Plausible age/grade range
            elif 3 <= n <= 80:
                conf["age_grade"] = 0.5
            else:
                conf["age_grade"] = 0.1
        else:
            conf["age_grade"] = 0.3
    else:
        conf["age_grade"] = 0.0

    return conf


def _score_list_confidence(profile: dict) -> dict:
    """Compute per-item confidence for list fields based on extraction quality.

    Returns: {"tech_stack": {"python": 0.9, ...}, ...}
    """
    conf: Dict[str, Dict[str, float]] = {}

    for key in _LIST_KEYS:
        items = profile.get(key, [])
        if not isinstance(items, list) or not items:
            continue
        item_conf: Dict[str, float] = {}
        for item in items:
            if not isinstance(item, str):
                continue
            # Items from known lists (tech, languages) get high confidence
            if key == "tech_stack":
                if item in _TECH_LOWERCASE.values() or item in _TECH_LOWERCASE:
                    item_conf[item] = 0.95
                elif item[0].isupper() and len(item) > 1:
                    item_conf[item] = 0.7
                else:
                    item_conf[item] = 0.5
            elif key == "languages":
                if item in _LANG_LOWERCASE.values() or item in _LANG_LOWERCASE:
                    item_conf[item] = 0.95
                else:
                    item_conf[item] = 0.5
            elif key in ("education", "projects"):
                item_conf[item] = 0.7  # Named entities
            elif key in ("goals", "achievements"):
                item_conf[item] = 0.6  # Longer text, inherently ambiguous
            elif key == "skills":
                item_conf[item] = 0.8
            else:
                item_conf[item] = 0.5
        if item_conf:
            conf[key] = item_conf

    return conf


def _inject_confidence(profile: dict) -> dict:
    """Add confidence metadata to profile.

    Stores _confidence dict with scalar and per-list-item scores.
    """
    conf: Dict[str, Any] = {}
    conf.update(_score_scalar_confidence(profile))
    conf.update(_score_list_confidence(profile))
    profile["_confidence"] = conf
    return profile


# ─── Profile Merge ──────────────────────────────────────

_LIST_KEYS = ["education", "projects", "relationships", "goals", "tech_stack", "achievements", "challenges", "skills", "languages", "personality_traits"]
_SCALAR_KEYS = ["name", "age_grade", "location"]
_DICT_KEYS = ["preferences", "interests_hobbies", "social_media", "devices_os", "learning", "entertainment", "career", "health_wellness", "social_media"]

def _merge_list_findings(profile: Dict, findings: Dict, key: str) -> list:
    """Merge a list field, returning new items added."""
    existing = set(p.lower().strip() if isinstance(p, str) else str(p) for p in profile.get(key, []))
    new_items = []
    for item in findings.get(key, []):
        if isinstance(item, str) and item.lower().strip() not in existing:
            new_items.append(item)
            existing.add(item.lower().strip())
    if new_items:
        profile.setdefault(key, []).extend(new_items)
    return new_items

def _merge_dict_findings(profile: Dict, findings: Dict, key: str) -> Dict[str, list]:
    """Merge a dict-of-lists field, returning {subkey: [new_items]}."""
    changes = {}
    for subkey in findings.get(key, {}):
        existing = set(p.lower().strip() if isinstance(p, str) else str(p) for p in profile.get(key, {}).get(subkey, []))
        new_items = []
        for item in findings[key].get(subkey, []):
            if isinstance(item, str) and item.lower().strip() not in existing:
                new_items.append(item)
                existing.add(item.lower().strip())
        if new_items:
            profile.setdefault(key, {}).setdefault(subkey, []).extend(new_items)
            changes[subkey] = new_items
    return changes

def update_profile_with_audit(audit_result: Dict[str, Any]) -> Dict[str, Any]:
    """Merge audit findings into the user profile. Only adds NEW information."""
    profile = load_profile()
    findings = audit_result.get("findings", {})

    changes = {}

    # Scalar fields: replace if new value is found
    for key in _SCALAR_KEYS:
        val = findings.get(key)
        if val and val != profile.get(key):
            changes[key] = {"old": profile.get(key), "new": val}
            profile[key] = val

    # List fields: append new items
    for key in _LIST_KEYS:
        new_items = _merge_list_findings(profile, findings, key)
        if new_items:
            changes[key] = {"added": new_items}

    # Dict-of-lists fields: merge per subkey
    for key in _DICT_KEYS:
        if key in findings:
            subchanges = _merge_dict_findings(profile, findings, key)
            if subchanges:
                changes[key] = subchanges

    # ── Merge TF-IDF classified terms into profile ──
    tfidf = audit_result.get("tfidf_analysis", {})
    if tfidf.get("enabled"):
        classified = tfidf.get("classified", {})

        # Boost tech_stack with high-TF-IDF tech terms not already there
        existing_tech = set(t.lower() for t in profile.get("tech_stack", []))
        tfidf_tech_added = []
        for t in classified.get("tech_terms", []):
            t_normalized = _normalize_item(t, "tech_stack")
            if t_normalized.lower() not in existing_tech:
                profile.setdefault("tech_stack", []).append(t_normalized)
                existing_tech.add(t_normalized.lower())
                tfidf_tech_added.append(t_normalized)
        if tfidf_tech_added:
            changes.setdefault("tech_stack", {}).setdefault("tfidf_discovered", tfidf_tech_added)

        # Boost skills with TF-IDF skill terms
        existing_skills = set(s.lower() for s in profile.get("skills", []))
        tfidf_skills_added = []
        for t in classified.get("skill_terms", []):
            if t not in existing_skills:
                profile.setdefault("skills", []).append(t.capitalize())
                existing_skills.add(t)
                tfidf_skills_added.append(t.capitalize())
        if tfidf_skills_added:
            changes.setdefault("skills", {}).setdefault("tfidf_discovered", tfidf_skills_added)

        # Boost interests with TF-IDF interest terms
        existing_interest_names = set(
            i.lower().strip() for i in profile.get("interests_hobbies", {}).get("hobbies", [])
        )
        tfidf_interest_added = []
        for t in classified.get("interest_terms", []):
            if t not in existing_interest_names:
                profile.setdefault("interests_hobbies", {}).setdefault("hobbies", []).append(t.capitalize())
                existing_interest_names.add(t)
                tfidf_interest_added.append(t.capitalize())
        if tfidf_interest_added:
            changes.setdefault("interests_hobbies", {}).setdefault("tfidf_discovered", tfidf_interest_added)

        # Store raw TF-IDF topics as profile metadata for reference
        overall = tfidf.get("overall_top_terms", [])
        if overall:
            profile["last_tfidf_topics"] = [t["term"] for t in overall[:15]]

    profile.setdefault("audits", []).append({
        "timestamp": audit_result.get("audited_at", datetime.now().isoformat()),
        "conversations_audited": audit_result.get("conversations_audited", 0),
        "changes_found": len(changes),
    })
    profile["last_updated"] = datetime.now().isoformat()
    profile["version"] = profile.get("version", 1) + 1 if changes else profile.get("version", 1)

    # Clean and inject confidence before saving
    try:
        clean_profile(profile)
        _inject_confidence(profile)
    except Exception:
        pass

    save_profile(profile)
    return changes

def generate_profile_markdown(profile: Optional[Dict[str, Any]] = None) -> str:
    """Generate a detailed user profile markdown from all accumulated data."""
    if profile is None:
        profile = load_profile()

    md = f"""# User Profile - Friday Memory System

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Profile Version: {profile.get('version', 1)}*
*Total Audits: {len(profile.get('audits', []))}*
*Total Conversations Audited: {sum(a.get('conversations_audited', 0) for a in profile.get('audits', []))}*

---

## Basic Information

| Field | Value |
|-------|-------|
"""

    md += f"| Name | {profile.get('name', 'Unknown')} |\n"
    md += f"| Age/Grade | {profile.get('age_grade', 'Unknown')} |\n"
    md += f"| Location | {profile.get('location', 'Unknown')} |\n"
    languages = profile.get("languages", [])
    md += f"| Languages | {', '.join(languages) if languages else 'Unknown'} |\n"

    md += _md_section("Education", profile.get("education"))
    md += _md_section("Projects", profile.get("projects"))

    tech_stack = profile.get("tech_stack", [])
    if tech_stack:
        md += "\n## Technology Stack\n\n"
        tags = "`" + "` `".join(tech_stack) + "`"
        md += f"{tags}\n"

    md += _md_section("Goals & Aspirations", profile.get("goals"))
    md += _md_section("Relationships", profile.get("relationships"))
    md += _md_section("Achievements", profile.get("achievements"))
    md += _md_section("Challenges & Pain Points", profile.get("challenges"))
    md += _md_section("Skills", profile.get("skills"))
    md += _md_section("Personality Traits", profile.get("personality_traits"))

    # Career
    career = profile.get("career", {})
    if any(career.values()):
        md += "\n## Career\n\n"
        for subkey in ["roles", "industries", "work_types"]:
            items = career.get(subkey, [])
            if items:
                md += f"### {subkey.replace('_', ' ').title()}\n\n"
                for item in items:
                    md += f"- {item}\n"
                md += "\n"

    # Preferences
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

    # Interests & Hobbies
    interests = profile.get("interests_hobbies", {})
    if any(interests.values()):
        md += "\n## Interests & Hobbies\n\n"
        for subkey in ["hobbies", "activities", "topics_of_interest"]:
            items = interests.get(subkey, [])
            if items:
                md += f"### {subkey.replace('_', ' ').title()}\n\n"
                for item in items:
                    md += f"- {item}\n"
                md += "\n"

    # Entertainment
    ent = profile.get("entertainment", {})
    if any(ent.values()):
        md += "\n## Entertainment\n\n"
        for subkey in ["shows", "movies", "anime", "music_genres"]:
            items = ent.get(subkey, [])
            if items:
                md += f"### {subkey.replace('_', ' ').title()}\n\n"
                for item in items:
                    md += f"- {item}\n"
                md += "\n"

    # Social Media
    social = profile.get("social_media", {})
    if any(social.values()):
        md += "\n## Social Media\n\n"
        for subkey in ["email", "github", "twitter", "linkedin", "discord", "other"]:
            items = social.get(subkey, [])
            if items:
                if subkey == "email":
                    md += "### Email\n\n" + "\n".join(f"- `{e}`" for e in items) + "\n\n"
                else:
                    md += f"### {subkey.capitalize()}\n\n" + "\n".join(f"- {item}" for item in items) + "\n\n"

    # Devices & OS
    devices = profile.get("devices_os", {})
    if any(devices.values()):
        md += "\n## Devices & Operating Systems\n\n"
        for subkey in ["os", "devices", "hardware"]:
            items = devices.get(subkey, [])
            if items:
                md += f"### {subkey.capitalize()}\n\n"
                for item in items:
                    md += f"- {item}\n"
                md += "\n"

    # Health & Wellness
    health = profile.get("health_wellness", {})
    if any(health.values()):
        md += "\n## Health & Wellness\n\n"
        for subkey in ["fitness", "sleep", "health_mentions"]:
            items = health.get(subkey, [])
            if items:
                md += f"### {subkey.replace('_', ' ').title()}\n\n"
                for item in items:
                    md += f"- {item}\n"
                md += "\n"

    # Learning
    learning = profile.get("learning", {})
    if any(learning.values()):
        md += "\n## Learning & Resources\n\n"
        for subkey in ["courses", "books", "resources"]:
            items = learning.get(subkey, [])
            if items:
                md += f"### {subkey.capitalize()}\n\n"
                for item in items:
                    md += f"- {item}\n"
                md += "\n"

    # ── TF-IDF Discovered Topics ──
    tfidf_topics = profile.get("last_tfidf_topics", [])
    if tfidf_topics:
        md += "\n## Key Topics (TF-IDF Analysis)\n\n"
        md += "Topics statistically important across conversations:\n\n"
        md += "`" + "` `".join(tfidf_topics) + "`\n\n"

    # ── Audit source breakdown ──
    total_convs = sum(a.get("conversations_audited", 0) for a in profile.get("audits", []))
    md += f"\n## Statistics\n\n"
    md += f"- **Total Conversations Audited:** {total_convs}\n"
    md += f"- **Profile Version:** {profile.get('version', 1)}\n"
    md += f"- **Last Updated:** {profile.get('last_updated', 'Never')}\n\n"

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


def _md_section(title: str, items: list) -> str:
    """Helper: generate a markdown section if items exist."""
    if not items:
        return ""
    md = f"\n## {title}\n\n"
    for item in items:
        md += f"- {item}\n"
    return md

# ─── Vector Memory Indexing ────────────────────────────

def _index_profile_to_vector_memory(profile: Dict[str, Any]) -> None:
    """Index profile data into vector memory for semantic retrieval.

    Pushes profile summary, projects, goals, tech stack, preferences,
    and TF-IDF topics into ChromaDB with appropriate metadata.
    Silently skipped if vector memory is unavailable.
    """
    try:
        from friday.vector_memory import get_vector_memory
        vm = get_vector_memory()
        if not vm or not vm.is_available():
            return
    except Exception:
        return

    try:
        # Profile summary as a single rich document
        summary = build_user_memory_context(max_chars=2000)
        if summary:
            vm.add(
                text=summary,
                metadata={"source": "memory_import", "type": "profile_summary"},
            )

        # Projects
        for proj in profile.get("projects", []):
            if isinstance(proj, str) and len(proj) > 3:
                vm.add(
                    text=f"Project: {proj}",
                    metadata={"source": "memory_import", "type": "project"},
                )

        # Goals
        for goal in profile.get("goals", []):
            if isinstance(goal, str) and len(goal) > 3:
                vm.add(
                    text=f"Goal: {goal}",
                    metadata={"source": "memory_import", "type": "goal"},
                )

        # Tech stack
        tech = profile.get("tech_stack", [])
        if tech:
            vm.add(
                text=f"Tech stack: {', '.join(tech)}",
                metadata={"source": "memory_import", "type": "preference"},
            )

        # Preferences summary
        prefs = profile.get("preferences", {})
        pref_items = []
        for cat, items in prefs.items():
            if isinstance(items, list) and items:
                pref_items.append(f"{cat}: {', '.join(str(i) for i in items[:5])}")
        if pref_items:
            vm.add(
                text=f"Preferences: {'; '.join(pref_items)}",
                metadata={"source": "memory_import", "type": "preference"},
            )

        # TF-IDF topics
        topics = profile.get("last_tfidf_topics", [])
        if topics:
            vm.add(
                text=f"Key topics from conversations: {', '.join(topics[:20])}",
                metadata={"source": "memory_import", "type": "topic"},
            )

        # Achievements
        for ach in profile.get("achievements", []):
            if isinstance(ach, str) and len(ach) > 3:
                vm.add(
                    text=f"Achievement: {ach}",
                    metadata={"source": "memory_import", "type": "achievement"},
                )

    except Exception:
        pass


# ─── Google Chat Import ─────────────────────────────────────

def import_from_google_chat(filepath: str) -> str:
    """Parse Google Chat / Hangouts JSON export from Google Takeout."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception as e:
        return f"[FAIL] Failed to read file: {e}"

    if not isinstance(data, dict) or "conversations" not in data or not isinstance(data["conversations"], list):
        return "[FAIL] Not a valid Google Chat export: missing 'conversations' key"

    profile = load_profile()
    user_name = (profile.get("name") or "").lower().strip()
    user_patterns = {"you", "me", "user"}
    if user_name:
        user_patterns.add(user_name)

    conversation_count = 0
    for conv in data["conversations"]:
        if not isinstance(conv, dict):
            continue
        name = conv.get("name", "Unknown Conversation")
        messages = conv.get("messages", [])
        if not isinstance(messages, list) or not messages:
            continue

        turns = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            text = msg.get("text", "")
            if not text:
                continue
            creator = msg.get("creator", {})
            if isinstance(creator, dict):
                creator_name = creator.get("name", "").lower().strip()
            else:
                creator_name = ""
            role = "user" if creator_name in user_patterns else "assistant"
            turns.append({"role": role, "content": text})

        if turns:
            sanitized_name = re.sub(r'[^\w\-_]', '_', name)[:50]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            copy_path = os.path.join(_RAW_IMPORTS_DIR, f"google_chat_{sanitized_name}_{timestamp}.json")
            conv_data = {
                "source": os.path.basename(filepath),
                "source_type": "google_chat",
                "imported_at": datetime.now().isoformat(),
                "conversations": [{"title": name[:200], "turns": turns}],
                "message_count": len(turns),
            }
            with open(copy_path, "w", encoding="utf-8") as f:
                json.dump(conv_data, f, indent=4)
            conversation_count += 1

    if conversation_count == 0:
        return "[FAIL] No conversations found in Google Chat export"

    stored = []
    for fpath in glob.glob(os.path.join(_RAW_IMPORTS_DIR, "google_chat_*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                stored.append(json.load(f))
        except Exception:
            pass

    if stored:
        try:
            audit_result = audit_imported_data(stored)
            update_profile_with_audit(audit_result)
            _index_profile_to_vector_memory(load_profile())
        except Exception:
            pass

    return f"[OK] Imported {conversation_count} conversations from Google Chat"


# ─── Gemini Activity Import ─────────────────────────────────

def parse_gemini_activity_time(time_str: str) -> Optional[datetime]:
    """Parse ISO datetime string from Gemini activity."""
    try:
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except Exception:
        return None


def import_from_gemini_activity(filepath: str) -> str:
    """Parse Gemini MyActivity.json from Google Takeout (flat, non-threaded format)."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception as e:
        return f"[FAIL] Failed to read file: {e}"

    if not isinstance(data, dict) or "activity" not in data or not isinstance(data["activity"], list):
        return "[FAIL] Not a valid Gemini activity export: missing 'activity' key"

    items = []
    for entry in data["activity"]:
        if not isinstance(entry, dict):
            continue
        if entry.get("header") != "Gemini":
            continue
        title = entry.get("title", "")
        subtitle = entry.get("subtitle", "")
        time_str = entry.get("time", "")
        if not title or not time_str:
            continue
        dt = parse_gemini_activity_time(time_str)
        if dt is None:
            continue
        items.append({"title": title, "subtitle": subtitle, "time": dt})

    if not items:
        return "[FAIL] No Gemini activity entries found"

    items.sort(key=lambda x: x["time"])

    conversations = []
    current_turns = []
    current_start = items[0]["time"]

    for item in items:
        if current_turns:
            time_diff = (item["time"] - current_start).total_seconds()
            if time_diff > 300:
                if current_turns:
                    conversations.append(current_turns)
                current_turns = []
        current_start = item["time"] if not current_turns else current_start
        current_turns.append({"role": "user", "content": item["title"]})
        if item["subtitle"]:
            current_turns.append({"role": "assistant", "content": item["subtitle"]})

    if current_turns:
        conversations.append(current_turns)

    conversation_count = 0
    for i, turns in enumerate(conversations):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        copy_path = os.path.join(_RAW_IMPORTS_DIR, f"gemini_activity_{i}_{timestamp}.json")
        conv_data = {
            "source": os.path.basename(filepath),
            "source_type": "gemini_activity",
            "imported_at": datetime.now().isoformat(),
            "conversations": [{"title": f"Gemini Activity {i+1}", "turns": turns}],
            "turn_count": len(turns),
        }
        with open(copy_path, "w", encoding="utf-8") as f:
            json.dump(conv_data, f, indent=4)
        conversation_count += 1

    if conversation_count == 0:
        return "[FAIL] No conversations could be reconstructed from Gemini activity"

    stored = []
    for fpath in glob.glob(os.path.join(_RAW_IMPORTS_DIR, "gemini_activity_*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                stored.append(json.load(f))
        except Exception:
            pass

    if stored:
        try:
            audit_result = audit_imported_data(stored)
            update_profile_with_audit(audit_result)
            _index_profile_to_vector_memory(load_profile())
        except Exception:
            pass

    return f"[OK] Imported {conversation_count} conversations from Gemini Activity"


# ─── Memory Import Tool ────────────────────────────────────

def memory_import_tool(action: str = "status", **kwargs) -> str:
    """
    Friday tool for importing and auditing chat history.
    Actions: status, import_file, import_dir, import_zip, import_exports, profile, audit, import_google_chat, import_gemini_activity
    """
    if action == "status":
        profile = load_profile()
        audits = profile.get("audits", [])
        total_convs = sum(a.get("conversations_audited", 0) for a in audits)
        p = profile
        skills = p.get("skills", [])
        langs = p.get("languages", [])
        traits = p.get("personality_traits", [])
        status_msg = (
            f"### MEMORY IMPORT STATUS\n\n"
            f"Profile Version: {p.get('version', 1)}\n"
            f"Total Audits Run: {len(audits)}\n"
            f"Total Conversations Processed: {total_convs}\n"
            f"Last Updated: {p.get('last_updated', 'Never')}\n"
            f"Name: {p.get('name', 'Not yet known')}\n"
            f"Location: {p.get('location', 'Not yet known')}\n"
            f"Languages: {', '.join(langs) if langs else 'Not yet known'}\n"
            f"Education: {', '.join(p.get('education', [])) or 'Not yet known'}\n"
            f"Tech Stack: {', '.join(p.get('tech_stack', [])) or 'Not yet known'}\n"
            f"Skills: {', '.join(skills) if skills else 'Not yet known'}\n"
            f"Projects: {len(p.get('projects', []))}\n"
            f"Goals: {len(p.get('goals', []))}\n"
            f"Achievements: {len(p.get('achievements', []))}\n"
            f"Challenges: {len(p.get('challenges', []))}\n"
            f"Personality: {', '.join(traits) if traits else 'Not yet known'}\n"
            f"Relationships: {len(p.get('relationships', []))}\n"
            f"Profile MD: {_PROFILE_MD}\n"
        )
        # Show last 10 imported source files
        source_files = []
        imports_dir = Path(_RAW_IMPORTS_DIR)
        if imports_dir.exists():
            source_files = sorted(f.name for f in imports_dir.iterdir() if f.suffix == '.json')
        if source_files:
            status_msg += "\n### Imported Source Files:\n"
            for f in source_files[-10:]:
                status_msg += f"- {f}\n"
        return status_msg

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
        _index_profile_to_vector_memory(load_profile())
        md = generate_profile_markdown()

        if changes:
            lines = [f"### AUDIT COMPLETE - New Information Found\n"]
            for key, val in changes.items():
                if isinstance(val, dict):
                    if "added" in val:
                        lines.append(f"  [ADDED] {key}: {', '.join(val['added'])}")
                    elif "old" in val:
                        lines.append(f"  [UPDATED] {key}: {val['old']} -> {val['new']}")
                    else:
                        lines.append(f"  [CHANGED] {key}: Updated")
                else:
                    lines.append(f"  [CHANGED] {key}: {val}")
            lines.append(f"\n[OK] Profile version {audit_result.get('findings', {}).get('audited_at', '?')[:10]}")
            return "\n".join(lines)
        else:
            return f"[OK] Audit complete. No new information found. ({audit_result.get('conversations_audited', 0)} conversations analyzed)"

    if action == "profile":
        md = generate_profile_markdown()
        profile = load_profile()
        p = profile
        return (
            f"### USER PROFILE\n\n"
            f"Name: {p.get('name', 'Unknown')}\n"
            f"Location: {p.get('location', 'Unknown')}\n"
            f"Age/Grade: {p.get('age_grade', 'Unknown')}\n"
            f"Languages: {', '.join(p.get('languages', [])) or 'Unknown'}\n"
            f"Education: {', '.join(p.get('education', [])) or 'Unknown'}\n"
            f"Tech Stack: {', '.join(p.get('tech_stack', [])) or 'Unknown'}\n"
            f"Skills: {', '.join(p.get('skills', [])) or 'Unknown'}\n"
            f"Projects: {len(p.get('projects', []))}\n"
            f"Goals: {len(p.get('goals', []))}\n"
            f"Achievements: {len(p.get('achievements', []))}\n"
            f"Personality: {', '.join(p.get('personality_traits', [])) or 'Unknown'}\n"
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

    if action == "repair_profile":
        profile = load_profile()
        if not profile or profile.get("version", 0) < 1:
            return "[FAIL] No profile to repair."

        issues = validate_profile(profile)
        _, report = clean_profile(profile)
        _inject_confidence(profile)
        profile["last_updated"] = datetime.now().isoformat()

        try:
            save_profile(profile)
            generate_profile_markdown()
        except Exception as e:
            return f"[FAIL] Failed to save repaired profile: {e}"

        # Optionally re-index into vector memory
        try:
            _index_profile_to_vector_memory(profile)
        except Exception:
            pass

        lines = ["### REPAIR PROFILE - Report\n"]
        if report.get("scalar_reset"):
            lines.append(f"  [RESET] Suspicious scalar fields: {', '.join(report['scalar_reset'])}")
        for key, items in report.get("removed", {}).items():
            if items:
                lines.append(f"  [REMOVED from {key}] {', '.join(items[:10])}")
                if len(items) > 10:
                    lines[-1] += f" (+{len(items)-10} more)"
        for key, pairs in report.get("normalized", {}).items():
            if pairs:
                normalized_show = [f"'{old}'->'{new}'" for old, new in pairs[:5]]
                lines.append(f"  [NORMALIZED {key}] {', '.join(normalized_show)}")
        if not report.get("scalar_reset") and not report.get("removed") and not report.get("normalized"):
            lines.append("  [OK] Profile looks clean -- no issues found.")
        if issues.get("warnings"):
            for w in issues["warnings"]:
                lines.append(f"  [WARN] {w}")

        lines.append(f"\n[OK] Profile repaired and saved.")
        return "\n".join(lines)

    if action == "doctor":
        profile = load_profile()
        if not profile or profile.get("version", 0) < 1:
            return "[FAIL] No profile to diagnose."

        lines = ["### MEMORY DOCTOR - Diagnostic Report\n"]

        # Validate
        issues = validate_profile(profile)
        if issues.get("invalid_fields"):
            lines.append(f"[ISSUE] Invalid fields: {', '.join(issues['invalid_fields'])}")
        if issues.get("warnings"):
            for w in issues["warnings"]:
                lines.append(f"[WARN] {w}")
        if not issues.get("invalid_fields") and not issues.get("warnings"):
            lines.append("[OK] Validation passed.")

        # Conflicts
        conflicts = detect_profile_conflicts(profile)
        if conflicts.get("warnings"):
            lines.append(f"\n[CONFLICTS] {len(conflicts['warnings'])} conflict(s):")
            for w in conflicts["warnings"]:
                lines.append(f"  - {w}")
        else:
            lines.append("\n[OK] No conflicts detected.")

        # Decay preview (dry run)
        _, decay_report = decay_profile_memory(dict(profile))
        if decay_report.get("removed_items"):
            lines.append(f"\n[DECAY] {len(decay_report['removed_items'])} item(s) would be removed:")
            for item in decay_report["removed_items"][:10]:
                lines.append(f"  - {item}")
            if len(decay_report["removed_items"]) > 10:
                lines[-1] += f" (+{len(decay_report['removed_items'])-10} more)"
        if decay_report.get("scalar_warnings"):
            for w in decay_report["scalar_warnings"]:
                lines.append(f"[DECAY SCALAR] {w}")
        if not decay_report.get("removed_items") and not decay_report.get("scalar_warnings"):
            lines.append("[OK] No decay needed.")
        lines.append(f"  (Pinned items spared: {decay_report.get('pinned_spared', 0)})")

        # Review queue
        queue = build_memory_review_queue(profile)
        if queue:
            lines.append(f"\n[REVIEW] {len(queue)} item(s) need review:")
            for item in queue[:10]:
                lines.append(f"  - [{item.get('id','?')}] {item.get('field','?')}: {item.get('value','?')[:60]} ({item.get('reason','?')})")
            if len(queue) > 10:
                lines.append(f"  ... and {len(queue)-10} more")
        else:
            lines.append("\n[OK] Review queue empty.")

        # Redaction test
        sample = "Contact: user@example.com or token=ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        redacted = redact_sensitive_text(sample)
        if "REDACTED" in redacted and "user@" not in redacted:
            lines.append(f"\n[OK] Redaction working (sample: '{redacted[:60]}...')")
        else:
            lines.append(f"\n[WARN] Redaction may not be working (sample result: '{redacted[:60]}')")

        # Profile size
        profile_json = json.dumps(profile, indent=2)
        lines.append(f"\n[INFO] Profile size: {len(profile_json)} bytes, {len(queue)} review items, {len(profile.get('audits', []))} audits")

        return "\n".join(lines)

    if action == "review_profile":
        profile = load_profile()
        if not profile or profile.get("version", 0) < 1:
            return "[FAIL] No profile to review."

        queue = build_memory_review_queue(profile)
        if not queue:
            return "[OK] Review queue is empty. No items need human review."

        lines = ["### MEMORY REVIEW QUEUE\n"]
        for i, item in enumerate(queue):
            lines.append(f"{i+1}. [{item['id']}]")
            lines.append(f"   Field: {item.get('field', '?')}")
            lines.append(f"   Value: {item.get('value', '?')[:80]}")
            lines.append(f"   Reason: {item.get('reason', '?')}")
            lines.append(f"   Confidence: {item.get('confidence', 'N/A')}")
            lines.append(f"   Suggested: {item.get('suggested_action', '?')}")
            lines.append("")
        lines.append(f"[QUEUE] {len(queue)} item(s) total.")
        lines.append("Use approve_memory(id=...) or reject_memory(id=...) to resolve.")
        return "\n".join(lines)

    if action == "approve_memory":
        mem_id = kwargs.get("id", "")
        if not mem_id:
            return "[FAIL] Usage: approve_memory(id='field::value')"
        profile = load_profile()
        if not profile or profile.get("version", 0) < 1:
            return "[FAIL] No profile."
        # Check if it exists in review queue
        queue = profile.get("_review_queue", [])
        new_queue = [q for q in queue if q.get("id") != mem_id]
        removed = len(queue) - len(new_queue)
        if removed == 0:
            # Maybe it was a low-confidence item - add to pinned
            parts = mem_id.split("::", 1)
            if len(parts) == 2:
                field, value = parts
                # Normalize value
                value = value.strip()
                pinned = profile.setdefault("_pinned", [])
                pin_key = f"{field}:{value.lower()}"
                if pin_key not in pinned:
                    pinned.append(pin_key)
                return f"[OK] Pinned '{value}' in '{field}' to protect from decay/removal."
            return f"[FAIL] No review item with id '{mem_id}' found."
        profile["_review_queue"] = new_queue
        # Also pin it
        parts = mem_id.split("::", 1)
        if len(parts) == 2:
            pinned = profile.setdefault("_pinned", [])
            pin_key = f"{parts[0]}:{parts[1].lower()}"
            if pin_key not in pinned:
                pinned.append(pin_key)
        try:
            save_profile(profile)
        except Exception as e:
            return f"[FAIL] Failed to save: {e}"
        return f"[OK] Approved and pinned '{mem_id}'."

    if action == "reject_memory":
        mem_id = kwargs.get("id", "")
        if not mem_id:
            return "[FAIL] Usage: reject_memory(id='field::value')"
        profile = load_profile()
        if not profile or profile.get("version", 0) < 1:
            return "[FAIL] No profile."

        # Remove from review queue
        queue = profile.get("_review_queue", [])
        new_queue = [q for q in queue if q.get("id") != mem_id]
        profile["_review_queue"] = new_queue

        # Also remove the actual value from the profile
        parts = mem_id.split("::", 1)
        removed_from_profile = False
        if len(parts) == 2:
            field, value = parts
            value = value.strip()
            items = profile.get(field, [])
            if isinstance(items, list):
                filtered = [i for i in items if not (isinstance(i, str) and i.lower().strip() == value.lower())]
                if len(filtered) != len(items):
                    profile[field] = filtered
                    removed_from_profile = True
            # Also check dict-of-list keys
            for dkey in _DICT_KEYS:
                d = profile.get(dkey, {})
                if isinstance(d, dict):
                    for subkey, subitems in d.items():
                        if isinstance(subitems, list):
                            filtered = [i for i in subitems if not (isinstance(i, str) and i.lower().strip() == value.lower())]
                            if len(filtered) != len(subitems):
                                d[subkey] = filtered
                                removed_from_profile = True

        try:
            save_profile(profile)
        except Exception as e:
            return f"[FAIL] Failed to save: {e}"

        if removed_from_profile:
            return f"[OK] Rejected '{mem_id}' and removed it from profile."
        return f"[OK] Rejected '{mem_id}' (removed from review queue, value not found in profile)."

    if action == "pin_memory":
        mem_id = kwargs.get("id", "")
        field = kwargs.get("field", "")
        value = kwargs.get("value", "")
        # Accept either id=FIELD::VALUE or separate field/value
        if not mem_id and field and value:
            mem_id = f"{field}::{value}"
        if not mem_id:
            return "[FAIL] Usage: pin_memory(id='field::value') or pin_memory(field='tech_stack', value='Python')"
        profile = load_profile()
        pinned = profile.setdefault("_pinned", [])
        parts = mem_id.split("::", 1)
        pin_key = mem_id if len(parts) == 1 else f"{parts[0]}:{parts[1].lower()}"
        if pin_key not in pinned:
            pinned.append(pin_key)
        try:
            save_profile(profile)
        except Exception as e:
            return f"[FAIL] Failed to save: {e}"
        return f"[OK] Pinned '{mem_id}'."

    if action == "unpin_memory":
        mem_id = kwargs.get("id", "")
        field = kwargs.get("field", "")
        value = kwargs.get("value", "")
        if not mem_id and field and value:
            mem_id = f"{field}::{value}"
        if not mem_id:
            return "[FAIL] Usage: unpin_memory(id='field::value')"
        profile = load_profile()
        pinned = profile.get("_pinned", [])
        parts = mem_id.split("::", 1)
        pin_key = mem_id if len(parts) == 1 else f"{parts[0]}:{parts[1].lower()}"
        if pin_key in pinned:
            pinned.remove(pin_key)
        try:
            save_profile(profile)
        except Exception as e:
            return f"[FAIL] Failed to save: {e}"
        return f"[OK] Unpinned '{mem_id}'."

    if action == "decay_profile":
        profile = load_profile()
        if not profile or profile.get("version", 0) < 1:
            return "[FAIL] No profile to decay."

        profile, decay_report = decay_profile_memory(profile)
        _inject_confidence(profile)
        profile["last_updated"] = datetime.now().isoformat()

        try:
            save_profile(profile)
        except Exception as e:
            return f"[FAIL] Failed to save decayed profile: {e}"

        lines = ["### MEMORY DECAY - Report\n"]
        if decay_report.get("removed_items"):
            lines.append(f"[REMOVED] {len(decay_report['removed_items'])} item(s):")
            for item in decay_report["removed_items"][:15]:
                lines.append(f"  - {item}")
            if len(decay_report["removed_items"]) > 15:
                lines[-1] += f" (+{len(decay_report['removed_items'])-15} more)"
        if decay_report.get("scalar_warnings"):
            for w in decay_report["scalar_warnings"]:
                lines.append(f"[WARN] {w}")
        if not decay_report.get("removed_items") and not decay_report.get("scalar_warnings"):
            lines.append("[OK] No items needed decay.")
        lines.append(f"[INFO] Pinned items spared: {decay_report.get('pinned_spared', 0)}")

        return "\n".join(lines)

    if action == "import_google_chat":
        filepath = kwargs.get("path") or kwargs.get("filepath") or kwargs.get("file")
        if not filepath or not os.path.exists(filepath):
            return f"[FAIL] File not found: {filepath}"
        return import_from_google_chat(filepath)

    if action == "import_gemini_activity":
        filepath = kwargs.get("path") or kwargs.get("filepath") or kwargs.get("file")
        if not filepath or not os.path.exists(filepath):
            return f"[FAIL] File not found: {filepath}"
        return import_from_gemini_activity(filepath)

    return f"Unknown action: {action}. Available: status, import_file, import_dir, import_zip, import_exports, audit, profile, repair_profile, doctor, review_profile, approve_memory, reject_memory, pin_memory, unpin_memory, decay_profile, import_google_chat, import_gemini_activity"


# ─── User Memory Context Builder ─────────────────────────

def build_user_memory_context(max_chars: int = 6000) -> str:
    """
    Build a compact memory-context block from the user profile.

    Uses confidence scores to decide which fields to include.
    Low-confidence scalar fields (< 0.5) are omitted.
    List items with per-item confidence < 0.3 are filtered out.
    Designed to be injected into the live session system prompt.

    Args:
        max_chars: Maximum character length for the output.

    Returns:
        A compact markdown/plain-text block with high-signal fields,
        or empty string if no usable profile data exists.
    """
    try:
        profile = load_profile()
        if not profile or profile.get("version", 0) < 1:
            return ""
        has_data = bool(
            profile.get("name")
            or profile.get("location")
            or profile.get("education")
            or profile.get("projects")
            or profile.get("tech_stack")
            or profile.get("last_tfidf_topics")
        )
        if not has_data:
            return ""
    except Exception:
        return ""

    # First, clean the profile so we don't inject garbage
    try:
        clean_profile(profile)
        _inject_confidence(profile)
    except Exception:
        pass

    conf: dict = profile.get("_confidence", {})

    def _keep(key: str, item: str) -> bool:
        """Check if item passes its per-item confidence threshold (>= 0.3)."""
        item_conf = conf.get(key, {})
        if isinstance(item_conf, dict):
            return item_conf.get(item, 0.5) >= 0.3
        return True

    parts = [
        "[USER MEMORY]",
        "This memory was inferred from imported chat history and may be imperfect.",
    ]

    # Name: include regardless (already validated)
    name = profile.get("name")
    name_conf = conf.get("name", 0) if isinstance(conf.get("name"), (int, float)) else 0
    if name and name_conf >= 0.5:
        parts.append(f"- Name: {name}")

    # Location: only if confidence >= 0.5
    loc = profile.get("location")
    loc_conf = conf.get("location", 0) if isinstance(conf.get("location"), (int, float)) else 0
    if loc and loc_conf >= 0.5:
        parts.append(f"- Location: {loc}")

    # Age/grade: only if confidence >= 0.5
    age = profile.get("age_grade")
    age_conf = conf.get("age_grade", 0) if isinstance(conf.get("age_grade"), (int, float)) else 0
    if age and age_conf >= 0.5:
        parts.append(f"- Age/Grade: {age}")

    langs = profile.get("languages", [])
    if langs:
        parts.append(f"- Languages: {', '.join(langs[:5])}")

    edu = [e for e in profile.get("education", []) if _keep("education", e)]
    if edu:
        parts.append(f"- Education: {'; '.join(edu[:3])}")

    projects = [p for p in profile.get("projects", []) if _keep("projects", p)]
    if projects:
        parts.append(f"- Key Projects: {'; '.join(projects[:5])}")

    tech = [t for t in profile.get("tech_stack", []) if _keep("tech_stack", t)]
    if tech:
        parts.append(f"- Tech: {'; '.join(tech[:10])}")

    goals = [g for g in profile.get("goals", []) if _keep("goals", g)]
    if goals:
        parts.append(f"- Goals: {'; '.join(goals[:5])}")

    prefs = profile.get("preferences", {})
    pref_parts = []
    for cat in ("browsers", "apps", "music", "food"):
        items = prefs.get(cat, [])
        if items:
            pref_parts.append(f"{cat}: {'; '.join(items[:3])}")
    if pref_parts:
        parts.append(f"- Preferences: {' | '.join(pref_parts)}")

    interests = profile.get("interests_hobbies", {})
    int_parts = []
    for subkey in ("hobbies", "activities", "topics_of_interest"):
        items = interests.get(subkey, [])
        if items:
            int_parts.append(
                f"{subkey.replace('_', ' ')}: {'; '.join(str(i) for i in items[:3])}"
            )
    if int_parts:
        parts.append(f"- Interests: {' | '.join(int_parts)}")

    learning = profile.get("learning", {})
    learn_parts = []
    for subkey in ("courses", "books", "resources"):
        items = learning.get(subkey, [])
        if items:
            learn_parts.append(f"{subkey}: {'; '.join(items[:3])}")
    if learn_parts:
        parts.append(f"- Learning: {' | '.join(learn_parts)}")

    career = profile.get("career", {})
    career_parts = []
    roles = career.get("roles", [])
    if roles:
        career_parts.append(f"roles: {'; '.join(roles[:3])}")
    industries = career.get("industries", [])
    if industries:
        career_parts.append(f"industries: {'; '.join(industries[:3])}")
    if career_parts:
        parts.append(f"- Career: {' | '.join(career_parts)}")

    challenges = profile.get("challenges", [])
    if challenges:
        parts.append(f"- Challenges: {'; '.join(challenges[:3])}")

    achievements = profile.get("achievements", [])
    if achievements:
        parts.append(f"- Achievements: {'; '.join(achievements[:3])}")

    topics = profile.get("last_tfidf_topics", [])
    if topics:
        parts.append(f"- Key Topics: {'; '.join(topics[:15])}")

    # If nothing meaningful made it in, return empty
    if len(parts) <= 2:
        return ""

    result = "\n".join(parts)
    if len(result) > max_chars:
        result = result[:max_chars].rsplit("\n", 1)[0] + "\n[TRUNCATED]"
    return result


# ─── Memory Upgrades: Redaction, Conflicts, Decay, Review ──


def redact_sensitive_text(text: str) -> str:
    """
    Redact sensitive information from text before storing in memory.

    Redacts:
    - Email addresses
    - API keys / tokens (hex or base64 patterns)
    - AWS / Azure / GCP keys
    - GitHub tokens
    - Slack tokens / webhooks
    - Private IP addresses (10.x, 172.16-31.x, 192.168.x)
    - JWT tokens
    - Phone numbers
    - Credit card numbers
    - Social security numbers / Aadhaar

    Args:
        text: Raw text to redact.

    Returns:
        Text with sensitive patterns replaced by '[REDACTED]'.
    """
    patterns = [
        # Email addresses
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[REDACTED_EMAIL]'),
        # API keys: hex (32+ chars) or base64 (40+ chars) patterns
        (r'(?i)(?:api[_-]?key|apikey|secret|token|password)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{16,}["\']?', '[REDACTED_CREDENTIAL]'),
        # Standalone hex tokens (32+ hex chars)
        (r'\b[0-9a-fA-F]{32,}\b', '[REDACTED_TOKEN]'),
        # Standalone base64-like tokens (40+ base64 chars)
        (r'\b[A-Za-z0-9+/]{40,}(?:={0,2})\b', '[REDACTED_TOKEN]'),
        # JWT tokens (header.payload.signature)
        (r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b', '[REDACTED_JWT]'),
        # Private IPv4 addresses
        (r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', '[REDACTED_IP_PRIVATE]'),
        (r'\b(?:172\.(?:1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3})\b', '[REDACTED_IP_PRIVATE]'),
        (r'\b(?:192\.168\.\d{1,3}\.\d{1,3})\b', '[REDACTED_IP_PRIVATE]'),
        # Phone numbers (basic patterns)
        (r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b', '[REDACTED_PHONE]'),
        # GitHub tokens (ghp_***)
        (r'\bgh[pso]_[A-Za-z0-9_]{36,}\b', '[REDACTED_GITHUB_TOKEN]'),
        # Slack tokens (xox[bpras]-***)
        (r'\bxox[bpras]-\d+-[A-Za-z0-9]{10,}\b', '[REDACTED_SLACK_TOKEN]'),
        # Webhook URLs
        (r'(?i)https?://hooks\.slack\.com/services/[A-Za-z0-9/]{20,}', '[REDACTED_WEBHOOK]'),
        # Credit cards (basic Luhn-checkable pattern)
        (r'\b(?:\d{4}[-\s]?){3}\d{4}\b', '[REDACTED_CC]'),
        # SSN-like (NNN-NN-NNNN)
        (r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED_SSN]'),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def detect_profile_conflicts(profile: dict) -> dict:
    """
    Detect conflicting information within the user profile.

    Checks:
    - Multiple age/grade values across audit records
    - Multiple location values across audit records
    - Conflicting name spellings
    - Projects that appear to be goals, or vice versa
    - Items that appear in multiple list categories (duplicate content)
    - Education that looks like a person name or vice versa

    Args:
        profile: The user profile dict.

    Returns:
        Dict with keys:
          - "age_grade": list of conflicting values
          - "location": list of conflicting values
          - "name": list of name variants found in audits
          - "cross_category": list of items found in suspiciously many categories
          - "warnings": list of human-readable conflict descriptions
    """
    conflicts: dict = {
        "age_grade": [],
        "location": [],
        "name": [],
        "cross_category": [],
        "warnings": [],
    }

    # Check audit history for changing scalar values
    audits = profile.get("audits", [])
    all_ages = set()
    all_locs = set()
    all_names = set()
    for audit in audits:
        findings = audit.get("findings", {})
        if isinstance(findings, dict):
            age = findings.get("age_grade")
            if age and isinstance(age, str):
                all_ages.add(age)
            loc = findings.get("location")
            if loc and isinstance(loc, str):
                all_locs.add(loc)
            name = findings.get("name")
            if name and isinstance(name, str):
                all_names.add(name)

    # Check for embedded audit_audit (nested findings)
    for audit in audits:
        af = audit.get("findings", {})
        sub = af.get("findings", {}) if isinstance(af, dict) else {}
        for f in [af, sub]:
            if isinstance(f, dict):
                age = f.get("age_grade")
                if age and isinstance(age, str):
                    all_ages.add(age)
                loc = f.get("location")
                if loc and isinstance(loc, str):
                    all_locs.add(loc)
                name = f.get("name") or f.get("person_name", "")
                if name and isinstance(name, str):
                    all_names.add(name)

    current_age = profile.get("age_grade")
    if current_age:
        all_ages.add(current_age)
    current_loc = profile.get("location")
    if current_loc:
        all_locs.add(current_loc)
    current_name = profile.get("name")
    if current_name:
        all_names.add(current_name)

    if len(all_ages) > 1:
        conflicts["age_grade"] = sorted(all_ages)
        conflicts["warnings"].append(
            f"Multiple age/grade values found: {', '.join(sorted(all_ages))}"
        )
    if len(all_locs) > 1:
        conflicts["location"] = sorted(all_locs)
        conflicts["warnings"].append(
            f"Multiple location values found: {', '.join(sorted(all_locs))}"
        )
    if len(all_names) > 1:
        conflicts["name"] = sorted(all_names)
        conflicts["warnings"].append(
            f"Multiple name variants found: {', '.join(sorted(all_names))}"
        )

    # Cross-category: items appearing in 3+ list categories
    all_list_items: dict = {}
    list_keys = [k for k in _LIST_KEYS if k not in ("languages", "personality_traits")]
    for key in list_keys:
        items = profile.get(key, [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str) and len(item) > 3:
                    norm = item.lower().strip()
                    all_list_items.setdefault(norm, []).append(key)

    for item, categories in all_list_items.items():
        if len(categories) >= 3:
            conflicts["cross_category"].append(item)
            conflicts["warnings"].append(
                f"'{item}' appears in {len(categories)} categories: {', '.join(categories)}"
            )

    return conflicts


def resolve_profile_conflicts(profile: dict) -> tuple[dict, dict]:
    """
    Auto-resolve profile conflicts by keeping the most-confident or most-recent value.

    Resolution strategy:
    - age_grade: keep the most common value across audits. If tie, keep current.
    - location: keep the most common, or most recent if tie.
    - name: keep the current name (assumed already validated). Flag others as notes.
    - cross-category: deduplicate by pruning from less specific categories.
    - Duplicate items: remove exact duplicates within same list.

    Args:
        profile: The user profile dict.

    Returns:
        (resolved_profile, resolution_report)
        resolution_report has keys: "age_grade", "location", "name", "deduplicated", "re categorized"
    """
    report: dict = {
        "age_grade": None,
        "location": None,
        "name": None,
        "deduplicated": [],
        "recategorized": [],
    }

    # Remove exact duplicates within each list
    for key in _LIST_KEYS:
        items = profile.get(key, [])
        if isinstance(items, list):
            seen = set()
            unique = []
            for item in items:
                if isinstance(item, str):
                    norm = item.lower().strip()
                    if norm not in seen:
                        seen.add(norm)
                        unique.append(item)
                    else:
                        report["deduplicated"].append(f"{key}: '{item}'")
            profile[key] = unique

    # For dict-of-list keys
    for key in _DICT_KEYS:
        d = profile.get(key, {})
        if isinstance(d, dict):
            for subkey, items in d.items():
                if isinstance(items, list):
                    seen = set()
                    unique = []
                    for item in items:
                        if isinstance(item, str):
                            norm = item.lower().strip()
                            if norm not in seen:
                                seen.add(norm)
                                unique.append(item)
                            else:
                                report["deduplicated"].append(f"{key}.{subkey}: '{item}'")
                    d[subkey] = unique

    return profile, report


def decay_profile_memory(profile: dict) -> tuple[dict, dict]:
    """
    Apply decay to profile memory: age old / unconfirmed items.

    Decay policy:
    - Items without recent confirmation (in last N audits) get demoted confidence.
    - Items with _decay score below threshold are removed.
    - Scalar values without re-confirmation in >5 audits are flagged.
    - Pinned items (in profile["_pinned"]) are exempt from decay.
    - Items already in memory for >10 audits with no reconfirmation get removed.

    Args:
        profile: The user profile dict.

    Returns:
        (decayed_profile, decay_report)
        decay_report has keys: "decayed_items" (list), "removed_items" (list),
                               "pinned_spared" (int), "scalar_warnings" (list)
    """
    report: dict = {
        "decayed_items": [],
        "removed_items": [],
        "pinned_spared": 0,
        "scalar_warnings": [],
    }

    pinned: set = set(profile.get("_pinned", []))
    audits: list = profile.get("audits", [])
    audit_count: int = len(audits)
    last_5_audit_sources: set = set()
    for audit in audits[-5:]:
        ts = audit.get("timestamp", "")
        if ts:
            last_5_audit_sources.add(ts)

    # Age scalar fields: if no re-confirmation in last 5 audits, warn
    for scalar_key in _SCALAR_KEYS:
        val = profile.get(scalar_key)
        if val and val not in (None, ""):
            reconfirmed = False
            for audit in audits[-5:]:
                findings = audit.get("findings", {})
                if isinstance(findings, dict):
                    if findings.get(scalar_key) == val:
                        reconfirmed = True
                        break
            if not reconfirmed and audit_count >= 5:
                report["scalar_warnings"].append(
                    f"{scalar_key}='{val}' not reconfirmed in last {min(5, audit_count)} audits"
                )

    # Age list items: remove items that haven't been seen in >10 audits
    for key in _LIST_KEYS:
        items = profile.get(key, [])
        if not isinstance(items, list):
            continue
        kept = []
        for item in items:
            if not isinstance(item, str):
                continue
            item_lower = item.lower().strip()
            pin_key = f"{key}:{item_lower}"
            if pin_key in pinned:
                kept.append(item)
                report["pinned_spared"] += 1
                continue
            # Check if item appeared in recent audits
            found_recent = False
            for audit in audits[-10:]:
                findings = audit.get("findings", {})
                # Flatten findings to find this item
                f_items = findings.get(key, [])
                if isinstance(f_items, list):
                    for fi in f_items:
                        if isinstance(fi, str) and fi.lower().strip() == item_lower:
                            found_recent = True
                            break
                if found_recent:
                    break
            if found_recent:
                kept.append(item)
            else:
                report["removed_items"].append(f"{key}: '{item}'")
        if kept or not items:
            profile[key] = kept
        else:
            profile[key] = []

    # Age dict-of-list items similarly
    for key in _DICT_KEYS:
        d = profile.get(key, {})
        if not isinstance(d, dict):
            continue
        for subkey, items in d.items():
            if not isinstance(items, list):
                continue
            kept = []
            for item in items:
                if not isinstance(item, str):
                    continue
                item_lower = item.lower().strip()
                pin_key = f"{key}.{subkey}:{item_lower}"
                if pin_key in pinned:
                    kept.append(item)
                    report["pinned_spared"] += 1
                    continue
                found_recent = False
                for audit in audits[-10:]:
                    findings = audit.get("findings", {})
                    # This is approximate; dict-of-list findings are harder to trace
                    if isinstance(findings, dict):
                        sub = findings.get(key, {})
                        if isinstance(sub, dict):
                            si = sub.get(subkey, [])
                            if isinstance(si, list):
                                for fi in si:
                                    if isinstance(fi, str) and fi.lower().strip() == item_lower:
                                        found_recent = True
                                        break
                    if found_recent:
                        break
                if found_recent:
                    kept.append(item)
                else:
                    report["removed_items"].append(f"{key}.{subkey}: '{item}'")
            d[subkey] = kept

    return profile, report


def build_memory_review_queue(profile: dict) -> list:
    """
    Build a queue of memory items that need human review.

    Items are queued when:
    - There are conflicting values for the same field (age, location, name)
    - Low-confidence items (< 0.4) that survived cleaning
    - Items in cross-category conflicts
    - Scalar fields that were never re-confirmed
    - Items specifically flagged as "review" in profile metadata

    Args:
        profile: The user profile dict.

    Returns:
        List of dicts, each with:
          - "id": unique identifier for this review item
          - "field": profile key
          - "value": the value needing review
          - "reason": why it needs review
          - "confidence": current confidence score (if available)
          - "suggested_action": "keep", "reject", or "clarify"
    """
    queue: list = []
    conf: dict = profile.get("_confidence", {})
    seen_ids: set = set()

    def _make_id(field: str, value: str) -> str:
        return f"{field}::{value.lower().strip()[:60]}"

    # 1. Conflicts from detect_profile_conflicts
    conflicts = detect_profile_conflicts(profile)
    for warning in conflicts.get("warnings", []):
        queue.append({
            "id": f"conflict::{len(queue)}",
            "field": "conflict",
            "value": warning,
            "reason": "Detected profile conflict",
            "confidence": 0.0,
            "suggested_action": "clarify",
        })

    # 2. Low-confidence list items
    for key in _LIST_KEYS:
        items = profile.get(key, [])
        if not isinstance(items, list):
            continue
        item_conf = conf.get(key, {})
        if not isinstance(item_conf, dict):
            continue
        for item in items:
            if not isinstance(item, str):
                continue
            c = item_conf.get(item, 0.5)
            if c < 0.4:
                item_id = _make_id(key, item)
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    queue.append({
                        "id": item_id,
                        "field": key,
                        "value": item,
                        "reason": f"Low confidence ({c:.2f})",
                        "confidence": c,
                        "suggested_action": "reject" if c < 0.2 else "clarify",
                    })

    # 3. Previously flagged review items
    flagged = profile.get("_review_queue", [])
    for f_item in flagged:
        if isinstance(f_item, dict):
            item_id = f_item.get("id") or _make_id(f_item.get("field", "?"), f_item.get("value", "?"))
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                f_item.setdefault("reason", "Previously flagged")
                f_item.setdefault("suggested_action", "clarify")
                queue.append(f_item)

    # 4. Scalar warnings from decay
    decay_result = decay_profile_memory(dict(profile))  # copy to avoid mutation
    for w in decay_result[1].get("scalar_warnings", []):
        queue.append({
            "id": f"decay_scalar::{len(queue)}",
            "field": "scalar",
            "value": w,
            "reason": "Scalar field not reconfirmed",
            "confidence": 0.3,
            "suggested_action": "clarify",
        })

    return queue


def _update_tool_action_list():
    """Update the available actions string in memory_import_tool docstring and error message."""
    pass  # Handled via the edit below


# ─── Main Entry Point ────────────────────────────────────

if __name__ == "__main__":
    print("Testing Memory Import System...\n")

    # Test 1: Status
    print("--- Status ---")
    print(memory_import_tool("status"))

    # Test 2: Profile (empty)
    print("\n--- Profile ---")
    print(memory_import_tool("profile"))
