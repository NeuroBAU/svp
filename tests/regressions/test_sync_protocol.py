"""Sync protocol verification tests (Bug S3-103).

Validates the one-way sync protocol, repo layout consolidation,
flat module import standardization, and sync config infrastructure.
"""
import json
import re
from pathlib import Path

# Paths relative to workspace/repo root
_ROOT = Path(__file__).parent.parent.parent
_SYNC_CONFIG = _ROOT / ".svp" / "sync_config.json"


def _load_sync_config():
    """Load sync config, return dict or None."""
    if _SYNC_CONFIG.exists():
        return json.loads(_SYNC_CONFIG.read_text())
    return None


def _get_repo_path():
    """Get repo path from sync config or fallback."""
    config = _load_sync_config()
    if config and "repo" in config:
        return Path(config["repo"])
    # Fallback for backward compatibility
    return _ROOT.parent / "svp2.2-pass2-repo"


# --- Sync Config Tests ---


class TestSyncConfig:
    """Sync config must exist and be valid."""

    def test_sync_config_exists(self):
        """S3-103: .svp/sync_config.json must exist in workspace (not repo)."""
        # Only check if we're running from a workspace (has specs/ directory)
        if not (_ROOT / "specs").is_dir():
            return  # Running from repo — sync_config is a workspace artifact
        assert _SYNC_CONFIG.exists(), (
            ".svp/sync_config.json missing — run restore_project or create manually"
        )

    def test_sync_config_valid_json(self):
        """S3-103: sync_config.json must be valid JSON."""
        if not _SYNC_CONFIG.exists():
            return  # covered by test above
        config = json.loads(_SYNC_CONFIG.read_text())
        assert isinstance(config, dict), "sync_config.json must be a JSON object"

    def test_sync_config_has_repo_path(self):
        """S3-103: sync_config must contain 'repo' key."""
        config = _load_sync_config()
        if config is None:
            return
        assert "repo" in config, "sync_config.json missing 'repo' key"

    def test_sync_config_repo_exists(self):
        """S3-103: repo path in sync_config must exist on disk."""
        config = _load_sync_config()
        if config is None or "repo" not in config:
            return
        repo = Path(config["repo"])
        assert repo.is_dir(), f"Repo path does not exist: {repo}"


# --- Repo Layout Tests ---


class TestRepoLayout:
    """Repo must have consolidated docs/ layout."""

    def test_no_scattered_specs_dir(self):
        """S3-103: repo must not have specs/ at root."""
        repo = _get_repo_path()
        assert not (repo / "specs").is_dir(), "Repo has specs/ — should be in docs/"

    def test_no_scattered_blueprint_dir(self):
        """S3-103: repo must not have blueprint/ at root."""
        repo = _get_repo_path()
        assert not (repo / "blueprint").is_dir(), "Repo has blueprint/ — should be in docs/"

    def test_no_scattered_references_dir(self):
        """S3-103: repo must not have references/ at root."""
        repo = _get_repo_path()
        assert not (repo / "references").is_dir(), "Repo has references/ — should be in docs/"

    def test_no_claude_md_at_repo_root(self):
        """S3-103: CLAUDE.md must not be at repo root (should be in docs/)."""
        repo = _get_repo_path()
        assert not (repo / "CLAUDE.md").is_file(), "CLAUDE.md at repo root — should be in docs/"

    def test_no_project_context_at_repo_root(self):
        """S3-103: project_context.md must not be at repo root (should be in docs/)."""
        repo = _get_repo_path()
        assert not (repo / "project_context.md").is_file(), (
            "project_context.md at repo root — should be in docs/"
        )

    def test_no_blueprint_contracts_at_repo_root(self):
        """S3-103: blueprint_contracts.md must not be at repo root."""
        repo = _get_repo_path()
        assert not (repo / "blueprint_contracts.md").is_file(), (
            "blueprint_contracts.md at repo root — should be in docs/"
        )


# --- Cross-Repo Consistency Tests ---


class TestCrossRepoConsistency:
    """Workspace docs must match repo docs/."""

    def test_spec_matches(self):
        """S3-103: workspace spec matches repo docs/."""
        repo = _get_repo_path()
        ws_spec = _ROOT / "specs" / "stakeholder_spec.md"
        repo_spec = repo / "docs" / "stakeholder_spec.md"
        if ws_spec.exists() and repo_spec.exists():
            assert ws_spec.read_text() == repo_spec.read_text(), "Spec out of sync"

    def test_blueprint_contracts_matches(self):
        """S3-103: workspace blueprint contracts matches repo docs/."""
        repo = _get_repo_path()
        ws = _ROOT / "blueprint" / "blueprint_contracts.md"
        repo_f = repo / "docs" / "blueprint_contracts.md"
        if ws.exists() and repo_f.exists():
            assert ws.read_text() == repo_f.read_text(), "Blueprint contracts out of sync"

    def test_lessons_learned_matches(self):
        """S3-103: workspace lessons learned matches repo docs/references/."""
        repo = _get_repo_path()
        ws = _ROOT / "references" / "svp_2_1_lessons_learned.md"
        repo_f = repo / "docs" / "references" / "svp_2_1_lessons_learned.md"
        if ws.exists() and repo_f.exists():
            assert ws.read_text() == repo_f.read_text(), "Lessons learned out of sync"

    def test_claude_md_matches(self):
        """S3-103: workspace CLAUDE.md matches repo docs/CLAUDE.md."""
        repo = _get_repo_path()
        ws = _ROOT / "CLAUDE.md"
        repo_f = repo / "docs" / "CLAUDE.md"
        if ws.exists() and repo_f.exists():
            assert ws.read_text() == repo_f.read_text(), "CLAUDE.md out of sync"

    def test_project_context_matches(self):
        """S3-103: workspace project_context.md matches repo docs/project_context.md."""
        repo = _get_repo_path()
        ws = _ROOT / "project_context.md"
        repo_f = repo / "docs" / "project_context.md"
        if ws.exists() and repo_f.exists():
            assert ws.read_text() == repo_f.read_text(), "project_context.md out of sync"


# --- Test Import Standardization Tests ---


class TestFlatImports:
    """All tests must use flat module imports, not stub imports."""

    def test_no_stub_imports_in_tests(self):
        """S3-103: no test file should import from src.unit_N.stub."""
        test_dir = _ROOT / "tests"
        violations = []
        for py_file in test_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            content = py_file.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                # Skip comments, docstrings, and string literals
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                    continue
                if re.match(r'\s*from src\.unit_\d+\.stub import', line):
                    violations.append(f"{py_file.name}:{i}: {stripped}")
                elif re.match(r'\s*from src\.unit_\d+ import stub', line):
                    violations.append(f"{py_file.name}:{i}: {stripped}")
        assert not violations, (
            f"Found {len(violations)} stub import(s) in tests:\n"
            + "\n".join(violations[:10])
        )

    def test_test_agent_definition_uses_flat_imports(self):
        """S3-103: TEST_AGENT_DEFINITION P3 must reference flat module imports."""
        from construction_agents import TEST_AGENT_DEFINITION
        assert "flat module import" in TEST_AGENT_DEFINITION.lower() or \
               "from module_name import" in TEST_AGENT_DEFINITION, (
            "TEST_AGENT_DEFINITION P3 must reference flat module imports, not stub imports"
        )
        # P3 must say "Always use flat module imports", not "Always use src. prefix"
        assert "Always use src. prefix" not in TEST_AGENT_DEFINITION, (
            "TEST_AGENT_DEFINITION P3 still recommends stub imports — should recommend flat modules"
        )
