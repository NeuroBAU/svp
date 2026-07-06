"""Shared fixtures for routing regression tests (audit 2026-07-06, P2)."""

import json
import sys
from pathlib import Path

SCRIPTS_DIR = str(Path(__file__).resolve().parents[2] / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from pipeline_state import PipelineState, save_state  # noqa: E402


def make_state(root, **kwargs):
    """Build and persist a PipelineState in *root*; returns the state."""
    state = PipelineState(**kwargs)
    save_state(root, state)
    return state


def write_status(root, status):
    (root / ".svp" / "last_status.txt").write_text(status + "\n", encoding="utf-8")


def read_state_dict(root):
    return json.loads((root / ".svp" / "pipeline_state.json").read_text(encoding="utf-8"))


def write_profile(root, **fields):
    profile = {"language": {"primary": "python"}}
    profile.update(fields)
    (root / "project_profile.json").write_text(
        json.dumps(profile), encoding="utf-8"
    )
