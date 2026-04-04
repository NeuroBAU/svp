"""Regression tests for Bug S3-83: E-mode bootstrap mode-blind.

_bootstrap_oracle_nested_session must copy test project artifacts in E-mode
(GoL) and SVP workspace artifacts in F-mode.
"""

from pathlib import Path

from routing import _bootstrap_oracle_nested_session, save_state
from pipeline_state import PipelineState


def _make_state(**overrides):
    defaults = {
        "stage": "5",
        "sub_stage": "pass_transition",
        "current_unit": None,
        "total_units": 29,
        "verified_units": [],
        "alignment_iterations": 0,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "primary_language": "python",
        "component_languages": [],
        "secondary_language": None,
        "oracle_session_active": True,
        "oracle_test_project": "docs/",
        "oracle_phase": "green_run",
        "oracle_run_count": 1,
        "oracle_nested_session_path": None,
        "oracle_modification_count": 0,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass_": 2,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _setup_svp_workspace(tmp_path):
    """Create a minimal SVP workspace with specs/, blueprint/, .svp/."""
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "stakeholder_spec.md").write_text("# SVP Spec")
    (tmp_path / "blueprint").mkdir()
    (tmp_path / "blueprint" / "blueprint_contracts.md").write_text("# SVP Blueprint")
    (tmp_path / "blueprint" / "blueprint_prose.md").write_text("# SVP Prose")
    (tmp_path / ".svp").mkdir()
    (tmp_path / ".svp" / "pipeline_state.json").write_text("{}")
    (tmp_path / "project_profile.json").write_text('{"archetype": "svp"}')
    (tmp_path / "project_context.md").write_text("SVP context")
    (tmp_path / "svp_config.json").write_text('{"iteration_limit": 3}')


def _setup_gol_test_project(tmp_path):
    """Create a GoL test project under examples/game-of-life/."""
    gol_dir = tmp_path / "examples" / "game-of-life"
    gol_dir.mkdir(parents=True)
    (gol_dir / "stakeholder_spec.md").write_text("# GoL Spec\nConway's Game of Life")
    (gol_dir / "blueprint_contracts.md").write_text("# GoL Blueprint Contracts")
    (gol_dir / "blueprint_prose.md").write_text("# GoL Blueprint Prose")
    (gol_dir / "project_context.md").write_text("GoL context")
    (gol_dir / "oracle_manifest.json").write_text('{"oracle_mode": "product"}')


class TestEmodeBootstrapArtifacts:
    """E-mode bootstrap must copy GoL artifacts, not SVP artifacts (Bug S3-83)."""

    def test_emode_copies_gol_spec(self, tmp_path):
        """E-mode nested session gets GoL spec, not SVP spec."""
        _setup_svp_workspace(tmp_path)
        _setup_gol_test_project(tmp_path)
        state = _make_state(oracle_test_project="examples/game-of-life/")
        new = _bootstrap_oracle_nested_session(state, tmp_path)
        nested = Path(new.oracle_nested_session_path)
        spec = (nested / "specs" / "stakeholder_spec.md").read_text()
        assert "GoL Spec" in spec, "E-mode should have GoL spec"
        assert "SVP Spec" not in spec, "E-mode should NOT have SVP spec"

    def test_emode_copies_gol_blueprint(self, tmp_path):
        """E-mode nested session gets GoL blueprint, not SVP blueprint."""
        _setup_svp_workspace(tmp_path)
        _setup_gol_test_project(tmp_path)
        state = _make_state(oracle_test_project="examples/game-of-life/")
        new = _bootstrap_oracle_nested_session(state, tmp_path)
        nested = Path(new.oracle_nested_session_path)
        bp = (nested / "blueprint" / "blueprint_contracts.md").read_text()
        assert "GoL Blueprint" in bp, "E-mode should have GoL blueprint"
        assert "SVP Blueprint" not in bp, "E-mode should NOT have SVP blueprint"

    def test_emode_copies_gol_context(self, tmp_path):
        """E-mode nested session gets GoL context."""
        _setup_svp_workspace(tmp_path)
        _setup_gol_test_project(tmp_path)
        state = _make_state(oracle_test_project="examples/game-of-life/")
        new = _bootstrap_oracle_nested_session(state, tmp_path)
        nested = Path(new.oracle_nested_session_path)
        ctx = (nested / "project_context.md").read_text()
        assert "GoL context" in ctx

    def test_emode_copies_svp_dir(self, tmp_path):
        """E-mode still copies .svp/ for pipeline state skeleton."""
        _setup_svp_workspace(tmp_path)
        _setup_gol_test_project(tmp_path)
        state = _make_state(oracle_test_project="examples/game-of-life/")
        new = _bootstrap_oracle_nested_session(state, tmp_path)
        nested = Path(new.oracle_nested_session_path)
        assert (nested / ".svp").is_dir()

    def test_emode_does_not_copy_svp_profile(self, tmp_path):
        """E-mode should NOT copy SVP project_profile.json."""
        _setup_svp_workspace(tmp_path)
        _setup_gol_test_project(tmp_path)
        state = _make_state(oracle_test_project="examples/game-of-life/")
        new = _bootstrap_oracle_nested_session(state, tmp_path)
        nested = Path(new.oracle_nested_session_path)
        assert not (nested / "project_profile.json").exists()


class TestFmodeBootstrapArtifacts:
    """F-mode bootstrap must copy SVP artifacts (existing behavior, Bug S3-83)."""

    def test_fmode_copies_svp_spec(self, tmp_path):
        """F-mode nested session gets SVP spec."""
        _setup_svp_workspace(tmp_path)
        state = _make_state(oracle_test_project="docs/")
        new = _bootstrap_oracle_nested_session(state, tmp_path)
        nested = Path(new.oracle_nested_session_path)
        spec = (nested / "specs" / "stakeholder_spec.md").read_text()
        assert "SVP Spec" in spec

    def test_fmode_copies_svp_blueprint(self, tmp_path):
        """F-mode nested session gets SVP blueprint."""
        _setup_svp_workspace(tmp_path)
        state = _make_state(oracle_test_project="docs/")
        new = _bootstrap_oracle_nested_session(state, tmp_path)
        nested = Path(new.oracle_nested_session_path)
        bp = (nested / "blueprint" / "blueprint_contracts.md").read_text()
        assert "SVP Blueprint" in bp

    def test_fmode_copies_svp_profile(self, tmp_path):
        """F-mode nested session gets project_profile.json."""
        _setup_svp_workspace(tmp_path)
        state = _make_state(oracle_test_project="docs/")
        new = _bootstrap_oracle_nested_session(state, tmp_path)
        nested = Path(new.oracle_nested_session_path)
        assert (nested / "project_profile.json").is_file()

    def test_fmode_copies_svp_config(self, tmp_path):
        """Both modes get svp_config.json."""
        _setup_svp_workspace(tmp_path)
        state = _make_state(oracle_test_project="docs/")
        new = _bootstrap_oracle_nested_session(state, tmp_path)
        nested = Path(new.oracle_nested_session_path)
        assert (nested / "svp_config.json").is_file()
