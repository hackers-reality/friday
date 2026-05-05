"""GitHub integration for Friday - Self-modification support."""

import os
import json
import base64
from typing import Optional, Dict, Any, List

class GitHubIntegration:
    """Integrate with GitHub for code management and self-modification."""
    
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.repo = os.getenv("GITHUB_REPO", "vierisid/jarvis")  # Default repo
        self.branch = os.getenv("GITHUB_BRANCH", "main")
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}" if self.token else "",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make a GitHub API request."""
        import requests
        url = f"{self.api_base}{endpoint}"
        try:
            if data:
                resp = requests.request(method, url, headers=self.headers, json=data, timeout=10)
            else:
                resp = requests.request(method, url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except Exception as e:
            return {"error": str(e)}
    
    def list_files(self, path: str = "") -> str:
        """List files in the repository."""
        endpoint = f"/repos/{self.repo}/contents/{path}"
        result = self._request("GET", endpoint)
        if "error" in result:
            return f"Error: {result['error']}"
        if isinstance(result, list):
            files = "\n".join(f"- {f['name']} ({f['type']})" for f in result)
            return f"Files in {path or 'root'}:\n{files}"
        return f"Error listing files: {result}"
    
    def read_file(self, path: str) -> str:
        """Read a file from the repository."""
        endpoint = f"/repos/{self.repo}/contents/{path}"
        result = self._request("GET", endpoint)
        if "error" in result:
            return f"Error: {result['error']}"
        if "content" in result:
            content = base64.b64decode(result["content"]).decode("utf-8")
            return content
        return f"Error reading file: {result}"
    
    def write_file(self, path: str, content: str, message: str = "Update via Friday") -> str:
        """Write/update a file in the repository."""
        # Get current file SHA if it exists
        endpoint = f"/repos/{self.repo}/contents/{path}"
        current = self._request("GET", endpoint)
        sha = current.get("sha") if "sha" in current else None
        
        data = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "branch": self.branch
        }
        if sha:
            data["sha"] = sha
        
        result = self._request("PUT", endpoint, data)
        if "error" in result:
            return f"Error: {result['error']}"
        if "content" in result:
            return f"File {path} updated successfully"
        return f"Error writing file: {result}"
    
    def create_branch(self, branch_name: str, from_branch: Optional[str] = None) -> str:
        """Create a new branch."""
        from_branch = from_branch or self.branch
        # Get the SHA of the from_branch
        ref_endpoint = f"/repos/{self.repo}/git/refs/heads/{from_branch}"
        ref_result = self._request("GET", ref_endpoint)
        if "object" not in ref_result:
            return f"Error getting ref: {ref_result}"
        sha = ref_result["object"]["sha"]
        
        # Create new branch
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }
        result = self._request("POST", f"/repos/{self.repo}/git/refs", data)
        if "error" in result:
            return f"Error: {result['error']}"
        return f"Branch {branch_name} created"
    
    def create_pull_request(self, title: str, body: str, head: str, base: Optional[str] = None) -> str:
        """Create a pull request."""
        base = base or self.branch
        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }
        result = self._request("POST", f"/repos/{self.repo}/pulls", data)
        if "error" in result:
            return f"Error: {result['error']}"
        if "html_url" in result:
            return f"PR created: {result['html_url']}"
        return f"Error creating PR: {result}"
    
    def get_pull_requests(self, state: str = "open") -> str:
        """List pull requests."""
        endpoint = f"/repos/{self.repo}/pulls?state={state}"
        result = self._request("GET", endpoint)
        if "error" in result:
            return f"Error: {result['error']}"
        if isinstance(result, list):
            prs = "\n".join(f"#{pr['number']}: {pr['title']} ({pr['state']})" for pr in result)
            return f"Pull Requests ({state}):\n{prs}" if prs else f"No {state} pull requests"
        return f"Error: {result}"
    
    def self_modify(self, file_path: str, new_content: str, commit_msg: str = "Self-modification by Friday") -> str:
        """Self-modify a file in the repository."""
        if not self.token:
            return "GitHub token not configured. Set GITHUB_TOKEN environment variable."
        
        # Read current file
        current = self.read_file(file_path)
        if current.startswith("Error"):
            return f"Cannot read file: {current}"
        
        # Write new content
        result = self.write_file(file_path, new_content, commit_msg)
        return f"Self-modification: {result}"


# Global instance
github = GitHubIntegration()


def github_list_files(path: str = "") -> str:
    """List files in the GitHub repository."""
    return github.list_files(path)


def github_read_file(path: str) -> str:
    """Read a file from the GitHub repository."""
    return github.read_file(path)


def github_write_file(path: str, content: str, message: str = "Update via Friday") -> str:
    """Write a file to the GitHub repository."""
    return github.write_file(path, content, message)


def github_create_branch(branch_name: str) -> str:
    """Create a new branch."""
    return github.create_branch(branch_name)


def github_create_pr(title: str, body: str, head: str) -> str:
    """Create a pull request."""
    return github.create_pull_request(title, body, head)


def github_self_modify(file_path: str, new_content: str, commit_msg: str = "Self-modification by Friday") -> str:
    """Self-modify a file in the repository."""
    return github.self_modify(file_path, new_content, commit_msg)
