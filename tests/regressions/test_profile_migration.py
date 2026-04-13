"""test_profile_migration.py — Regression: SVP 2.1 → 2.2 profile migration.

NEW IN SVP 2.2. Verifies that SVP 2.1-format profiles (with flat
`delivery` and `quality` sections) auto-migrate to the language-keyed
2.2 format when loaded via `load_profile()`.

This test was declared in the blueprint's Preamble file tree (annotated
`<- Unit 3 (NEW IN 2.2)`) and referenced in specs Section 1536 but never
implemented. Its absence was detected by Bug S3-113's
`validate_delivered_repo_contents` assembly-map parity check, which
flagged the entry in `.svp/assembly_map.json` pointing at a
non-existent file. Created as part of the S3-113 fix to restore
blueprint-to-filesystem parity.
"""
import copy
import json
from pathlib import Path

import pytest

from profile_schema import DEFAULT_PROFILE, load_profile


def _write_profile(project_root: Path, profile: dict) -> None:
    (project_root / "project_profile.json").write_text(json.dumps(profile))


class TestSvp21FlatDeliveryMigration:
    """SVP 2.1 profiles had a flat `delivery` section; 2.2 keys by language."""

    def test_flat_delivery_is_wrapped_under_primary_language(self, tmp_path):
        """A flat `delivery` block becomes `delivery.python` after load."""
        _write_profile(tmp_path, {
            "archetype": "python_project",
            "language": {"primary": "python"},
            "delivery": {"entry_points": True, "source_layout": "conventional"},
        })
        profile = load_profile(tmp_path)
        assert "python" in profile["delivery"]
        assert profile["delivery"]["python"]["entry_points"] is True
        assert profile["delivery"]["python"]["source_layout"] == "conventional"

    def test_flat_delivery_wraps_under_r_for_r_project(self, tmp_path):
        """For an R archetype, flat delivery wraps under 'r', not 'python'."""
        _write_profile(tmp_path, {
            "archetype": "r_project",
            "language": {"primary": "r"},
            "delivery": {"package_layout": "standard"},
        })
        profile = load_profile(tmp_path)
        assert "r" in profile["delivery"]
        assert profile["delivery"]["r"]["package_layout"] == "standard"


class TestSvp21FlatQualityMigration:
    """SVP 2.1 profiles had a flat `quality` section; 2.2 keys by language."""

    def test_flat_quality_is_wrapped_under_primary_language(self, tmp_path):
        _write_profile(tmp_path, {
            "archetype": "python_project",
            "language": {"primary": "python"},
            "quality": {"linter": "ruff", "formatter": "black"},
        })
        profile = load_profile(tmp_path)
        assert "python" in profile["quality"]
        assert profile["quality"]["python"]["linter"] == "ruff"


class TestAlreadyMigratedProfileUnchanged:
    """A profile already in 2.2 language-keyed format must pass through unchanged."""

    def test_nested_delivery_is_not_rewrapped(self, tmp_path):
        """A profile with delivery.python.X should not become delivery.python.python.X."""
        _write_profile(tmp_path, {
            "archetype": "python_project",
            "language": {"primary": "python"},
            "delivery": {
                "python": {"entry_points": True, "source_layout": "conventional"}
            },
        })
        profile = load_profile(tmp_path)
        # The 'python' key remains the immediate child; no double-wrap.
        assert "python" in profile["delivery"]
        assert "python" not in profile["delivery"]["python"]
        assert profile["delivery"]["python"]["entry_points"] is True

    def test_nested_quality_is_not_rewrapped(self, tmp_path):
        _write_profile(tmp_path, {
            "archetype": "python_project",
            "language": {"primary": "python"},
            "quality": {"python": {"linter": "ruff"}},
        })
        profile = load_profile(tmp_path)
        assert "python" in profile["quality"]
        assert "python" not in profile["quality"]["python"]
        assert profile["quality"]["python"]["linter"] == "ruff"


class TestArchetypeDerivedFields:
    """load_profile derives is_svp_build and self_build_scope from archetype."""

    def test_normal_archetype_has_no_svp_build_flags(self, tmp_path):
        _write_profile(tmp_path, {
            "archetype": "python_project",
            "language": {"primary": "python"},
        })
        profile = load_profile(tmp_path)
        assert profile["is_svp_build"] is False
        assert profile["self_build_scope"] is None

    def test_svp_language_extension_archetype_sets_flags(self, tmp_path):
        _write_profile(tmp_path, {
            "archetype": "svp_language_extension",
            "language": {"primary": "python"},
        })
        profile = load_profile(tmp_path)
        assert profile["is_svp_build"] is True
        assert profile["self_build_scope"] == "language_extension"

    def test_svp_architectural_archetype_sets_flags(self, tmp_path):
        _write_profile(tmp_path, {
            "archetype": "svp_architectural",
            "language": {"primary": "python"},
        })
        profile = load_profile(tmp_path)
        assert profile["is_svp_build"] is True
        assert profile["self_build_scope"] == "architectural"


class TestMissingProfile:
    """load_profile raises FileNotFoundError when the profile file is absent."""

    def test_missing_profile_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_profile(tmp_path)
