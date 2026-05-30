"""
GitHub OSINT Tool — user search, repo analysis, commit email extraction.
Wraps the PyGithub library for FRIDAY OSINT profiling.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


@dataclass
class GithubRepo:
    name: str
    full_name: str
    description: Optional[str] = None
    url: Optional[str] = None
    language: Optional[str] = None
    stars: int = 0
    forks: int = 0
    issues: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    topics: list[str] = field(default_factory=list)
    is_fork: bool = False
    is_archived: bool = False


@dataclass
class GithubUserInfo:
    login: str
    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    blog: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    public_repos: int = 0
    public_gists: int = 0
    followers: int = 0
    following: int = 0
    created_at: Optional[str] = None
    is_hireable: bool = False
    twitter_username: Optional[str] = None
    repos: list[GithubRepo] = field(default_factory=list)


@dataclass
class GithubCommitInfo:
    sha: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    date: Optional[str] = None
    message: Optional[str] = None
    repo: Optional[str] = None


@dataclass
class GithubResult:
    success: bool = False
    error: Optional[str] = None
    scan_time_s: float = 0.0
    user: Optional[GithubUserInfo] = None
    repos: list[GithubRepo] = field(default_factory=list)
    commits: list[GithubCommitInfo] = field(default_factory=list)
    search_results: list[dict] = field(default_factory=list)


def _get_token() -> str:
    return os.environ.get("GITHUB_TOKEN", "")


async def _ensure_pygithub_installed() -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            _python(), "-c", "import github; print(github.__version__)",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=10)
        if proc.returncode == 0:
            return True
    except Exception:
        pass
    logger.info("PyGithub not found — attempting pip install PyGithub ...")
    try:
        proc = await asyncio.create_subprocess_exec(
            _python(), "-m", "pip", "install", "PyGithub",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            logger.warning("PyGithub install failed: %s", stderr.decode(errors="replace")[:200])
            return False
        return True
    except Exception as exc:
        logger.warning("PyGithub install exception: %s", exc)
        return False


def _python() -> str:
    import sys
    return sys.executable


async def github_user_info(username: str, timeout: int = 30) -> GithubResult:
    """
    Get detailed GitHub user profile information including repos.

    Args:
        username: GitHub username
        timeout: Timeout in seconds

    Returns:
        GithubResult with user info and repositories
    """
    available = await _ensure_pygithub_installed()
    if not available:
        return GithubResult(error="PyGithub not installed")

    t0 = time.time()
    try:
        from github import Github

        token = _get_token()
        g = Github(token) if token else Github()

        user = await asyncio.get_event_loop().run_in_executor(
            None, lambda: g.get_user(username)
        )

        info = GithubUserInfo(
            login=user.login,
            id=user.id,
            name=user.name,
            email=user.email,
            company=user.company,
            blog=user.blog,
            location=user.location,
            bio=user.bio,
            public_repos=user.public_repos,
            public_gists=user.public_gists,
            followers=user.followers,
            following=user.following,
            created_at=str(user.created_at) if user.created_at else None,
            is_hireable=user.hireable,
            twitter_username=user.twitter_username,
        )

        repos_raw = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(user.get_repos())[:50]
        )
        for repo in repos_raw:
            info.repos.append(GithubRepo(
                name=repo.name,
                full_name=repo.full_name,
                description=repo.description,
                url=repo.html_url,
                language=repo.language,
                stars=repo.stargazers_count,
                forks=repo.forks_count,
                issues=repo.open_issues_count,
                created_at=str(repo.created_at) if repo.created_at else None,
                updated_at=str(repo.updated_at) if repo.updated_at else None,
                topics=repo.get_topics(),
                is_fork=repo.fork,
                is_archived=repo.archived,
            ))

        return GithubResult(
            success=True,
            user=info,
            repos=info.repos,
            scan_time_s=round(time.time() - t0, 2),
        )

    except Exception as exc:
        logger.exception("GitHub user lookup failed: %s", exc)
        return GithubResult(
            error=str(exc),
            scan_time_s=round(time.time() - t0, 2),
        )


async def github_search_users(
    query: str,
    limit: int = 10,
    timeout: int = 30,
) -> GithubResult:
    """
    Search GitHub for users matching a query.

    Args:
        query: Search query (e.g. "location:london language:python")
        limit: Maximum results
        timeout: Timeout in seconds

    Returns:
        GithubResult with search results
    """
    available = await _ensure_pygithub_installed()
    if not available:
        return GithubResult(error="PyGithub not installed")

    t0 = time.time()
    try:
        from github import Github

        g = Github(_get_token())
        users = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(g.search_users(query)[:limit])
        )

        results = []
        for u in users:
            results.append({
                "login": u.login,
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "company": u.company,
                "location": u.location,
                "bio": u.bio,
                "public_repos": u.public_repos,
                "followers": u.followers,
                "url": u.html_url,
                "type": u.type,
            })

        return GithubResult(
            success=True,
            search_results=results,
            scan_time_s=round(time.time() - t0, 2),
        )

    except Exception as exc:
        logger.exception("GitHub user search failed: %s", exc)
        return GithubResult(
            error=str(exc),
            scan_time_s=round(time.time() - t0, 2),
        )


async def github_search_repos(
    query: str,
    limit: int = 10,
    timeout: int = 30,
) -> GithubResult:
    """
    Search GitHub for repositories matching a query.

    Args:
        query: Search query (e.g. "machine learning language:python")
        limit: Maximum results
        timeout: Timeout in seconds

    Returns:
        GithubResult with repo search results
    """
    available = await _ensure_pygithub_installed()
    if not available:
        return GithubResult(error="PyGithub not installed")

    t0 = time.time()
    try:
        from github import Github

        g = Github(_get_token())
        repos = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(g.search_repositories(query)[:limit])
        )

        found = []
        for r in repos:
            found.append(GithubRepo(
                name=r.name,
                full_name=r.full_name,
                description=r.description,
                url=r.html_url,
                language=r.language,
                stars=r.stargazers_count,
                forks=r.forks_count,
                issues=r.open_issues_count,
                created_at=str(r.created_at) if r.created_at else None,
                updated_at=str(r.updated_at) if r.updated_at else None,
                topics=r.get_topics(),
                is_fork=r.fork,
                is_archived=r.archived,
            ))

        return GithubResult(
            success=True,
            repos=found,
            scan_time_s=round(time.time() - t0, 2),
        )

    except Exception as exc:
        logger.exception("GitHub repo search failed: %s", exc)
        return GithubResult(
            error=str(exc),
            scan_time_s=round(time.time() - t0, 2),
        )


async def github_commit_emails(
    repo_full_name: str,
    limit: int = 100,
    timeout: int = 30,
) -> GithubResult:
    """
    Extract email addresses from commit history of a repository.

    Args:
        repo_full_name: Repository full name (e.g. "owner/repo")
        limit: Maximum commits to scan
        timeout: Timeout in seconds

    Returns:
        GithubResult with commit info including emails
    """
    available = await _ensure_pygithub_installed()
    if not available:
        return GithubResult(error="PyGithub not installed")

    t0 = time.time()
    try:
        from github import Github

        g = Github(_get_token())
        repo = await asyncio.get_event_loop().run_in_executor(
            None, lambda: g.get_repo(repo_full_name)
        )
        commits_raw = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(repo.get_commits()[:limit])
        )

        commits = []
        seen_emails = set()
        for c in commits_raw:
            author = c.commit.author
            email = author.email if author else None
            if email and email not in seen_emails:
                seen_emails.add(email)
            commits.append(GithubCommitInfo(
                sha=c.sha,
                author_name=author.name if author else None,
                author_email=email,
                date=str(author.date) if author and author.date else None,
                message=(c.commit.message or "")[:500],
                repo=repo_full_name,
            ))

        return GithubResult(
            success=True,
            commits=commits,
            scan_time_s=round(time.time() - t0, 2),
        )

    except Exception as exc:
        logger.exception("GitHub commit email extraction failed: %s", exc)
        return GithubResult(
            error=str(exc),
            scan_time_s=round(time.time() - t0, 2),
        )


async def github_org_repos(
    org_name: str,
    limit: int = 50,
    timeout: int = 30,
) -> GithubResult:
    """
    List all repositories for a GitHub organization.

    Args:
        org_name: GitHub organization name
        limit: Maximum repos to return
        timeout: Timeout in seconds

    Returns:
        GithubResult with repos
    """
    available = await _ensure_pygithub_installed()
    if not available:
        return GithubResult(error="PyGithub not installed")

    t0 = time.time()
    try:
        from github import Github

        g = Github(_get_token())
        org = await asyncio.get_event_loop().run_in_executor(
            None, lambda: g.get_organization(org_name)
        )
        repos_raw = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(org.get_repos()[:limit])
        )

        found = []
        for r in repos_raw:
            found.append(GithubRepo(
                name=r.name,
                full_name=r.full_name,
                description=r.description,
                url=r.html_url,
                language=r.language,
                stars=r.stargazers_count,
                forks=r.forks_count,
                issues=r.open_issues_count,
                created_at=str(r.created_at) if r.created_at else None,
                updated_at=str(r.updated_at) if r.updated_at else None,
                topics=r.get_topics(),
                is_fork=r.fork,
                is_archived=r.archived,
            ))

        return GithubResult(
            success=True,
            repos=found,
            scan_time_s=round(time.time() - t0, 2),
        )

    except Exception as exc:
        logger.exception("GitHub org repos failed: %s", exc)
        return GithubResult(
            error=str(exc),
            scan_time_s=round(time.time() - t0, 2),
        )
