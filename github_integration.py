"""
Friday GitHub Integration - Code analysis, PR management, repo operations.
Uses GitHub API for seamless integration with GitHub.
"""
from __future__ import annotations

import os
import json
import base64
from typing import Optional, Dict, Any, List


# ─── GitHub Client ────────────────────────────────────#

class GitHubClient:
    """GitHub API client for Friday."""
    
    def __init__(self, token: str = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.api_base = "https://api.github.com"
        self.headers = {}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
            self.headers["Accept"] = "application/vnd.github.v3+json"
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make a GitHub API request."""
        import requests
        
        url = f"{self.api_base}{endpoint}"
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except Exception as e:
            return {"error": str(e)}
    
    def is_authenticated(self) -> bool:
        """Check if authenticated."""
        if not self.token:
            return False
        result = self._request("GET", "/user")
        return "error" not in result
    
    def get_user(self) -> Dict:
        """Get authenticated user info."""
        return self._request("GET", "/user")
    
    def list_repos(self, username: str = None) -> List[Dict]:
        """List repositories."""
        if username:
            endpoint = f"/users/{username}/repos"
        else:
            endpoint = "/user/repos"
        return self._request("GET", endpoint)
    
    def get_repo(self, owner: str, repo: str) -> Dict:
        """Get repository info."""
        return self._request("GET", f"/repos/{owner}/{repo}")
    
    def create_repo(self, name: str, description: str = "", private: bool = False) -> Dict:
        """Create a new repository."""
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": True,
        }
        return self._request("POST", "/user/repos", data)
    
    def list_issues(self, owner: str, repo: str, state: str = "open") -> List[Dict]:
        """List issues."""
        return self._request("GET", f"/repos/{owner}/{repo}/issues?state={state}")
    
    def create_issue(self, owner: str, repo: str, title: str, body: str = "") -> Dict:
        """Create an issue."""
        data = {"title": title, "body": body}
        return self._request("POST", f"/repos/{owner}/{repo}/issues", data)
    
    def list_prs(self, owner: str, repo: str, state: str = "open") -> List[Dict]:
        """List pull requests."""
        return self._request("GET", f"/repos/{owner}/{repo}/pulls?state={state}")
    
    def create_pr(self, owner: str, repo: str, title: str, head: str, base: str = "main", body: str = "") -> Dict:
        """Create a pull request."""
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
        }
        return self._request("POST", f"/repos/{owner}/{repo}/pulls", data)
    
    def get_file_content(self, owner: str, repo: str, path: str, ref: str = "main") -> str:
        """Get file content from repo."""
        result = self._request("GET", f"/repos/{owner}/{repo}/contents/{path}?ref={ref}")
        if "content" in result:
            return base64.b64decode(result["content"]).decode("utf-8")
        return f"Error: {result.get('error', 'Unknown error')}"
    
    def create_file(self, owner: str, repo: str, path: str, content: str, message: str, branch: str = "main") -> Dict:
        """Create or update a file."""
        data = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        return self._request("PUT", f"/repos/{owner}/{repo}/contents/{path}", data)
    
    def list_commits(self, owner: str, repo: str, limit: int = 10) -> List[Dict]:
        """List recent commits."""
        return self._request("GET", f"/repos/{owner}/{repo}/commits?per_page={limit}")
    
    def search_repos(self, query: str) -> List[Dict]:
        """Search repositories."""
        return self._request("GET", f"/search/repositories?q={query}&per_page=10").get("items", [])
    
    def search_code(self, query: str) -> List[Dict]:
        """Search code across GitHub."""
        return self._request("GET", f"/search/code?q={query}&per_page=10").get("items", [])


# ─── Singleton Client ────────────────────────────────────#

_client: Optional[GitHubClient] = None

def get_github_client() -> GitHubClient:
    """Get or create GitHub client."""
    global _client
    if _client is None:
        _client = GitHubClient()
    return _client


# ─── Tool Function for Friday ────────────────────────────────────#

def github_tool(
    action: str = "status",
    owner: str = None,
    repo: str = None,
    title: str = None,
    body: str = None,
    path: str = None,
    content: str = None,
    query: str = None,
) -> str:
    """
    Friday tool for GitHub operations.
    Actions: status, repos, create_repo, issues, create_issue,
            prs, create_pr, get_file, create_file, commits, search_repos, search_code
    """
    client = get_github_client()
    
    if not client.token:
        return "[FAIL] GITHUB_TOKEN not set. Get token from: https://github.com/settings/tokens"
    
    if action == "status":
        if client.is_authenticated():
            user = client.get_user()
            return f"[OK] Authenticated as: {user.get('login', 'Unknown')}"
        return "[FAIL] Not authenticated. Check GITHUB_TOKEN."
    
    if action == "repos":
        repos = client.list_repos()
        if isinstance(repos, dict) and "error" in repos:
            return f"[FAIL] {repos['error']}"
        lines = ["### YOUR REPOSITORIES", ""]
        for r in repos[:20]:
            lines.append(f"**{r['full_name']}** - {r.get('description', 'No description')}")
        return "\n".join(lines)
    
    if action == "create_repo":
        if not title:
            return "[FAIL] Repository name required."
        result = client.create_repo(title, body or "")
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return f"[OK] Created repo: {result.get('html_url')}"
    
    if action == "issues":
        if not owner or not repo:
            return "[FAIL] Owner and repo required."
        issues = client.list_issues(owner, repo)
        lines = [f"### ISSUES: {owner}/{repo}", ""]
        for issue in issues[:20]:
            lines.append(f"#{issue['number']} - {issue['title']} ({issue['state']})")
        return "\n".join(lines)
    
    if action == "create_issue":
        if not owner or not repo or not title:
            return "[FAIL] Owner, repo, and title required."
        result = client.create_issue(owner, repo, title, body or "")
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return f"[OK] Created issue: {result.get('html_url')}"
    
    if action == "prs":
        if not owner or not repo:
            return "[FAIL] Owner and repo required."
        prs = client.list_prs(owner, repo)
        lines = [f"### PULL REQUESTS: {owner}/{repo}", ""]
        for pr in prs[:20]:
            lines.append(f"#{pr['number']} - {pr['title']} ({pr['state']})")
        return "\n".join(lines)
    
    if action == "get_file":
        if not owner or not repo or not path:
            return "[FAIL] Owner, repo, and path required."
        content = client.get_file_content(owner, repo, path)
        return content[:5000]
    
    if action == "create_file":
        if not owner or not repo or not path or content is None:
            return "[FAIL] Owner, repo, path, and content required."
        result = client.create_file(owner, repo, path, content, title or "Update file")
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return f"[OK] File created/updated: {result.get('content', {}).get('html_url', '')}"
    
    if action == "commits":
        if not owner or not repo:
            return "[FAIL] Owner and repo required."
        commits = client.list_commits(owner, repo)
        lines = [f"### RECENT COMMITS: {owner}/{repo}", ""]
        for c in commits[:10]:
            lines.append(f"{c['sha'][:7]} - {c['commit']['message'][:80]}")
        return "\n".join(lines)
    
    if action == "search_repos":
        if not query:
            return "[FAIL] Search query required."
        repos = client.search_repos(query)
        lines = [f"### SEARCH RESULTS: {query}", ""]
        for r in repos[:10]:
            lines.append(f"**{r['full_name']}** - ⭐ {r['stargazers_count']}")
        return "\n".join(lines)
    
    if action == "search_code":
        if not query:
            return "[FAIL] Search query required."
        results = client.search_code(query)
        lines = [f"### CODE SEARCH: {query}", ""]
        for r in results[:10]:
            lines.append(f"{r['repository']['full_name']} - {r['path']}")
        return "\n".join(lines)
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing GitHub Integration...")
    
    client = get_github_client()
    
    if not client.token:
        print("[FAIL] Set GITHUB_TOKEN environment variable")
    else:
        print("\n--- Status ---")
        print(github_tool("status"))
        
        print("\n--- Search Repos ---")
        print(github_tool("search_repos", query="friday ai agent"))
