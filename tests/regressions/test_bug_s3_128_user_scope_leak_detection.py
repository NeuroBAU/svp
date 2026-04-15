"""Regression tests for Bug S3-128: preflight detection of pre-S3-123
user-scope plugin leak.

Bug S3-123 migrated SVP to project-scope plugin activation and documented
the user-side migration path (`claude plugin uninstall svp@svp --scope user`).
The migration is opt-in. Users who upgraded SVP without performing it
retained `enabledPlugins["svp@svp"] = true` in `~/.claude/settings.json`
indefinitely, leaking SVP into every Claude Code session on the machine.
There was no runtime signal that the migration was incomplete.

Fix: new `check_user_scope_svp_leak()` helper in Unit 29, wired into
`preflight_check()` as an advisory (not a failure). The helper reads
`~/.claude/settings.json` defensively and returns an advisory message
when the leak is detected, or None otherwise.

This file locks:
  - return-None invariants on every failure mode (missing file, corrupt
    JSON, non-dict root, non-dict enabledPlugins, svp@svp absent, svp@svp
    set to False/0/string/None)
  - return-string invariants when the leak is present (message content,
    migration command reference, spec citation)
  - preflight integration (advisory printed to stdout, errors list
    unaffected by leak state, `!` marker prefix, `_check` ordering)

All tests use `monkeypatch.setattr(Path, "home", lambda: tmp_path)` to
redirect `Path.home()` so the tests are hermetic on every developer's
machine regardless of their own user-scope settings.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# S3-103 discipline: import from the derived `svp_launcher` module (script),
# not from `src.unit_29.stub`.
from svp_launcher import check_user_scope_svp_leak, preflight_check


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch) -> Path:
    """Redirect Path.home() to a tmp directory so the helper reads our
    fake settings.json instead of the developer's real one.
    """
    fake = tmp_path / "fake_home"
    fake.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake)
    return fake


def _write_user_settings(home: Path, data) -> Path:
    """Write arbitrary `data` (not required to be a dict) to
    `home/.claude/settings.json` as JSON and return the path."""
    settings_dir = home / ".claude"
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path = settings_dir / "settings.json"
    settings_path.write_text(json.dumps(data))
    return settings_path


def _write_user_settings_raw(home: Path, raw: str) -> Path:
    """Write raw (possibly invalid JSON) content to settings.json."""
    settings_dir = home / ".claude"
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path = settings_dir / "settings.json"
    settings_path.write_text(raw)
    return settings_path


# ---------------------------------------------------------------------------
# Negative cases: return None (no leak detected)
# ---------------------------------------------------------------------------


class TestReturnsNoneWhenNoLeak:
    """check_user_scope_svp_leak() must return None on every non-leak path."""

    def test_missing_file_returns_none(self, fake_home):
        assert not (fake_home / ".claude" / "settings.json").exists()
        assert check_user_scope_svp_leak() is None

    def test_missing_claude_dir_returns_none(self, fake_home):
        assert not (fake_home / ".claude").exists()
        assert check_user_scope_svp_leak() is None

    def test_empty_dict_returns_none(self, fake_home):
        _write_user_settings(fake_home, {})
        assert check_user_scope_svp_leak() is None

    def test_no_enabled_plugins_key_returns_none(self, fake_home):
        _write_user_settings(fake_home, {"theme": "dark", "effortLevel": "high"})
        assert check_user_scope_svp_leak() is None

    def test_empty_enabled_plugins_returns_none(self, fake_home):
        _write_user_settings(fake_home, {"enabledPlugins": {}})
        assert check_user_scope_svp_leak() is None

    def test_svp_set_to_false_returns_none(self, fake_home):
        _write_user_settings(fake_home, {"enabledPlugins": {"svp@svp": False}})
        assert check_user_scope_svp_leak() is None

    def test_svp_set_to_truthy_string_returns_none(self, fake_home):
        """Only the literal Python True triggers the advisory. Truthy
        strings ('true', '1') must NOT trigger — they are type errors,
        not enablement."""
        _write_user_settings(fake_home, {"enabledPlugins": {"svp@svp": "true"}})
        assert check_user_scope_svp_leak() is None

    def test_svp_set_to_one_returns_none(self, fake_home):
        """Integer 1 is truthy in Python but is not True-identical. The
        helper uses `is not True` so this case returns None."""
        _write_user_settings(fake_home, {"enabledPlugins": {"svp@svp": 1}})
        assert check_user_scope_svp_leak() is None

    def test_other_plugin_enabled_but_not_svp_returns_none(self, fake_home):
        _write_user_settings(
            fake_home,
            {"enabledPlugins": {"debrief@debrief": True, "svp@svp": False}},
        )
        assert check_user_scope_svp_leak() is None


class TestReturnsNoneOnCorruptInput:
    """check_user_scope_svp_leak() must never raise, regardless of file state."""

    def test_corrupt_json_returns_none(self, fake_home):
        _write_user_settings_raw(fake_home, "{not valid json")
        assert check_user_scope_svp_leak() is None

    def test_empty_file_returns_none(self, fake_home):
        _write_user_settings_raw(fake_home, "")
        assert check_user_scope_svp_leak() is None

    def test_root_is_list_returns_none(self, fake_home):
        _write_user_settings(fake_home, ["not", "a", "dict"])
        assert check_user_scope_svp_leak() is None

    def test_root_is_string_returns_none(self, fake_home):
        _write_user_settings(fake_home, "just a string")
        assert check_user_scope_svp_leak() is None

    def test_enabled_plugins_is_list_returns_none(self, fake_home):
        _write_user_settings(fake_home, {"enabledPlugins": ["svp@svp"]})
        assert check_user_scope_svp_leak() is None

    def test_enabled_plugins_is_string_returns_none(self, fake_home):
        _write_user_settings(fake_home, {"enabledPlugins": "svp@svp"})
        assert check_user_scope_svp_leak() is None


# ---------------------------------------------------------------------------
# Positive case: return advisory string
# ---------------------------------------------------------------------------


class TestReturnsAdvisoryWhenLeaked:
    """check_user_scope_svp_leak() must return a well-formed advisory
    when enabledPlugins['svp@svp'] is literally True."""

    def test_svp_enabled_returns_string(self, fake_home):
        _write_user_settings(fake_home, {"enabledPlugins": {"svp@svp": True}})
        msg = check_user_scope_svp_leak()
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_advisory_mentions_plugin_identifier(self, fake_home):
        _write_user_settings(fake_home, {"enabledPlugins": {"svp@svp": True}})
        msg = check_user_scope_svp_leak()
        assert "svp@svp" in msg, (
            "Advisory must cite the plugin identifier so the user can grep "
            "their settings file to find the entry."
        )

    def test_advisory_mentions_user_scope(self, fake_home):
        _write_user_settings(fake_home, {"enabledPlugins": {"svp@svp": True}})
        msg = check_user_scope_svp_leak()
        assert "user scope" in msg, (
            "Advisory must state 'user scope' so the user understands why "
            "the plugin is leaking into unrelated directories."
        )

    def test_advisory_references_migration_command(self, fake_home):
        _write_user_settings(fake_home, {"enabledPlugins": {"svp@svp": True}})
        msg = check_user_scope_svp_leak()
        assert "claude plugin uninstall svp@svp --scope user" in msg, (
            "Advisory must give the exact CLI command to fix the leak. "
            "Instructions without concrete commands don't get followed."
        )

    def test_advisory_cites_spec_section(self, fake_home):
        _write_user_settings(fake_home, {"enabledPlugins": {"svp@svp": True}})
        msg = check_user_scope_svp_leak()
        assert "§4.4" in msg, (
            "Advisory must cite spec §4.4 so a motivated user can read the "
            "full migration story and understand the invariant."
        )

    def test_advisory_preserved_when_other_plugins_also_enabled(self, fake_home):
        _write_user_settings(
            fake_home,
            {
                "enabledPlugins": {
                    "svp@svp": True,
                    "debrief@debrief": True,
                    "other@other": False,
                }
            },
        )
        msg = check_user_scope_svp_leak()
        assert msg is not None
        assert "svp@svp" in msg


# ---------------------------------------------------------------------------
# Preflight integration
# ---------------------------------------------------------------------------


class TestPreflightIntegration:
    """preflight_check() must print the advisory when the leak is present,
    AND must not fail preflight solely because of the leak (advisory-only)."""

    def test_preflight_prints_advisory_marker_when_leak(self, fake_home, capsys):
        _write_user_settings(fake_home, {"enabledPlugins": {"svp@svp": True}})
        preflight_check(verbose=True)
        captured = capsys.readouterr()
        assert "svp@svp" in captured.out, (
            "Preflight must print the leak advisory to stdout when verbose=True"
        )
        # The advisory is printed with the `!` marker prefix (matches the
        # existing advisory pattern used by the API-credentials check).
        assert "!" in captured.out

    def test_preflight_silent_when_no_leak(self, fake_home, capsys):
        """When there's no leak, preflight must not print anything containing
        'svp@svp' in an advisory context. (The plugin-loaded check may print
        'SVP plugin loaded' but that doesn't include '@'.)"""
        _write_user_settings(fake_home, {"enabledPlugins": {}})
        preflight_check(verbose=True)
        captured = capsys.readouterr()
        assert "svp@svp" not in captured.out

    def test_preflight_silent_when_settings_missing(self, fake_home, capsys):
        """No settings file on this machine → no advisory."""
        preflight_check(verbose=True)
        captured = capsys.readouterr()
        assert "svp@svp" not in captured.out

    def test_preflight_advisory_does_not_add_error(self, fake_home):
        """The leak advisory must NOT be appended to the errors list.
        Preflight's pass/fail decision depends on errors only."""
        _write_user_settings(fake_home, {"enabledPlugins": {"svp@svp": True}})
        errors_leaked = preflight_check(verbose=False)

        # Now clear the leak and re-run. The errors list must be identical
        # (or at least contain no reference to svp@svp or "user scope").
        _write_user_settings(fake_home, {"enabledPlugins": {}})
        errors_clean = preflight_check(verbose=False)

        leak_related = [e for e in errors_leaked if e not in errors_clean]
        assert not any("svp@svp" in e for e in leak_related), (
            "Leak state must not introduce errors — advisory only."
        )
        assert not any("user scope" in e for e in leak_related), (
            "Leak state must not introduce errors — advisory only."
        )

    def test_preflight_corrupt_user_settings_does_not_crash(self, fake_home):
        """A corrupt user settings file must not crash preflight."""
        _write_user_settings_raw(fake_home, "{not valid json")
        # Should not raise.
        preflight_check(verbose=False)
