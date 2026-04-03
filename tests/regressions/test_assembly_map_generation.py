"""test_assembly_map_generation.py -- Regression test for assembly map generation.

NEW IN SVP 2.2 (Unit 23). This regression test verifies the assembly map
generation produces correct bidirectional mappings from blueprint annotations.

Tests:
- Parsing of `<- Unit N` annotations from blueprint prose
- Bidirectional mapping keys (workspace_to_repo and repo_to_workspace)
- Bijectivity invariant (every forward mapping has a reverse)
- ValueError on incomplete mappings
"""
import json

import pytest

from src.unit_23.stub import generate_assembly_map


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
        w2r = result["workspace_to_repo"]
        assert "src/unit_14/routing.py" in w2r
        assert "src/unit_5/pipeline_state.py" in w2r
        assert w2r["src/unit_14/routing.py"] == "svp/scripts/routing.py"
        assert w2r["src/unit_5/pipeline_state.py"] == "svp/scripts/pipeline_state.py"

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
        assert len(result["workspace_to_repo"]) == 3


class TestBidirectionalMapping:
    """Assembly map contains both workspace_to_repo and repo_to_workspace keys."""

    def test_both_keys_present(self, workspace):
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
        assert "workspace_to_repo" in result
        assert "repo_to_workspace" in result

    def test_repo_to_workspace_is_inverse(self, workspace):
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
        assert r2w["svp/scripts/routing.py"] == "src/unit_14/routing.py"
        assert r2w["svp/scripts/pipeline_state.py"] == "src/unit_5/pipeline_state.py"


class TestBijectivity:
    """Every forward mapping has a corresponding reverse mapping."""

    def test_every_forward_has_reverse(self, workspace):
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
        w2r = result["workspace_to_repo"]
        r2w = result["repo_to_workspace"]
        for ws_path, repo_path in w2r.items():
            assert repo_path in r2w, (
                f"Forward mapping {ws_path} -> {repo_path} has no reverse"
            )
            assert r2w[repo_path] == ws_path

    def test_every_reverse_has_forward(self, workspace):
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
        w2r = result["workspace_to_repo"]
        r2w = result["repo_to_workspace"]
        for repo_path, ws_path in r2w.items():
            assert ws_path in w2r, (
                f"Reverse mapping {repo_path} -> {ws_path} has no forward"
            )
            assert w2r[ws_path] == repo_path


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
