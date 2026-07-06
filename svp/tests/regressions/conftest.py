"""Fixtures for routing regression tests (audit 2026-07-06, P2)."""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = str(Path(__file__).resolve().parents[2] / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


@pytest.fixture()
def project_root(tmp_path):
    """A minimal SVP project root: nested so a sibling delivered-repo dir
    can be created next to it, with an .svp directory ready."""
    root = tmp_path / "proj"
    (root / ".svp").mkdir(parents=True)
    return root
