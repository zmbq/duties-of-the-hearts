#!/usr/bin/env python
"""Test script to verify configuration is working."""

from src.utils import config
from pathlib import Path

# Get PROJECT_ROOT from the module
import src.utils as utils_module
PROJECT_ROOT = utils_module.PROJECT_ROOT

print("Configuration Test")
print("=" * 50)
print(f"Project Root: {PROJECT_ROOT}")
print(f"Config Path: {config.config_path}")
print(f"Database URL: {config.database_url}")
print(f"OpenAI Model: {config.openai_model}")
print(f"Output Directory: {config.output_dir}")
print(f"Assets Directory: {config.assets_dir}")
print(f"Available Prompts: {', '.join(config.list_prompts())}")

print("\nTesting API key...")
try:
    api_key = config.openai_api_key
    # Mask the key for security
    masked = f"{api_key[:10]}...{api_key[-4:]}"
    print(f"✓ OpenAI API Key: {masked} (configured)")
except ValueError as e:
    print(f"✗ OpenAI API Key: Not configured")
    print(f"  Error: {e}")
    print("\n  To fix this:")
    print("  1. Copy .env.example to .env")
    print("  2. Edit .env and add your OpenAI API key")

print("\n" + "=" * 50)
print("Configuration test complete!")
