# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-02-17

### Added
- Initial release of Championship Squares web application
- Flask-based REST API backend with SQLite database persistence
- Interactive web-based grid interface with D3.js visualization
- Support for multiple sports: NFL, NHL, MLB, and Olympics
- Platform-aware configuration system for cross-platform compatibility
- Automatic launcher scripts for Unix/macOS (`start_server.sh`) and Windows (`start_server.ps1`)
- Player management system with token-based betting
- Real-time multiplier system for variable bet values
- Team selection with comprehensive sport-specific team lists
- Score tracking and winner determination
- Lite mode toggle for reduced visual effects
- Desktop shortcut creation via launcher setup action
- Comprehensive documentation:
  - API documentation for all endpoints
  - Configuration guide for sport-specific settings
  - Deployment guide with Docker support
  - Developer guide with architecture overview
  - Game rules and mechanics documentation
  - Testing guide with pytest configuration
  - Troubleshooting guide for common issues
- GitHub Actions CI/CD pipeline
- Test suite with pytest:
  - API endpoint tests
  - Game state tests
  - Smoke tests for basic functionality
  - Test setup script (`generate_fake_game.py`) for automated game creation with:
    - Support for all sports (NFL, NHL, MLB, Olympics)
    - Configurable player count and token distribution
    - Biased square generation favoring lower scores
    - Automated team selection and score setting
    - Server health checks and error handling

### Technical Details
- Python 3.7+ requirement
- Flask web framework
- SQLite database for state persistence
- Vanilla JavaScript frontend with D3.js
- Cross-platform support (Linux, macOS, Windows)
- Virtual environment auto-setup on first run
- Automatic browser launch on server start

[Unreleased]: https://github.com/bilbilivo/championship-squares/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/bilbilivo/championship-squares/releases/tag/v1.0.0
