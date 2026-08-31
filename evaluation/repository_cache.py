#!/usr/bin/env python3
"""
Shared repository cache and acquisition helpers for the evaluation harness.
"""

import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

GIT_TIMEOUT_SECONDS = 300
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1


def cache_path(repo_url: str, commit_sha: str, cache_dir: Path) -> Path:
    """
    Return the expected cache directory path for a given repo URL and commit SHA.
    The cache directory name is: <sanitized-repo-url>_<first 12 chars of SHA>
    """
    # Sanitize the repo URL for use as a directory name: remove scheme, replace
    # slashes and colons with underscores, and remove any trailing .git.
    parsed = urlsplit(repo_url)
    netloc = parsed.netloc
    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    # Replace any remaining slashes with underscores
    path = path.replace("/", "_")
    # Remove leading/trailing underscores
    path = path.strip("_")
    # If the path is empty, use the netloc only
    if not path:
        dir_name = netloc
    else:
        dir_name = f"{netloc}_{path}"
    # Truncate SHA to 12 characters
    short_sha = commit_sha[:12]
    cache_name = f"{dir_name}_{short_sha}"
    return cache_dir / cache_name


def _display_url(repo_url: str) -> str:
    """
    Return a URL suitable for display (strip userinfo, query, fragment).
    """
    parsed = urlsplit(repo_url)
    # Reconstruct without userinfo, query, fragment
    display = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    return display


def _is_git_worktree(path: Path) -> bool:
    """
    Check if the given path is a Git work tree.
    """
    try:
        subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _get_remote_url(path: Path) -> str:
    """
    Get the remote origin URL for the given Git work tree.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _make_writable_and_retry(func, path: Path, exc_info) -> None:
    """
    Helper to handle read-only files on Windows during removal.
    """
    try:
        os.chmod(path, 0o700)  # rwx------
        func(path)
    except OSError:
        pass  # Best effort; if it still fails, let the outer handler deal with it


def _remove_directory(path: Path) -> None:
    """
    Best-effort removal of a directory, handling read-only files on Windows.
    """
    shutil.rmtree(str(path), onerror=lambda func, p, _: _make_writable_and_retry(func, Path(p), None))


def clone_or_update_repo(repo_url: str, commit_sha: str, cache_dir: Path) -> Path:
    """
    Clone or update a repository to the exact commit SHA, using a cache.
    Returns the path to the cloned repository.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    repo_cache_dir = cache_path(repo_url, commit_sha, cache_dir)

    # If the cache exists and is a valid Git work tree with the correct remote,
    # try to checkout the desired SHA directly.
    if repo_cache_dir.is_dir() and _is_git_worktree(repo_cache_dir):
        remote_url = _get_remote_url(repo_cache_dir)
        if remote_url.lower() == repo_url.lower().rstrip("/.git"):
            # Try to checkout the SHA directly (it may already be present)
            try:
                subprocess.run(
                    ["git", "-C", str(repo_cache_dir), "fetch", "--depth", "1", "origin", commit_sha],
                    check=True,
                    capture_output=True,
                    timeout=GIT_TIMEOUT_SECONDS,
                )
                subprocess.run(
                    ["git", "-C", str(repo_cache_dir), "checkout", "--detach", commit_sha],
                    check=True,
                    capture_output=True,
                    timeout=GIT_TIMEOUT_SECONDS,
                )
                # Verify we are on the correct commit
                result = subprocess.run(
                    ["git", "-C", str(repo_cache_dir), "rev-parse", "HEAD"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if result.stdout.strip() == commit_sha:
                    return repo_cache_dir
                # If not, fall through to re-clone
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                # If fetch or checkout fails, we will re-clone
                pass

    # Otherwise, we need to (re)clone.
    # Remove any existing cache directory to start fresh.
    if repo_cache_dir.is_dir():
        _remove_directory(repo_cache_dir)

    # Attempt clone with retries and backoff.
    attempt = 0
    while True:
        attempt += 1
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(repo_cache_dir)],
                check=True,
                capture_output=True,
                timeout=GIT_TIMEOUT_SECONDS,
            )
            # Checkout the desired SHA (depth 1 clone may not have it if it's not the tip)
            subprocess.run(
                ["git", "-C", str(repo_cache_dir), "fetch", "--depth", "1", "origin", commit_sha],
                check=True,
                capture_output=True,
                timeout=GIT_TIMEOUT_SECONDS,
            )
            subprocess.run(
                ["git", "-C", str(repo_cache_dir), "checkout", "--detach", commit_sha],
                check=True,
                capture_output=True,
                timeout=GIT_TIMEOUT_SECONDS,
            )
            # Verify
            result = subprocess.run(
                ["git", "-C", str(repo_cache_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
            if result.stdout.strip() != commit_sha:
                raise RuntimeError(f"Checked out commit does not match expected SHA: {commit_sha}")
            return repo_cache_dir
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            if attempt >= MAX_ATTEMPTS:
                # Clean up the partial cache and raise
                _remove_directory(repo_cache_dir)
                if isinstance(e, subprocess.TimeoutExpired):
                    raise RuntimeError(
                        f"Timed out while cloning {repo_url} after {e.timeout} seconds"
                    ) from e
                else:
                    raise RuntimeError(
                        f"Failed to clone {repo_url} (git exited with status {e.returncode})"
                    ) from e
            # Wait before retrying
            time.sleep(BACKOFF_SECONDS)