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
        
        # Default configuration
        self.config = {
            'host': '0.0.0.0',  # Listen on all interfaces
            'port': 5000,
            'debug': False,
            'max_players': 10,
            'grid_size': 61
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
                    'port': 5000
                },
                'linux': {
                    'host': '0.0.0.0',
                    'port': 5000
                },
                'darwin': {  # macOS
                    'host': 'localhost',
                    'port': 5000
                },
                'raspberry_pi': {
                    'host': '0.0.0.0',
                    'port': 8080  # Different port for Raspberry Pi
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

# Create global configuration instance
config = Config()