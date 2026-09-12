import subprocess
from pathlib import Path

import pytest

from scripts.check_conventional_commits import (
    commit_subjects,
    is_conventional_subject,
    main,
    validation_errors,
)


@pytest.mark.parametrize(
    "subject",
    [
        "feat: add scoreboard sharing",
        "fix(sync): recover missed updates",
        "feat(api)!: replace the state response",
        "revert: restore the previous board layout",
        "release: v2026.14",
    ],
)
def test_accepts_supported_conventional_subjects(subject):
    assert is_conventional_subject(subject)


@pytest.mark.parametrize(
    "subject",
    [
        "Feat: use an uppercase type",
        "feature: use an unsupported type",
        "fix(Sync): use an uppercase scope",
        "fix(): use an empty scope",
        "docs update contribution guidance",
        "docs:",
        "docs: ",
    ],
)
def test_rejects_invalid_subjects(subject):
    assert not is_conventional_subject(subject)


def test_reports_title_and_commit_failures():
    errors = validation_errors(
        "Update checks",
        [("0123456789abcdef", "fix: valid subject"), ("fedcba9876543210", "bad commit")],
    )

    assert errors == [
        "PR title is invalid: 'Update checks'",
        "Commit fedcba987654 is invalid: 'bad commit'",
    ]


def run_git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def commit_file(repository: Path, filename: str, contents: str, subject: str) -> str:
    (repository / filename).write_text(contents, encoding="utf-8")
    run_git(repository, "add", filename)
    run_git(repository, "commit", "-m", subject)
    return run_git(repository, "rev-parse", "HEAD")


def test_commit_range_excludes_merges_and_preserves_order(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    run_git(repository, "init", "-b", "main")
    run_git(repository, "config", "user.name", "Test User")
    run_git(repository, "config", "user.email", "test@example.com")

    commit_file(repository, "base.txt", "base", "chore: create test repository")

    run_git(repository, "checkout", "-b", "feature")
    valid_revision = commit_file(repository, "feature.txt", "one", "feat: add feature")

    run_git(repository, "checkout", "main")
    commit_file(repository, "main.txt", "main", "fix: update main")
    base = run_git(repository, "rev-parse", "HEAD")
    run_git(repository, "checkout", "feature")
    run_git(repository, "merge", "--no-ff", "main", "-m", "Merge main into feature")
    invalid_revision = commit_file(repository, "later.txt", "two", "invalid subject")

    commits = commit_subjects(base, "HEAD", cwd=repository)

    assert commits == [
        (valid_revision, "feat: add feature"),
        (invalid_revision, "invalid subject"),
    ]
    assert validation_errors("feat: add feature", commits) == [
        f"Commit {invalid_revision[:12]} is invalid: 'invalid subject'"
    ]


def test_cli_returns_failure_with_actionable_guidance(monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.check_conventional_commits.commit_subjects",
        lambda base, head: [("0123456789abcdef", "not conventional")],
    )

    result = main(["--title", "Bad title", "--base", "main", "--head", "HEAD"])
    captured = capsys.readouterr()

    assert result == 1
    assert "PR title is invalid" in captured.err
    assert "Commit 0123456789ab is invalid" in captured.err
    assert "Expected: type(scope)!: description" in captured.err
    assert "release" in captured.err
