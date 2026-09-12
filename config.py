# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Stephane Belliveau
import os
import platform
import secrets
from pathlib import Path


def load_flask_secret(base_dir=None):
    """Load a stable signing secret without putting it in source or SQLite."""
    configured = os.environ.get('FLASK_SECRET_KEY')
    if configured is not None:
        if not configured:
            raise RuntimeError('FLASK_SECRET_KEY must not be empty')
        return configured

    root = Path(base_dir) if base_dir is not None else Path(__file__).parent.absolute()
    secret_path = Path(os.environ.get('FLASK_SECRET_KEY_FILE', root / '.flask-secret'))
    if secret_path.is_symlink():
        raise RuntimeError(f'Refusing to use a symlink as the Flask secret file: {secret_path}')

    try:
        secret = secret_path.read_text(encoding='ascii').strip()
    except FileNotFoundError:
        secret = secrets.token_urlsafe(48)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(secret_path, flags, 0o600)
        except FileExistsError:
            secret = secret_path.read_text(encoding='ascii').strip()
        except OSError as error:
            raise RuntimeError(
                f'Cannot create the Flask signing secret at {secret_path}; set FLASK_SECRET_KEY '
                'or FLASK_SECRET_KEY_FILE to a protected writable location'
            ) from error
        else:
            with os.fdopen(descriptor, 'w', encoding='ascii') as secret_file:
                secret_file.write(f'{secret}\n')
                secret_file.flush()
                os.fsync(secret_file.fileno())
    except OSError as error:
        raise RuntimeError(
            f'Cannot read the Flask signing secret at {secret_path}; set FLASK_SECRET_KEY '
            'or FLASK_SECRET_KEY_FILE to a protected writable location'
        ) from error

    if len(secret) < 32:
        raise RuntimeError(f'Flask signing secret at {secret_path} must contain at least 32 characters')
    try:
        secret_path.chmod(0o600)
    except OSError:
        # Windows ACLs do not map cleanly to POSIX modes. The file remains local
        # and excluded from source control; administrators can apply an ACL.
        pass
    return secret


class Config:
    def __init__(self):
        self.system = platform.system().lower()
        self.base_dir = Path(__file__).parent.absolute()
        self.template_dir = self.base_dir / 'templates'
        self.static_dir = self.base_dir / 'static'

        # Create necessary directories if they don't exist
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.static_dir.mkdir(parents=True, exist_ok=True)

        # Sport-specific max scores
        self.max_scores = {
            'nfl': 70,
            'nhl': 12,
            'nba': 160,
            'mlb': 30,
            'olym': 12,
            'fifa': 10
        }

        # Sport-specific multiplier configurations
        self.multipliers = {
            'nfl': [1, 2, 4, 8],
            'nhl': [1, 2, 4],
            'nba': [1, 2, 4, 8],
            'mlb': [1, 2, 4, 8],
            'olym': [1, 2, 4],
            'fifa': [1, 2]
        }

        # Sport-specific multiplier labels (when to use each multiplier)
        self.multiplier_labels = {
            'nfl': ['<Q1', '<Q2', '<Q3', '<Q4'],
            'nhl': ['<P1', '<P2', '<P3'],
            'nba': ['<Q1', '<Q2', '<Q3', '<Q4'],
            'mlb': ['<I3', '<I6', '<I8', '<I9'],
            'olym': ['<P1', '<P2', '<P3'],
            'fifa': ['<H1', '<H2']
        }

        # Sport-specific total tokens available for betting
        self.total_tokens = {
            'nfl': 40,
            'nhl': 12,
            'nba': 48,
            'mlb': 20,
            'olym': 12,
            'fifa': 8
        }

        # Platform-specific host settings
        platform_hosts = {
            'windows': 'localhost',
            'linux': '0.0.0.0',
            'darwin': 'localhost'
        }

        # Configuration
        self.config = {
            'host': platform_hosts.get(self.system, '0.0.0.0'),
            'port': 8080,
            'debug': False,
            'max_players': 12,
            'max_score': self.max_scores['nfl']
        }

    def update_sport(self, sport):
        """Update max score based on selected sport"""
        if sport in self.max_scores:
            self.config['max_score'] = self.max_scores[sport]
            return True
        return False
        
# Create global configuration instance
config = Config()
