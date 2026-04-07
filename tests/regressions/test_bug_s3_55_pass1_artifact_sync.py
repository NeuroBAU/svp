"""Regression tests for Bug S3-55: Pass 1 artifact synchronization.

Verifies that sync_pass1_artifacts() correctly copies accumulated
artifacts from the Pass 1 workspace into the Pass 2 workspace,
including regression tests, lessons learned, spec amendments,
and .svp metadata — without touching source code.
"""

import json
import tempfile
from pathlib import Path

import pytest

from sync_debug_docs import (
    _derive_pass1_workspace,
    sync_pass1_artifacts,
)


def _create_workspace_pair(tmp: Path):
    """Create a mock Pass 1 + Pass 2 workspace pair."""
    pass1 = tmp / "myproject"
    pass2 = tmp / "myproject-pass2"
    pass1.mkdir()
    pass2.mkdir()

    # Pass 1 pipeline state
    (pass1 / "pipeline_state.json").write_text('{"stage": "5", "pass": 1}')
    (pass2 / "pipeline_state.json").write_text('{"stage": "5", "pass": 2}')

    # Pass 1 .svp metadata
    (pass1 / ".svp").mkdir()
    (pass1 / ".svp" / "alignment_checker_checklist.md").write_text("checklist content")
    (pass1 / ".svp" / "quality_report.md").write_text("quality report")
    (pass1 / ".svp" / "triage_result.json").write_text('{"result": "ok"}')
    (pass2 / ".svp").mkdir()
    (pass2 / ".svp" / "last_status.txt").write_text("TESTS PASSED")

    # Pass 1 regression tests
    (pass1 / "tests" / "regressions").mkdir(parents=True)
    (pass1 / "tests" / "regressions" / "__init__.py").write_text("")
    (pass1 / "tests" / "regressions" / "test_bug_s3_10.py").write_text("# s3-10 test")
    (pass1 / "tests" / "regressions" / "test_bug_s3_15.py").write_text("# s3-15 test")
    (pass1 / "tests" / "regressions" / "test_shared.py").write_text("# shared test pass1")

    # Pass 2 regression tests (partial overlap)
    (pass2 / "tests" / "regressions").mkdir(parents=True)
    (pass2 / "tests" / "regressions" / "__init__.py").write_text("")
    (pass2 / "tests" / "regressions" / "test_shared.py").write_text("# shared test pass2")
    (pass2 / "tests" / "regressions" / "test_bug_s3_51.py").write_text("# s3-51 test")

    # Pass 1 lessons learned (longer)
    (pass1 / "references").mkdir()
    (pass1 / "references" / "svp_2_1_lessons_learned.md").write_text(
        "# Lessons\n\n## Part 1: Bug Catalog\n\nBug S3-1\nBug S3-10\nBug S3-15\n\n"
        "## Part 2: Pattern Catalog\n\nP1 incomplete\n"
    )

    # Pass 2 lessons learned (shorter base + unique Part 3)
    (pass2 / "references").mkdir()
    (pass2 / "references" / "svp_2_1_lessons_learned.md").write_text(
        "# Lessons\n\n## Part 1: Bug Catalog\n\nBug S3-1\n\n"
        "## Part 2: Pattern Catalog\n\nP1 incomplete\n\n"
        "## Part 3: Plugin Assembly\n\nS3-51 through S3-54\n"
    )

    # Pass 1 spec with S3-47 marker
    (pass1 / "specs").mkdir()
    (pass1 / "specs" / "stakeholder_spec.md").write_text(
        "# SVP Spec\n\n## Section 15: Stub generation\n\n"
        "Stub generation produces files for each unit.\n"
        "**Upstream import TYPE_CHECKING guards (Bug S3-47).** Use guards.\n\n"
        "## Section 24: Failure Modes\n\nBug catalog here.\n"
    )

    # Pass 2 spec with S3-51 marker but missing S3-47
    (pass2 / "specs").mkdir()
    (pass2 / "specs" / "stakeholder_spec.md").write_text(
        "# SVP Spec\n\n## Section 15: Stub generation\n\n"
        "Stub generation produces files for each unit.\n\n"
        "## Section 24: Failure Modes\n\nBug catalog here.\n\n"
        "### 24.70 Bug S3-51\n\nPlugin manifest.\n"
    )

    # Pass 1 source code (should NOT be synced)
    (pass1 / "src").mkdir()
    (pass1 / "src" / "pass1_code.py").write_text("pass1 code")

    # Pass 2 source code
    (pass2 / "src").mkdir()
    (pass2 / "src" / "pass2_code.py").write_text("pass2 code")

    return pass1, pass2


class TestS3_55_DerivePass1Workspace:
    """Pass 1 workspace path derivation."""

    def test_valid_derivation(self):
        result = _derive_pass1_workspace(Path("/tmp/myproject-pass2"))
        assert result == Path("/tmp/myproject")

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError, match="does not end with '-pass2'"):
            _derive_pass1_workspace(Path("/tmp/myproject"))

    def test_nested_pass2_suffix(self):
        result = _derive_pass1_workspace(Path("/a/b/svp2.2-pass2"))
        assert result == Path("/a/b/svp2.2")


class TestS3_55_SyncRegressionTests:
    """Regression test union sync."""

    def test_union_copies_missing_files(self):
        with tempfile.TemporaryDirectory() as td:
            _, pass2 = _create_workspace_pair(Path(td))
            sync_pass1_artifacts(pass2)
            reg_dir = pass2 / "tests" / "regressions"
            assert (reg_dir / "test_bug_s3_10.py").is_file()
            assert (reg_dir / "test_bug_s3_15.py").is_file()

    def test_union_preserves_pass2_files(self):
        with tempfile.TemporaryDirectory() as td:
            _, pass2 = _create_workspace_pair(Path(td))
            sync_pass1_artifacts(pass2)
            content = (pass2 / "tests" / "regressions" / "test_shared.py").read_text()
            assert "pass2" in content  # Not overwritten by Pass 1

    def test_union_keeps_pass2_only_files(self):
        with tempfile.TemporaryDirectory() as td:
            _, pass2 = _create_workspace_pair(Path(td))
            sync_pass1_artifacts(pass2)
            assert (pass2 / "tests" / "regressions" / "test_bug_s3_51.py").is_file()

    def test_init_not_copied(self):
        with tempfile.TemporaryDirectory() as td:
            _, pass2 = _create_workspace_pair(Path(td))
            result = sync_pass1_artifacts(pass2)
            assert not any("__init__" in f for f in result["synced_files"])


class TestS3_55_SyncLessonsLearned:
    """Lessons learned merge."""

    def test_pass2_gets_all_entries(self):
        with tempfile.TemporaryDirectory() as td:
            _, pass2 = _create_workspace_pair(Path(td))
            sync_pass1_artifacts(pass2)
            content = (pass2 / "references" / "svp_2_1_lessons_learned.md").read_text()
            assert "Bug S3-10" in content  # From Pass 1
            assert "Bug S3-15" in content  # From Pass 1
            assert "Part 3" in content  # From Pass 2
            assert "S3-51 through S3-54" in content  # From Pass 2


class TestS3_55_SyncSpec:
    """Spec merge."""

    def test_spec_has_both_markers(self):
        with tempfile.TemporaryDirectory() as td:
            _, pass2 = _create_workspace_pair(Path(td))
            sync_pass1_artifacts(pass2)
            content = (pass2 / "specs" / "stakeholder_spec.md").read_text()
            assert "Bug S3-47" in content  # Merged from Pass 1
            assert "Bug S3-51" in content  # Preserved from Pass 2


class TestS3_55_SyncMetadata:
    """SVP metadata sync."""

    def test_metadata_copied(self):
        with tempfile.TemporaryDirectory() as td:
            _, pass2 = _create_workspace_pair(Path(td))
            sync_pass1_artifacts(pass2)
            assert (pass2 / ".svp" / "alignment_checker_checklist.md").is_file()
            assert (pass2 / ".svp" / "quality_report.md").is_file()
            assert (pass2 / ".svp" / "triage_result.json").is_file()

    def test_existing_metadata_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            _, pass2 = _create_workspace_pair(Path(td))
            sync_pass1_artifacts(pass2)
            content = (pass2 / ".svp" / "last_status.txt").read_text()
            assert content == "TESTS PASSED"  # Not overwritten


class TestS3_55_NoCodeSync:
    """Source code must NOT be synced."""

    def test_src_not_copied(self):
        with tempfile.TemporaryDirectory() as td:
            _, pass2 = _create_workspace_pair(Path(td))
            sync_pass1_artifacts(pass2)
            assert not (pass2 / "src" / "pass1_code.py").exists()
            assert (pass2 / "src" / "pass2_code.py").is_file()


class TestS3_55_Idempotency:
    """Sync must be idempotent."""

    def test_second_call_is_noop(self):
        with tempfile.TemporaryDirectory() as td:
            _, pass2 = _create_workspace_pair(Path(td))
            result1 = sync_pass1_artifacts(pass2)
            assert len(result1["synced_files"]) > 0

            result2 = sync_pass1_artifacts(pass2)
            assert len(result2["synced_files"]) == 0
            assert "Already synced" in result2["errors"][0]

    def test_marker_file_created(self):
        with tempfile.TemporaryDirectory() as td:
            _, pass2 = _create_workspace_pair(Path(td))
            sync_pass1_artifacts(pass2)
            marker = pass2 / ".svp" / "pass1_sync_complete"
            assert marker.is_file()
            data = json.loads(marker.read_text())
            assert "timestamp" in data


class TestS3_55_EdgeCases:
    """Edge cases and error handling."""

    def test_pass1_not_found(self):
        with tempfile.TemporaryDirectory() as td:
            pass2 = Path(td) / "orphan-pass2"
            pass2.mkdir()
            (pass2 / ".svp").mkdir()
            result = sync_pass1_artifacts(pass2)
            assert len(result["errors"]) > 0
            assert "not found" in result["errors"][0]

    def test_non_pass2_name(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "myproject"
            workspace.mkdir()
            result = sync_pass1_artifacts(workspace)
            assert len(result["errors"]) > 0
            assert "does not end with" in result["errors"][0]
