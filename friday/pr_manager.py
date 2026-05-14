"""Friday Proactive PR Manager — polls configured GitHub repos for open PRs,
auto-analyzes new ones, and surfaces reviews. No GPU needed."""
from __future__ import annotations
import os
import json
import threading
import time
from datetime import datetime
from typing import Optional

from friday._paths import FRIDAY_MEMORY

_STATE_FILE = os.path.join(FRIDAY_MEMORY, "pr_manager_state.json")
_watch_thread: Optional[threading.Thread] = None
_watch_stop = threading.Event()


def _load_state() -> dict:
    if os.path.exists(_STATE_FILE):
        try:
            with open(_STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"repos": [], "seen_prs": {}, "reviews": []}


def _save_state(state: dict):
    os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def _get_github() -> object:
    from friday.github import GitHubIntegration
    return GitHubIntegration()


def list_repos() -> str:
    state = _load_state()
    repos = state.get("repos", [])
    if not repos:
        return "No repos configured. Use add_repo to add one."
    lines = ["### WATCHED REPOS"]
    for r in repos:
        prs = state.get("seen_prs", {}).get(r, [])
        lines.append(f"  - {r} ({len(prs)} PRs tracked)")
    return "\n".join(lines)


def add_repo(repo: str = "hackers-reality/friday") -> str:
    state = _load_state()
    repos = state.setdefault("repos", [])
    if repo in repos:
        return f"[OK] {repo} already watched."
    repos.append(repo)
    _save_state(state)
    return f"[OK] Now watching {repo} for new PRs."


def remove_repo(repo: str) -> str:
    state = _load_state()
    repos = state.get("repos", [])
    if repo not in repos:
        return f"[FAIL] {repo} not in watch list."
    repos.remove(repo)
    state.get("seen_prs", {}).pop(repo, None)
    _save_state(state)
    return f"[OK] Stopped watching {repo}."


def _scan_repo(repo: str, gh: object) -> list:
    """Fetch open PRs for a repo and return new (unseen) ones."""
    state = _load_state()
    seen = state.setdefault("seen_prs", {}).setdefault(repo, [])

    # Use the GitHubIntegration to list PRs
    gh.repo = repo
    endpoint = f"/repos/{repo}/pulls?state=open&per_page=20"
    result = gh._request("GET", endpoint)
    if "error" in result:
        return []
    if not isinstance(result, list):
        return []

    new_prs = []
    for pr in result:
        pr_id = str(pr["number"])
        if pr_id in seen:
            continue

        # Track it
        seen.append(pr_id)
        pr_info = {
            "number": pr["number"],
            "title": pr["title"],
            "author": pr["user"]["login"] if pr.get("user") else "unknown",
            "created_at": pr.get("created_at", ""),
            "url": pr["html_url"],
            "discovered_at": datetime.now().isoformat(),
            "analyzed": False,
        }
        new_prs.append(pr_info)
        state["seen_prs"][repo].append(pr_id)

    _save_state(state)
    return new_prs


def _auto_review(pr_info: dict, gh: object) -> str:
    """Run the existing review pipeline on a PR."""
    from friday.github import github_review_pr
    try:
        review = github_review_pr(pr_info["number"])
        pr_info["analyzed"] = True

        state = _load_state()
        reviews = state.setdefault("reviews", [])
        reviews.append({
            "repo": gh.repo,
            "pr_number": pr_info["number"],
            "title": pr_info["title"],
            "timestamp": datetime.now().isoformat(),
            "summary": review[:500],
        })
        _save_state(state)
        return review
    except Exception as e:
        return f"[FAIL] Auto-review error: {e}"


def scan_now(auto_review: bool = True) -> str:
    """Scan all configured repos for new PRs, optionally auto-analyze."""
    gh = _get_github()
    state = _load_state()
    repos = state.get("repos", [])
    if not repos:
        return "No repos configured. Use add_repo first."

    lines = []
    for repo in repos:
        new_prs = _scan_repo(repo, gh)
        if not new_prs:
            lines.append(f"  {repo}: no new PRs")
            continue
        for pr in new_prs:
            lines.append(f"  #{pr['number']} {pr['title']} by {pr['author']}")
            if auto_review:
                review = _auto_review(pr, gh)
                lines.append(f"       Review: {review[:200]}...")

    if not lines:
        return "Scanned — no new PRs found."
    return "### PR SCAN RESULTS\n" + "\n".join(lines)


def reviews(limit: int = 10) -> str:
    state = _load_state()
    all_reviews = state.get("reviews", [])
    if not all_reviews:
        return "No reviews performed yet."
    lines = ["### RECENT PR REVIEWS"]
    for r in all_reviews[-limit:]:
        ts = r.get("timestamp", "?")[:19]
        lines.append(f"  [{ts}] {r.get('repo', '?')} #{r['pr_number']}: {r.get('title', '?')}")
    return "\n".join(lines)


def status() -> str:
    state = _load_state()
    repos = state.get("repos", [])
    total_seen = sum(len(v) for v in state.get("seen_prs", {}).values())
    total_reviews = len(state.get("reviews", []))
    running = _watch_thread is not None and _watch_thread.is_alive()
    return (
        f"PR Manager: {'ACTIVE' if running else 'IDLE'}\n"
        f"Watched repos: {len(repos)}\n"
        f"Total PRs tracked: {total_seen}\n"
        f"Reviews completed: {total_reviews}"
    )


def start_watcher():
    global _watch_thread, _watch_stop
    if _watch_thread and _watch_thread.is_alive():
        return
    _watch_stop.clear()

    def _loop():
        while not _watch_stop.is_set():
            try:
                state = _load_state()
                if state.get("repos"):
                    gh = _get_github()
                    for repo in state["repos"]:
                        new_prs = _scan_repo(repo, gh)
                        for pr in new_prs:
                            print(f"[PR_MANAGER] New PR in {repo}: #{pr['number']} {pr['title']}")
                            _auto_review(pr, gh)
                            print(f"[PR_MANAGER] Auto-reviewed #{pr['number']}")
            except Exception:
                pass
            _watch_stop.wait(300)

    _watch_thread = threading.Thread(target=_loop, daemon=True)
    _watch_thread.start()


def stop_watcher():
    _watch_stop.set()


def _fetch_prs(repo: str, state: str = "open") -> str:
    """Fetch PRs directly from GitHub API for any repo (not just watched ones)."""
    from friday.github import github_list_prs as _glp
    return _glp(repo=repo, state=state)


def pr_manager_tool(action: str = "status", **kwargs) -> str:
    """Proactive PR manager: polls GitHub repos for open PRs and auto-reviews them.
    Actions: status (show state), list_repos (show watched repos), add_repo (add repo, default: hackers-reality/friday),
    remove_repo (stop watching a repo), scan_now (immediate scan, auto_review=true by default),
    list_prs (fetch ALL open PRs for a repo: repo=owner/repo, state=open/closed/all),
    reviews (recent PR reviews), watch (start background poll every 5 min), stop."""
    try:
        if action == "status":
            return status()
        elif action == "list_repos":
            return list_repos()
        elif action == "add_repo":
            return add_repo(repo=kwargs.get("repo", "hackers-reality/friday"))
        elif action == "remove_repo":
            repo = kwargs.get("repo", "")
            if not repo:
                return "[FAIL] repo parameter is required."
            return remove_repo(repo)
        elif action == "scan_now":
            auto_review = kwargs.get("auto_review", True)
            if isinstance(auto_review, str):
                auto_review = auto_review.lower() in ("true", "1", "yes")
            return scan_now(auto_review=auto_review)
        elif action == "list_prs":
            repo = kwargs.get("repo", "")
            state = kwargs.get("state", "open")
            if not repo:
                return "[FAIL] repo parameter is required (e.g., 'vierisid/jarvis')."
            return _fetch_prs(repo=repo, state=state)
        elif action == "reviews":
            return reviews(limit=kwargs.get("limit", 10))
        elif action == "watch":
            start_watcher()
            return "[OK] PR manager watcher started (5 min polling)."
        elif action == "stop":
            stop_watcher()
            return "[OK] PR manager watcher stopped."
        else:
            return f"[FAIL] Unknown action: {action}"
    except Exception as e:
        return f"[FAIL] PR manager error: {e}"
