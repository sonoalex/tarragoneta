"""
Core application components
"""
from app.core.cli import register_cli_commands
from app.core.context_processors import register_context_processors
from app.core.error_handlers import register_error_handlers
from app.core.logging_config import setup_logging

__all__ = [
    'register_cli_commands',
    'register_context_processors',
    'register_error_handlers',
    'setup_logging'
]

