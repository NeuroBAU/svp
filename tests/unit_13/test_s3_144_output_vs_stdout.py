"""Tests for Bug S3-144: prepare_task.py --output and stdout are mutually exclusive.

When --output is provided, the file is written (the contract) and stdout
stays silent. This avoids the Windows cp1252 UnicodeEncodeError crash on
task prompts containing non-cp1252 characters (box-drawing glyphs,
em-dashes, etc.).

When --output is absent, stdout carries the content for interactive
standalone invocations.
"""

import json
from pathlib import Path

import pytest

from prepare_task import main


_MIN_BLUEPRINT_CONTRACTS = """## Unit 1: Test

### Tier 2 — Signatures

```python
def f(): ...
```
"""


@pytest.fixture
def project_root(tmp_path):
    """Minimal project-root scaffolding sufficient for _prepare_test_agent."""
    svp = tmp_path / ".svp"
    svp.mkdir()
    bp = tmp_path / "blueprint"
    bp.mkdir()
    (bp / "blueprint_contracts.md").write_text(_MIN_BLUEPRINT_CONTRACTS)
    (bp / "blueprint_prose.md").write_text("")
    (svp / "pipeline_state.json").write_text(
        json.dumps({"stage": "3", "sub_stage": "test_generation", "total_units": 1})
    )
    (tmp_path / "project_profile.json").write_text(
        json.dumps({"language": {"primary": "python"}})
    )
    return tmp_path


def test_output_flag_silences_stdout(project_root, capsys):
    """With --output, file is written AND stdout is empty (S3-144 contract)."""
    custom_output = project_root / "custom_prompt.md"
    main(
        [
            "--agent", "test_agent",
            "--project-root", str(project_root),
            "--unit", "1",
            "--output", str(custom_output),
        ]
    )
    assert custom_output.exists(), "--output path must be written"
    assert custom_output.stat().st_size > 0, "--output path must have content"

    captured = capsys.readouterr()
    assert captured.out == "", (
        f"Expected empty stdout when --output is set (Bug S3-144); "
        f"got {len(captured.out)} chars"
    )


def test_no_output_flag_prints_to_stdout(project_root, capsys):
    """Without --output, stdout carries the content for interactive use."""
    main(
        [
            "--agent", "test_agent",
            "--project-root", str(project_root),
            "--unit", "1",
        ]
    )
    captured = capsys.readouterr()
    assert len(captured.out) > 0, (
        "Expected non-empty stdout when --output is absent"
    )
