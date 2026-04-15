"""Regression tests for Bug S3-123: Plugin Activation Leaks at User Scope.

SVP shipped with no mechanism for writing project-scoped plugin enablement,
so activation relied on ~/.claude/settings.json (user scope). Result:
SVP loaded in every Claude Code session on the machine regardless of cwd.

The fix adds `ensure_project_settings(project_root, plugin_root)` to the
launcher (Unit 29), which writes <project_root>/.claude/settings.json with
the SVP marketplace registration and plugin enablement keys. The helper is
idempotent, non-destructive, self-healing, corrupt-JSON-recoverable, and
writes atomically. It is called from all four launcher entry points
(svp new, svp resume, svp restore, and `_bootstrap_oracle_nested_session`
in the routing module).

This file locks all six properties of the helper plus the four call sites
via AST checks. Modeled on debrief's BUG-AUDIT-8 13-test suite.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

# S3-103 discipline: import from the derived `svp_launcher` module (script),
# not from `src.unit_29.stub`. Unit 29 is on the _NON_SCRIPT_UNITS allowlist
# only for specific tests — the regression tests import from scripts/.
from svp_launcher import ensure_project_settings


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """A clean temp project directory with no pre-existing .claude/."""
    return tmp_path / "pipeline_project"


@pytest.fixture
def plugin_root(tmp_path: Path) -> Path:
    """A mock plugin root directory at <marketplace>/svp/.

    The marketplace root (plugin_root.parent) is what ensure_project_settings
    will store in extraKnownMarketplaces.svp.source.path.

    Bug S3-127 enforces that the marketplace root contains a real
    ``.claude-plugin/marketplace.json`` listing an ``svp`` plugin. The
    fixture now creates that file so the S3-123 helper can locate the
    marketplace via its fast path (``plugin_root.parent``). Without this,
    the post-S3-127 helper would walk up from ``__file__`` or raise
    ``FileNotFoundError`` — neither of which is what these tests intend.
    """
    marketplace_root = tmp_path / "svp_marketplace_repo"
    marketplace_root.mkdir(parents=True)
    # S3-127: real marketplace.json advertising the svp plugin.
    marketplace_dot_plugin = marketplace_root / ".claude-plugin"
    marketplace_dot_plugin.mkdir()
    (marketplace_dot_plugin / "marketplace.json").write_text(
        json.dumps({
            "name": "svp",
            "plugins": [
                {"name": "svp", "source": "./svp", "version": "2.2.0"}
            ],
        })
    )
    plugin_dir = marketplace_root / "svp"
    plugin_dir.mkdir()
    return plugin_dir


def _read_settings(project_root: Path) -> dict:
    """Read and parse the settings.json from project_root/.claude/."""
    settings_path = project_root / ".claude" / "settings.json"
    assert settings_path.is_file(), f"settings.json missing at {settings_path}"
    return json.loads(settings_path.read_text())


# ---------------------------------------------------------------------------
# Correctness
# ---------------------------------------------------------------------------


class TestCorrectness:
    """ensure_project_settings writes the expected keys (Bug S3-123)."""

    def test_creates_settings_file_in_dot_claude(self, project_root, plugin_root):
        """Creates <project_root>/.claude/settings.json."""
        ensure_project_settings(project_root, plugin_root)
        settings_path = project_root / ".claude" / "settings.json"
        assert settings_path.is_file()

    def test_creates_dot_claude_directory_if_missing(
        self, project_root, plugin_root
    ):
        """Parent .claude/ directory is created if it does not exist."""
        assert not (project_root / ".claude").exists()
        ensure_project_settings(project_root, plugin_root)
        assert (project_root / ".claude").is_dir()

    def test_enabled_plugins_set(self, project_root, plugin_root):
        """enabledPlugins['svp@svp'] == True."""
        ensure_project_settings(project_root, plugin_root)
        data = _read_settings(project_root)
        assert data["enabledPlugins"]["svp@svp"] is True

    def test_marketplace_registration(self, project_root, plugin_root):
        """extraKnownMarketplaces.svp.source.path == plugin_root.parent resolved."""
        ensure_project_settings(project_root, plugin_root)
        data = _read_settings(project_root)
        source = data["extraKnownMarketplaces"]["svp"]["source"]
        assert source["source"] == "directory"
        assert source["path"] == str(plugin_root.parent.resolve())

    def test_marketplace_path_is_absolute(self, project_root, plugin_root):
        """The marketplace path is always absolute (from .resolve())."""
        ensure_project_settings(project_root, plugin_root)
        data = _read_settings(project_root)
        path = data["extraKnownMarketplaces"]["svp"]["source"]["path"]
        assert Path(path).is_absolute()


# ---------------------------------------------------------------------------
# Idempotency and self-heal
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Re-running produces identical output (Bug S3-123)."""

    def test_rerun_byte_equal(self, project_root, plugin_root):
        """Calling twice with same args produces byte-equal output."""
        ensure_project_settings(project_root, plugin_root)
        first = (project_root / ".claude" / "settings.json").read_bytes()
        ensure_project_settings(project_root, plugin_root)
        second = (project_root / ".claude" / "settings.json").read_bytes()
        assert first == second

    def test_rerun_preserves_unrelated_keys(self, project_root, plugin_root):
        """Re-running preserves keys added to settings.json between calls."""
        ensure_project_settings(project_root, plugin_root)
        # User manually adds an unrelated key between launcher runs
        data = _read_settings(project_root)
        data["theme"] = "dark"
        data["effortLevel"] = "high"
        (project_root / ".claude" / "settings.json").write_text(
            json.dumps(data, indent=2)
        )
        # Re-run: the helper must not touch the unrelated keys
        ensure_project_settings(project_root, plugin_root)
        reread = _read_settings(project_root)
        assert reread["theme"] == "dark"
        assert reread["effortLevel"] == "high"


class TestSelfHeal:
    """Stale marketplace paths are rewritten on re-run (Bug S3-123)."""

    def test_stale_path_rewritten(self, project_root, plugin_root, tmp_path):
        """If the marketplace path is stale, re-run rewrites it to the new one."""
        # Simulate a stale pre-existing settings file with an old path
        stale_path = str(tmp_path / "old_location" / "svp_repo")
        settings_dir = project_root / ".claude"
        settings_dir.mkdir(parents=True)
        (settings_dir / "settings.json").write_text(
            json.dumps(
                {
                    "enabledPlugins": {"svp@svp": True},
                    "extraKnownMarketplaces": {
                        "svp": {
                            "source": {
                                "source": "directory",
                                "path": stale_path,
                            }
                        }
                    },
                },
                indent=2,
            )
        )
        ensure_project_settings(project_root, plugin_root)
        data = _read_settings(project_root)
        new_path = data["extraKnownMarketplaces"]["svp"]["source"]["path"]
        assert new_path == str(plugin_root.parent.resolve())
        assert new_path != stale_path


# ---------------------------------------------------------------------------
# Non-destructive (preservation of unrelated keys)
# ---------------------------------------------------------------------------


class TestNonDestructive:
    """Only the two SVP-related keys are touched (Bug S3-123)."""

    def test_preserves_top_level_unrelated_keys(self, project_root, plugin_root):
        """Pre-existing top-level keys (theme, effortLevel, etc.) survive."""
        settings_dir = project_root / ".claude"
        settings_dir.mkdir(parents=True)
        (settings_dir / "settings.json").write_text(
            json.dumps(
                {
                    "theme": "dark",
                    "effortLevel": "high",
                    "skipDangerousModePermissionPrompt": True,
                    "customField": "userValue",
                },
                indent=2,
            )
        )
        ensure_project_settings(project_root, plugin_root)
        data = _read_settings(project_root)
        assert data["theme"] == "dark"
        assert data["effortLevel"] == "high"
        assert data["skipDangerousModePermissionPrompt"] is True
        assert data["customField"] == "userValue"

    def test_preserves_other_plugin_enablements(
        self, project_root, plugin_root
    ):
        """enabledPlugins entries for other plugins are preserved."""
        settings_dir = project_root / ".claude"
        settings_dir.mkdir(parents=True)
        (settings_dir / "settings.json").write_text(
            json.dumps(
                {
                    "enabledPlugins": {
                        "other@other": True,
                        "third_party@thing": False,
                    }
                },
                indent=2,
            )
        )
        ensure_project_settings(project_root, plugin_root)
        data = _read_settings(project_root)
        enabled = data["enabledPlugins"]
        assert enabled["other@other"] is True
        assert enabled["third_party@thing"] is False
        assert enabled["svp@svp"] is True  # our key added

    def test_preserves_other_marketplace_entries(
        self, project_root, plugin_root
    ):
        """extraKnownMarketplaces entries for other marketplaces are preserved."""
        settings_dir = project_root / ".claude"
        settings_dir.mkdir(parents=True)
        (settings_dir / "settings.json").write_text(
            json.dumps(
                {
                    "extraKnownMarketplaces": {
                        "debrief": {
                            "source": {
                                "source": "directory",
                                "path": "/some/debrief/path",
                            }
                        }
                    }
                },
                indent=2,
            )
        )
        ensure_project_settings(project_root, plugin_root)
        data = _read_settings(project_root)
        assert (
            data["extraKnownMarketplaces"]["debrief"]["source"]["path"]
            == "/some/debrief/path"
        )
        assert "svp" in data["extraKnownMarketplaces"]


# ---------------------------------------------------------------------------
# Corrupt JSON recovery
# ---------------------------------------------------------------------------


class TestCorruptJsonRecovery:
    """Corrupt pre-existing JSON is replaced with a fresh dict (Bug S3-123)."""

    def test_corrupt_json_does_not_raise(self, project_root, plugin_root):
        """Invalid JSON in the pre-existing file does not cause a crash."""
        settings_dir = project_root / ".claude"
        settings_dir.mkdir(parents=True)
        (settings_dir / "settings.json").write_text(
            "{this is not valid JSON at all ]]]}"
        )
        # Must not raise
        ensure_project_settings(project_root, plugin_root)

    def test_corrupt_json_replaced_with_fresh_data(
        self, project_root, plugin_root
    ):
        """After recovery, the file parses and has the expected keys."""
        settings_dir = project_root / ".claude"
        settings_dir.mkdir(parents=True)
        (settings_dir / "settings.json").write_text("{corrupt")
        ensure_project_settings(project_root, plugin_root)
        data = _read_settings(project_root)
        assert data["enabledPlugins"]["svp@svp"] is True
        assert "svp" in data["extraKnownMarketplaces"]

    def test_non_dict_root_recovered(self, project_root, plugin_root):
        """A JSON root that is not a dict (e.g., a list) is recovered to empty dict."""
        settings_dir = project_root / ".claude"
        settings_dir.mkdir(parents=True)
        (settings_dir / "settings.json").write_text('["not a dict"]')
        ensure_project_settings(project_root, plugin_root)
        data = _read_settings(project_root)
        assert data["enabledPlugins"]["svp@svp"] is True


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


class TestAtomicWrite:
    """Uses .tmp + replace pattern (Bug S3-123)."""

    def test_no_tmp_file_left_behind(self, project_root, plugin_root):
        """After a successful run, settings.json.tmp is not left on disk."""
        ensure_project_settings(project_root, plugin_root)
        tmp_file = project_root / ".claude" / "settings.json.tmp"
        assert not tmp_file.exists(), (
            f"Temporary file {tmp_file} was not renamed/cleaned up. "
            "Atomic write must use .tmp + Path.replace()."
        )

    def test_source_uses_replace(self):
        """Unit 29's ensure_project_settings source uses Path.replace() atomically."""
        import svp_launcher

        src = Path(svp_launcher.__file__).read_text()
        # Must contain an atomic rename pattern
        assert ".replace(" in src and "ensure_project_settings" in src, (
            "ensure_project_settings source must use Path.replace() for "
            "atomic write"
        )


# ---------------------------------------------------------------------------
# No subprocess invocation
# ---------------------------------------------------------------------------


class TestNoSubprocess:
    """ensure_project_settings does not shell out (Bug S3-123)."""

    def test_source_does_not_call_subprocess(self):
        """AST check: ensure_project_settings does not call subprocess.*."""
        import svp_launcher

        src = Path(svp_launcher.__file__).read_text()
        tree = ast.parse(src)

        # Find the ensure_project_settings function
        func_node = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "ensure_project_settings"
            ):
                func_node = node
                break
        assert func_node is not None, "ensure_project_settings not found in module"

        # Walk the function body and assert no subprocess.* call
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call) and isinstance(
                node.func, ast.Attribute
            ):
                value = node.func.value
                if isinstance(value, ast.Name) and value.id == "subprocess":
                    raise AssertionError(
                        f"ensure_project_settings calls subprocess.{node.func.attr} "
                        f"at line {node.lineno}. The install command is a user "
                        f"migration step, not a runtime dependency."
                    )


# ---------------------------------------------------------------------------
# Marketplace root computation
# ---------------------------------------------------------------------------


class TestMarketplaceRootComputation:
    """plugin_root.parent is the marketplace root (Bug S3-123)."""

    def test_plugin_inner_dir_resolved_to_parent(
        self, project_root, plugin_root
    ):
        """Given plugin_root = repo/svp/, marketplace root is repo/."""
        ensure_project_settings(project_root, plugin_root)
        data = _read_settings(project_root)
        path = Path(data["extraKnownMarketplaces"]["svp"]["source"]["path"])
        assert path == plugin_root.parent.resolve()
        # And the parent should NOT be the plugin_root itself
        assert path != plugin_root.resolve()


# ---------------------------------------------------------------------------
# AST checks — all four call sites exist
# ---------------------------------------------------------------------------


class TestCallSites:
    """All four launcher entry points call ensure_project_settings (Bug S3-123)."""

    def _load_launcher_source(self) -> str:
        import svp_launcher

        return Path(svp_launcher.__file__).read_text()

    def _load_routing_source(self) -> str:
        import routing

        return Path(routing.__file__).read_text()

    def _find_main_function(self, src: str) -> ast.FunctionDef:
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                return node
        raise AssertionError("main() not found in svp_launcher")

    def test_new_branch_calls_ensure_project_settings(self):
        """The `new` branch in main() calls ensure_project_settings."""
        src = self._load_launcher_source()
        # Regex-level check: find the `new` branch block and assert the call
        # is present within it. A more rigorous AST walker would be nicer but
        # this is sufficient as a regression guard.
        new_block = re.search(
            r'args\.command\s*==\s*"new".*?elif\s+args\.command',
            src,
            re.DOTALL,
        )
        assert new_block, "Could not locate the `new` command branch"
        assert "ensure_project_settings" in new_block.group(0), (
            "`new` command branch in main() must call ensure_project_settings"
        )

    def test_resume_branch_calls_ensure_project_settings(self):
        """The `resume` branch in main() calls ensure_project_settings."""
        src = self._load_launcher_source()
        resume_block = re.search(
            r'args\.command\s*==\s*"resume".*?elif\s+args\.command',
            src,
            re.DOTALL,
        )
        assert resume_block, "Could not locate the `resume` command branch"
        assert "ensure_project_settings" in resume_block.group(0), (
            "`resume` command branch in main() must call ensure_project_settings"
        )

    def test_restore_branch_calls_ensure_project_settings(self):
        """The `restore` branch in main() calls ensure_project_settings."""
        src = self._load_launcher_source()
        # The restore branch is the last elif and runs to end-of-function
        restore_idx = src.find('args.command == "restore"')
        assert restore_idx >= 0, "Could not locate the `restore` command branch"
        restore_tail = src[restore_idx:]
        assert "ensure_project_settings" in restore_tail, (
            "`restore` command branch in main() must call ensure_project_settings"
        )

    def test_bootstrap_oracle_nested_calls_ensure_project_settings(self):
        """routing.py _bootstrap_oracle_nested_session calls ensure_project_settings."""
        src = self._load_routing_source()
        tree = ast.parse(src)
        func_node = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_bootstrap_oracle_nested_session"
            ):
                func_node = node
                break
        assert func_node is not None, (
            "_bootstrap_oracle_nested_session not found in routing.py"
        )

        # Walk the function body looking for a call to ensure_project_settings
        found = False
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "ensure_project_settings":
                    found = True
                    break
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "ensure_project_settings"
                ):
                    found = True
                    break
        assert found, (
            "_bootstrap_oracle_nested_session must call ensure_project_settings "
            "so oracle nested sessions load SVP via project-scoped enablement "
            "(Bug S3-123)"
        )


# ---------------------------------------------------------------------------
# Integration: full-cycle temp directory fixture
# ---------------------------------------------------------------------------


class TestIntegration:
    """Full-cycle fixture test (Bug S3-123)."""

    def test_full_cycle(self, tmp_path):
        """Create a fresh project dir, run the helper, verify all invariants."""
        proj = tmp_path / "pipeline"
        plugin = tmp_path / "svp_repo" / "svp"
        plugin.mkdir(parents=True)
        # S3-127: real marketplace.json so the fast path in
        # _find_marketplace_root(plugin.parent) succeeds.
        mp_dir = plugin.parent / ".claude-plugin"
        mp_dir.mkdir()
        (mp_dir / "marketplace.json").write_text(
            json.dumps({"name": "svp", "plugins": [{"name": "svp", "source": "./svp"}]})
        )

        ensure_project_settings(proj, plugin)

        # File exists
        settings_path = proj / ".claude" / "settings.json"
        assert settings_path.is_file()

        # File is valid JSON
        data = json.loads(settings_path.read_text())

        # Has both expected top-level keys
        assert "enabledPlugins" in data
        assert "extraKnownMarketplaces" in data

        # enabledPlugins has svp@svp True
        assert data["enabledPlugins"]["svp@svp"] is True

        # Marketplace path is absolute and points at plugin.parent
        mp_path = data["extraKnownMarketplaces"]["svp"]["source"]["path"]
        assert Path(mp_path).is_absolute()
        assert Path(mp_path) == plugin.parent.resolve()

        # No .tmp file left behind
        assert not (proj / ".claude" / "settings.json.tmp").exists()

        # Re-run is idempotent
        first = settings_path.read_bytes()
        ensure_project_settings(proj, plugin)
        second = settings_path.read_bytes()
        assert first == second
