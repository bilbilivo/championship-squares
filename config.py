import platform
from pathlib import Path

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
            'mlb': 16,
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
