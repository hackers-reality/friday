"""GitHub integration for Friday - Self-modification support."""

import os
import json
import base64
from typing import Optional, Dict, Any, List

_GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "Iv23liuQ5XPhsBjONt9B")
_GITHUB_TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".github_token.json")
_IS_GITHUB_APP = _GITHUB_CLIENT_ID.startswith(("Iv1.", "lv1.")) if _GITHUB_CLIENT_ID else False


def _is_github_app(client_id: str) -> bool:
    """Detect if a client ID belongs to a GitHub App (starts with Iv1. or lv1.)."""
    return client_id.startswith(("Iv1.", "lv1."))


def _load_saved_token() -> Optional[dict]:
    """Load saved token data from .github_token.json."""
    if os.path.exists(_GITHUB_TOKEN_FILE):
        try:
            with open(_GITHUB_TOKEN_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_token_data(data: dict):
    """Save full token data including access_token, refresh_token, expiry."""
    os.makedirs(os.path.dirname(_GITHUB_TOKEN_FILE), exist_ok=True)
    with open(_GITHUB_TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _refresh_github_app_token():
    """Refresh a GitHub App user token using its refresh_token."""
    saved = _load_saved_token()
    if not saved or not saved.get("refresh_token"):
        return None
    import requests, time
    try:
        resp = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": _GITHUB_CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": saved["refresh_token"],
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )
        result = resp.json()
    except Exception:
        return None
    if "access_token" in result:
        full = {
            "access_token": result["access_token"],
            "token_type": result.get("token_type", "bearer"),
            "expires_in": result.get("expires_in", 28800),
            "refresh_token": result.get("refresh_token", saved.get("refresh_token")),
            "refresh_token_expires_in": result.get("refresh_token_expires_in", 15811200),
            "scope": result.get("scope", ""),
            "created_at": time.time(),
        }
        _save_token_data(full)
        return full["access_token"]
    return None


def _get_active_token() -> str:
    """Get the active GitHub token from env PAT or saved OAuth/GitHub App token. Auto-refreshes if expiring."""
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token
    try:
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token
    except Exception:
        pass
    saved = _load_saved_token()
    if saved and saved.get("access_token"):
        if saved.get("refresh_token") and saved.get("expires_in"):
            import time
            created = saved.get("created_at", 0)
            expires_in = saved["expires_in"]
            if time.time() - created > expires_in - 60:
                refreshed = _refresh_github_app_token()
                if refreshed:
                    return refreshed
        return saved["access_token"]
    return ""


class GitHubIntegration:
    """Integrate with GitHub for code management and self-modification."""

    def __init__(self):
        self.token = _get_active_token()
        self.repo = os.getenv("GITHUB_REPO", "hackers-reality/friday")
        self.branch = os.getenv("GITHUB_BRANCH", "main")
        self.api_base = "https://api.github.com"
        self._update_headers()
    
    def _update_headers(self):
        """Set auth header — Bearer for GitHub App tokens, token for PATs."""
        if not self.token:
            self.headers = {"Accept": "application/vnd.github.v3+json"}
        elif _IS_GITHUB_APP or self.token.startswith("ghu_"):
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
        else:
            self.headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make a GitHub API request with auto-refresh for GitHub App tokens."""
        import requests
        url = f"{self.api_base}{endpoint}"
        try:
            if data:
                resp = requests.request(method, url, headers=self.headers, json=data, timeout=10)
            else:
                resp = requests.request(method, url, headers=self.headers, timeout=10)
            # If 401 and we have a GitHub App, try refreshing token
            if resp.status_code == 401 and _IS_GITHUB_APP:
                refreshed = _refresh_github_app_token()
                if refreshed:
                    self.token = refreshed
                    self._update_headers()
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
    
    def create_repo(self, name: str, description: str = "", private: bool = False) -> str:
        """Create a new repository."""
        if not self.token:
            return "GitHub token not configured."
        data = {"name": name, "description": description, "private": private, "auto_init": True}
        result = self._request("POST", "/user/repos", data)
        if "error" in result:
            return f"Error: {result['error']}"
        if "html_url" in result:
            return f"Repository created: {result['html_url']}"
        return str(result)

    def list_issues(self, state: str = "open", labels: str = "") -> str:
        """List issues in the repository."""
        endpoint = f"/repos/{self.repo}/issues?state={state}&sort=updated"
        if labels:
            endpoint += f"&labels={labels}"
        result = self._request("GET", endpoint)
        if "error" in result:
            return f"Error: {result['error']}"
        if not isinstance(result, list):
            return str(result)
        if not result:
            return "No issues found."
        lines = [f"#{i['number']}: {i['title']} ({i['state']})" for i in result]
        return "Issues:\n" + "\n".join(lines)

    def create_issue(self, title: str, body: str = "", labels: str = "") -> str:
        """Create an issue in the repository."""
        data = {"title": title, "body": body}
        if labels:
            data["labels"] = [l.strip() for l in labels.split(",")]
        result = self._request("POST", f"/repos/{self.repo}/issues", data)
        if "error" in result:
            return f"Error: {result['error']}"
        if "html_url" in result:
            return f"Issue created: {result['html_url']}"
        return str(result)

    def search_code(self, query: str, repo: str = "") -> str:
        """Search code across repositories."""
        q = query
        if repo:
            q += f" repo:{repo}"
        elif self.repo:
            q += f" repo:{self.repo}"
        result = self._request("GET", f"/search/code?q={q}&per_page=10")
        if "error" in result:
            return f"Error: {result['error']}"
        items = result.get("items", [])
        if not items:
            return "No results found."
        lines = [f"- {i['path']} ({i['repository']['full_name']})" for i in items[:10]]
        return f"Code search results ({result.get('total_count', 0)}):\n" + "\n".join(lines)

    def merge_pull_request(self, pr_number: int, commit_title: str = "") -> str:
        """Merge a pull request."""
        data = {}
        if commit_title:
            data["commit_title"] = commit_title
        result = self._request("PUT", f"/repos/{self.repo}/pulls/{pr_number}/merge", data)
        if "error" in result:
            return f"Error: {result['error']}"
        if "merged" in result and result["merged"]:
            return f"PR #{pr_number} merged successfully"
        return str(result)

    def get_repo_info(self) -> str:
        """Get repository information."""
        result = self._request("GET", f"/repos/{self.repo}")
        if "error" in result:
            return f"Error: {result['error']}"
        return (f"Repository: {result.get('full_name')}\n"
                f"Description: {result.get('description', 'N/A')}\n"
                f"Stars: {result.get('stargazers_count', 0)}\n"
                f"Forks: {result.get('forks_count', 0)}\n"
                f"Language: {result.get('language', 'N/A')}\n"
                f"Default branch: {result.get('default_branch')}\n"
                f"Private: {result.get('private')}")

    def list_branches(self) -> str:
        """List all branches in the repository."""
        result = self._request("GET", f"/repos/{self.repo}/branches")
        if "error" in result:
            return f"Error: {result['error']}"
        if not isinstance(result, list):
            return str(result)
        branches = "\n".join(f"- {b['name']}" for b in result)
        return f"Branches:\n{branches}"

    def get_commit_history(self, path: str = "", limit: int = 10) -> str:
        """Get commit history for the repository or a specific file."""
        endpoint = f"/repos/{self.repo}/commits?per_page={limit}"
        if path:
            endpoint += f"&path={path}"
        result = self._request("GET", endpoint)
        if "error" in result:
            return f"Error: {result['error']}"
        if not isinstance(result, list):
            return str(result)
        lines = []
        for c in result:
            author = c.get("commit", {}).get("author", {}).get("name", "Unknown")
            msg = c.get("commit", {}).get("message", "").split("\n")[0]
            sha = c.get("sha", "")[:7]
            lines.append(f"  {sha} - {msg} ({author})")
        return f"Recent commits:\n" + "\n".join(lines)

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


    def review_pull_request(self, pr_number: int) -> str:
        """Deep PR review: fetches diff, analyzes with Gemini, returns structured review."""
        if not self.token:
            return "GitHub token not configured. Set GITHUB_TOKEN environment variable."

        endpoint = f"/repos/{self.repo}/pulls/{pr_number}"
        result = self._request("GET", endpoint)
        if "error" in result:
            return f"Error: {result['error']}"

        # Get diff
        import requests
        diff_url = result.get("diff_url", "")
        try:
            diff_resp = requests.get(diff_url, headers=self.headers, timeout=15)
            diff = diff_resp.text[:30000]  # Limit to 30k chars
        except Exception as e:
            return f"Error fetching diff: {e}"

        pr_title = result.get("title", "N/A")
        pr_body = (result.get("body") or "")[:2000]

        # Analyze with Gemini
        try:
            from google import genai
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            prompt = f"""Review this GitHub PR and provide structured feedback:

## PR: {pr_title}
## Description: {pr_body}

## Diff:
{diff[:25000]}

Provide a review covering:
1. **Summary** — what does this PR do?
2. **Code Quality** — readability, maintainability issues
3. **Security** — any vulnerabilities or unsafe patterns
4. **Performance** — potential performance concerns
5. **Correctness** — logic bugs or edge cases
6. **Specific Suggestions** — line-level improvements with code snippets
7. **Verdict** — approve / changes requested / reject"""
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            review = response.text
            
            # Post review comment on GitHub
            comment_data = {"body": f"## 🤖 Friday AI Review\n\n{review}"}
            self._request("POST", f"/repos/{self.repo}/pulls/{pr_number}/comments", comment_data)
            
            return f"## 🔍 PR Review #{pr_number}: {pr_title}\n\n{review}"
        except Exception as e:
            return f"Error analyzing PR: {e}"


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


def github_list_prs(repo: str = "", state: str = "open") -> str:
    """List pull requests for a repository."""
    target = repo or github.repo
    original = github.repo
    github.repo = target
    try:
        result = github.get_pull_requests(state=state)
        return result
    finally:
        github.repo = original


def github_self_modify(file_path: str, new_content: str, commit_msg: str = "Self-modification by Friday") -> str:
    """Self-modify a file in the repository."""
    return github.self_modify(file_path, new_content, commit_msg)


def github_review_pr(pr_number: int) -> str:
    """Deep PR review: fetches diff, analyzes with Gemini, posts review comments on the PR."""
    return github.review_pull_request(pr_number)


def github_create_repo(name: str, description: str = "", private: bool = False) -> str:
    """Create a new GitHub repository."""
    return github.create_repo(name, description, private)


def github_list_issues(state: str = "open", labels: str = "") -> str:
    """List issues in the repository."""
    return github.list_issues(state, labels)


def github_create_issue(title: str, body: str = "", labels: str = "") -> str:
    """Create an issue in the repository."""
    return github.create_issue(title, body, labels)


def github_search_code(query: str, repo: str = "") -> str:
    """Search code across GitHub repositories."""
    return github.search_code(query, repo)


def github_merge_pr(pr_number: int, commit_title: str = "") -> str:
    """Merge a pull request."""
    return github.merge_pull_request(pr_number, commit_title)


def github_repo_info() -> str:
    """Get repository information."""
    return github.get_repo_info()


def github_list_branches() -> str:
    """List all branches in the repository."""
    return github.list_branches()


def github_commit_history(path: str = "", limit: int = 10) -> str:
    """Get commit history."""
    return github.get_commit_history(path, limit)


# ======== GitHub OAuth Device Flow (no browser redirect server needed) ========


def _get_oauth_creds() -> tuple:
    """Get GitHub client_id and client_secret.
    Checks env, .env, then falls back to hardcoded default.
    """
    cid = os.getenv("GITHUB_CLIENT_ID")
    cs = os.getenv("GITHUB_CLIENT_SECRET", "")
    if cid:
        return cid, cs
    try:
        from dotenv import load_dotenv
        load_dotenv()
        cid = os.getenv("GITHUB_CLIENT_ID")
        cs = os.getenv("GITHUB_CLIENT_SECRET", "")
        if cid:
            return cid, cs
    except Exception:
        pass
    # Fall back to hardcoded default
    if _GITHUB_CLIENT_ID:
        return _GITHUB_CLIENT_ID, cs
    return None, None


def github_authorize() -> str:
    """Start GitHub Device Flow OR guide PAT setup. Prints code to console prominently.
    PREFERRED: Just set GITHUB_TOKEN in .env -- no flow needed.
    """
    # First check if already have GITHUB_TOKEN
    existing = _get_active_token()
    if existing:
        return "[OK] GITHUB_TOKEN already set. No authorization needed."

    print("\n" + "=" * 60)
    print("  GITHUB AUTHORIZATION")
    print("=" * 60)
    print("  PREFERRED: Add GITHUB_TOKEN to your .env file")
    print("  (Settings > Developer settings > Personal access tokens > Fine-grained tokens)")
    print("=" * 60)

    cid, cs = _get_oauth_creds()
    if not cid:
        return _github_setup_wizard()

    import requests, time, json, webbrowser
    is_gh_app = _is_github_app(cid)

    print(f"\n  Using Device Flow as fallback (Client ID: {cid[:8]}...)")
    print("  Opening browser...\n")

    # Step 1: Request device code
    device_payload = {"client_id": cid}
    if not is_gh_app:
        device_payload["scope"] = "repo workflow admin:org"
    try:
        resp = requests.post(
            "https://github.com/login/device/code",
            data=device_payload,
            headers={"Accept": "application/json"},
            timeout=15,
        )
        data = resp.json()
    except Exception as e:
        return f"[FAIL] Device code request failed: {e}"

    if "device_code" not in data:
        return f"[FAIL] Device code request failed: {data.get('error_description', data)}"

    device_code = data["device_code"]
    user_code = data["user_code"]
    verification_uri = data.get("verification_uri", "https://github.com/login/device")
    interval = data.get("interval", 5)

    app_type = "GitHub App" if is_gh_app else "OAuth App"

    # Print code PROMINENTLY to console
    print("\n" + "!" * 60)
    print(f"  >>> YOUR CODE:  {user_code}  <<<")
    print(f"  >>> Enter this at: {verification_uri}")
    print("!" * 60 + "\n")

    msg = (
        f"[OK] GitHub Device Flow started ({app_type}).\n\n"
        f"  >>> YOUR CODE: {user_code} <<<\n"
        f"  >>> Enter at: {verification_uri}\n\n"
        f"Waiting for authorization... (timeout: 5 minutes)"
    )

    try:
        webbrowser.open(verification_uri)
    except Exception:
        pass

    # Step 2: Poll for access token
    start = time.time()
    timeout = 300
    while time.time() - start < timeout:
        time.sleep(interval)
        try:
            poll = requests.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": cid,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
                timeout=15,
            )
            result = poll.json()
        except Exception as e:
            return f"[FAIL] Polling error: {e}"

        if "access_token" in result:
            token = result["access_token"]
            saved = {
                "access_token": token,
                "token_type": result.get("token_type", "bearer"),
                "scope": result.get("scope", ""),
                "created_at": time.time(),
            }
            if is_gh_app and "expires_in" in result and result["expires_in"]:
                saved["expires_in"] = result["expires_in"]
                saved["refresh_token"] = result.get("refresh_token", "")
                saved["refresh_token_expires_in"] = result.get("refresh_token_expires_in", 15811200)
            _save_token_data(saved)

            global github
            github.token = token
            github._update_headers()
            extra = ""
            if is_gh_app:
                extra = " (token expiry disabled — permanent token)"
            return f"[OK] GitHub authorized! Token saved.{extra}"

        error = result.get("error", "")
        if error == "authorization_pending":
            continue
        elif error == "slow_down":
            interval += 5
            continue
        elif error == "expired_token":
            return "[FAIL] Device code expired. Run github_authorize() again."
        elif error == "access_denied":
            return "[FAIL] Authorization denied by user."
        elif error:
            return f"[FAIL] Polling error: {error}"

    return f"[FAIL] Timeout waiting for authorization (5 minutes). Run github_authorize() to try again."


def _github_setup_wizard() -> str:
    """Guides the user through GitHub authorization with PAT as primary method."""
    return (
        "[SETUP] GitHub Authentication\n\n"
        "Two ways to set up:\n\n"
        "METHOD 1 (PREFERRED) — Personal Access Token:\n"
        "  1. Go to https://github.com/settings/tokens?type=beta\n"
        "  2. Click 'Generate new token' → 'Fine-grained token'\n"
        "  3. Set repo scope (all), read:user, workflow\n"
        "  4. Copy the token and add to your .env file:\n"
        "     GITHUB_TOKEN=github_pat_...\n"
        "  5. Restart Friday — done.\n\n"
        "METHOD 2 — Device Flow (auto):\n"
        "  The GitHub App 'friday-from-ironman' is pre-configured.\n"
        "  Run github_authorize() — it will open a browser and show you a code.\n\n"
        "Permissions needed: read/write repos, PRs, issues, actions, workflows."
    )


def github_exchange_code(device_code: str = "") -> str:
    """Poll for token using device_code, or check token status. For GitHub Apps, also shows expiry."""
    if not device_code:
        saved = _load_saved_token()
        if saved and saved.get("access_token"):
            if saved.get("refresh_token"):
                import time
                created = saved.get("created_at", 0)
                expires_in = saved.get("expires_in", 28800)
                remaining = max(0, int(expires_in - (time.time() - created)))
                return f"[OK] GitHub App token active. Expires in {remaining}s. Refresh available."
            return f"[OK] Token exists."
        return "[INFO] No saved token. Run github_authorize() to start."

    cid, cs = _get_oauth_creds()
    if not cid:
        return "[FAIL] GitHub not configured. Run github_authorize() to set up."

    import requests, time
    is_gh_app = _is_github_app(cid)
    start = time.time()
    timeout = 300
    interval = 5
    while time.time() - start < timeout:
        time.sleep(interval)
        try:
            poll = requests.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": cid,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
                timeout=15,
            )
            result = poll.json()
        except Exception as e:
            return f"[FAIL] Polling error: {e}"

        if "access_token" in result:
            token = result["access_token"]
            saved = {
                "access_token": token,
                "token_type": result.get("token_type", "bearer"),
                "scope": result.get("scope", ""),
                "created_at": time.time(),
            }
            if is_gh_app and "expires_in" in result and result["expires_in"]:
                saved["expires_in"] = result["expires_in"]
                saved["refresh_token"] = result.get("refresh_token", "")
                saved["refresh_token_expires_in"] = result.get("refresh_token_expires_in", 15811200)
            _save_token_data(saved)

            global github
            github.token = token
            github._update_headers()
            return f"[OK] GitHub authorized! Token saved."

        error = result.get("error", "")
        if error == "authorization_pending":
            continue
        elif error == "slow_down":
            interval += 5
            continue
        elif error == "expired_token":
            return "[FAIL] Device code expired."
        elif error == "access_denied":
            return "[FAIL] Authorization denied."
        elif error:
            return f"[FAIL] Polling error: {error}"

    return "[FAIL] Timeout."


def github_setup(token: str = "") -> str:
    """Set up GitHub authentication with a Personal Access Token (PAT).
    PREFERRED METHOD: Generate a token at GitHub Settings → Developer settings → Personal access tokens.
    Then run: github_setup(token='github_pat_...')
    Or add GITHUB_TOKEN=... to your .env file.
    """
    if token:
        # Validate by making a test API call
        import requests
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        try:
            resp = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            if resp.status_code == 200:
                user = resp.json().get("login", "unknown")
                # Save to .env
                env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
                try:
                    with open(env_path, "a") as f:
                        f.write(f"\n# Added by Friday github_setup\nGITHUB_TOKEN={token}\n")
                except Exception:
                    pass
                global github
                github.token = token
                github._update_headers()
                return f"[OK] GitHub authenticated as {user}. Token saved to .env."
            else:
                return f"[FAIL] Token invalid: {resp.status_code} {resp.text[:200]}"
        except Exception as e:
            return f"[FAIL] Error validating token: {e}"

    # No token provided — show instructions
    existing = _get_active_token()
    if existing:
        return "[OK] GITHUB_TOKEN is already set and working."
    return _github_setup_wizard()


def github_refresh_token() -> str:
    """Manually refresh the GitHub App token. Only works for GitHub Apps (client ID starts with Iv1.)."""
    if not _IS_GITHUB_APP:
        return "[FAIL] Not a GitHub App. Only GitHub Apps support token refresh."
    refreshed = _refresh_github_app_token()
    if refreshed:
        global github
        github.token = refreshed
        github._update_headers()
        saved = _load_saved_token()
        remaining = "unknown"
        if saved:
            import time
            remaining = str(max(0, int((saved.get("created_at", 0) + saved.get("expires_in", 28800)) - time.time())))
        return f"[OK] Token refreshed. Next expiry in {remaining}s."
    return "[FAIL] Token refresh failed. Re-authorize with github_authorize()."
