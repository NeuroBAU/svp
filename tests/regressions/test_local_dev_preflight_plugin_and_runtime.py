"""Regression tests for the local-dev / profile-function ``svp new`` preflight.

Two defects made ``svp new <project>`` fail with "2 pre-flight error(s).
Cannot continue." when SVP was activated via the documented no-pip
profile-function method (``setup_svp_user.ps1``) and run from a freshly
opened shell:

  1. **Plugin not found.** ``_find_plugin_root()`` searched only
     ``SVP_PLUGIN_ROOT`` and standard *install* locations. The
     profile-function install sets ``SVP_PLUGIN_ROOT`` at User scope, but a
     User-scope env var only loads in *new* shells -- so the shell that just
     ran the setup script (or any shell where the var has not propagated)
     reported "SVP plugin loaded -- not found in any standard location",
     even though the launcher itself was executing from inside the plugin.
     Fix: ``_find_plugin_root()`` now also derives the plugin root from the
     launcher's own on-disk location (``__file__``), mirroring the
     ``__file__`` walk-up ``_find_marketplace_root()`` already relies on.

  2. **Optional language runtime treated as required.** The language-runtime
     pre-flight iterated the entire ``LANGUAGE_REGISTRY`` and hard-failed when
     *any* runtime was missing, so a Python-only user with no R installed was
     blocked by "R runtime -- 'Rscript --version' not available". The spec
     says this check runs "for each *declared* language", but at ``svp new``
     time no language is declared (the profile is chosen later inside the SVP
     session). Fix: when ``declared_languages`` is None the check is advisory;
     when languages are declared, a missing runtime for a declared language is
     still a hard error.

This file locks both invariants via black-box tests against the derived
``svp_launcher`` module (S3-103 stub-import discipline).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

# S3-103 discipline: import from the derived `svp_launcher` module (script),
# not from `src.unit_29.stub`.
import svp_launcher
from svp_launcher import _find_plugin_root, preflight_check


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Strip the SVP env vars so tests start from a known baseline."""
    monkeypatch.delenv("SVP_MARKETPLACE_ROOT", raising=False)
    monkeypatch.delenv("SVP_PLUGIN_ROOT", raising=False)
    yield


# ---------------------------------------------------------------------------
# Bug 1: plugin discovered from the launcher's own __file__ location
# ---------------------------------------------------------------------------


class TestPluginDiscoveryFromLauncherLocation:
    """``_find_plugin_root()`` must resolve the plugin from the launcher's own
    on-disk location when ``SVP_PLUGIN_ROOT`` is unset and no standard install
    location contains the plugin."""

    def _make_source_checkout(self, root: Path) -> Path:
        """Create ``<root>/svp/`` with a valid plugin manifest and a
        ``scripts/svp_launcher.py`` (the launcher lives one level below the
        plugin root). Returns the plugin root (``<root>/svp``)."""
        plugin_root = root / "svp"
        (plugin_root / ".claude-plugin").mkdir(parents=True)
        (plugin_root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "svp", "version": "2.2.0"})
        )
        scripts = plugin_root / "scripts"
        scripts.mkdir()
        launcher = scripts / "svp_launcher.py"
        launcher.write_text("")
        return plugin_root

    def test_resolves_plugin_from_file_location(self, tmp_path, monkeypatch):
        plugin_root = self._make_source_checkout(tmp_path)

        # Launcher executes from inside the checkout; no env var, and no
        # standard install location contains the plugin.
        monkeypatch.setattr(
            svp_launcher, "__file__",
            str(plugin_root / "scripts" / "svp_launcher.py"),
        )
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "empty_home")
        monkeypatch.setattr(svp_launcher, "_get_plugin_search_locations",
                            lambda: [])

        resolved = _find_plugin_root()
        assert resolved.resolve() == plugin_root.resolve()

    def test_preflight_reports_plugin_loaded(self, tmp_path, monkeypatch):
        """The whole point: preflight must NOT emit a 'plugin' error when the
        launcher runs from a valid checkout with no env var set."""
        plugin_root = self._make_source_checkout(tmp_path)
        monkeypatch.setattr(
            svp_launcher, "__file__",
            str(plugin_root / "scripts" / "svp_launcher.py"),
        )
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "empty_home")
        monkeypatch.setattr(svp_launcher, "_get_plugin_search_locations",
                            lambda: [])

        errors = preflight_check(verbose=False)
        plugin_errors = [e for e in errors if "plugin" in e.lower()]
        assert plugin_errors == []


# ---------------------------------------------------------------------------
# Bug 2: undeclared language runtimes are advisory, declared ones are required
# ---------------------------------------------------------------------------


def _rscript_missing(*args, **kwargs):
    """subprocess.run stand-in: Rscript is absent, everything else succeeds."""
    cmd = args[0] if args else kwargs.get("args")
    argv = cmd if isinstance(cmd, (list, tuple)) else str(cmd).split()
    if argv and "Rscript" in argv[0]:
        raise FileNotFoundError("Rscript not found")
    return subprocess.CompletedProcess(argv, 0, b"", b"")


class TestOptionalLanguageRuntime:
    """A missing runtime for a not-yet-declared language must not fail
    preflight; a missing runtime for a *declared* language must."""

    def test_missing_r_is_advisory_when_nothing_declared(self, monkeypatch):
        with patch("subprocess.run", side_effect=_rscript_missing):
            errors = preflight_check(verbose=False, declared_languages=None)
        r_errors = [e for e in errors if "R runtime" in e]
        assert r_errors == [], (
            "Missing R must be advisory at `svp new` time, not a hard error"
        )

    def test_missing_r_is_error_when_r_declared(self, monkeypatch):
        with patch("subprocess.run", side_effect=_rscript_missing):
            errors = preflight_check(verbose=False, declared_languages=["r"])
        r_errors = [e for e in errors if "R runtime" in e]
        assert len(r_errors) == 1, (
            "A declared language whose runtime is missing must fail preflight"
        )
