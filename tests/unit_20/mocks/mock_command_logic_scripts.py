# Auto-generated stub — do not edit
from unittest.mock import MagicMock
from typing import Optional, Dict, Any
from pathlib import Path

def save_project(project_root: Path) -> str:
    return ''

def quit_project(project_root: Path) -> str:
    return ''

def get_status(project_root: Path) -> str:
    return ''

def format_pass_history(pass_history: list) -> str:
    return ''

def format_debug_history(debug_history: list) -> str:
    return ''

def clean_workspace(project_root: Path, mode: str) -> str:
    return ''

def archive_workspace(project_root: Path) -> Path:
    return MagicMock()

def delete_workspace(project_root: Path) -> None:
    return None

def remove_conda_env(env_name: str) -> bool:
    return False
