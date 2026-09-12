# Contributing to Championship Squares

Thank you for helping improve Championship Squares. Keep each change focused so it
is straightforward to review, test, and release.

## Branches

Create branches from an up-to-date `main` using `<category>/<kebab-case>`, for
example `feature/shared-end-game-cinematic` or `fix/player-session-refresh`.
Common categories are `feature`, `fix`, `docs`, `ci`, `chore`, and `refactor`.

## Conventional Commits

Pull request titles and every non-merge commit introduced by the pull request must
use this form:

```text
type(scope)!: description
```

The scope and `!` are optional. Types and scopes must be lowercase, and the
description must not be empty. Supported types are `feat`, `fix`, `docs`, `style`,
`refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`, and `release`.

Examples:

```text
feat: broadcast the end-game cinematic
fix(sync): recover missed score updates
feat(api)!: replace the game-state response
release: v2026.14
```

Use `!` when a commit introduces a breaking change. Explain the impact and
migration in a `BREAKING CHANGE:` footer in the commit body and in the pull
request's Breaking changes section.

The `Conventional commits` workflow checks the pull request title and all
non-merge commits in the `Validate PR and commits` job. GitHub's checks UI renders
the context as `Conventional commits / Validate PR and commits`; select that check
when configuring branch protection. Update an invalid title or rewrite invalid
commits, then push the corrected branch to rerun the check.

## Pull Requests

Before opening a pull request:

1. Rebase or merge the latest `main` into the branch.
2. Run the Python and JavaScript suites:

   ```bash
   venv/bin/python -m pytest -q
   node --test tests/*.test.cjs
   ```

3. Update tests for behavior changes.
4. Update relevant documentation and API references. Add notable user-facing,
   compatibility, security, or workflow changes to the Unreleased changelog.
5. Complete every applicable section of the pull request template. Include
   screenshots or other UI evidence for visual changes; write “Not applicable”
   when evidence or a section does not apply.

Keep the pull request focused on one purpose. Call out migrations, compatibility
effects, security considerations, and breaking changes explicitly.

Pull requests are squash-merged. Set the PR title to the Conventional Commit
subject that should appear on `main`; GitHub must be configured to use that title
as the squash commit subject. The individual branch commits remain validated to
keep review history understandable.

## Repository Settings

A repository administrator must configure the `main` ruleset or branch protection
in GitHub. These settings cannot be imposed by files in the repository alone.

- Require pull requests and at least one approval before merging.
- Require branches to be current before merging.
- Require all existing CI checks plus
  `Conventional commits / Validate PR and commits`.
- Require linear history and prevent ordinary contributors from bypassing rules.
- Enable squash merging, choose the PR title as the default squash commit subject,
  and disable merge commits. Rebase merging may also be disabled so squash is the
  only merge path.
- Retain an explicit administrator recovery path for repository emergencies.

Changing these GitHub settings is a one-time administrator action and is not
performed by the validation workflow.

## Releases

Prepare releases on a dedicated branch and open a pull request titled
`release: vYYYY.MM`. After it passes review and is squash-merged, tag the resulting
commit on `main`, push the annotated tag, and publish the GitHub Release. See the
[Developer Guide](DEVELOPER_GUIDE.md#release-procedure) for the complete sequence.
