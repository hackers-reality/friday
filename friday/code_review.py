"""F.R.I.D.A.Y. Deep Code Review - analyze, fix, fork, and ship projects.
Walks source trees, reviews every file with Gemini, reports progress to console,
and can auto-create PRs, forks, or entire repos.

Rate limit: set FRIDAY_REVIEW_DELAY (seconds between files, default 5 for free tier).
Model: set FRIDAY_REVIEW_MODEL (default gemini-3.1-flash-lite)."""

from __future__ import annotations

import os
import re
import json
import subprocess
import tempfile
import textwrap
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types as genai_types

from friday._paths import FRIDAY_MEMORY, PROJECT_ROOT

# ── Gemini client (lazy init) ──
_client = None


def _get_client():
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        _client = genai.Client(api_key=key)
    return _client


# ── Supported source file extensions ──
# ── Model ──
REVIEW_MODEL = os.getenv("FRIDAY_REVIEW_MODEL", "gemini-3.1-flash-lite")

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".kt", ".scala",
    ".swift", ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".r", ".m",
    ".mm", ".vue", ".svelte", ".astro", ".pl", ".pm", ".sh", ".bash", ".zsh",
    ".ps1", ".bat", ".cmd", ".sql", ".graphql", ".proto", ".yaml", ".yml",
    ".json", ".xml", ".html", ".css", ".scss", ".less", ".md", ".rst",
    ".toml", ".ini", ".cfg", ".conf", ".env.example", ".dockerfile",
    "Dockerfile", "Makefile", "CMakeLists.txt", "Cargo.toml", "go.mod",
}

# ── Files/dirs to skip ──
SKIP_DIRS = {
    "__pycache__", ".git", ".svn", ".hg", "node_modules", ".venv", "venv",
    ".tox", ".eggs", "eggs", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".hypothesis", "dist", "build", ".next", "out", ".nuxt",
    ".github", "target", "bin", "obj", ".terraform", "vendor",
    ".vscode", ".idea", "*.egg-info", ".coverage", "htmlcov",
}

SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    ".DS_Store", "Thumbs.db", "*.pyc", "*.pyo", "*.min.js", "*.min.css",
    "*.map", "*.svg", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico",
    "*.woff", "*.woff2", "*.ttf", "*.eot", "*.pdf", "*.zip", "*.tar.gz",
    "*.exe", "*.dll", "*.so", "*.dylib", "*.o", "*.a", "*.class",
    ".env", ".github_token.json",
}


def _is_source_file(path: str) -> bool:
    name = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()
    basename_lower = name.lower()
    if name in (".env.example",) or ext in SOURCE_EXTENSIONS:
        return True
    if basename_lower in ("dockerfile", "makefile", "cmakelists.txt",
                          "cargo.toml", "go.mod"):
        return True
    return False


def _should_skip(path: str, is_dir: bool) -> bool:
    name = os.path.basename(path)
    if is_dir:
        return name in SKIP_DIRS or name.startswith(".")
    ext = os.path.splitext(path)[1].lower()
    if ext in {".pyc", ".pyo", ".min.js", ".min.css", ".map",
               ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico",
               ".woff", ".woff2", ".ttf", ".eot", ".pdf",
               ".zip", ".tar.gz", ".exe", ".dll", ".so",
               ".dylib", ".o", ".a", ".class"}:
        return True
    if name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                "poetry.lock", ".DS_Store", "Thumbs.db",
                ".env", ".github_token.json"}:
        return True
    return False


def _walk_source(root: str) -> list[str]:
    files = []
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not _should_skip(
                os.path.join(dirpath, d), True)]
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                if not _should_skip(fpath, False) and _is_source_file(fpath):
                    files.append(fpath)
    except Exception as e:
        print(f"  [WARN] Error walking {root}: {e}")
    return sorted(files)


def _count_lines(content: str) -> int:
    return len(content.splitlines())


def _syntax_check_py(content: str) -> list[str]:
    errors = []
    try:
        compile(content, "<review>", "exec")
    except SyntaxError as e:
        errors.append(f"  SyntaxError at line {e.lineno}: {e.msg}")
    return errors


def _review_file(path: str, content: str, client: genai.Client) -> dict:
    """Analyze a single file with Gemini. Returns {issues, warnings, suggestions, score}."""
    rel_path = os.path.relpath(path, PROJECT_ROOT) if path.startswith(str(PROJECT_ROOT)) else path
    basename = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()
    lines = _count_lines(content)
    print(f"  Analyzing {rel_path} ({lines} lines)...")

    # Quick Python syntax check
    syntax_issues = []
    if ext == ".py":
        syntax_issues = _syntax_check_py(content)

    # Truncate very large files for analysis
    max_chars = 15000
    if len(content) > max_chars:
        content_sample = content[:max_chars] + f"\n\n... [TRUNCATED, {len(content) - max_chars} more chars]"
    else:
        content_sample = content

    prompt = f"""You are F.R.I.D.A.Y.'s code review engine. Review this source file for bugs, security issues, performance problems, and code quality concerns.

File: {rel_path}
Language: {ext or basename}
Lines: {lines}

Rules:
- Be specific: report exact line numbers, exact code snippets
- Be concise: one sentence per finding
- Categorize each finding as: BUG, SECURITY, PERFORMANCE, or STYLE
- If the code looks clean, return a brief positive summary
- Do NOT suggest docstrings or comments unless they'd fix a real bug
- Do NOT suggest type hints unless the project already uses them

Return a JSON object with this structure:
{{
  "issues": [{{"line": <int or null>, "category": "BUG|SECURITY|PERFORMANCE|STYLE", "message": "<one sentence>"}}],
  "summary": "<one sentence evaluation>",
  "score": <0-100, how healthy this file is>
}}

CODE TO REVIEW:
```{ext[1:] if ext else basename}
{content_sample}
```"""

    try:
        import time
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=REVIEW_MODEL,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=4096,
                    ),
                )
                raw = response.text.strip()
                break
            except Exception as e:
                err_str = str(e)
                # Parse retry delay from 429 errors
                retry_after = None
                import re as _re
                m = _re.search(r"retry in (\d+(?:\.\d+)?)\s*s", err_str, _re.IGNORECASE)
                if m:
                    retry_after = float(m.group(1)) + 1
                if attempt < max_retries - 1:
                    sleep_time = retry_after or (2 ** attempt)
                    print(f"  [RETRY] {err_str[:80]}... waiting {sleep_time:.0f}s")
                    time.sleep(sleep_time)
                    continue
                raise
        # Extract JSON from response (handle markdown fences, leading/trailing text)
        raw_clean = raw.strip()
        # Strip markdown code fences
        raw_clean = re.sub(r"^```(?:json)?\s*\n?|\n?```\s*$", "", raw_clean, flags=re.MULTILINE)
        # Find first `{` and last `}`
        start = raw_clean.find("{")
        end = raw_clean.rfind("}")
        if start != -1 and end > start:
            raw_clean = raw_clean[start:end+1]
        try:
            result = json.loads(raw_clean)
        except json.JSONDecodeError:
            # Try finding any valid JSON object in the text
            json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', raw_clean, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    result = {"issues": [], "summary": raw_clean[:200], "score": 50}
            else:
                result = {"issues": [], "summary": raw_clean[:200], "score": 50}
        if not isinstance(result, dict):
            result = {"issues": [], "summary": str(result)[:200], "score": 50}

        # Merge syntax errors into issues
        for se in syntax_issues:
            result.setdefault("issues", []).append({
                "line": None, "category": "BUG", "message": se.strip()
            })

        if not result.get("issues"):
            result["issues"] = []
        if not result.get("summary"):
            result["summary"] = "No significant issues found."
        result["score"] = max(0, min(100, result.get("score", 50)))
        result["file"] = rel_path
        result["lines"] = lines
        return result

    except Exception as e:
        print(f"  [WARN] Gemini analysis failed for {rel_path}: {e}")
        return {
            "file": rel_path,
            "lines": lines,
            "issues": [],
            "summary": f"Analysis skipped: {e}",
            "score": 50,
        }


def _format_report(all_results: list[dict]) -> str:
    if not all_results:
        return "[INFO] No files to review."

    total_issues = 0
    total_bugs = 0
    total_security = 0
    total_perf = 0
    total_style = 0
    total_files = len(all_results)
    total_lines = sum(r.get("lines", 0) for r in all_results)
    scores = [r.get("score", 50) for r in all_results if r.get("score") is not None]

    for r in all_results:
        for iss in r.get("issues", []):
            total_issues += 1
            cat = iss.get("category", "").upper()
            if "BUG" in cat:
                total_bugs += 1
            elif "SEC" in cat:
                total_security += 1
            elif "PERF" in cat:
                total_perf += 1
            else:
                total_style += 1

    avg_score = sum(scores) / len(scores) if scores else 50

    lines = [
        "=" * 60,
        "DEEP CODE REVIEW REPORT",
        "=" * 60,
        f"Date:     {datetime.now().isoformat()}",
        f"Files:    {total_files}",
        f"Lines:    {total_lines}",
        f"Avg Score: {avg_score:.0f}/100",
        f"Issues:   {total_issues} (Bugs: {total_bugs}, Security: {total_security}, Perf: {total_perf}, Style: {total_style})",
        "-" * 60,
    ]

    # List files with scores
    for r in all_results:
        f = r.get("file", "?")
        s = r.get("score", 50)
        ic = len(r.get("issues", []))
        icon = "PASS" if s >= 80 else ("WARN" if s >= 50 else "FAIL")
        lines.append(f"  [{icon:4s}] {f} ({ic} issues, score {s})")

    # Detail: bugs and security
    bug_lines = []
    for r in all_results:
        for iss in r.get("issues", []):
            cat = iss.get("category", "").upper()
            if "BUG" in cat or "SEC" in cat:
                fn = r.get("file", "?")
                ln = iss.get("line", "?")
                bug_lines.append(f"  [{cat[:4]}] {fn}:{ln} -- {iss['message']}")

    if bug_lines:
        lines.extend(["-" * 60, "CRITICAL ISSUES:", "-" * 60])
        lines.extend(bug_lines)

    lines.append("=" * 60)
    return "\n".join(lines)


def _resolve_target(target: str) -> str:
    """Resolve target to a local path or GitHub clone dir."""
    target = target.strip()

    if not target or target == "self":
        return str(PROJECT_ROOT)

    if target == "tools" or target == "current":
        return str(PROJECT_ROOT)

    if os.path.exists(target):
        return os.path.abspath(target)

    if target.startswith("github.com/"):
        target = target[len("github.com/"):]
    if target.startswith("http://") or target.startswith("https://"):
        # Extract owner/repo from URL
        m = re.search(r"github\.com[/:]([\w.-]+/[\w.-]+?)(?:\.git)?(?:\?.*)?$", target)
        if m:
            target = m.group(1)
        else:
            return f"[FAIL] Could not parse GitHub URL: {target}"

    # If it looks like owner/repo, clone it
    if "/" in target and not os.path.exists(target):
        print(f"  Cloning {target}...")
        clone_dir = os.path.join(FRIDAY_MEMORY, "repos", target.replace("/", "_"))
        if os.path.exists(clone_dir):
            print(f"  Using cached clone at {clone_dir}")
            return clone_dir
        parent = os.path.dirname(clone_dir)
        os.makedirs(parent, exist_ok=True)
        url = f"https://github.com/{target}.git"
        r = subprocess.run(
            ["git", "clone", "--depth=1", url, clone_dir],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            return f"[FAIL] Git clone error: {r.stderr[:300]}"
        print(f"  Cloned to {clone_dir}")
        return clone_dir

    return f"[FAIL] Target not found: {target}"


def _create_branch_and_pr(repo: str, branch: str, files: dict[str, str],
                          title: str, body: str) -> str:
    """Create branch, commit files, push, and open PR. Uses GitHub API."""
    import base64
    import requests
    from friday.github import GitHubIntegration
    gh = GitHubIntegration()
    api_base = gh.api_base
    headers = gh.headers

    # Get default branch SHA
    r = requests.get(f"{api_base}/repos/{repo}/git/refs/heads/{gh.branch}",
                     headers=headers, timeout=15)
    if r.status_code != 200:
        return f"[FAIL] Could not get default branch: {r.status_code} {r.text[:200]}"
    sha = r.json()["object"]["sha"]

    # Create branch
    r2 = requests.post(f"{api_base}/repos/{repo}/git/refs",
                       json={"ref": f"refs/heads/{branch}",
                             "sha": sha},
                       headers=headers, timeout=15)
    if r2.status_code not in (201, 422):
        return f"[FAIL] Could not create branch: {r2.status_code} {r2.text[:200]}"

    # Create/update files
    for file_path, content in files.items():
        # Check if file exists
        r3 = requests.get(
            f"{api_base}/repos/{repo}/contents/{file_path}",
            headers={**headers, "Accept": "application/vnd.github.v3+json"},
            params={"ref": branch},
            timeout=15,
        )
        if r3.status_code == 200:
            sha_file = r3.json()["sha"]
            r4 = requests.put(
                f"{api_base}/repos/{repo}/contents/{file_path}",
                json={"message": f"fix: {title}",
                      "content": base64.b64encode(
                          content.encode()).decode(),
                      "sha": sha_file,
                      "branch": branch},
                headers=headers, timeout=15,
            )
        else:
            r4 = requests.put(
                f"{api_base}/repos/{repo}/contents/{file_path}",
                json={"message": f"feat: {title}",
                      "content": base64.b64encode(
                          content.encode()).decode(),
                      "branch": branch},
                headers=headers, timeout=15,
            )
        if r4.status_code not in (200, 201):
            return f"[FAIL] Could not write {file_path}: {r4.status_code} {r4.text[:200]}"

    # Create PR
    r5 = requests.post(f"{api_base}/repos/{repo}/pulls",
                       json={"title": title, "body": body,
                             "head": branch, "base": gh.branch},
                       headers=headers, timeout=15)
    if r5.status_code == 201:
        pr_url = r5.json().get("html_url", "")
        return f"[OK] PR created: {pr_url}"
    return f"[FAIL] PR creation failed: {r5.status_code} {r5.text[:200]}"


# ── Main tool ──

def deep_code_review(
    action: str = "analyze",
    target: str = "",
    file_pattern: str = "*.*",
    auto_fix: bool = False,
    pr_title: str = "",
    pr_body: str = "",
    repo_description: str = "",
    branch_name: str = "",
    repo_name: str = "",
    github_repo: str = "",
) -> str:
    """Deep code review powered by Gemini. Walks source files, analyzes each with AI, and reports findings.
    Actions:
      analyze - review source code, return structured report
      fix - review + auto-create a GitHub PR with fixes
      new_project - create a new GitHub repo and push source code
      fork_pr - fork a repo (if no write access), create branch, commit, and PR
    Target can be: 'self' (FRIDAY's own code), a local path, or a GitHub 'owner/repo'.
    Set auto_fix=True to have the AI generate and apply fixes to each issue found."""
    try:
        if action == "new_project":
            return _action_new_project(target, repo_name, repo_description)
        if action == "fork_pr":
            return _action_fork_pr(target, pr_title, pr_body, branch_name)

        # Resolve target to local path
        resolved = _resolve_target(target)
        if resolved.startswith("[FAIL]") or resolved.startswith("Could not"):
            return resolved

        if os.path.isfile(resolved):
            files = [resolved]
        elif os.path.isdir(resolved):
            files = _walk_source(resolved)
        else:
            return f"[FAIL] Not found: {resolved}"

        print(f"\n{'='*60}")
        print(f"DEEP CODE REVIEW - Target: {resolved}")
        print(f"{'='*60}")

        if not files:
            return f"[INFO] No source files found in {resolved}"

        print(f"  Found {len(files)} source files to review.")
        print(f"{'-'*60}")

        # Review each file (paced to avoid rate limits)
        import time as _time
        # Free tier: 15 req/min for flash-lite. At 5s = 12/min, safe margin.
        review_delay = float(os.getenv("FRIDAY_REVIEW_DELAY", "5"))
        client = _get_client()
        all_results = []
        for idx, fpath in enumerate(files):
            if idx > 0:
                _time.sleep(review_delay)
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception as e:
                print(f"  [WARN] Could not read {fpath}: {e}")
                continue

            result = _review_file(fpath, content, client)
            all_results.append(result)

            # Print issues found so far
            issues = result.get("issues", [])
            if issues:
                for iss in issues:
                    cat = iss.get("category", "?")
                    msg = iss.get("message", "?")
                    ln = iss.get("line", "?")
                    print(f"    ! [{cat}] {result.get('file', '?')}:{ln} -- {msg}")

            # Positive feedback for clean files
            if not issues:
                score = result.get("score", 50)
                if score >= 80:
                    print(f"    OK Looks clean (score {score})")
                else:
                    print(f"    ~ Score {score}")

        # Generate final report
        report = _format_report(all_results)
        print(f"\n{report}")

        # Auto-fix mode: create PR with fixes
        if auto_fix or action == "fix":
            if not github_repo:
                repo_matches = re.findall(
                    r"github\.com[/:]([\w.-]+/[\w.-]+?)(?:\.git|/|$)",
                    target + " "
                )
                if repo_matches:
                    github_repo = repo_matches[0]
                else:
                    github_repo = os.getenv("GITHUB_REPO", "hackers-reality/friday")

            bug_issues = []
            for r in all_results:
                for iss in r.get("issues", []):
                    if "BUG" in iss.get("category", "").upper():
                        bug_issues.append((r["file"], iss))

            if not bug_issues:
                return report + "\n\n[INFO] No bugs found to fix. Report above."

            # Generate fixes for each bug
            pr_title = pr_title or f"Auto-fix: {len(bug_issues)} issues found by FRIDAY code review"
            pr_body = pr_body or f"## Automated Fix\n\nFRIDAY's deep code review found {len(bug_issues)} issues:\n\n"
            for fn, iss in bug_issues:
                pr_body += f"- **{fn}:{iss.get('line', '?')}** -- {iss['message']}\n"
            pr_body += "\n---\n_Generated by FRIDAY Deep Code Review_"

            branch = branch_name or f"friday-fix/{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # For each buggy file, ask Gemini to generate a fix
            files_to_update = {}
            for fpath_abs, issues_list in _group_by_file(all_results):
                rel = os.path.relpath(fpath_abs, resolved).replace("\\", "/")
                try:
                    with open(fpath_abs, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue

                issue_descriptions = "\n".join(
                    f"- Line {i.get('line', '?')}: {i['message']}"
                    for i in issues_list
                    if "BUG" in i.get("category", "").upper()
                )
                if not issue_descriptions:
                    continue

                fix_prompt = f"""Fix the following issues in this file. Return ONLY the corrected file content, nothing else.

File: {rel}
Issues to fix:
{issue_descriptions}

Current content:
```{os.path.splitext(rel)[1] or ''}
{content[:20000]}
```"""

                try:
                    fix_resp = client.models.generate_content(
                        model=REVIEW_MODEL,
                        contents=fix_prompt,
                        config=genai_types.GenerateContentConfig(
                            temperature=0.1,
                            max_output_tokens=32768,
                        ),
                    )
                    fixed = fix_resp.text.strip()
                    # Strip code fences if present
                    fixed = re.sub(
                        r"^```\w*\n|```$", "", fixed, flags=re.MULTILINE
                    ).strip()
                    if fixed and fixed != content:
                        files_to_update[rel] = fixed
                        print(f"  ✓ Generated fix for {rel}")
                except Exception as e:
                    print(f"  [WARN] Fix generation failed for {rel}: {e}")

            if not files_to_update:
                return report + "\n\n[INFO] Could not generate fixes automatically."

            result = _create_branch_and_pr(
                github_repo, branch, files_to_update,
                pr_title, pr_body,
            )
            return report + f"\n\n{result}"

        return report

    except Exception as e:
        tb = traceback.format_exc()
        return f"[FAIL] Deep code review error: {e}\n{tb[:500]}"


def _group_by_file(results: list[dict]) -> list[tuple[str, list[dict]]]:
    by_file = {}
    for r in results:
        f = r.get("file", "?")
        abs_f = os.path.join(PROJECT_ROOT, f) if not os.path.isabs(f) else f
        if abs_f not in by_file:
            by_file[abs_f] = []
        by_file[abs_f].extend(r.get("issues", []))
    return list(by_file.items())


def _action_new_project(target: str, repo_name: str, description: str) -> str:
    """Create a new GitHub repo from local source."""
    import requests

    if not target:
        return "[FAIL] target (local directory) required for new_project"
    if not repo_name:
        return "[FAIL] repo_name required for new_project"

    from friday.github import GitHubIntegration
    gh = GitHubIntegration()
    headers = gh._headers

    # Create repo
    r = requests.post(
        f"{gh.api_base}/user/repos",
        json={"name": repo_name, "description": description or "",
              "private": False, "auto_init": False},
        headers=headers, timeout=15,
    )
    if r.status_code not in (201, 422):
        return f"[FAIL] Repo creation failed: {r.status_code} {r.text[:300]}"

    if r.status_code == 422:
        repo_full = repo_name
    else:
        repo_full = r.json().get("full_name", repo_name)

    print(f"  ✓ Repo {repo_full} ready")

    # Push local directory
    print(f"  Pushing {target} to {repo_full}...")
    token = gh.token
    remote_url = f"https://x-access-token:{token}@github.com/{repo_full}.git"

    try:
        subprocess.run(["git", "init"], cwd=target, capture_output=True, text=True, timeout=10)
        subprocess.run(["git", "add", "-A"], cwd=target, capture_output=True, text=True, timeout=30)
        subprocess.run(
            ["git", "commit", "-m", f"Initial commit: {description or repo_name}"],
            cwd=target, capture_output=True, text=True, timeout=15,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", remote_url],
            cwd=target, capture_output=True, text=True, timeout=10,
        )
        r2 = subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=target, capture_output=True, text=True, timeout=60,
        )
        if r2.returncode != 0:
            return f"[FAIL] Push failed: {r2.stderr[:300]}"
    except Exception as e:
        return f"[FAIL] Push error: {e}"

    return f"[OK] Project pushed to https://github.com/{repo_full}"


def _action_fork_pr(target: str, pr_title: str, pr_body: str, branch_name: str = "") -> str:
    """Fork a repo, create branch, push changes, open PR."""
    import requests
    from friday.github import GitHubIntegration

    if not target:
        return "[FAIL] target (owner/repo) required for fork_pr"

    gh = GitHubIntegration()
    headers = gh.headers

    # Get user info
    r_user = requests.get(f"{gh.api_base}/user", headers=headers, timeout=15)
    if r_user.status_code != 200:
        return "[FAIL] Could not get user info"
    username = r_user.json().get("login", "")

    print(f"  Forking {target} to {username}...")
    r_fork = requests.post(
        f"{gh.api_base}/repos/{target}/forks",
        headers=headers, timeout=30,
    )
    if r_fork.status_code not in (200, 201, 202):
        return f"[FAIL] Fork failed: {r_fork.status_code} {r_fork.text[:300]}"

    forked_repo = f"{username}/{target.split('/')[1]}"
    print(f"  ✓ Forked to {forked_repo}")

    # Clone fork
    clone_dir = os.path.join(FRIDAY_MEMORY, "forks", forked_repo.replace("/", "_"))
    if os.path.exists(clone_dir):
        import shutil
        shutil.rmtree(clone_dir)

    url = f"https://x-access-token:{gh.token}@github.com/{forked_repo}.git"
    r_clone = subprocess.run(
        ["git", "clone", url, clone_dir],
        capture_output=True, text=True, timeout=60,
    )
    if r_clone.returncode != 0:
        return f"[FAIL] Clone failed: {r_clone.stderr[:300]}"

    branch = branch_name or f"friday-patch-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    subprocess.run(["git", "checkout", "-b", branch], cwd=clone_dir,
                   capture_output=True, text=True, timeout=10)

    # Analyze the cloned code
    print(f"  Analyzing forked repo at {clone_dir}...")
    files = _walk_source(clone_dir)
    if not files:
        subprocess.run(["git", "checkout", "main"], cwd=clone_dir,
                       capture_output=True, text=True, timeout=10)
        return "[INFO] No source files to analyze. Fork created, no changes made."

    client = _get_client()
    all_results = []
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            continue
        result = _review_file(fpath, content, client)
        all_results.append(result)

        for iss in result.get("issues", []):
            cat = iss.get("category", "").upper()
            if "BUG" in cat:
                print(f"    ! [{cat}] {result['file']}:{iss.get('line', '?')} -- {iss['message']}")

    # Generate fixes
    bug_issues_by_file = {}
    for r in all_results:
        for iss in r.get("issues", []):
            if "BUG" in iss.get("category", "").upper():
                abs_f = os.path.join(clone_dir, r["file"])
                bug_issues_by_file.setdefault(abs_f, []).append(iss)

    if not bug_issues_by_file:
        subprocess.run(["git", "checkout", "main"], cwd=clone_dir,
                       capture_output=True, text=True, timeout=10)
        return "[INFO] No bugs found in forked repo. Fork created but no PR opened."

    files_changed = 0
    for fpath_abs, issues_list in bug_issues_by_file.items():
        try:
            with open(fpath_abs, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        rel = os.path.relpath(fpath_abs, clone_dir).replace("\\", "/")
        issue_desc = "\n".join(
            f"- Line {i.get('line', '?')}: {i['message']}" for i in issues_list
        )

        fix_prompt = f"""Fix these issues. Return only corrected content.

File: {rel}
Issues:
{issue_desc}

```{os.path.splitext(rel)[1] or ''}
{content[:20000]}
```"""

        try:
            fix_resp = client.models.generate_content(
                model=REVIEW_MODEL,
                contents=fix_prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.1, max_output_tokens=32768,
                ),
            )
            fixed = fix_resp.text.strip()
            fixed = re.sub(r"^```\w*\n|```$", "", fixed, flags=re.MULTILINE).strip()
            if fixed and fixed != content:
                with open(fpath_abs, "w", encoding="utf-8") as f:
                    f.write(fixed)
                files_changed += 1
                print(f"  ✓ Fixed {rel}")
        except Exception as e:
            print(f"  [WARN] Fix failed for {rel}: {e}")

    if not files_changed:
        return "[INFO] No fixes generated. Fork created, no PR opened."

    title = pr_title or f"FRIDAY code review: {files_changed} file(s) fixed"
    body = pr_body or f"## Automated fixes by FRIDAY\n\nFixes applied to {files_changed} files based on deep code review.\n\n---\n_Generated by FRIDAY Deep Code Review_"

    subprocess.run(["git", "add", "-A"], cwd=clone_dir,
                   capture_output=True, text=True, timeout=30)
    subprocess.run(
        ["git", "commit", "-m", f"fix: {title[:72]}"],
        cwd=clone_dir, capture_output=True, text=True, timeout=15,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", branch],
        cwd=clone_dir, capture_output=True, text=True, timeout=60,
    )

    # Create PR to original repo
    r_pr = requests.post(
        f"{gh.api_base}/repos/{target}/pulls",
        json={"title": title, "body": body,
              "head": f"{username}:{branch}", "base": "main"},
        headers=headers, timeout=15,
    )
    if r_pr.status_code == 201:
        pr_url = r_pr.json().get("html_url", "")
        return f"[OK] PR created in {target}: {pr_url}"
    return f"[FAIL] PR creation: {r_pr.status_code} {r_pr.text[:300]}"


def code_review_report(target: str) -> str:
    """Quick summary of source files in a target. Returns file count, sizes, types."""
    resolved = _resolve_target(target)
    if resolved.startswith("[FAIL]"):
        return resolved

    if os.path.isfile(resolved):
        files = [resolved]
    elif os.path.isdir(resolved):
        files = _walk_source(resolved)
    else:
        return f"[FAIL] Not found: {resolved}"

    if not files:
        return "[INFO] No source files found."

    total_lines = 0
    by_ext = {}
    for f in files:
        _, ext = os.path.splitext(f)
        ext = ext.lower() or os.path.basename(f).lower()
        by_ext[ext] = by_ext.get(ext, 0) + 1
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                total_lines += sum(1 for _ in fh)
        except Exception:
            pass

    lines = [
        f"Code Review Report for: {resolved}",
        f"  Files:  {len(files)}",
        f"  Lines:  {total_lines}",
        f"  Types:  {', '.join(f'{ext}: {cnt}' for ext, cnt in sorted(by_ext.items(), key=lambda x: -x[1]))}",
    ]
    return "\n".join(lines)
