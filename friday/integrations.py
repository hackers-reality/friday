"""
Friday Integrations - Third-party service integrations.
Slack, Discord, GitHub, Jira, Trello, and more.
"""
from __future__ import annotations

import os
import sys
import json
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import requests


# ─── Slack Integration ──────────────────────────#

class SlackIntegration:
    """Slack API integration."""
    
    def __init__(self, token: str = None):
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        self.available = self.token is not None
        
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8",
        }
    
    def send_message(self, channel: str, text: str) -> Dict[str, Any]:
        """Send message to Slack channel."""
        if not self.available:
            return {"success": False, "error": "Slack token not set. Set SLACK_BOT_TOKEN."}
        
        try:
            response = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers=self._headers(),
                json={"channel": channel, "text": text},
                timeout=10,
            )
            
            data = response.json()
            if data.get("ok"):
                return {"success": True, "ts": data.get("ts"), "channel": channel}
            else:
                return {"success": False, "error": data.get("error", "Unknown error")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_channels(self) -> Dict[str, Any]:
        """List Slack channels."""
        if not self.available:
            return {"success": False, "error": "Slack token not set."}
        
        try:
            response = requests.get(
                "https://slack.com/api/conversations.list",
                headers=self._headers(),
                timeout=10,
            )
            
            data = response.json()
            if data.get("ok"):
                channels = [{"id": c["id"], "name": c["name"]} for c in data.get("channels", [])]
                return {"success": True, "channels": channels, "count": len(channels)}
            else:
                return {"success": False, "error": data.get("error", "Unknown error")}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Discord Integration ──────────────────────────#

class DiscordIntegration:
    """Discord bot integration."""
    
    def __init__(self, token: str = None, bot: bool = True):
        self.token = token or os.getenv("DISCORD_BOT_TOKEN")
        self.bot = bot
        self.available = self.token is not None
        
    def send_message(self, channel_id: str, content: str) -> Dict[str, Any]:
        """Send message to Discord channel."""
        if not self.available:
            return {"success": False, "error": "Discord token not set. Set DISCORD_BOT_TOKEN."}
        
        try:
            headers = {
                "Authorization": f"Bot {self.token}" if self.bot else self.token,
                "Content-Type": "application/json",
            }
            
            response = requests.post(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers=headers,
                json={"content": content},
                timeout=10,
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                return {"success": True, "id": data.get("id"), "channel_id": channel_id}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── GitHub Integration ──────────────────────────#

class GitHubIntegration:
    """GitHub API integration."""
    
    def __init__(self, token: str = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.available = self.token is not None
        
    def _headers(self):
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers
    
    def list_repos(self, user: str = None) -> Dict[str, Any]:
        """List GitHub repositories."""
        try:
            if user:
                url = f"https://api.github.com/users/{user}/repos"
            else:
                url = "https://api.github.com/user/repos"
            
            response = requests.get(url, headers=self._headers(), timeout=10)
            
            if response.status_code == 200:
                repos = response.json()
                return {
                    "success": True,
                    "repos": [{"name": r["name"], "full_name": r["full_name"]} for r in repos],
                    "count": len(repos),
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_issue(self, repo: str, title: str, body: str = "") -> Dict[str, Any]:
        """Create GitHub issue."""
        if not self.available:
            return {"success": False, "error": "GitHub token not set. Set GITHUB_TOKEN."}
        
        try:
            url = f"https://api.github.com/repos/{repo}/issues"
            response = requests.post(
                url,
                headers=self._headers(),
                json={"title": title, "body": body},
                timeout=10,
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                return {"success": True, "number": data["number"], "html_url": data["html_url"]}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Jira Integration ──────────────────────────#

class JiraIntegration:
    """Jira API integration."""
    
    def __init__(self, server: str = None, username: str = None, token: str = None):
        self.server = server or os.getenv("JIRA_SERVER")
        self.username = username or os.getenv("JIRA_USERNAME")
        self.token = token or os.getenv("JIRA_API_TOKEN")
        self.available = all([self.server, self.username, self.token])
        
    def _auth(self):
        return (self.username, self.token)
    
    def search_issues(self, jql: str) -> Dict[str, Any]:
        """Search Jira issues using JQL."""
        if not self.available:
            return {"success": False, "error": "Jira credentials not set."}
        
        try:
            url = f"{self.server}/rest/api/2/search"
            response = requests.get(
                url,
                auth=self._auth(),
                params={"jql": jql, "maxResults": 50},
                timeout=10,
            )
            
            if response.status_code == 200:
                data = response.json()
                issues = [{"key": i["key"], "summary": i["fields"]["summary"]} for i in data.get("issues", [])]
                return {"success": True, "issues": issues, "count": len(issues)}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_issue(self, project: str, summary: str, issue_type: str = "Task") -> Dict[str, Any]:
        """Create Jira issue."""
        if not self.available:
            return {"success": False, "error": "Jira credentials not set."}
        
        try:
            url = f"{self.server}/rest/api/2/issue"
            payload = {
                "fields": {
                    "project": {"key": project},
                    "summary": summary,
                    "issuetype": {"name": issue_type},
                }
            }
            
            response = requests.post(
                url,
                auth=self._auth(),
                json=payload,
                timeout=10,
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                return {"success": True, "key": data["key"], "self": data["self"]}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Trello Integration ──────────────────────────#

class TrelloIntegration:
    """Trello API integration."""
    
    def __init__(self, api_key: str = None, token: str = None):
        self.api_key = api_key or os.getenv("TRELLO_API_KEY")
        self.token = token or os.getenv("TRELLO_TOKEN")
        self.available = all([self.api_key, self.token])
        
    def _params(self):
        return {"key": self.api_key, "token": self.token}
    
    def list_boards(self) -> Dict[str, Any]:
        """List Trello boards."""
        if not self.available:
            return {"success": False, "error": "Trello credentials not set."}
        
        try:
            response = requests.get(
                "https://api.trello.com/1/members/me/boards",
                params=self._params(),
                timeout=10,
            )
            
            if response.status_code == 200:
                boards = response.json()
                return {
                    "success": True,
                    "boards": [{"id": b["id"], "name": b["name"]} for b in boards],
                    "count": len(boards),
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Integrations Tool for Friday ──────────────────────────#

def integrations_tool(
    action: str = "status",
    target: str = None,
    params: Dict = None,
) -> str:
    """
    Friday tool for third-party integrations.
    Actions: status, slack_msg, slack_channels, discord_msg,
            github_repos, github_issue, jira_search, jira_create,
            trello_boards
    """
    params = params or {}
    
    if action == "status":
        lines = ["### INTEGRATIONS STATUS", ""]
        lines.append("**Available Integrations**:")
        lines.append("  - Slack (chat)")
        lines.append("  - Discord (chat)")
        lines.append("  - GitHub (repo management)")
        lines.append("  - Jira (issue tracking)")
        lines.append("  - Trello (board management)")
        return "\n".join(lines)
    
    if action == "slack_msg":
        if not target or "message" not in params:
            return "[FAIL] Channel and message required."
        slack = SlackIntegration()
        result = slack.send_message(target, params["message"])
        if result["success"]:
            return f"### SLACK MESSAGE\n\n[OK] Sent to {result['channel']}"
        else:
            return f"[FAIL] Slack error: {result.get('error', 'Unknown')}"
    
    if action == "slack_channels":
        slack = SlackIntegration()
        result = slack.list_channels()
        if result["success"]:
            lines = [f"### SLACK CHANNELS ({result['count']})", ""]
            for ch in result["channels"][:10]:
                lines.append(f"  - #{ch['name']}")
            return "\n".join(lines)
        else:
            return f"[FAIL] Slack error: {result.get('error', 'Unknown')}"
    
    if action == "discord_msg":
        if not target or "message" not in params:
            return "[FAIL] Channel ID and message required."
        discord = DiscordIntegration()
        result = discord.send_message(target, params["message"])
        if result["success"]:
            return f"### DISCORD MESSAGE\n\n[OK] Sent to channel {result['channel_id']}"
        else:
            return f"[FAIL] Discord error: {result.get('error', 'Unknown')}"
    
    if action == "github_repos":
        github = GitHubIntegration()
        user = params.get("user")
        result = github.list_repos(user)
        if result["success"]:
            lines = [f"### GITHUB REPOS ({result['count']})", ""]
            for repo in result["repos"][:10]:
                lines.append(f"  - {repo['full_name']}")
            return "\n".join(lines)
        else:
            return f"[FAIL] GitHub error: {result.get('error', 'Unknown')}"
    
    if action == "github_issue":
        if not target or "title" not in params:
            return "[FAIL] Repo and title required."
        github = GitHubIntegration()
        result = github.create_issue(target, params["title"], params.get("body", ""))
        if result["success"]:
            return f"### GITHUB ISSUE\n\n[OK] Created #{result['number']}\nURL: {result['html_url']}"
        else:
            return f"[FAIL] GitHub error: {result.get('error', 'Unknown')}"
    
    if action == "jira_search":
        if not target:
            return "[FAIL] JQL query required."
        jira = JiraIntegration()
        result = jira.search_issues(target)
        if result["success"]:
            lines = [f"### JIRA ISSUES ({result['count']})", ""]
            for issue in result["issues"][:10]:
                lines.append(f"  - {issue['key']}: {issue['summary']}")
            return "\n".join(lines)
        else:
            return f"[FAIL] Jira error: {result.get('error', 'Unknown')}"
    
    if action == "jira_create":
        if not target or "summary" not in params:
            return "[FAIL] Project and summary required."
        jira = JiraIntegration()
        result = jira.create_issue(target, params["summary"], params.get("issuetype", "Task"))
        if result["success"]:
            return f"### JIRA ISSUE\n\n[OK] Created {result['key']}"
        else:
            return f"[FAIL] Jira error: {result.get('error', 'Unknown')}"
    
    if action == "trello_boards":
        trello = TrelloIntegration()
        result = trello.list_boards()
        if result["success"]:
            lines = [f"### TRELLO BOARDS ({result['count']})", ""]
            for board in result["boards"][:10]:
                lines.append(f"  - {board['name']}")
            return "\n".join(lines)
        else:
            return f"[FAIL] Trello error: {result.get('error', 'Unknown')}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Integrations...\n")
    
    # Test status
    print("--- Integrations Status ---")
    print(integrations_tool("status"))
    
    # Test GitHub (public repos)
    print("\n--- GitHub Repos (no auth) ---")
    print(integrations_tool("github_repos", params={"user": "torvalds"}))
