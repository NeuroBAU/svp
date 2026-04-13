"""test_assembly_map_generation.py -- Regression test for assembly map generation.

NEW IN SVP 2.2 (Unit 23). CHANGED IN 2.2 (Bug S3-111): the map schema was
flattened from bidirectional (workspace_to_repo + repo_to_workspace) to a
single `repo_to_workspace` direction because the post-S3-98 relationship is
many-to-one (many deployed artifacts ← one stub), which a Dict[str, str]
cannot represent. Source paths are now always `src/unit_N/stub.py`.

Tests:
- Parsing of `<- Unit N` annotations from blueprint prose
- Single top-level `repo_to_workspace` key (no `workspace_to_repo`)
- Every value matches the stub.py naming convention
- ValueError on incomplete mappings
"""
import json
import re

import pytest

from generate_assembly_map import generate_assembly_map


STUB_PATH_RE = re.compile(r"^src/unit_\d+/stub\.py$")


@pytest.fixture
def workspace(tmp_path):
    """Create a minimal workspace with blueprint prose containing annotations."""
    blueprint_dir = tmp_path / "blueprint"
    blueprint_dir.mkdir()
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir()
    return tmp_path, blueprint_dir


def _write_blueprint(blueprint_dir, content):
    (blueprint_dir / "blueprint_prose.md").write_text(content, encoding="utf-8")


class TestAnnotationParsing:
    """generate_assembly_map parses <- Unit N annotations from blueprint prose."""

    def test_parses_unit_annotations(self, workspace):
        project_root, blueprint_dir = workspace
        _write_blueprint(blueprint_dir, """\
## Preamble

```
svp/
  scripts/
    routing.py             <- Unit 14
    pipeline_state.py      <- Unit 5
```
""")
        result = generate_assembly_map(blueprint_dir, project_root)
        r2w = result["repo_to_workspace"]
        assert "svp/scripts/routing.py" in r2w
        assert "svp/scripts/pipeline_state.py" in r2w
        # Bug S3-111: every value is the source stub for that unit.
        assert r2w["svp/scripts/routing.py"] == "src/unit_14/stub.py"
        assert r2w["svp/scripts/pipeline_state.py"] == "src/unit_5/stub.py"

    def test_multiple_annotations(self, workspace):
        project_root, blueprint_dir = workspace
        _write_blueprint(blueprint_dir, """\
## Preamble

```
svp/
  scripts/
    routing.py             <- Unit 14
    pipeline_state.py      <- Unit 5
    hooks.py               <- Unit 17
```
""")
        result = generate_assembly_map(blueprint_dir, project_root)
        assert len(result["repo_to_workspace"]) == 3


class TestSchemaShape:
    """Bug S3-111: assembly map has exactly one top-level key, `repo_to_workspace`."""

    def test_only_one_top_level_key(self, workspace):
        project_root, blueprint_dir = workspace
        _write_blueprint(blueprint_dir, """\
## Preamble

```
svp/
  scripts/
    routing.py             <- Unit 14
```
""")
        result = generate_assembly_map(blueprint_dir, project_root)
        assert list(result.keys()) == ["repo_to_workspace"]

    def test_no_workspace_to_repo_key(self, workspace):
        """Bug S3-111: the legacy forward direction key must NOT exist."""
        project_root, blueprint_dir = workspace
        _write_blueprint(blueprint_dir, """\
## Preamble

```
svp/
  scripts/
    routing.py             <- Unit 14
```
""")
        result = generate_assembly_map(blueprint_dir, project_root)
        assert "workspace_to_repo" not in result


class TestManyToOneRelationship:
    """Bug S3-111: multiple deployed artifacts from the same unit share one stub."""

    def test_multiple_deployed_files_from_one_unit_share_stub(self, workspace):
        project_root, blueprint_dir = workspace
        _write_blueprint(blueprint_dir, """\
## Preamble

```
svp/
  agents/
    git_repo_agent.md        <- Unit 23
    checklist_generation.md  <- Unit 23
    oracle_agent.md          <- Unit 23
  scripts/
    generate_assembly_map.py <- Unit 23
```
""")
        result = generate_assembly_map(blueprint_dir, project_root)
        r2w = result["repo_to_workspace"]
        # All four deployed files map to the same source stub.
        assert r2w["svp/agents/git_repo_agent.md"] == "src/unit_23/stub.py"
        assert r2w["svp/agents/checklist_generation.md"] == "src/unit_23/stub.py"
        assert r2w["svp/agents/oracle_agent.md"] == "src/unit_23/stub.py"
        assert r2w["svp/scripts/generate_assembly_map.py"] == "src/unit_23/stub.py"
        # Count distinct source values.
        unique_sources = set(r2w.values())
        assert unique_sources == {"src/unit_23/stub.py"}


class TestStalenessInvariant:
    """Bug S3-111: every value in repo_to_workspace must match the stub naming
    convention `src/unit_N/stub.py`. The previous formula `src/unit_N/<filename>`
    produced 100% stale entries post-Bug-S3-98. This test would have caught that.
    """

    def test_every_value_matches_stub_naming_convention(self, workspace):
        project_root, blueprint_dir = workspace
        _write_blueprint(blueprint_dir, """\
## Preamble

```
svp/
  scripts/
    routing.py             <- Unit 14
    pipeline_state.py      <- Unit 5
    hooks.py               <- Unit 17
  agents/
    git_repo_agent.md      <- Unit 23
```
""")
        result = generate_assembly_map(blueprint_dir, project_root)
        r2w = result["repo_to_workspace"]
        bad = [v for v in r2w.values() if not STUB_PATH_RE.match(v)]
        assert not bad, (
            f"Non-stub source paths in repo_to_workspace: {bad}. "
            f"Every value must match ^src/unit_\\d+/stub\\.py$ (Bug S3-111)."
        )


class TestIncompleteMapping:
    """ValueError raised when annotations cannot be fully mapped."""

    def test_missing_blueprint_prose_raises(self, workspace):
        project_root, blueprint_dir = workspace
        with pytest.raises(FileNotFoundError):
            generate_assembly_map(blueprint_dir, project_root)

    def test_no_annotations_raises(self, workspace):
        project_root, blueprint_dir = workspace
        _write_blueprint(blueprint_dir, """\
## Preamble

No code block here, just prose.
""")
        with pytest.raises(ValueError, match="Could not find file tree"):
            generate_assembly_map(blueprint_dir, project_root)
