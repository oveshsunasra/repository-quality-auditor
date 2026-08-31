"""Tests for local-path and GitHub URL acquisition helpers."""

import subprocess
from pathlib import Path

import pytest

from auditor import cli


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/example/project", "https://github.com/example/project"),
        ("https://github.com/example/project.git", "https://github.com/example/project"),
    ],
)
def test_parse_github_repository_url_accepts_documented_forms(url, expected):
    assert cli._parse_github_repository_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/example/project",
        "https://gitlab.com/example/project",
        "https://user:token@github.com/example/project",
        "https://github.com/example/project?token=secret",
        "https://github.com/example/project/extra",
    ],
)
def test_parse_github_repository_url_rejects_unsupported_forms(url):
    with pytest.raises(ValueError, match="Unsupported repository URL"):
        cli._parse_github_repository_url(url)


def test_clone_github_repository_uses_argument_list_and_temp_directory(monkeypatch, tmp_path):
    clone_dir = tmp_path / "clone"
    calls = []

    monkeypatch.setattr(cli.shutil, "which", lambda executable: "git")
    monkeypatch.setattr(cli.tempfile, "mkdtemp", lambda prefix: str(clone_dir))

    def fake_run(arguments, **kwargs):
        calls.append((arguments, kwargs))
        return subprocess.CompletedProcess(arguments, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli._clone_github_repository("https://github.com/example/project")

    assert result == clone_dir
    assert calls == [
        (
            ["git", "clone", "--depth", "1", "https://github.com/example/project", str(clone_dir)],
            {
                "check": True,
                "capture_output": True,
                "timeout": cli.GIT_CLONE_TIMEOUT_SECONDS,
            },
        )
    ]


def test_clone_github_repository_reports_safe_failure_and_cleans_up(monkeypatch, tmp_path):
    clone_dir = tmp_path / "clone"
    clone_dir.mkdir()
    (clone_dir / "partial-file").write_text("partial", encoding="utf-8")

    monkeypatch.setattr(cli.shutil, "which", lambda executable: "git")
    monkeypatch.setattr(cli.tempfile, "mkdtemp", lambda prefix: str(clone_dir))

    def fake_run(arguments, **kwargs):
        raise subprocess.CalledProcessError(
            128,
            arguments,
            stderr=b"fatal: https://user:token@github.com/example/project",
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="git exited with status 128") as error:
        cli._clone_github_repository("https://github.com/example/project")

    assert "token" not in str(error.value)
    assert not clone_dir.exists()


def test_clone_github_repository_requires_git(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda executable: None)

    with pytest.raises(RuntimeError, match="not found in PATH"):
        cli._clone_github_repository("https://github.com/example/project")


def test_http_url_detection_preserves_local_path_handling():
    assert cli._is_http_url("https://github.com/example/project") is True
    assert cli._is_http_url("./local-repository") is False
    assert cli._is_http_url(r"C:\local-repository") is False
