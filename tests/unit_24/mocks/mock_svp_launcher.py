# Auto-generated stub — do not edit
from unittest.mock import MagicMock
from typing import Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timezone
import subprocess
import sys
import argparse
import shutil
import os
import json
import stat
import time
RESTART_SIGNAL_FILE: str = '.svp/restart_signal'
STATE_FILE: str = 'pipeline_state.json'
CONFIG_FILE: str = 'svp_config.json'
SVP_DIR: str = '.svp'
MARKERS_DIR: str = '.svp/markers'
CLAUDE_MD_FILE: str = 'CLAUDE.md'
README_SVP_FILE: str = 'README_SVP.txt'
SVP_ENV_VAR: str = 'SVP_PLUGIN_ACTIVE'
PROJECT_DIRS: List[str] = ['.svp', '.svp/markers', '.claude', 'scripts', 'ledgers', 'logs', 'logs/rollback', 'specs', 'specs/history', 'blueprint', 'blueprint/history', 'references', 'references/index', 'src', 'tests', 'data']

def _find_plugin_root() -> Optional[Path]:
    return None

def _is_svp_plugin_dir(path: Path) -> bool:
    return False

def _print_header(text: str) -> None:
    return None

def _print_status(name: str, passed: bool, message: str) -> None:
    return None

def _print_transition(message: str) -> None:
    return None

def parse_args(argv: Optional[List[str]]=None) -> argparse.Namespace:
    return MagicMock()

def check_claude_code() -> Tuple[bool, str]:
    return ()

def check_svp_plugin() -> Tuple[bool, str]:
    return ()

def check_api_credentials() -> Tuple[bool, str]:
    return ()

def check_conda() -> Tuple[bool, str]:
    return ()

def check_python() -> Tuple[bool, str]:
    return ()

def check_pytest() -> Tuple[bool, str]:
    return ()

def check_git() -> Tuple[bool, str]:
    return ()

def check_network() -> Tuple[bool, str]:
    return ()

def run_all_prerequisites() -> List[Tuple[str, bool, str]]:
    return []

def create_project_directory(project_name: str, parent_dir: Path) -> Path:
    return MagicMock()

def copy_scripts_to_workspace(plugin_root: Path, project_root: Path) -> None:
    return None

def generate_claude_md(project_root: Path, project_name: str) -> None:
    return None

def _generate_claude_md_fallback(project_name: str) -> str:
    return ''

def write_initial_state(project_root: Path, project_name: str) -> None:
    return None

def write_default_config(project_root: Path) -> None:
    return None

def write_readme_svp(project_root: Path) -> None:
    return None

def set_filesystem_permissions(project_root: Path, read_only: bool) -> None:
    return None

def launch_claude_code(project_root: Path, plugin_dir: Path) -> int:
    return 0

def detect_restart_signal(project_root: Path) -> Optional[str]:
    return None

def clear_restart_signal(project_root: Path) -> None:
    return None

def run_session_loop(project_root: Path, plugin_dir: Path) -> int:
    return 0

def detect_existing_project(directory: Path) -> bool:
    return False

def resume_project(project_root: Path, plugin_dir: Path) -> int:
    return 0

def _handle_new_project(args: argparse.Namespace, plugin_dir: Path) -> int:
    return 0

def _handle_restore(args: argparse.Namespace, plugin_dir: Path) -> int:
    return 0

def _handle_resume(plugin_dir: Path) -> int:
    return 0

def main(argv: Optional[List[str]]=None) -> int:
    return 0
