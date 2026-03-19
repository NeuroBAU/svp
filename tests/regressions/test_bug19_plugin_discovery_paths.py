"""Bug 19 (2.1) regression: Plugin discovery must validate JSON content.

_is_svp_plugin_dir must read plugin.json and check name == 'svp',
not just check that the directory exists.
"""

import json
from pathlib import Path

from svp_launcher import _is_svp_plugin_dir


def test_valid_plugin_dir_accepted(tmp_path):
    """Directory with valid plugin.json must be accepted."""
    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps({"name": "svp", "version": "2.1.0"}))
    assert _is_svp_plugin_dir(tmp_path) is True


def test_missing_plugin_json_rejected(tmp_path):
    """Directory without plugin.json must be rejected."""
    assert _is_svp_plugin_dir(tmp_path) is False


def test_wrong_name_rejected(tmp_path):
    """Directory with plugin.json but wrong name must be rejected."""
    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps({"name": "other_plugin"}))
    assert _is_svp_plugin_dir(tmp_path) is False


def test_invalid_json_rejected(tmp_path):
    """Directory with invalid JSON in plugin.json must be rejected."""
    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text("not valid json{{{")
    assert _is_svp_plugin_dir(tmp_path) is False
