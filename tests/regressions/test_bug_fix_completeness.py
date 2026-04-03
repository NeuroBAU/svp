"""
Structural completion audit for bug fixes (Bug S3-46).

Validates that all bug fix artifacts are consistent across workspace
and all delivered repositories. Run after every bug fix.
"""
import re
from pathlib import Path

import pytest

# pytestmark removed after comprehensive resync (2026-04-01)

# Paths relative to workspace root
WORKSPACE = Path(__file__).parent.parent.parent
PASS1_REPO = WORKSPACE.parent / "svp2.2-repo"
PASS2_REPO = WORKSPACE.parent / "svp2.2-pass2-repo"


class TestSpecSync:
    """Spec must be identical in workspace and all delivered repos."""

    def test_spec_matches_pass1_repo(self):
        ws = (WORKSPACE / "specs" / "stakeholder_spec.md").read_text()
        repo = (PASS1_REPO / "docs" / "stakeholder_spec.md").read_text()
        assert ws == repo, "Spec out of sync with Pass 1 repo"

    def test_spec_matches_pass2_repo(self):
        ws = (WORKSPACE / "specs" / "stakeholder_spec.md").read_text()
        p2 = PASS2_REPO / "docs" / "stakeholder_spec.md"
        if p2.exists():
            assert ws == p2.read_text(), "Spec out of sync with Pass 2 repo"


class TestBlueprintSync:
    """Blueprint must be identical in workspace and all delivered repos."""

    def test_blueprint_matches_pass1_repo(self):
        ws = (WORKSPACE / "blueprint" / "blueprint_contracts.md").read_text()
        repo = (PASS1_REPO / "docs" / "blueprint_contracts.md").read_text()
        assert ws == repo, "Blueprint out of sync with Pass 1 repo"

    def test_blueprint_matches_pass2_repo(self):
        ws = (WORKSPACE / "blueprint" / "blueprint_contracts.md").read_text()
        p2 = PASS2_REPO / "docs" / "blueprint_contracts.md"
        if p2.exists():
            assert ws == p2.read_text(), "Blueprint out of sync with Pass 2 repo"


class TestLessonsLearnedSync:
    """Lessons learned must be identical in workspace and all delivered repos."""

    def test_lessons_learned_matches_pass1_repo(self):
        ws = (WORKSPACE / "references" / "svp_2_1_lessons_learned.md").read_text()
        repo = (PASS1_REPO / "docs" / "references" / "svp_2_1_lessons_learned.md").read_text()
        assert ws == repo, "Lessons learned out of sync with Pass 1 repo"

    def test_lessons_learned_matches_pass2_repo(self):
        ws = (WORKSPACE / "references" / "svp_2_1_lessons_learned.md").read_text()
        p2 = PASS2_REPO / "docs" / "references" / "svp_2_1_lessons_learned.md"
        if p2.exists():
            assert ws == p2.read_text(), "Lessons learned out of sync with Pass 2 repo"


class TestDeliveryArtifactParity:
    """S3-50: Pass 2 repo must have all delivery artifacts from Pass 1."""

    def test_pass2_repo_has_all_root_delivery_files(self):
        delivery_files = ["environment.yml", "pyproject.toml", "README.md",
                          "CHANGELOG.md", "LICENSE", ".gitignore"]
        for f in delivery_files:
            if (PASS1_REPO / f).exists():
                assert (PASS2_REPO / f).exists(), f"Pass 2 repo missing {f} (present in Pass 1)"


class TestBugMarkerCompleteness:
    """Every bug referenced in spec must have a lessons learned entry."""

    def test_all_spec_bugs_in_lessons_learned(self):
        spec = (WORKSPACE / "specs" / "stakeholder_spec.md").read_text()
        lessons = (WORKSPACE / "references" / "svp_2_1_lessons_learned.md").read_text()
        # Find S3-N markers (the bug catalog format used in this build)
        spec_bugs = set(re.findall(r"S3-\d+", spec))
        lessons_bugs = set(re.findall(r"S3-\d+", lessons))
        missing = spec_bugs - lessons_bugs
        # Filter: only bugs that appear as "Bug S3-N" in spec (not just passing references)
        spec_bug_entries = set(re.findall(r"Bug S3-\d+", spec))
        spec_bug_numbers = {m.replace("Bug ", "") for m in spec_bug_entries}
        missing_entries = spec_bug_numbers - lessons_bugs
        assert not missing_entries, (
            f"Bugs in spec but not in lessons learned: {sorted(missing_entries)}"
        )

    def test_all_regression_test_bugs_in_lessons_learned(self):
        """Every bug with a regression test file should have a lessons learned entry."""
        lessons = (WORKSPACE / "references" / "svp_2_1_lessons_learned.md").read_text()
        lessons_bugs = set(re.findall(r"S3-\d+", lessons))
        reg_dir = WORKSPACE / "tests" / "regressions"
        for f in reg_dir.glob("test_bug_s3_*.py"):
            # Extract bug numbers from filename
            file_bugs = set(re.findall(r"s3_(\d+)", f.name))
            for num in file_bugs:
                marker = f"S3-{num}"
                assert marker in lessons_bugs, (
                    f"Regression test {f.name} references {marker} but no lessons learned entry"
                )
