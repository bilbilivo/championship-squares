
import os
import platform
import json
from pathlib import Path

class Config:
    def __init__(self):
        self.system = platform.system().lower()
        self.is_raspberry_pi = self._is_raspberry_pi()
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
        
        # Default configuration
        self.config = {
            'host': '0.0.0.0',  # Listen on all interfaces
            'port': 8080,
            'debug': False,
            'max_players': 10,
            'max_score': self.max_scores['nfl']  # Default max score
        }
        
        # Load environment-specific configuration
        self._load_environment_config()

    def _is_raspberry_pi(self):
        """Check if running on Raspberry Pi"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                return 'Raspberry Pi' in f.read()
        except:
            return False

    def _load_environment_config(self):
        """Load configuration based on environment"""
        config_file = self.base_dir / 'config.json'
        
        # Create default config if it doesn't exist
        if not config_file.exists():
            env_config = {
                'windows': {
                    'host': 'localhost',
                    'port': 8080
                },
                'linux': {
                    'host': '0.0.0.0',
                    'port': 8080
                },
                'darwin': {  # macOS
                    'host': 'localhost',
                    'port': 8080
                },
                'raspberry_pi': {
                    'host': '0.0.0.0',
                    'port': 8080
                }
            }
            
            with open(config_file, 'w') as f:
                json.dump(env_config, f, indent=4)
        
        # Load environment-specific configuration
        try:
            with open(config_file, 'r') as f:
                env_config = json.load(f)
                
            # Select configuration based on platform
            if self.is_raspberry_pi:
                platform_config = env_config.get('raspberry_pi', {})
            else:
                platform_config = env_config.get(self.system, {})
                
            # Update configuration with platform-specific settings
            self.config.update(platform_config)
                
        except Exception as e:
            print(f"Error loading configuration: {e}")
            print("Using default configuration")

    def get_config(self):
        """Get the current configuration"""
        return self.config
   
    def update_sport(self, sport):
        """Update max score based on selected sport"""
        if sport in self.max_scores:
            self.config['max_score'] = self.max_scores[sport]
            return True
        return False
        
# Create global configuration instance
config = Config()
