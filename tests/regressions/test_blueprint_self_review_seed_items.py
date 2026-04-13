"""Regression tests locking the six universal categories of seed items
in spec Section 44.11.

This test file is a convention lock: if anyone removes a seed item from
Section 44.11 or renumbers without updating this test, the test fails
loudly. It does NOT test agent behavior — it tests that the spec carries
the seed items the Checklist Generation Agent is contractually obligated
to embed.

The six categories:
- S (Schema Coherence): SC-27..SC-31
- F (Function Reachability): SC-32..SC-36
- I (Invariant Coherence): SC-37..SC-41
- D (Dispatch Completeness): SC-42..SC-47
- B (Branch Reachability): SC-48..SC-52
- C (Contract Bidirectional Mapping): SC-53..SC-57
"""
from pathlib import Path

import pytest


def _resolve_spec_path() -> Path:
    """Return the project's stakeholder spec path. Workspace layout uses
    `specs/stakeholder_spec.md`; delivered repo layout uses
    `docs/stakeholder_spec.md`. We accept either."""
    project_root = Path(__file__).parent.parent.parent
    workspace_layout = project_root / "specs" / "stakeholder_spec.md"
    if workspace_layout.exists():
        return workspace_layout
    repo_layout = project_root / "docs" / "stakeholder_spec.md"
    if repo_layout.exists():
        return repo_layout
    raise FileNotFoundError(
        f"Neither {workspace_layout} nor {repo_layout} exists"
    )


SPEC_PATH = _resolve_spec_path()


@pytest.fixture(scope="module")
def spec_text():
    return SPEC_PATH.read_text()


class TestSection44_11Exists:
    def test_section_44_11_header_present(self, spec_text):
        assert "### 44.11 Universal Software Engineering Principles" in spec_text, (
            "Spec must contain Section 44.11 'Universal Software Engineering Principles'"
        )

    def test_six_subsection_headers_present(self, spec_text):
        for subheader in [
            "#### 44.11.1 Schema Coherence",
            "#### 44.11.2 Function Reachability",
            "#### 44.11.3 Invariant Coherence",
            "#### 44.11.4 Dispatch Completeness",
            "#### 44.11.5 Branch Reachability",
            "#### 44.11.6 Contract Bidirectional Mapping",
        ]:
            assert subheader in spec_text, f"Missing subsection: {subheader}"


class TestCategoryS_SchemaCoherence:
    def test_seed_items_sc_27_to_sc_31_present(self, spec_text):
        for sc_id, alias in [
            ("SC-27", "S-1"),
            ("SC-28", "S-2"),
            ("SC-29", "S-3"),
            ("SC-30", "S-4"),
            ("SC-31", "S-5"),
        ]:
            assert f"{sc_id} ({alias})" in spec_text, (
                f"Schema Coherence seed item {sc_id} ({alias}) missing from Section 44.11.1"
            )


class TestCategoryF_FunctionReachability:
    def test_seed_items_sc_32_to_sc_36_present(self, spec_text):
        for sc_id, alias in [
            ("SC-32", "F-1"),
            ("SC-33", "F-2"),
            ("SC-34", "F-3"),
            ("SC-35", "F-4"),
            ("SC-36", "F-5"),
        ]:
            assert f"{sc_id} ({alias})" in spec_text, (
                f"Function Reachability seed item {sc_id} ({alias}) missing"
            )


class TestCategoryI_InvariantCoherence:
    def test_seed_items_sc_37_to_sc_41_present(self, spec_text):
        for sc_id, alias in [
            ("SC-37", "I-1"),
            ("SC-38", "I-2"),
            ("SC-39", "I-3"),
            ("SC-40", "I-4"),
            ("SC-41", "I-5"),
        ]:
            assert f"{sc_id} ({alias})" in spec_text, (
                f"Invariant Coherence seed item {sc_id} ({alias}) missing"
            )


class TestCategoryD_DispatchCompleteness:
    def test_seed_items_sc_42_to_sc_47_present(self, spec_text):
        for sc_id, alias in [
            ("SC-42", "D-1"),
            ("SC-43", "D-2"),
            ("SC-44", "D-3"),
            ("SC-45", "D-4"),
            ("SC-46", "D-5"),
            ("SC-47", "D-6"),
        ]:
            assert f"{sc_id} ({alias})" in spec_text, (
                f"Dispatch Completeness seed item {sc_id} ({alias}) missing"
            )


class TestCategoryB_BranchReachability:
    def test_seed_items_sc_48_to_sc_52_present(self, spec_text):
        for sc_id, alias in [
            ("SC-48", "B-1"),
            ("SC-49", "B-2"),
            ("SC-50", "B-3"),
            ("SC-51", "B-4"),
            ("SC-52", "B-5"),
        ]:
            assert f"{sc_id} ({alias})" in spec_text, (
                f"Branch Reachability seed item {sc_id} ({alias}) missing"
            )


class TestCategoryC_ContractBidirectionalMapping:
    def test_seed_items_sc_53_to_sc_57_present(self, spec_text):
        for sc_id, alias in [
            ("SC-53", "C-1"),
            ("SC-54", "C-2"),
            ("SC-55", "C-3"),
            ("SC-56", "C-4"),
            ("SC-57", "C-5"),
        ]:
            assert f"{sc_id} ({alias})" in spec_text, (
                f"Contract Bidirectional Mapping seed item {sc_id} ({alias}) missing"
            )


class TestSection7_8_2MentionsSixCategories:
    """Section 7.8.2 (mandatory categories) must explicitly reference the
    six new categories from Section 44.11."""

    def test_seven_eight_two_lists_six_universal_categories(self, spec_text):
        # Find Section 7.8.2 region
        start = spec_text.find("Mandatory categories (closed required set)")
        end = spec_text.find("**Final item (mandatory)", start)
        assert start != -1 and end != -1, (
            "Could not locate Section 7.8.2 mandatory categories list"
        )
        region = spec_text[start:end]
        for category_marker in [
            "Category S",
            "Category F",
            "Category I",
            "Category D",
            "Category B",
            "Category C",
        ]:
            assert category_marker in region, (
                f"Section 7.8.2 must list {category_marker} as a mandatory "
                f"category for the generated checklist."
            )


class TestSection7_8_4MentionsSelfReviewArtifact:
    """Section 7.8.4 (Checklist Delivery) must document the new
    .svp/blueprint_self_review.md artifact produced by the blueprint author."""

    def test_self_review_artifact_documented(self, spec_text):
        assert ".svp/blueprint_self_review.md" in spec_text, (
            "Section 7.8.4 must reference .svp/blueprint_self_review.md "
            "as the blueprint author's self-review artifact."
        )

    def test_iteration_until_all_pass_documented(self, spec_text):
        # Find Section 7.8.4
        start = spec_text.find("#### 7.8.4 Checklist Delivery")
        end = spec_text.find("#### 7.8.5", start)
        assert start != -1 and end != -1, "Could not locate Section 7.8.4"
        region = spec_text[start:end]
        assert "ALL_PASS" in region, (
            "Section 7.8.4 must document the ALL_PASS outcome convention."
        )
        assert "iterate" in region.lower() or "re-run" in region.lower(), (
            "Section 7.8.4 must document the iteration-until-pass rule."
        )
