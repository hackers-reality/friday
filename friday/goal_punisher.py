"""FRIDAY Goal Monitoring & Punishment System.
Monitors user activity, detects distractions, enforces goals with escalating punishment.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
import webbrowser
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, Any
from uuid import uuid4

from friday._paths import FRIDAY_MEMORY


# ── Data Models ─────────────────────────────────────────────

@dataclass
class UserGoal:
    id: str = field(default_factory=lambda: f"goal_{uuid4().hex[:12]}")
    title: str = ""
    description: str = ""
    priority: int = 3
    deadline: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "active"
    learning_urls: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserGoal:
        return cls(**data)


@dataclass
class DistractionAction:
    type: str = ""          # game / social / entertainment / video
    name: str = ""
    process_names: list[str] = field(default_factory=list)
    window_title_patterns: list[str] = field(default_factory=list)
    category: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DistractionAction:
        return cls(**data)


@dataclass
class ViolationRecord:
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    distraction_type: str = ""
    distraction_name: str = ""
    strike_number: int = 1
    action_taken: str = "warning"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ViolationRecord:
        return cls(**data)


# ── Escalation messages ─────────────────────────────────────

_SCOLD_MESSAGES = [
    "Boss, that's distraction #{strike}. You're better than this.",
    "Seriously? #{strike}. Focus on what matters.",
    "Strike #{strike}. Your goals aren't going to achieve themselves.",
    "That's #{strike} now. Do I need to lock your computer down?",
    "Strike #{strike}. You're testing my patience, boss.",
    "#{strike} strikes. I'm starting to think you don't care about your goals.",
    "That's #{strike}. I'm genuinely disappointed.",
    "#{strike} infractions. I'll keep closing them. All day.",
]

_WARNING_MESSAGES = [
    "Heads up, boss — that looks like {name}. Shouldn't you be studying?",
    "I see {name} running. Your goals are waiting.",
    "Distraction detected: {name}. Want me to close it?",
    "I notice you're on {name}. Remember your priorities.",
]


# ── Default distraction patterns ────────────────────────────

_DEFAULT_DISTRACTIONS = [
    DistractionAction("game", "Minecraft", ["minecraft.exe", "javaw.exe"], []),
    DistractionAction("game", "Valorant", ["VALORANT.exe", "valorant.exe"], ["valorant"]),
    DistractionAction("game", "Fortnite", ["FortniteClient-Win64-Shipping.exe", "FortniteLauncher.exe"], ["fortnite"]),
    DistractionAction("game", "League of Legends", ["LeagueClient.exe", "LeagueOfLegends.exe"], ["league of legends", "lol"]),
    DistractionAction("game", "Counter-Strike 2", ["cs2.exe", "csgo.exe"], ["counter-strike", "cs2"]),
    DistractionAction("game", "GTA V", ["GTA5.exe", "gtav.exe"], ["gta v", "grand theft auto"]),
    DistractionAction("game", "Call of Duty", ["cod.exe", "blackops.exe", "modernwarfare.exe"], ["call of duty", "cod"]),
    DistractionAction("game", "Roblox", ["RobloxPlayerBeta.exe", "roblox.exe"], ["roblox"]),
    DistractionAction("game", "Steam", ["steam.exe"], ["steam"]),
    DistractionAction("game", "Epic Games", ["EpicGamesLauncher.exe"], ["epic games"]),
    DistractionAction("game", "Discord", ["Discord.exe"], ["discord"]),
    DistractionAction("game", "Among Us", ["Among Us.exe"], ["among us"]),
    DistractionAction("game", "Apex Legends", ["r5apex.exe", "EasyAntiCheat.exe"], ["apex legends"]),
    DistractionAction("game", "Overwatch", ["Overwatch.exe"], ["overwatch"]),
    DistractionAction("game", "Genshin Impact", ["GenshinImpact.exe", "genshin.exe"], ["genshin"]),
    DistractionAction("game", "Minecraft Launcher", ["MinecraftLauncher.exe"], []),
    DistractionAction("video", "YouTube", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["youtube.com/watch"]),
    DistractionAction("video", "Netflix", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["netflix.com"]),
    DistractionAction("video", "Prime Video", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["primevideo.com", "amazon.com/video"]),
    DistractionAction("video", "Disney+ Hotstar", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["hotstar.com", "disneyplus.com"]),
    DistractionAction("video", "Crunchyroll", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["crunchyroll.com"]),
    DistractionAction("social", "Instagram", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["instagram.com"]),
    DistractionAction("social", "Facebook", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["facebook.com"]),
    DistractionAction("social", "Reddit", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["reddit.com"]),
    DistractionAction("social", "TikTok", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["tiktok.com"]),
    DistractionAction("social", "Twitter / X", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["twitter.com", "x.com"]),
    DistractionAction("social", "Snapchat", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["snapchat.com"]),
    DistractionAction("social", "WhatsApp Web", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["whatsapp.com"]),
    DistractionAction("social", "Discord Web", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["discord.com/channels", "discord.com/app"]),
    DistractionAction("social", "Twitch", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["twitch.tv"]),
    DistractionAction("entertainment", "Spotify", ["Spotify.exe"], ["spotify"]),
    DistractionAction("entertainment", "VLC Player", ["vlc.exe"], []),
    DistractionAction("entertainment", "Plex", ["plex.exe", "PlexMediaPlayer.exe"], ["plex"]),
    DistractionAction("entertainment", "Porn / NSFW", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], [
        "pornhub", "xvideos", "xnxx", "xhamster", "redtube", "youporn",
        "onlyfans", "stripchat", "chaturbate", "adultwork",
    ]),
    DistractionAction("entertainment", "Kodi", ["kodi.exe"], []),
    DistractionAction("game", "YouTube (Shorts)", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["youtube.com/shorts"]),
    DistractionAction("social", "LinkedIn", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["linkedin.com"]),
    DistractionAction("social", "Pinterest", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"], ["pinterest.com"]),
    DistractionAction("social", "Telegram", ["Telegram.exe"], ["telegram"]),
]


# ── Main Goal Punisher ──────────────────────────────────────

class GoalPunisher:
    """Monitors user goals, detects distractions, enforces focus."""

    def __init__(self, data_dir: str | None = None):
        self._data_dir = data_dir or os.path.join(FRIDAY_MEMORY, "goal_punisher")
        os.makedirs(self._data_dir, exist_ok=True)

        self._goals_file = os.path.join(self._data_dir, "goals.json")
        self._violations_file = os.path.join(self._data_dir, "violations.json")
        self._distractions_file = os.path.join(self._data_dir, "distractions.json")
        self._strikes_file = os.path.join(self._data_dir, "strike.json")

        self.goals: list[UserGoal] = []
        self.distractions: list[DistractionAction] = []
        self.violations: list[ViolationRecord] = []
        self._strikes: int = 0
        self._last_warning_time: float = 0.0
        self._warning_cooldown: float = 30.0

        self.load_state()

    # ── Persistence ──────────────────────────────────────

    def save_state(self) -> None:
        try:
            with open(self._goals_file, "w", encoding="utf-8") as f:
                json.dump([g.to_dict() for g in self.goals], f, indent=2)
        except Exception as e:
            print(f"[GoalPunisher] Goals save error: {e}")

        try:
            with open(self._violations_file, "w", encoding="utf-8") as f:
                json.dump([v.to_dict() for v in self.violations], f, indent=2)
        except Exception as e:
            print(f"[GoalPunisher] Violations save error: {e}")

        try:
            with open(self._distractions_file, "w", encoding="utf-8") as f:
                json.dump([d.to_dict() for d in self.distractions], f, indent=2)
        except Exception as e:
            print(f"[GoalPunisher] Distractions save error: {e}")

        try:
            with open(self._strikes_file, "w", encoding="utf-8") as f:
                json.dump({"strikes": self._strikes}, f, indent=2)
        except Exception as e:
            print(f"[GoalPunisher] Strikes save error: {e}")

    def load_state(self) -> None:
        if os.path.exists(self._goals_file):
            try:
                with open(self._goals_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.goals = [UserGoal.from_dict(g) for g in data]
            except Exception as e:
                print(f"[GoalPunisher] Goals load error: {e}")

        if os.path.exists(self._distractions_file):
            try:
                with open(self._distractions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.distractions = [DistractionAction.from_dict(d) for d in data]
            except Exception:
                pass

        if not self.distractions:
            self.distractions = _DEFAULT_DISTRACTIONS
            self.save_state()

        if os.path.exists(self._violations_file):
            try:
                with open(self._violations_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.violations = [ViolationRecord.from_dict(v) for v in data]
            except Exception:
                pass

        if os.path.exists(self._strikes_file):
            try:
                with open(self._strikes_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._strikes = data.get("strikes", 0)
            except Exception:
                pass

    # ── Goal management ──────────────────────────────────

    def add_goal(self, title: str, description: str = "", priority: int = 3,
                 deadline: str | None = None, learning_urls: list[str] | None = None,
                 tags: list[str] | None = None) -> UserGoal:
        goal = UserGoal(
            title=title,
            description=description,
            priority=priority,
            deadline=deadline,
            learning_urls=learning_urls or [],
            tags=tags or [],
        )
        self.goals.append(goal)
        self.save_state()
        return goal

    async def add_goal_async(self, title: str, description: str = "", priority: int = 3,
                             deadline: str | None = None, learning_urls: list[str] | None = None,
                             tags: list[str] | None = None) -> UserGoal:
        return self.add_goal(title, description, priority, deadline, learning_urls, tags)

    def list_goals(self, status: str | None = None) -> list[UserGoal]:
        if status:
            return [g for g in self.goals if g.status == status]
        return list(self.goals)

    async def list_goals_async(self, status: str | None = None) -> list[UserGoal]:
        return self.list_goals(status)

    def update_goal_status(self, goal_id: str, status: str) -> bool:
        for g in self.goals:
            if g.id == goal_id:
                g.status = status
                self.save_state()
                return True
        return False

    async def update_goal_status_async(self, goal_id: str, status: str) -> bool:
        return self.update_goal_status(goal_id, status)

    def get_active_goals(self) -> list[UserGoal]:
        now = datetime.now()
        active = []
        for g in self.goals:
            if g.status != "active":
                continue
            if g.deadline:
                try:
                    dl = datetime.fromisoformat(g.deadline)
                    if dl < now:
                        continue
                except (ValueError, TypeError):
                    pass
            active.append(g)
        active.sort(key=lambda x: x.priority, reverse=True)
        return active

    def get_goal_context(self, goal_id: str) -> dict[str, Any] | None:
        for g in self.goals:
            if g.id == goal_id:
                return g.to_dict()
        return None

    # ── Distraction management ───────────────────────────

    def add_distraction_pattern(self, name: str, process_names: list[str],
                                window_patterns: list[str], category: str = "entertainment") -> DistractionAction:
        da = DistractionAction(
            type=category,
            name=name,
            process_names=process_names,
            window_title_patterns=window_patterns,
            category=category,
        )
        self.distractions.append(da)
        self.save_state()
        return da

    async def add_distraction_pattern_async(self, name: str, process_names: list[str],
                                            window_patterns: list[str], category: str = "entertainment") -> DistractionAction:
        return self.add_distraction_pattern(name, process_names, window_patterns, category)

    # ── Window / process scanning ────────────────────────

    def _get_running_processes(self) -> set[str]:
        try:
            import psutil
            return {p.info["name"] for p in psutil.process_iter(["name"]) if p.info.get("name")}
        except Exception:
            return set()

    def _get_window_titles(self) -> list[str]:
        titles = []
        try:
            import win32gui

            def _enum_callback(hwnd: int, results: list[str]) -> None:
                if win32gui.IsWindowVisible(hwnd):
                    text = win32gui.GetWindowText(hwnd)
                    if text:
                        results.append(text.lower())

            win32gui.EnumWindows(_enum_callback, titles)
        except ImportError:
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "(Get-Process | Where-Object { $_.MainWindowTitle } | Select-Object -ExpandProperty MainWindowTitle) -join '|'"],
                    capture_output=True, text=True, timeout=5
                )
                if result.stdout:
                    titles = [t.lower() for t in result.stdout.strip().split("|") if t.strip()]
            except Exception:
                pass
        except Exception:
            pass
        return titles

    def scan_for_distractions(self) -> list[tuple[DistractionAction, str]]:
        """Check running processes & window titles for known distractions.
        Returns list of (DistractionAction, matched_detail) tuples.
        """
        found: list[tuple[DistractionAction, str]] = []
        processes = self._get_running_processes()
        window_titles = self._get_window_titles()

        for d in self.distractions:
            for proc in d.process_names:
                if proc.lower() in processes:
                    found.append((d, f"process:{proc}"))
                    break
            else:
                for pattern in d.window_title_patterns:
                    if any(pattern.lower() in title for title in window_titles):
                        found.append((d, f"window match:{pattern}"))
                        break

        return found

    async def scan_for_distractions_async(self) -> list[tuple[DistractionAction, str]]:
        return await asyncio.to_thread(self.scan_for_distractions)

    def detect_entertainment_windows(self) -> list[dict[str, str]]:
        """Use win32gui to find entertainment-related windows by title pattern."""
        titles = self._get_window_titles()
        entertainment_keywords = [
            "youtube", "netflix", "prime video", "hotstar", "disney+",
            "crunchyroll", "twitch", "spotify", "vlc", "plex",
            "instagram", "facebook", "reddit", "tiktok", "twitter",
            "x.com", "snapchat", "whatsapp", "discord", "pornhub",
            "xvideos", "xnxx", "xhamster", "onlyfans", "chaturbate",
            "steam", "epic games", "roblox", "minecraft",
            "fortnite", "valorant", "league of legends",
        ]
        results = []
        for title in titles:
            for kw in entertainment_keywords:
                if kw.lower() in title.lower():
                    results.append({"title": title, "matched": kw})
                    break
        return results

    async def detect_entertainment_windows_async(self) -> list[dict[str, str]]:
        return await asyncio.to_thread(self.detect_entertainment_windows)

    # ── Escalation actions ───────────────────────────────

    def warn_user(self, distraction: DistractionAction) -> str:
        import random
        msg = random.choice(_WARNING_MESSAGES).format(name=distraction.name)
        self._send_notification(f"⚠️ {msg}", urgency="normal")
        return msg

    def close_distraction(self, distraction: DistractionAction) -> list[str]:
        closed = []
        for proc in distraction.process_names:
            try:
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", proc],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    closed.append(proc)
            except Exception:
                pass

        browser_exes = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"}
        if any(p.lower() in browser_exes for p in distraction.process_names):
            conhost_tabs = self._close_browser_tabs(distraction.window_title_patterns)
            closed.extend(conhost_tabs)

        return closed

    def _close_browser_tabs(self, patterns: list[str]) -> list[str]:
        """Try to close browser tabs matching URL patterns via JS alert / PowerShell."""
        closed = []
        try:
            import psutil
            for proc in psutil.process_iter(["pid", "name"]):
                if not proc.info.get("name"):
                    continue
                pname = proc.info["name"].lower()
                if pname not in ("chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"):
                    continue
                try:
                    child = proc.children()
                    if child:
                        for c in child:
                            c.kill()
                            closed.append(f"{pname}:{c.pid}")
                except Exception:
                    pass
        except Exception:
            pass

        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", "chrome.exe"],
                capture_output=True, text=True, timeout=5
            )
            closed.append("chrome.exe")
        except Exception:
            pass

        return closed

    def open_learning_material(self, goal: UserGoal) -> list[str]:
        opened = []
        urls = list(goal.learning_urls)

        if not urls:
            search_query = goal.title.replace(" ", "+")
            urls.append(f"https://www.google.com/search?q={search_query}+tutorial")

        for url in urls:
            try:
                webbrowser.open(url)
                opened.append(url)
            except Exception:
                pass
        return opened

    def scold_user(self, distraction: DistractionAction, strike: int) -> str:
        import random
        idx = min(strike - 1, len(_SCOLD_MESSAGES) - 1)
        msg = _SCOLD_MESSAGES[idx].format(strike=strike)
        self._send_notification(f"🔴 {msg}", urgency="critical")
        return msg

    def _send_notification(self, message: str, urgency: str = "normal") -> None:
        try:
            from friday.notify import send_notification
            send_notification(message, urgency=urgency)
        except Exception:
            safe_msg = message[:200].replace('"', '`"')
            try:
                ps_script = f'''
$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textNodes = $template.GetElementsByTagName("text")
$textNodes.Item(0).AppendChild($template.CreateTextNode("Friday")) > $null
$textNodes.Item(1).AppendChild($template.CreateTextNode("{safe_msg}")) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Friday").Show($toast)
'''
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_script],
                    capture_output=True, timeout=5
                )
            except Exception:
                print(f"[GoalPunisher - {urgency.upper()}] {message}")

    # ── Main violation flow ──────────────────────────────

    def handle_violation(self, distraction: DistractionAction) -> dict[str, Any]:
        now = time.time()
        is_repeat = (
            self.violations
            and self.violations[-1].distraction_name == distraction.name
            and (now - self._last_warning_time) < 120
        )

        self._strikes += 1
        result: dict[str, Any] = {
            "distraction": distraction.name,
            "type": distraction.type,
            "strike": self._strikes,
            "actions": [],
        }

        if self._strikes == 1 or not is_repeat:
            msg = self.warn_user(distraction)
            result["actions"].append({"action": "warning", "message": msg})
            action_taken = "warning"
        elif self._strikes == 2:
            msg = self.warn_user(distraction)
            result["actions"].append({"action": "warning", "message": msg})
            closed = self.close_distraction(distraction)
            result["actions"].append({"action": "closed", "processes": closed})
            active_goals = self.get_active_goals()
            if active_goals:
                opened = self.open_learning_material(active_goals[0])
                result["actions"].append({"action": "opened_learning", "urls": opened})
            action_taken = "closed"
        else:
            msg = self.scold_user(distraction, self._strikes)
            result["actions"].append({"action": "scolded", "message": msg})
            closed = self.close_distraction(distraction)
            result["actions"].append({"action": "closed", "processes": closed})
            active_goals = self.get_active_goals()
            if active_goals:
                opened = self.open_learning_material(active_goals[0])
                result["actions"].append({"action": "opened_learning", "urls": opened})
            action_taken = "scolded"

        self._last_warning_time = now

        record = ViolationRecord(
            distraction_type=distraction.type,
            distraction_name=distraction.name,
            strike_number=self._strikes,
            action_taken=action_taken,
        )
        self.violations.append(record)
        self.save_state()

        return result

    async def handle_violation_async(self, distraction: DistractionAction) -> dict[str, Any]:
        return await asyncio.to_thread(self.handle_violation, distraction)

    # ── Strike management ────────────────────────────────

    def get_strike_count(self) -> int:
        return self._strikes

    async def get_strike_count_async(self) -> int:
        return self._strikes

    def reset_strikes(self) -> None:
        self._strikes = 0
        self.save_state()

    async def reset_strikes_async(self) -> None:
        self.reset_strikes()

    # ── Goal urgency checks ─────────────────────────────

    def _get_goals_in_jeopardy(self) -> list[UserGoal]:
        """Return active goals where deadline is approaching or user is idle too long.
        
        A goal is 'in jeopardy' if:
        - Deadline exists and < 25% time remaining (urgency)
        - OR user has been idle on ALL goals for > 2 days (idle slacking)
        - OR priority is 4+ and deadline exists (any deadline = urgent for high pri)
        """
        now = datetime.now()
        jeopardized: list[UserGoal] = []

        for g in self.goals:
            if g.status != "active":
                continue
            if not g.deadline:
                continue
            try:
                dl = datetime.fromisoformat(g.deadline)
                if dl <= now:
                    continue  # already past deadline, skip
                total = (dl - datetime.fromisoformat(g.created_at)).total_seconds()
                elapsed = (now - datetime.fromisoformat(g.created_at)).total_seconds()
                if total <= 0:
                    continue
                pct_remaining = (1 - elapsed / total) * 100
                is_urgent = pct_remaining < 25.0
                is_high_pri = g.priority >= 4
                if is_urgent or is_high_pri:
                    jeopardized.append(g)
            except (ValueError, TypeError):
                continue

        return jeopardized

    def _is_user_idle_too_long(self) -> bool:
        """Check if user has been idle (no goal progress activity) for > 2 days."""
        if not self.violations:
            return False
        last_violation_time_str = self.violations[-1].timestamp
        try:
            last = datetime.fromisoformat(last_violation_time_str)
            idle_days = (datetime.now() - last).days
            return idle_days >= 2
        except (ValueError, TypeError):
            return False

    def _should_enforce(self) -> bool:
        """Only enforce punishment if goals are truly in jeopardy."""
        if not self.goals:
            return False
        if self._get_goals_in_jeopardy():
            return True
        if self._is_user_idle_too_long():
            return True
        return False

    # ── Full scan-then-enforce ───────────────────────────

    async def full_enforcement_cycle(self) -> dict[str, Any]:
        """Scan for distractions, then enforce ONLY if goals are in jeopardy.
        
        Three enforcement tiers:
        - No jeopardized goals → silently note distraction, no action
        - Jeopardized goals + distraction found → warn → close → scold escalation
        - Idle > 2 days + any distraction → escalate directly
        """
        result: dict[str, Any] = {
            "distractions_found": [],
            "violations_handled": [],
            "goals_in_jeopardy": [],
            "enforcement_skipped": False,
        }

        jeopardized = self._get_goals_in_jeopardy()
        idle_too_long = self._is_user_idle_too_long()

        result["goals_in_jeopardy"] = [g.title for g in jeopardized]

        if not jeopardized and not idle_too_long:
            result["enforcement_skipped"] = True
            return result

        distractions = await self.scan_for_distractions_async()
        if not distractions:
            return result

        for d, detail in distractions:
            violation = await self.handle_violation_async(d)
            result["distractions_found"].append({"name": d.name, "detail": detail})
            result["violations_handled"].append(violation)

        return result
