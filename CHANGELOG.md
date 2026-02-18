# Changelog

All notable changes to Championship Squares will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [v2026.03] - 2026-02-18

### Changed
- Raised minimum Python version from 3.7+ to 3.10+ across all documentation and CI
- Updated development dependencies to latest versions:
  - pytest: ^7.4.0
  - pytest-cov: ^4.1.0
  - flake8: ^6.1.0
  - pip-audit: ^2.6.1
- Updated GitHub Actions CI matrix to test on Python 3.10 and 3.12 (removed EOL Python 3.8 support)
- Enhanced documentation:
  - README.md, DEVELOPER_GUIDE.md, DEPLOYMENT.md, TESTING.md, CONFIGURATION.md with venv usage and Python 3.10+ requirement

### Quality & Testing
- All 93 unit tests passing
- Code coverage: 86%
- Linting passes flake8 checks
- No security vulnerabilities detected via pip-audit

### Release Procedure
- Releases are created in two steps:
  1. Create a git tag for the release (e.g. v2026.03)
  2. Publish a GitHub Release from the tag, including release notes and comparison links

## [v2026.02] - 2026-02-18

### Added
- SQLite database persistence layer, replacing JSON file storage (`database.py`)
- Comprehensive test suite with pytest achieving 80%+ code coverage
- CI/CD pipeline via GitHub Actions (lint, test across Python 3.8/3.12, dependency audit)
- Full documentation suite: API reference, configuration guide, deployment guide, developer guide, game rules, testing procedures, and troubleshooting
- Development dependency manifest (`requirements-dev.txt`)
- Test data generator for simulating full games (`tests/generate_fake_game.py`)
- Flask `SECRET_KEY` configuration via `FLASK_SECRET_KEY` environment variable
- Security response headers (`X-Content-Type-Options`, `X-Frame-Options`)

### Changed
- Refactored frontend: extracted CSS and JavaScript from monolithic `index.html` into `static/css/style.css` and `static/js/game.js`
- Implemented draft-style round-robin betting system
- Moved `requests` package from production to development dependencies
- Improved `.gitignore` with broader coverage for Python artifacts and sensitive files

### Fixed
- Grid desynchronization when switching sports mid-game
- Hardened `/api/squares` endpoint with explicit integer type validation for row/col
- Prevented error message information leaks on template loading failures
- Eliminated XSS vector in celebration overlay by using `textContent` instead of `innerHTML` for player names
- Removed debug `console.log` statements from production JavaScript
- Removed `.coverage` binary file from version control

### Security
- Full security audit of codebase and git history (no secrets or credentials found)
- Added security response headers to all Flask responses
- Added Flask secret key for defense-in-depth (configurable via environment variable)
- Hardened input validation on square placement API
- Removed unused production dependency (`requests`) to reduce attack surface

## [v2026.01] - 2026-02-10

### Added
- Initial public release of Championship Squares
- Multi-sport support: NFL, NHL, NBA, MLB, Olympics, FIFA
- Interactive D3.js grid visualization with zoom and pan
- Multiplier-based betting system with sport-specific token allocations
- Winner calculation via Manhattan distance algorithm
- Multi-winner support for ties at equal distance
- End-game celebration with confetti, fireworks, and podium display
- Lite mode for reduced visual effects on lower-performance devices
- Desktop launcher scripts for Linux/macOS (`start_server.sh`) and Windows (`start_server.ps1`)
- Automatic virtual environment creation and dependency installation on first run
- Desktop shortcut creation (`.desktop` for Linux, `.lnk` for Windows)
- Team selection with sport-specific team rosters and color themes
- 8-bit retro visual theme with sport-specific color schemes

[v2026.03]: https://github.com/bilbilivo/championship-squares/compare/v2026.02...v2026.03
[v2026.02]: https://github.com/bilbilivo/championship-squares/compare/v2026.01...v2026.02
[v2026.01]: https://github.com/bilbilivo/championship-squares/releases/tag/v2026.01
