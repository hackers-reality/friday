"""
Friday Goal Memory System - Phase 4.1-4.6
Goal tracking, user profile, calendar integration, enforcement.
"""
from __future__ import annotations

import os
import json
import sys
import time
import threading
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

# ─── File Paths ────────────────────────────────────────────

_MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friday_memory")
_GOALS_FILE = os.path.join(_MEMORY_DIR, "goals.json")
_PROFILE_FILE = os.path.join(_MEMORY_DIR, "user_profile.json")

# Ensure directory exists
os.makedirs(_MEMORY_DIR, exist_ok=True)


# ─── User Profile ──────────────────────────────────────────────

DEFAULT_PROFILE = {
    "name": "Arnav",
    "grade_level": None,
    "school": None,
    "exam_dates": [],  # [{"exam": "Math", "date": "2026-05-20", "priority": "high"}]
    "class_timings": [],  # [{"day": "Monday", "start": "09:00", "end": "10:30", "subject": "Physics"}]
    "preferred_browser": "Chrome",
    "current_courses": [],  # [{"name": "IITM Course", "start_date": "2026-04-06", "end_date": "2026-05-31", "url": "https://iitm.x.x.com", "completed": False}]
    "work_hours": {"start": "09:00", "end": "17:00"},
    "streak_data": {"last_study_date": None, "total_study_days": 0},
}

def load_profile() -> Dict[str, Any]:
    """Load user profile from file."""
    if os.path.exists(_PROFILE_FILE):
        try:
            with open(_PROFILE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_PROFILE.copy()

def save_profile(profile: Dict[str, Any]) -> None:
    """Save user profile to file."""
    try:
        with open(_PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=4)
    except Exception as e:
        print(f"[GoalSystem] Profile save error: {e}")

def update_profile(key: str, value: Any) -> str:
    """Update a single profile field."""
    profile = load_profile()
    profile[key] = value
    save_profile(profile)
    return f"Profile updated: {key} = {value}"

def get_profile_summary() -> str:
    """Get a human-readable profile summary."""
    p = load_profile()
    lines = [
        "### USER PROFILE",
        f"- Name: {p.get('name', 'Unknown')}",
        f"- Grade: {p.get('grade_level', 'Not set')}",
        f"- School: {p.get('school', 'Not set')}",
        f"- Prefurred Browser: {p.get('preferred_browser', 'Chrome')}",
    ]
    
    courses = p.get("current_courses", [])
    if courses:
        lines.append("\n**Current Courses:**")
        for c in courses:
            status = "[OK] Done" if c.get("completed") else "⏳ In Progress"
            lines.append(f"  - {c.get('name', 'Unknown')}: {c.get('start_date', '?')} to {c.get('end_date', '?')} {status}")
            if c.get("url"):
                lines.append(f"    URL: {c['url']}")
    
    exams = p.get("exam_dates", [])
    if exams:
        lines.append("\n**Upcoming Exams:**")
        for e in exams:
            lines.append(f"  - {e.get('exam', 'Unknown')}: {e.get('date', '?')} (Priority: {e.get('priority', 'medium')})")
    
    return "\n".join(lines)


# ─── Goals System ──────────────────────────────────────────────

DEFAULT_GOAL = {
    "id": None,
    "type": "generic",  # generic, course, exam, assignment
    "title": "",
    "description": "",
    "start_date": None,
    "end_date": None,
    "deadline": None,
    "url": None,  # Reference URL (course link, etc.)
    "priority": "medium",  # low, medium, high, critical
    "status": "active",  # active, completed, overdue, paused
    "progress": 0,  # 0-100
    "verification_method": None,  # "browser_history", "file_check", "manual"
    "verification_data": None,  # URL pattern, file path, etc.
    "streak": 0,
    "last_verified": None,
    "scolding_count": 0,  # How many times user was scolded
    "created_at": None,
    "completed_at": None,
}

def load_goals() -> List[Dict[str, Any]]:
    """Load all goals from file."""
    if os.path.exists(_GOALS_FILE):
        try:
            with open(_GOALS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_goals(goals: List[Dict[str, Any]]) -> None:
    """Save goals to file."""
    try:
        with open(_GOALS_FILE, "w", encoding="utf-8") as f:
            json.dump(goals, f, indent=4)
    except Exception as e:
        print(f"[GoalSystem] Goals save error: {e}")

def add_goal(
    title: str,
    goal_type: str = "generic",
    description: str = "",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    deadline: Optional[str] = None,
    url: Optional[str] = None,
    priority: str = "medium",
    verification_method: Optional[str] = None,
    verification_data: Optional[str] = None,
) -> str:
    """Add a new goal."""
    goals = load_goals()
    
    goal = DEFAULT_GOAL.copy()
    goal["id"] = f"goal_{int(time.time())}"
    goal["type"] = goal_type
    goal["title"] = title
    goal["description"] = description
    goal["start_date"] = start_date or datetime.now().strftime("%Y-%m-%d")
    goal["end_date"] = end_date
    goal["deadline"] = deadline
    goal["url"] = url
    goal["priority"] = priority
    goal["verification_method"] = verification_method
    goal["verification_data"] = verification_data
    goal["created_at"] = datetime.now().isoformat()
    
    goals.append(goal)
    save_goals(goals)
    
    return f"[OK] Goal added: {title} (ID: {goal['id']})"

def update_goal(goal_id: str, **kwargs) -> str:
    """Update a goal's fields."""
    goals = load_goals()
    for g in goals:
        if g.get("id") == goal_id:
            for k, v in kwargs.items():
                if k in g:
                    g[k] = v
            save_goals(goals)
            return f"[OK] Goal {goal_id} updated."
    return f"[FAIL] Goal {goal_id} not found."

def complete_goal(goal_id: str) -> str:
    """Mark a goal as completed."""
    return update_goal(goal_id, status="completed", completed_at=datetime.now().isoformat())

def delete_goal(goal_id: str) -> str:
    """Delete a goal."""
    goals = load_goals()
    new_goals = [g for g in goals if g.get("id") != goal_id]
    if len(new_goals) < len(goals):
        save_goals(new_goals)
        return f"🗑️ Goal {goal_id} deleted."
    return f"[FAIL] Goal {goal_id} not found."

def list_goals(status_filter: Optional[str] = None) -> str:
    """List all goals, optionally filtered by status."""
    goals = load_goals()
    
    if status_filter:
        goals = [g for g in goals if g.get("status") == status_filter]
    
    if not goals:
        return "No goals found."
    
    lines = ["### GOALS", ""]
    for g in goals:
        status_emoji = {
            "active": "⏳",
            "completed": "[OK]",
            "overdue": "🔴",
            "paused": "⏸",
        }.get(g.get("status", "active"), "⏳")
        
        lines.append(f"{status_emoji} **{g.get('title', 'Unknown')}** (ID: {g.get('id', '?')})")
        lines.append(f"   Type: {g.get('type', 'generic')} | Priority: {g.get('priority', 'medium')}")
        lines.append(f"   Progress: {g.get('progress', 0)}% | Streak: {g.get('streak', 0)} days")
        
        if g.get("end_date"):
            lines.append(f"   End Date: {g['end_date']}")
        if g.get("url"):
            lines.append(f"   URL: {g['url']}")
        lines.append("")
    
    return "\n".join(lines)


# ─── Google Calendar Integration (Phase 4.2) ────────────────────

def get_calendar_service():
    """Get authenticated Google Calendar service.
    Uses unified .gmail_token.json (Gmail + Calendar) first, falls back to calendar_token.json.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        
        SCOPES = [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ]
        creds = None
        credentials_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")
        
        # 1. Try unified .gmail_token.json first (has Gmail + Calendar scopes)
        unified_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gmail_token.json")
        if os.path.exists(unified_path):
            try:
                creds = Credentials.from_authorized_user_file(unified_path, SCOPES + [
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.modify",
                ])
            except Exception:
                pass
        
        # 2. Fall back to old calendar_token.json
        if not creds or not creds.valid:
            token_path = os.path.join(_MEMORY_DIR, "calendar_token.json")
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        # 3. If still no valid creds, run OAuth
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    return None, "Google Calendar not configured. Place credentials.json in the project root."
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(os.path.join(_MEMORY_DIR, "calendar_token.json"), "w") as f:
                f.write(creds.to_json())
        
        service = build("calendar", "v3", credentials=creds)
        return service, None
    
    except ImportError:
        return None, "Google API client not installed. Install: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
    except Exception as e:
        return None, f"Calendar error: {str(e)}"

def fetch_calendar_events(max_results: int = 10, days_ahead: int = 7) -> str:
    """Fetch upcoming calendar events."""
    service, error = get_calendar_service()
    if error:
        return error
    
    try:
        now = datetime.now().isoformat() + "Z"
        time_max = (datetime.now() + timedelta(days=days_ahead)).isoformat() + "Z"
        
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        
        events = events_result.get("items", [])
        
        if not events:
            return "No upcoming events found."
        
        lines = [f"### CALENDAR EVENTS (Next {days_ahead} days)", ""]
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            lines.append(f"📅 **{event.get('summary', 'Untitled')}**")
            lines.append(f"   When: {start}")
            if event.get("description"):
                lines.append(f"   Description: {event['description'][:100]}")
            lines.append("")
        
        return "\n".join(lines)
    
    except Exception as e:
        return f"Calendar fetch error: {str(e)}"

def sync_calendar_to_goals() -> str:
    """Sync calendar events to goals (for classes, exams)."""
    service, error = get_calendar_service()
    if error:
        return error
    
    try:
        # Fetch events for next 30 days
        now = datetime.now().isoformat() + "Z"
        time_max = (datetime.now() + timedelta(days=30)).isoformat() + "Z"
        
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            timeMax=time_max,
            maxResults=50,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        
        events = events_result.get("items", [])
        goals = load_goals()
        
        synced = 0
        for event in events:
            summary = event.get("summary", "").lower()
            
            # Detect exams
            if any(word in summary for word in ["exam", "test", "quiz"]):
                goal_type = "exam"
                priority = "high"
            # Detect classes
            elif any(word in summary for word in ["class", "lecture", "course", "session"]):
                goal_type = "course"
                priority = "medium"
            else:
                continue
            
            # Check if already exists
            event_id = event.get("id")
            if any(g.get("calendar_event_id") == event_id for g in goals):
                continue
            
            # Create new goal
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date")) if event.get("end") else None
            
            goal = DEFAULT_GOAL.copy()
            goal["id"] = f"goal_{int(time.time())}_{synced}"
            goal["type"] = goal_type
            goal["title"] = event.get("summary", "Untitled")
            goal["description"] = event.get("description", "")
            goal["start_date"] = start[:10] if start else None
            goal["end_date"] = end[:10] if end else None
            goal["deadline"] = end[:10] if end else None
            goal["priority"] = priority
            goal["calendar_event_id"] = event_id
            goal["created_at"] = datetime.now().isoformat()
            
            goals.append(goal)
            synced += 1
        
        save_goals(goals)
        return f"[OK] Synced {synced} events from calendar to goals."
    
    except Exception as e:
        return f"Sync error: {str(e)}"


# ─── Daily Goal Check (Phase 4.3) ─────────────────────────────

def check_goal_progress(goal: Dict[str, Any]) -> Dict[str, Any]:
    """Check if a goal has been worked on today."""
    result = {
        "goal_id": goal.get("id"),
        "title": goal.get("title"),
        "status": goal.get("status"),
        "verified": False,
        "message": "",
    }
    
    verification_method = goal.get("verification_method")
    verification_data = goal.get("verification_data")
    
    if not verification_method or not verification_data:
        result["message"] = "No verification method set."
        return result
    
    # Browser history verification
    if verification_method == "browser_history":
        try:
            from browser_history_tools import check_visited_today
            if check_visited_today(verification_data):
                result["verified"] = True
                result["message"] = f"[OK] Visited {verification_data} today."
            else:
                result["message"] = f"[FAIL] Haven't visited {verification_data} today."
        except Exception as e:
            result["message"] = f"Verification error: {e}"
    
    return result

def daily_goal_check() -> str:
    """Run daily check on all active goals."""
    goals = load_goals()
    active_goals = [g for g in goals if g.get("status") == "active"]
    
    if not active_goals:
        return "[OK] No active goals to check."
    
    lines = ["### DAILY GOAL CHECK", ""]
    all_passed = True
    
    for g in active_goals:
        check = check_goal_progress(g)
        lines.append(f"**{g.get('title')}**: {check['message']}")
        
        if not check["verified"]:
            all_passed = False
            # Increment scolding count
            g["scolding_count"] = g.get("scolding_count", 0) + 1
            g["last_verified"] = datetime.now().isoformat()
    
    # Save updated goals
    save_goals(goals)
    
    lines.append("")
    if all_passed:
        lines.append("🎉 All goals verified for today!")
    else:
        lines.append("[WARN] Some goals need attention. Friday will take action.")
    
    return "\n".join(lines)


# ─── Enforcement Actions (Phase 4.5) ─────────────────────────

def enforce_goal(goal_id: str, level: int = None) -> str:
    """Enforce a goal with progressive punishment levels.
    Levels: 1=warn, 2=close distractions, 3=lock-in + notify, 4=escalate.
    If level not specified, auto-chooses based on scolding_count.
    """
    goals = load_goals()
    
    goal = None
    for g in goals:
        if g.get("id") == goal_id:
            goal = g
            break
    
    if not goal:
        return f"[FAIL] Goal {goal_id} not found."
    
    scolding = goal.get("scolding_count", 0)
    if level is None:
        if scolding < 2:
            level = 1
        elif scolding < 5:
            level = 2
        elif scolding < 8:
            level = 3
        else:
            level = 4
    
    goal["scolding_count"] = scolding + 1
    goal["last_enforced"] = datetime.now().isoformat()
    save_goals(goals)
    
    lines = [f"### ENFORCEMENT LVL {level}: {goal.get('title')}", ""]
    
    if level >= 1:
        lines.append("[FRIDAY] Boss, you need to focus on your goal. Let me help.")
    
    if level >= 2:
        try:
            import subprocess
            distractions = ["steam", "epicgameslauncher", "discord", "spotify", "brave", "chrome", "msedge", "firefox"]
            for d in distractions:
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", f"{d}.exe"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    lines.append(f"Closed distraction: {d}")
        except Exception as e:
            lines.append(f"Note: kill error: {e}")
    
    if level >= 3:
        url = goal.get("url")
        if url:
            try:
                import webbrowser
                webbrowser.open(url)
                lines.append(f"Opened required URL: {url}")
            except Exception as e:
                lines.append(f"Failed to open URL: {e}")
    
    if level >= 4:
        lines.append("[ESCALATION] Goal consistently missed. Consider:")
        lines.append(f"  - Reporting to parent/teacher")
        lines.append(f"  - Locking device during focus hours")
        lines.append(f"  - Reducing screen time allowance")
    
    lines.append(f"\nScolding count: {goal['scolding_count']}")
    return "\n".join(lines)


# ─── Integration with Friday Tools ─────────────────────────

def goals_tool_handler(action: str, **kwargs) -> str:
    """Handler for goals tool in Friday."""
    if action == "add":
        return add_goal(**kwargs)
    elif action == "list":
        return list_goals(status_filter=kwargs.get("status"))
    elif action == "complete":
        return complete_goal(kwargs.get("goal_id"))
    elif action == "delete":
        return delete_goal(kwargs.get("goal_id"))
    elif action == "check":
        return daily_goal_check()
    elif action == "enforce":
        return enforce_goal(kwargs.get("goal_id"))
    elif action == "sync_calendar":
        return sync_calendar_to_goals()
    elif action == "calendar":
        return fetch_calendar_events()
    elif action == "profile":
        return get_profile_summary()
    elif action == "update_profile":
        return update_profile(kwargs.get("key"), kwargs.get("value"))
    else:
        return f"Unknown goals action: {action}"


if __name__ == "__main__":
    # Test
    print("Testing Goal Memory System...")
    
    # Add a test goal
    print(goals_tool_handler("add",
        title="IITM 8-week Course",
        goal_type="course",
        description="Complete the 8-week IITM course",
        start_date="2026-04-06",
        end_date="2026-05-31",
        url="https://iitm.x.x.com",
        priority="high",
        verification_method="browser_history",
        verification_data="iitm",
    ))
    
    # List goals
    print("\n" + goals_tool_handler("list"))
    
    # Show profile
    print("\n" + get_profile_summary())
