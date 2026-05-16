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
    if os.path.isdir(_E_DOWNLOADS):
        scan_dirs.append(_E_DOWNLOADS)

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
            return m.group(0).strip()
    return None


def _extract_education(text: str) -> List[str]:
    details = []
    patterns = [
        # School/college names with word-boundary guard
        _wb(r"(?:school|college|university|academy|institute|institution)\s+(?:of\s+)?(?:is\s+)?(?:at\s+|in\s+)?([A-Z][A-Za-z\s.'&-]{3,60}?)(?:\.|,|$)"),
        r"(?:studying|studied|pursuing|enrolled|doing|taking)\s+([A-Za-z\s]{4,50}?)\s+(?:at|in|from|,|\.)",
        r"(\d+)(?:th|st|nd|rd)\s*(?:grade|class|standard)\s+(?:at|in|,)?\s*([A-Z][A-Za-z\s]{3,40}?)(?:\.|,|$)",
        # Specific exams — only as whole words
        _wb(r"(?:CBSE|ICSE|IB)\s+(?:board\s+)?(?:[A-Z][A-Za-z\s]{3,30})?"),
        _wb(r"(IIT|NIT|IIIT|JEE|NEET|GATE|UPSC|CAT|GMAT|GRE|TOEFL|IELTS|SAT)\s*(?:[A-Za-z]{2,30})?(?:\s*\d+[\.,]?\d*)?"),
        # Scores with word boundaries
        r"(?:percentage|score|marks|grade|GPA|CGPA|aggregate)\s*(?::|is|-|\s+)(\d+[\.,]?\d*\s*%?)",
    ]
    for p in patterns:
        if p.startswith(_WORD_BOUNDARY):
            # This pattern already has word boundaries
            matches = re.findall(p, text, re.IGNORECASE)
        else:
            matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                m = " ".join(part for part in m if part).strip()
            else:
                m = m.strip()
            if len(m) > 3 and len(m) < 100 and m not in details:
                score = _score_item_quality(m, text)
                if score > 0.3:
                    details.append(m)
    return _deduplicate(details)


def _extract_projects(text: str) -> List[str]:
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
    goals = []
    patterns = [
        r"(?:want to|need to|planning to|going to|aim to|goal is|aspire to|trying to|hoping to|looking to)\s+([A-Za-z\s]{5,80}?)(?:\.|,|$|so that|because|and|but)",
        _wb(r"(?:goal|target|aim|dream|ambition|objective)\s*(?::|is|-|\s+)([A-Za-z\s]{5,80}?)(?:\.|,|$)"),
        r"(?:preparing|studying|study|prepare|give|appear|sit)\s+(?:for|in)\s+([A-Za-z0-9\s]{3,40}?)(?:\.|,|$|next|this|exam|test|competition)",
    ]
    stop_phrases = {"it", "this", "that", "the", "a", "an", "do", "make", "get", "have", "be", "go", "see", "know", "find", "use", "take", "come", "work", "look", "want", "give", "tell", "help", "keep", "let", "start", "show", "hear", "play", "run", "move", "live", "believe", "hold", "bring", "happen", "write", "provide", "sit", "stand", "lose", "pay", "meet", "include", "continue", "set", "learn", "change", "lead", "understand", "watch"}
    for p in patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                m = " ".join(part for part in m if part).strip()
            else:
                m = m.strip().rstrip(".,;")
            first_word = m.split()[0].lower() if m.split() else ""
            if first_word in stop_phrases:
                continue
            if 5 <= len(m) <= 80 and m not in goals:
                score = _score_item_quality(m, text)
                if score > 0.35:
                    goals.append(m)
    return _deduplicate(goals)


def _extract_location(text: str) -> Optional[str]:
    patterns = [
        r"(?:live in|from|based in|located in|stay in|reside in|hailing from)\s+([A-Z][a-z]+(?:[, ]+\s*[A-Z][a-z]+)?(?:[, ]+\s*[A-Z][a-z]+)?)",
        r"(?:city|town|village|place|area|region)\s*(?::|is|-|\s+)([A-Z][a-z]+(?:[, ]+\s*[A-Z][a-z]+)?)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            loc = m.group(1).strip().rstrip(".,")
            if loc.lower() not in {"the", "this", "that", "here", "there", "where"} and len(loc) > 2:
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
            if t not in existing_tech:
                profile.setdefault("tech_stack", []).append(t)
                existing_tech.add(t)
                tfidf_tech_added.append(t)
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

    save_profile(profile)
    return changes

def generate_profile_markdown() -> str:
    """Generate a detailed user profile markdown from all accumulated data."""
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
        p = profile
        skills = p.get("skills", [])
        langs = p.get("languages", [])
        traits = p.get("personality_traits", [])
        return (
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

    return f"Unknown action: {action}. Available: status, import_file, import_dir, import_zip, import_exports, audit, profile"


if __name__ == "__main__":
    print("Testing Memory Import System...\n")

    # Test 1: Status
    print("--- Status ---")
    print(memory_import_tool("status"))

    # Test 2: Profile (empty)
    print("\n--- Profile ---")
    print(memory_import_tool("profile"))
