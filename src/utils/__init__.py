"""
Configuration management for Duties of the Hearts translation project.

This module loads configuration from:
1. .env file (for secrets like API keys)
2. config.yaml (for application settings)
3. Environment variables (override config.yaml)
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Load .env file if it exists
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    load_dotenv(env_path)


class Config:
    """Configuration manager for the application."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to config.yaml. If None, uses default location.
        """
        if config_path is None:
            config_path = PROJECT_ROOT / 'config.yaml'
        
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        
        # Load config.yaml
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Example:
            config.get('openai.default_model')
            config.get('database.echo', False)
        
        Args:
            key: Configuration key in dot notation (e.g., 'section.subsection.key')
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    # Convenience properties for commonly used values
    
    @property
    def openai_api_key(self) -> str:
        """Get OpenAI API key from environment."""
        api_key = os.getenv('OPENAI_API_KEY', '')
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Please create a .env file with your API key. "
                "See .env.example for template."
            )
        return api_key
    
    @property
    def openai_model(self) -> str:
        """Get OpenAI model (env var overrides config)."""
        return os.getenv('OPENAI_MODEL') or self.get('openai.default_model', 'gpt-4')
    
    @property
    def database_url(self) -> str:
        """Get database URL (env var overrides config)."""
        env_url = os.getenv('DATABASE_URL')
        if env_url:
            return env_url
        
        # Default to SQLite
        db_path = self.get('database.default_path', 'duties_of_the_hearts.db')
        db_file = PROJECT_ROOT / db_path
        return f'sqlite:///{db_file}'
    
    @property
    def database_echo(self) -> bool:
        """Whether to echo SQL queries."""
        return self.get('database.echo', False)
    
    @property
    def output_dir(self) -> Path:
        """Get output directory path."""
        output_path = self.get('export.output_dir', 'output')
        output_dir = PROJECT_ROOT / output_path
        output_dir.mkdir(exist_ok=True)
        return output_dir
    
    @property
    def assets_dir(self) -> Path:
        """Get assets directory path."""
        assets_dir = PROJECT_ROOT / 'assets'
        if not assets_dir.exists():
            raise FileNotFoundError(f"Assets directory not found: {assets_dir}")
        return assets_dir
    
    def get_prompt(self, prompt_name: str) -> Dict[str, str]:
        """
        Get a translation prompt configuration.
        
        Args:
            prompt_name: Name of the prompt (e.g., 'literal', 'modern', 'simplified')
        
        Returns:
            Dictionary with 'name', 'description', and 'system_prompt' keys
        
        Raises:
            KeyError: If prompt not found
        """
        prompts = self.get('prompts', {})
        if prompt_name not in prompts:
            available = ', '.join(prompts.keys())
            raise KeyError(
                f"Prompt '{prompt_name}' not found. "
                f"Available prompts: {available}"
            )
        return prompts[prompt_name]
    
    def list_prompts(self) -> list[str]:
        """Get list of available prompt names."""
        return list(self.get('prompts', {}).keys())


# Global config instance
config = Config()


if __name__ == '__main__':
    # Test the configuration
    print("Configuration Test")
    print("=" * 50)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Config Path: {config.config_path}")
    print(f"Database URL: {config.database_url}")
    print(f"OpenAI Model: {config.openai_model}")
    print(f"Output Directory: {config.output_dir}")
    print(f"Available Prompts: {', '.join(config.list_prompts())}")
    
    try:
        api_key = config.openai_api_key
        print(f"OpenAI API Key: {'*' * 20} (configured)")
    except ValueError as e:
        print(f"OpenAI API Key: Not configured - {e}")
