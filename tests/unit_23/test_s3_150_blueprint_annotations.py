"""Tests for Bug S3-150: blueprint Preamble file-tree annotations.

Verifies:
  (a) BLUEPRINT_AUTHOR_DEFINITION source contains the "Delivered File Tree"
      section instruction (regression anchor — the agent prompt is a deployed
      artifact; this guards against future drift)
  (b) generate_assembly_map raises an actionable ValueError when the
      blueprint lacks the Preamble section
  (c) generate_assembly_map succeeds when given a synthetic blueprint with
      the Preamble section
"""

import pytest

from generate_assembly_map import generate_assembly_map
from construction_agents import BLUEPRINT_AUTHOR_DEFINITION


# ---------------------------------------------------------------------------
# (a) Agent prompt regression anchor
# ---------------------------------------------------------------------------


def test_blueprint_author_definition_requires_delivered_file_tree():
    """The agent prompt MUST instruct the agent to produce the Preamble
    file-tree section. If this regresses, A-D blueprints will silently lose
    the requirement and Stage 5 will fail with the S3-150 symptom."""
    assert "Delivered File Tree" in BLUEPRINT_AUTHOR_DEFINITION, (
        "Agent prompt regressed: BLUEPRINT_AUTHOR_DEFINITION must include the "
        "'Delivered File Tree' section header (Bug S3-150, spec §24.164). "
        "Without it the agent will not produce the Preamble section that "
        "generate_assembly_map requires."
    )
    # Mandatory marker — pinpoints intent so the section is hard to delete by
    # accident in a future prose edit
    assert "MANDATORY" in BLUEPRINT_AUTHOR_DEFINITION
    # The annotation marker should appear in the worked example
    assert "<- Unit" in BLUEPRINT_AUTHOR_DEFINITION


# ---------------------------------------------------------------------------
# (b) ValueError is actionable when the section is missing
# ---------------------------------------------------------------------------


def test_generate_assembly_map_raises_actionable_error_without_preamble(tmp_path):
    """A blueprint without the Preamble section produces a ValueError whose
    message names the missing section AND points at the agent's
    responsibility AND references the spec entry."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()
    # Minimal prose file with NO Preamble section
    (bp_dir / "blueprint_prose.md").write_text(
        "# Blueprint\n\n## Unit 1: Engine\nSome description.\n"
    )

    with pytest.raises(ValueError) as exc:
        generate_assembly_map(bp_dir, tmp_path)

    msg = str(exc.value)
    # Must mention the missing section by name
    assert "Preamble" in msg, f"Error message should name 'Preamble'; got: {msg!r}"
    # Must reference the annotation marker so the user knows the format
    assert "<- Unit" in msg
    # Must reference the bug ID and spec section so the user can find context
    assert "S3-150" in msg
    assert "24.164" in msg or "section 24.164" in msg


# ---------------------------------------------------------------------------
# (c) Happy path: synthetic blueprint with Preamble parses correctly
# ---------------------------------------------------------------------------


def test_generate_assembly_map_succeeds_with_preamble_section(tmp_path):
    """A blueprint with a properly-formatted Preamble section produces a
    non-empty repo_to_workspace map."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()
    (bp_dir / "blueprint_prose.md").write_text(
        "# Blueprint\n\n"
        "## Preamble: Delivered File Tree\n\n"
        "```\n"
        "demo-repo/\n"
        "|-- pyproject.toml\n"
        "|-- src/\n"
        "|   +-- demo_pkg/\n"
        "|       |-- __init__.py\n"
        "|       |-- engine.py                <- Unit 1\n"
        "|       +-- patterns.py              <- Unit 2\n"
        "+-- tests/\n"
        "    |-- unit_1/\n"
        "    |   +-- test_engine.py           <- Unit 1\n"
        "    +-- unit_2/\n"
        "        +-- test_patterns.py         <- Unit 2\n"
        "```\n\n"
        "## Unit 1: Engine\n"
    )
    # .svp dir for the side-effect write
    (tmp_path / ".svp").mkdir()

    result = generate_assembly_map(bp_dir, tmp_path)

    assert "repo_to_workspace" in result
    mapping = result["repo_to_workspace"]
    assert len(mapping) >= 4  # 2 source + 2 test files
    # Spot-check one entry
    src_entries = [
        (k, v) for k, v in mapping.items() if k.endswith("engine.py")
    ]
    assert src_entries, f"Expected an engine.py entry; got keys: {list(mapping)}"
    deployed, source = src_entries[0]
    assert "src/unit_1/stub.py" == source
