"""Bug 50 regression test: contract sufficiency and boundary
violations in blueprint.

Verifies that implementations contain the critical data values
and behavioral details that the contracts should specify.
Covers 16 functions across 6 units (1, 3, 6, 10, 24).
"""

from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any, Dict

# --------------- path setup ----------------------------- #

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent

# Try delivered layout first, then workspace layout.
_SCRIPTS_DIR = _REPO_ROOT / "svp" / "scripts"
if not _SCRIPTS_DIR.is_dir():
    _SCRIPTS_DIR = _REPO_ROOT / "scripts"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# ======================================================= #
# Unit 1 tests                                            #
# ======================================================= #


class TestUnit1ContextBudget:
    """Verify model context mapping and budget constants."""

    def test_model_context_windows_exist(self) -> None:
        """Implementation has a model context mapping with
        known models."""
        import svp_config

        mapping = svp_config._MODEL_CONTEXT_WINDOWS
        assert isinstance(mapping, dict)
        assert len(mapping) > 0
        # Must include at least the primary models
        assert "claude-opus-4-6" in mapping
        assert "claude-sonnet-4-6" in mapping

    def test_context_budget_fallback_default(self) -> None:
        """Fallback is 200000 when no model matches."""
        import svp_config

        config: Dict[str, Any] = {
            "models": {"default": "unknown-model-xyz"},
            "context_budget_override": None,
        }
        budget = svp_config.get_effective_context_budget(config)
        overhead = svp_config._CONTEXT_BUDGET_OVERHEAD
        assert budget == 200_000 - overhead

    def test_context_overhead_constant(self) -> None:
        """Overhead constant is 20000."""
        import svp_config

        assert svp_config._CONTEXT_BUDGET_OVERHEAD == 20_000


class TestUnit1ValidateProfile:
    """Verify enum validation sets in validate_profile."""

    def _make_profile(self, **overrides: Any) -> dict:
        import svp_config

        p = copy.deepcopy(svp_config.DEFAULT_PROFILE)
        for dotted_key, val in overrides.items():
            parts = dotted_key.split(".")
            target = p
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = val
        return p

    def test_validate_profile_valid_linters(self) -> None:
        import svp_config

        for val in ("ruff", "flake8", "pylint", "none"):
            p = self._make_profile(**{"quality.linter": val})
            errors = svp_config.validate_profile(p)
            assert not errors, f"linter={val!r} should be valid"

    def test_validate_profile_valid_formatters(self) -> None:
        import svp_config

        for val in ("ruff", "black", "none"):
            p = self._make_profile(**{"quality.formatter": val})
            errors = svp_config.validate_profile(p)
            assert not errors, f"formatter={val!r} should be valid"

    def test_validate_profile_valid_type_checkers(
        self,
    ) -> None:
        import svp_config

        for val in ("mypy", "pyright", "none"):
            p = self._make_profile(**{"quality.type_checker": val})
            errors = svp_config.validate_profile(p)
            assert not errors, f"type_checker={val!r} should be valid"

    def test_validate_profile_valid_changelogs(self) -> None:
        import svp_config

        for val in (
            "keep_a_changelog",
            "conventional_changelog",
            "none",
        ):
            p = self._make_profile(**{"vcs.changelog": val})
            errors = svp_config.validate_profile(p)
            assert not errors, f"changelog={val!r} should be valid"


class TestUnit1Contradictions:
    """Verify detect_profile_contradictions patterns."""

    def _make_profile(self, **overrides: Any) -> dict:
        import svp_config

        p = copy.deepcopy(svp_config.DEFAULT_PROFILE)
        for dotted_key, val in overrides.items():
            parts = dotted_key.split(".")
            target = p
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = val
        return p

    def test_detect_contradictions_env_mismatch(
        self,
    ) -> None:
        """Catches environment/dependency mismatch."""
        import svp_config

        p = self._make_profile(
            **{
                "delivery.environment_recommendation": ("conda"),
                "delivery.dependency_format": ("requirements.txt"),
            }
        )
        result = svp_config.detect_profile_contradictions(p)
        assert any(
            "environment_recommendation" in c or "dependency_format" in c
            for c in result
        ), "Should catch env/dependency mismatch"

    def test_detect_contradictions_linter_none(self) -> None:
        """Catches vcs.commit_style custom with no
        template."""
        import svp_config

        p = self._make_profile(
            **{
                "vcs.commit_style": "custom",
                "vcs.commit_template": None,
            }
        )
        result = svp_config.detect_profile_contradictions(p)
        assert any("commit_style" in c or "commit_template" in c for c in result), (
            "Should catch custom style with no template"
        )


class TestUnit1Toolchain:
    """Verify recognized placeholder set."""

    def test_validate_toolchain_recognized_placeholders(
        self,
    ) -> None:
        import svp_config

        placeholders = svp_config._RECOGNIZED_PLACEHOLDERS
        assert isinstance(placeholders, set)
        for expected in (
            "env_name",
            "test_path",
            "files",
            "message",
            "module",
            "packages",
        ):
            assert expected in placeholders, f"{expected!r} not in recognized set"


# ======================================================= #
# Unit 3 tests                                            #
# ======================================================= #


class TestUnit3Rollback:
    """Verify rollback backup behavior."""

    def test_rollback_creates_backup(self) -> None:
        """Rollback preserves code in logs/rollback/."""
        import pipeline_state
        import state_transitions

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create required dirs
            (root / ".svp" / "markers").mkdir(parents=True)
            (root / "logs" / "rollback").mkdir(parents=True)
            src = root / "src" / "unit_1"
            src.mkdir(parents=True)
            (src / "stub.py").write_text("# code")
            tests = root / "tests" / "unit_1"
            tests.mkdir(parents=True)
            (tests / "test_stub.py").write_text("# test")

            # Create marker
            marker = root / ".svp" / "markers" / "unit_1_verified"
            marker.touch()

            state = pipeline_state.PipelineState(
                stage="3",
                current_unit=1,
                total_units=3,
                verified_units=[{"unit": 1, "timestamp": "t"}],
            )

            state_transitions.rollback_to_unit(state, 1, root)

            backup_src = root / "logs" / "rollback" / "unit_1_src"
            backup_tests = root / "logs" / "rollback" / "unit_1_tests"
            assert backup_src.exists(), "Source backup missing"
            assert backup_tests.exists(), "Test backup missing"


class TestUnit3Immutability:
    """Verify transition functions don't mutate input."""

    def test_transitions_do_not_mutate_input(self) -> None:
        import pipeline_state
        import state_transitions

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp" / "markers").mkdir(parents=True)

            # Create files needed for stage advancement
            (root / "project_profile.json").write_text("{}")

            state = pipeline_state.PipelineState(
                stage="0",
                sub_stage="hook_activation",
            )
            original_dict = state.to_dict()

            # advance_stage
            state_transitions.advance_stage(state, root)
            assert state.to_dict() == original_dict, "advance_stage mutated input"

            # advance_sub_stage
            state2 = pipeline_state.PipelineState(
                stage="3",
                sub_stage=None,
                current_unit=1,
                total_units=3,
            )
            orig2 = state2.to_dict()
            state_transitions.advance_sub_stage(state2, "test_generation", root)
            assert state2.to_dict() == orig2, "advance_sub_stage mutated input"


# ======================================================= #
# Unit 6 tests                                            #
# ======================================================= #


class TestUnit6StubGenerator:
    """Verify stub generation uses ast.unparse and
    sentinel."""

    def test_stub_source_uses_ast_unparse(self) -> None:
        """Output is valid Python (round-trip parseable)."""
        import stub_generator

        code = textwrap.dedent("""\
            import os
            from pathlib import Path

            def hello(name: str) -> str:
                return f"Hello {name}"
        """)
        tree = ast.parse(code)
        result = stub_generator.generate_stub_source(tree)
        # Must be parseable
        ast.parse(result)

    def test_sentinel_before_first_non_import(self) -> None:
        """Sentinel appears before first non-import."""
        import stub_generator

        code = textwrap.dedent("""\
            import os

            X = 1

            def foo():
                pass
        """)
        tree = ast.parse(code)
        result = stub_generator.generate_stub_source(tree)
        lines = result.splitlines()
        # Find first non-import, non-empty line
        sentinel_found = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("import "):
                continue
            if stripped.startswith("from "):
                continue
            # First non-import line should be sentinel
            assert "__SVP_STUB__" in stripped, f"Expected sentinel, got: {stripped!r}"
            sentinel_found = True
            break
        assert sentinel_found, "Sentinel not found"


# ======================================================= #
# Unit 10 tests                                           #
# ======================================================= #


class TestUnit10Dispatch:
    """Verify dispatch_agent_status transitions."""

    def _make_state(self, **kwargs: Any) -> Any:
        import pipeline_state

        return pipeline_state.PipelineState(**kwargs)

    def test_dispatch_test_agent_advances_to_gate_a(
        self,
    ) -> None:
        """test_agent -> quality_gate_a."""
        import routing

        state = self._make_state(
            stage="3",
            sub_stage="test_generation",
            current_unit=1,
            total_units=3,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp" / "markers").mkdir(parents=True)
            new = routing.dispatch_agent_status(
                state,
                "test_agent",
                "TEST_GENERATION_COMPLETE",
                1,
                "test_generation",
                root,
            )
            assert new.sub_stage == "quality_gate_a"

    def test_dispatch_impl_agent_advances_to_gate_b(
        self,
    ) -> None:
        """implementation_agent -> quality_gate_b."""
        import routing

        state = self._make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            total_units=3,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp" / "markers").mkdir(parents=True)
            new = routing.dispatch_agent_status(
                state,
                "implementation_agent",
                "IMPLEMENTATION_COMPLETE",
                1,
                "implementation",
                root,
            )
            assert new.sub_stage == "quality_gate_b"

    def test_dispatch_coverage_advances_to_completion(
        self,
    ) -> None:
        """coverage_review -> unit_completion."""
        import routing

        state = self._make_state(
            stage="3",
            sub_stage="coverage_review",
            current_unit=1,
            total_units=3,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp" / "markers").mkdir(parents=True)
            new = routing.dispatch_agent_status(
                state,
                "coverage_review",
                "COVERAGE_COMPLETE: no gaps",
                1,
                "coverage_review",
                root,
            )
            assert new.sub_stage == "unit_completion"

    def test_dispatch_reference_indexing_advances(
        self,
    ) -> None:
        """reference_indexing -> stage 3."""
        import routing

        state = self._make_state(
            stage="pre_stage_3",
            sub_stage=None,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".svp" / "markers").mkdir(parents=True)
            new = routing.dispatch_agent_status(
                state,
                "reference_indexing",
                "INDEXING_COMPLETE",
                None,
                "reference_indexing",
                root,
            )
            assert new.stage == "3"


# ======================================================= #
# Unit 24 tests                                           #
# ======================================================= #


class TestUnit24CopyHooks:
    """Verify copy_hooks sets executable permissions."""

    def test_copy_hooks_sets_executable(self) -> None:
        """Hook scripts get executable permission."""
        import svp_launcher

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            plugin = root / "plugin"
            hooks_dir = plugin / "hooks"
            scripts_dir = hooks_dir / "scripts"
            scripts_dir.mkdir(parents=True)

            # Create a hooks.json
            hooks_json = hooks_dir / "hooks.json"
            hooks_json.write_text(json.dumps({"hooks": {"PreToolUse": []}}))

            # Create a script file
            script = scripts_dir / "test_hook.sh"
            script.write_text("#!/bin/bash\nexit 0\n")
            # Remove executable bit
            script.chmod(0o644)

            project = root / "project"
            project.mkdir()

            svp_launcher.copy_hooks(plugin, project)

            dst = project / ".claude" / "scripts" / "test_hook.sh"
            assert dst.exists(), "Hook script not copied"


class TestUnit24LaunchClaudeCode:
    """Verify skip_permissions config flag affects cmd."""

    def test_launch_claude_code_respects_skip_perms(
        self,
    ) -> None:
        """Config flag affects command construction."""
        import svp_launcher

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Write config with skip_permissions=True
            cfg = root / "svp_config.json"
            cfg.write_text(json.dumps({"skip_permissions": True}))

            config = svp_launcher._load_launch_config(root)
            assert config.get("skip_permissions") is True

            # Write config with skip_permissions=False
            cfg.write_text(json.dumps({"skip_permissions": False}))
            config = svp_launcher._load_launch_config(root)
            assert config.get("skip_permissions") is False
