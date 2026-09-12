#!/usr/bin/env python3
"""Validate a pull request title and commit subjects."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ALLOWED_TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
    "release",
)
EXPECTED_FORMAT = "type(scope)!: description"
SUBJECT_PATTERN = re.compile(
    rf"^(?:{'|'.join(ALLOWED_TYPES)})"
    r"(?:\([a-z0-9][a-z0-9._/-]*\))?"
    r"!?: \S.*$"
)


def is_conventional_subject(subject: str) -> bool:
    """Return whether a subject follows this repository's convention."""
    return bool(SUBJECT_PATTERN.fullmatch(subject))


def commit_subjects(
    base: str,
    head: str,
    cwd: str | Path | None = None,
) -> list[tuple[str, str]]:
    """Return non-merge commits in chronological order for base..head."""
    revision_range = f"{base}..{head}"
    revisions = subprocess.run(
        ["git", "rev-list", "--no-merges", "--reverse", revision_range],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    subjects = []
    for revision in revisions:
        subject = subprocess.run(
            ["git", "show", "-s", "--format=%s", revision],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.rstrip("\n")
        subjects.append((revision, subject))
    return subjects


def validation_errors(
    title: str,
    commits: list[tuple[str, str]],
) -> list[str]:
    """Return human-readable failures for the title and commit subjects."""
    errors = []
    if not is_conventional_subject(title):
        errors.append(f"PR title is invalid: {title!r}")

    for revision, subject in commits:
        if not is_conventional_subject(subject):
            errors.append(f"Commit {revision[:12]} is invalid: {subject!r}")
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a PR title and all non-merge commits in a range."
    )
    parser.add_argument("--title", required=True, help="Pull request title")
    parser.add_argument("--base", required=True, help="Base commit or ref")
    parser.add_argument("--head", required=True, help="Head commit or ref")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        commits = commit_subjects(args.base, args.head)
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() if error.stderr else str(error)
        print(f"Unable to inspect commit range: {detail}", file=sys.stderr)
        return 2

    errors = validation_errors(args.title, commits)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        allowed = ", ".join(ALLOWED_TYPES)
        print(f"Expected: {EXPECTED_FORMAT}", file=sys.stderr)
        print(f"Allowed types: {allowed}", file=sys.stderr)
        return 1

    print(f"Validated PR title and {len(commits)} non-merge commit(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
