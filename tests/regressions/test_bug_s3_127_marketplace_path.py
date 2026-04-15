"""Regression tests for Bug S3-127: ensure_project_settings wrote a
cache-parent path that has no marketplace.json.

After the S3-123 migration to project-scope activation, starting Claude Code
from an SVP pipeline directory crashed at plugin load time with:

    Marketplace file not found at
    /Users/<user>/.claude/plugins/cache/svp/svp/.claude-plugin/marketplace.json

Root cause: _find_plugin_root() returned the Claude Code plugin cache copy
(~/.claude/plugins/cache/svp/svp/<version>/) and ensure_project_settings()
computed marketplace_root = plugin_root.parent.resolve() — but the cache
parent (~/.claude/plugins/cache/svp/svp/) contains no marketplace.json.
The assumption "plugin's parent is the marketplace root" holds for source
repo layouts but is false for Claude Code's plugin cache layout.

Fix: introduce _find_marketplace_root(plugin_root) which validates that the
returned directory actually contains .claude-plugin/marketplace.json listing
the svp plugin. ensure_project_settings() hard-fails with FileNotFoundError
if no valid marketplace root can be located, and widens self-healing to
rewrite any stored path whose target is missing marketplace.json.
_find_plugin_root() is made two-pass: first pass prefers candidates whose
parent is a valid marketplace root (source-repo installs over cache
snapshots); second pass falls back to the pre-S3-127 behavior.

This file locks all five invariants via black-box tests against the derived
svp_launcher module (S3-103 stub-import discipline).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

# S3-103 discipline: import from the derived `svp_launcher` module (script),
# not from `src.unit_29.stub`.
from svp_launcher import (
    _find_marketplace_root,
    _find_plugin_root,
    _is_valid_marketplace_dir,
    ensure_project_settings,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plugin_dir(parent: Path, with_marketplace: bool = False) -> Path:
    """Create a .claude-plugin/plugin.json under parent/svp/.

    If with_marketplace is True, also create parent/.claude-plugin/marketplace.json
    listing the svp plugin. This makes ``parent`` a valid marketplace root.
    """
    plugin_dir = parent / "svp"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / ".claude-plugin").mkdir()
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "svp", "version": "2.2.0"})
    )
    if with_marketplace:
        mp_dir = parent / ".claude-plugin"
        mp_dir.mkdir()
        (mp_dir / "marketplace.json").write_text(
            json.dumps({
                "name": "svp",
                "plugins": [{"name": "svp", "source": "./svp"}],
            })
        )
    return plugin_dir


def _make_cache_layout(cache_root: Path, version: str = "2.2.0") -> Path:
    """Create the exact Claude Code cache layout that triggered S3-127.

    Structure:
        <cache_root>/svp/svp/<version>/.claude-plugin/plugin.json

    No marketplace.json anywhere. Returns the innermost plugin dir.
    """
    plugin_dir = cache_root / "svp" / "svp" / version
    plugin_dir.mkdir(parents=True)
    (plugin_dir / ".claude-plugin").mkdir()
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "svp", "version": version})
    )
    return plugin_dir


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Strip SVP_MARKETPLACE_ROOT and SVP_PLUGIN_ROOT from the environment
    so tests start from a known baseline. Individual tests may re-set them.
    """
    monkeypatch.delenv("SVP_MARKETPLACE_ROOT", raising=False)
    monkeypatch.delenv("SVP_PLUGIN_ROOT", raising=False)
    yield


# ---------------------------------------------------------------------------
# Test 1: parent-with-no-marketplace must not be silently written
# ---------------------------------------------------------------------------


class TestRejectsParentWithoutMarketplace:
    """A plugin_root whose parent has no marketplace.json must NOT be silently
    written into extraKnownMarketplaces.svp.source.path (Bug S3-127)."""

    def test_hard_fails_when_no_marketplace_reachable(self, tmp_path, monkeypatch):
        """When neither plugin_root.parent nor the __file__ walk-up yields a
        valid marketplace, ensure_project_settings raises FileNotFoundError."""
        plugin_dir = _make_plugin_dir(tmp_path, with_marketplace=False)
        project = tmp_path / "pipeline"

        # Force the __file__ walk-up to also fail by patching _find_marketplace_root
        # to short-circuit step 3. The cleanest way is to patch the module-level
        # __file__ used by the launcher to a tmp location with no marketplace
        # anywhere in its ancestry.
        import svp_launcher
        isolated_file = tmp_path / "isolated_ancestry" / "svp_launcher.py"
        isolated_file.parent.mkdir()
        isolated_file.write_text("")
        monkeypatch.setattr(svp_launcher, "__file__", str(isolated_file))

        with pytest.raises(FileNotFoundError, match="marketplace"):
            ensure_project_settings(project, plugin_dir)

    def test_does_not_write_cache_parent_path(self, tmp_path, monkeypatch):
        """The settings file must NOT be written with the bare parent as path
        when that parent has no marketplace.json. Either the helper raises,
        or it discovers a valid root elsewhere — never silent corruption."""
        plugin_dir = _make_plugin_dir(tmp_path, with_marketplace=False)
        project = tmp_path / "pipeline"

        import svp_launcher
        isolated_file = tmp_path / "isolated_ancestry2" / "svp_launcher.py"
        isolated_file.parent.mkdir()
        isolated_file.write_text("")
        monkeypatch.setattr(svp_launcher, "__file__", str(isolated_file))

        with pytest.raises(FileNotFoundError):
            ensure_project_settings(project, plugin_dir)

        # Settings file must not exist, OR if it does, must not contain the
        # invalid parent path. The strict behavior is: no partial write on
        # failure. Tolerate either no file (strict) or no stale entry.
        settings_path = project / ".claude" / "settings.json"
        if settings_path.is_file():
            data = json.loads(settings_path.read_text())
            stored = (
                data.get("extraKnownMarketplaces", {})
                .get("svp", {})
                .get("source", {})
                .get("path")
            )
            assert stored != str(plugin_dir.parent.resolve()), (
                "Helper silently wrote a parent path that has no marketplace.json"
            )


# ---------------------------------------------------------------------------
# Test 2: exact cache layout is rejected
# ---------------------------------------------------------------------------


class TestCacheLayoutRejected:
    """Given the exact Claude Code cache layout that triggered S3-127, the
    helper must reject it rather than write the cache parent into settings."""

    def test_cache_layout_raises(self, tmp_path, monkeypatch):
        """cache/svp/svp/<version>/ plugin with no marketplace.json anywhere
        in the cache hierarchy must cause a FileNotFoundError."""
        cache_root = tmp_path / "cache_home"
        plugin_dir = _make_cache_layout(cache_root)
        assert plugin_dir.name == "2.2.0"
        assert not (plugin_dir.parent / ".claude-plugin" / "marketplace.json").exists()

        # Isolate __file__ so walk-up doesn't find an unrelated marketplace.
        import svp_launcher
        isolated_file = tmp_path / "isolated_cache" / "svp_launcher.py"
        isolated_file.parent.mkdir()
        isolated_file.write_text("")
        monkeypatch.setattr(svp_launcher, "__file__", str(isolated_file))

        project = tmp_path / "pipeline"
        with pytest.raises(FileNotFoundError):
            ensure_project_settings(project, plugin_dir)

    def test_find_marketplace_root_returns_none_for_cache_layout(
        self, tmp_path, monkeypatch
    ):
        """_find_marketplace_root must return None for a cache-layout
        plugin_root when no fallback is reachable."""
        cache_root = tmp_path / "cache_home"
        plugin_dir = _make_cache_layout(cache_root)

        import svp_launcher
        isolated_file = tmp_path / "isolated_cache2" / "svp_launcher.py"
        isolated_file.parent.mkdir()
        isolated_file.write_text("")
        monkeypatch.setattr(svp_launcher, "__file__", str(isolated_file))

        assert _find_marketplace_root(plugin_dir) is None


# ---------------------------------------------------------------------------
# Test 3: SVP_MARKETPLACE_ROOT env var honored
# ---------------------------------------------------------------------------


class TestEnvVarOverride:
    """SVP_MARKETPLACE_ROOT env var takes precedence over plugin_root.parent
    and over __file__ walk-up (Bug S3-127)."""

    def test_env_var_wins_over_parent(self, tmp_path, monkeypatch):
        """When both plugin_root.parent and SVP_MARKETPLACE_ROOT are valid
        marketplace dirs, the env var wins."""
        # plugin_root.parent IS a valid marketplace (normally would be used).
        repo_a = tmp_path / "repo_a"
        plugin_dir = _make_plugin_dir(repo_a, with_marketplace=True)

        # A different valid marketplace exists elsewhere.
        repo_b = tmp_path / "repo_b"
        _make_plugin_dir(repo_b, with_marketplace=True)

        monkeypatch.setenv("SVP_MARKETPLACE_ROOT", str(repo_b))
        project = tmp_path / "pipeline"
        ensure_project_settings(project, plugin_dir)

        data = json.loads((project / ".claude" / "settings.json").read_text())
        stored = data["extraKnownMarketplaces"]["svp"]["source"]["path"]
        assert stored == str(repo_b.resolve()), (
            f"Env var should win; got {stored}, expected {repo_b.resolve()}"
        )
        assert stored != str(repo_a.resolve())

    def test_env_var_set_but_invalid_raises(self, tmp_path, monkeypatch):
        """SVP_MARKETPLACE_ROOT set but pointing at a dir with no marketplace.json
        must raise — silent fallback would defeat the purpose of the env var."""
        bogus = tmp_path / "bogus_marketplace"
        bogus.mkdir()  # empty directory, no .claude-plugin/

        monkeypatch.setenv("SVP_MARKETPLACE_ROOT", str(bogus))
        plugin_dir = _make_plugin_dir(tmp_path / "repo", with_marketplace=True)

        with pytest.raises(FileNotFoundError, match="SVP_MARKETPLACE_ROOT"):
            _find_marketplace_root(plugin_dir)


# ---------------------------------------------------------------------------
# Test 4: self-heal rewrites stored path missing marketplace.json
# ---------------------------------------------------------------------------


class TestSelfHealMissingMarketplace:
    """A pre-existing settings.json whose extraKnownMarketplaces.svp.source.path
    points at a directory missing marketplace.json must be rewritten on the
    next ensure_project_settings call (Bug S3-127 widens S3-123's self-heal)."""

    def test_stale_cache_path_is_rewritten(self, tmp_path):
        """Pre-write a stale cache-parent path, then run the helper with a
        valid plugin_root. The stale path must be replaced with the valid one."""
        # Valid plugin_root with a real marketplace.
        repo = tmp_path / "svp_repo"
        plugin_dir = _make_plugin_dir(repo, with_marketplace=True)

        # Pre-existing stale settings pointing at a cache-parent-like path
        # that has no marketplace.json.
        project = tmp_path / "pipeline"
        settings_dir = project / ".claude"
        settings_dir.mkdir(parents=True)
        stale_cache_parent = tmp_path / "fake_cache" / "svp" / "svp"
        stale_cache_parent.mkdir(parents=True)
        assert not (stale_cache_parent / ".claude-plugin" / "marketplace.json").exists()

        (settings_dir / "settings.json").write_text(
            json.dumps({
                "enabledPlugins": {"svp@svp": True},
                "extraKnownMarketplaces": {
                    "svp": {
                        "source": {
                            "source": "directory",
                            "path": str(stale_cache_parent),
                        }
                    }
                },
            })
        )

        ensure_project_settings(project, plugin_dir)

        data = json.loads((settings_dir / "settings.json").read_text())
        new_path = data["extraKnownMarketplaces"]["svp"]["source"]["path"]
        assert new_path == str(repo.resolve())
        assert new_path != str(stale_cache_parent)


# ---------------------------------------------------------------------------
# Test 5: _find_plugin_root prefers source-repo over cache
# ---------------------------------------------------------------------------


class TestFindPluginRootPrefersSourceRepo:
    """When both a source-repo install (parent has marketplace.json) and a
    cache snapshot (parent has no marketplace.json) are discoverable,
    _find_plugin_root must return the source-repo candidate first pass
    (Bug S3-127)."""

    def test_source_repo_wins_over_cache(self, tmp_path, monkeypatch):
        """Set up two plugin candidates via a mocked search path; verify
        the source-repo one is returned by the first pass."""
        source_repo = tmp_path / "svp_source_repo"
        source_plugin = _make_plugin_dir(source_repo, with_marketplace=True)

        cache_root = tmp_path / "cache"
        cache_plugin = _make_cache_layout(cache_root)

        import svp_launcher

        # Mock _get_plugin_search_locations to return both plugin dirs as
        # plain (non-cache-marker) locations. The cache-marker branch in
        # _find_plugin_root only fires for the hardcoded ~/.claude path,
        # so injecting paths as plain locations bypasses it entirely.
        monkeypatch.setattr(
            svp_launcher,
            "_get_plugin_search_locations",
            lambda: [source_plugin, cache_plugin],
        )

        result = _find_plugin_root()
        assert result.resolve() == source_plugin.resolve(), (
            f"Expected source-repo plugin at {source_plugin}, got {result}. "
            "First-pass preference for marketplace-valid candidates is broken."
        )

    def test_cache_fallback_when_no_source_repo(self, tmp_path, monkeypatch):
        """When only a cache-layout candidate exists, _find_plugin_root still
        returns it (second-pass fallback). The downstream failure then happens
        in ensure_project_settings, not in _find_plugin_root."""
        cache_root = tmp_path / "cache"
        cache_plugin = _make_cache_layout(cache_root)

        import svp_launcher
        monkeypatch.setattr(
            svp_launcher,
            "_get_plugin_search_locations",
            lambda: [cache_plugin],
        )

        result = _find_plugin_root()
        assert result.resolve() == cache_plugin.resolve()


# ---------------------------------------------------------------------------
# Extra: _is_valid_marketplace_dir semantic check
# ---------------------------------------------------------------------------


class TestIsValidMarketplaceDir:
    """_is_valid_marketplace_dir enforces the three-part invariant:
    file exists, plugins array present, svp entry listed."""

    def test_missing_file_is_invalid(self, tmp_path):
        assert not _is_valid_marketplace_dir(tmp_path)

    def test_empty_plugins_array_is_invalid(self, tmp_path):
        mp = tmp_path / ".claude-plugin"
        mp.mkdir()
        (mp / "marketplace.json").write_text(json.dumps({"name": "svp", "plugins": []}))
        assert not _is_valid_marketplace_dir(tmp_path)

    def test_plugins_array_without_svp_is_invalid(self, tmp_path):
        mp = tmp_path / ".claude-plugin"
        mp.mkdir()
        (mp / "marketplace.json").write_text(
            json.dumps({"name": "other", "plugins": [{"name": "other"}]})
        )
        assert not _is_valid_marketplace_dir(tmp_path)

    def test_plugins_array_with_svp_is_valid(self, tmp_path):
        mp = tmp_path / ".claude-plugin"
        mp.mkdir()
        (mp / "marketplace.json").write_text(
            json.dumps({"name": "svp", "plugins": [{"name": "svp"}]})
        )
        assert _is_valid_marketplace_dir(tmp_path)

    def test_corrupt_json_is_invalid(self, tmp_path):
        mp = tmp_path / ".claude-plugin"
        mp.mkdir()
        (mp / "marketplace.json").write_text("{not valid json")
        assert not _is_valid_marketplace_dir(tmp_path)
