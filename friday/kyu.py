"""Know Your User — personality adaptation, preference learning, profile interviews."""
from __future__ import annotations
import os
import json
from datetime import datetime
from typing import Any

_ROOT = os.path.dirname(os.path.abspath(__file__))
_KYU_FILE = os.path.join(os.path.dirname(_ROOT), "friday_memory", "kyu_profile.json")

DEFAULT_KYU = {
    "name": "Arnav",
    "personality_traits": {
        "communication_style": "neutral",  # direct, warm, casual, formal
        "patience_level": 5,  # 1-10
        "independence_level": 5,  # 1-10 (how much automation vs asking)
        "humor_tolerance": 5,  # 1-10
        "verbosity_preference": "concise",  # concise, balanced, detailed
        "feedback_sensitivity": 5,  # 1-10
    },
    "learning_profile": {
        "primary_goal": "",
        "subjects": [],
        "learning_style": "",  # visual, reading, practical
        "peak_focus_time": "",  # morning, afternoon, evening, night
        "study_duration_minutes": 30,
    },
    "productivity_patterns": {
        "distraction_sites": [],
        "focus_apps": [],
        "typical_work_hours": {"start": "09:00", "end": "17:00"},
        "break_frequency_minutes": 60,
        "screen_time_goal_hours": 4,
    },
    "preferences": {
        "voice_tone": "casual",  # casual, professional, warm
        "greeting_style": "time_aware",  # time_aware, minimal, enthusiastic
        "reminder_frequency": "moderate",  # low, moderate, high
        "correction_style": "direct",  # direct, gentle, humorous
        "emoji_usage": "minimal",  # none, minimal, moderate
    },
    "interview_progress": {
        "stage": 0,  # 0=not_started, 1-4=in_progress, 5=complete
        "last_interview": None,
        "questions_answered": 0,
    },
    "observed_patterns": {
        "common_commands": [],
        "frequent_tools": [],
        "active_hours": {},
        "last_active_date": None,
    },
    "created_at": None,
    "updated_at": None,
}


def load_kyu() -> dict:
    if os.path.exists(_KYU_FILE):
        try:
            with open(_KYU_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    profile = DEFAULT_KYU.copy()
    profile["created_at"] = datetime.now().isoformat()
    return profile


def save_kyu(profile: dict) -> None:
    os.makedirs(os.path.dirname(_KYU_FILE), exist_ok=True)
    profile["updated_at"] = datetime.now().isoformat()
    try:
        with open(_KYU_FILE, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
    except Exception as e:
        print(f"[KYU] Save error: {e}")


INTERVIEW_QUESTIONS = [
    # Stage 1: Communication
    [
        "How do you prefer I talk to you? Direct and brief, warm and friendly, or formal and professional?",
        "Do you mind humor and occasional sass, or would you rather I keep it strictly business?",
        "When I give you updates, do you want short one-liners or more detailed explanations?",
    ],
    # Stage 2: Productivity
    [
        "What's your main focus right now? Studying, work projects, creative work, or something else?",
        "What times of day are you most productive? Morning, afternoon, evening, or late night?",
        "Which apps or sites tend to distract you the most? I can help keep you on track.",
    ],
    # Stage 3: Learning & Goals
    [
        "What are your top 2-3 goals or subjects you're working on right now?",
        "How do you learn best — reading, watching tutorials, or hands-on practice?",
        "How long can you focus in one sitting before needing a break?",
    ],
    # Stage 4: Automation
    [
        "How much automation do you want? Should I do things automatically or always ask first?",
        "Any routines you do daily that I could help automate or remind you about?",
        "How should I handle it when you're falling behind on goals — gentle nudge or drill sergeant?",
    ],
]


def kyu_status() -> str:
    """Get KYU profile readiness summary."""
    kyu = load_kyu()
    stage = kyu.get("interview_progress", {}).get("stage", 0)
    if stage >= 4:
        return "[OK] Know Your User profile complete. Personality adaptation active."
    elif stage > 0:
        return f"[INFO] KYU interview in progress (stage {stage+1}/4). {4-stage} stages remaining."
    else:
        return "[INFO] Know Your User not set up. Run kyu_interview(stage=1) to begin."


def kyu_interview(stage: int = None) -> str:
    """Get interview questions for the next stage (1-4). Returns questions the AI can ask."""
    kyu = load_kyu()
    progress = kyu.get("interview_progress", {})
    current = progress.get("stage", 0)

    if stage is None:
        stage = current + 1

    if stage < 1:
        stage = 1
    if stage > 4:
        return "[OK] KYU interview already complete. Profile is ready."

    questions = INTERVIEW_QUESTIONS[stage - 1]
    progress["stage"] = stage
    progress["last_interview"] = datetime.now().isoformat()
    kyu["interview_progress"] = progress
    save_kyu(kyu)

    lines = [f"### KYU INTERVIEW — Stage {stage}/4", ""]
    for i, q in enumerate(questions, 1):
        lines.append(f"{i}. {q}")
    lines.append("")
    lines.append("Answer each question and I'll update your profile.")
    if stage < 4:
        lines.append(f"After this, there are {4-stage} more stages.")
    else:
        lines.append("This is the final stage!")
    return "\n".join(lines)


def kyu_learn(tool_name: str = None, active_window: str = None, hour: int = None) -> str:
    """Observe user behavior and update the KYU profile automatically."""
    kyu = load_kyu()
    patterns = kyu.get("observed_patterns", {})
    now = datetime.now()

    # Track active hours
    if hour is None:
        hour = now.hour
    active_hours = patterns.get("active_hours", {})
    hour_key = f"{hour:02d}:00"
    active_hours[hour_key] = active_hours.get(hour_key, 0) + 1
    patterns["active_hours"] = active_hours

    # Track tool usage
    if tool_name:
        freq_tools = patterns.get("frequent_tools", [])
        freq_tools.append(tool_name)
        if len(freq_tools) > 100:
            freq_tools = freq_tools[-100:]
        patterns["frequent_tools"] = freq_tools

    # Track active window patterns
    if active_window:
        common = patterns.get("common_commands", [])
        common.append(active_window)
        if len(common) > 50:
            common = common[-50:]
        patterns["common_commands"] = common

    patterns["last_active_date"] = now.strftime("%Y-%m-%d")
    kyu["observed_patterns"] = patterns

    # Auto-adjust verbosity based on tool call frequency
    freq_tools = patterns.get("frequent_tools", [])
    if len(freq_tools) > 20:
        recent = freq_tools[-20:]
        unique_ratio = len(set(recent)) / len(recent)
        if unique_ratio < 0.3:
            kyu["personality_traits"]["verbosity_preference"] = "concise"
        elif unique_ratio > 0.7:
            kyu["personality_traits"]["verbosity_preference"] = "balanced"

    save_kyu(kyu)
    return "[OK] KYU observation recorded."


def kyu_profile() -> str:
    """Get a full KYU profile summary."""
    kyu = load_kyu()
    lines = ["### KNOW YOUR USER — Profile", ""]

    traits = kyu.get("personality_traits", {})
    lines.append("**Personality:**")
    for k, v in traits.items():
        lines.append(f"  {k.replace('_', ' ').title()}: {v}")
    lines.append("")

    learning = kyu.get("learning_profile", {})
    lines.append("**Learning Profile:**")
    for k, v in learning.items():
        if v:
            lines.append(f"  {k.replace('_', ' ').title()}: {v}")
    lines.append("")

    prefs = kyu.get("preferences", {})
    lines.append("**Preferences:**")
    for k, v in prefs.items():
        lines.append(f"  {k.replace('_', ' ').title()}: {v}")
    lines.append("")

    patterns = kyu.get("observed_patterns", {})
    lines.append("**Observed Patterns:**")
    freq = patterns.get("frequent_tools", [])
    if freq:
        from collections import Counter
        top = Counter(freq).most_common(5)
        lines.append("  Top tools: " + ", ".join(f"{t}({c})" for t, c in top))
    ah = patterns.get("active_hours", {})
    if ah:
        peak = max(ah, key=ah.get)
        lines.append(f"  Peak activity hour: {peak}")
    lines.append("")

    stage = kyu.get("interview_progress", {}).get("stage", 0)
    lines.append(f"**Interview:** Stage {stage}/4")

    return "\n".join(lines)


def kyu_adapt() -> dict:
    """Get adaptation parameters for the main engine based on KYU profile."""
    kyu = load_kyu()
    traits = kyu.get("personality_traits", {})
    prefs = kyu.get("preferences", {})
    return {
        "verbosity": traits.get("verbosity_preference", "concise"),
        "humor": traits.get("humor_tolerance", 5) >= 6,
        "patience": traits.get("patience_level", 5),
        "voice_tone": prefs.get("voice_tone", "casual"),
        "emoji": prefs.get("emoji_usage", "minimal") != "none",
        "reminder_freq": prefs.get("reminder_frequency", "moderate"),
    }
