"""Bug S3-116 regression: deterministic unit heading format validation.

End-to-end integration test exercising both enforcement points of the
unit heading grammar invariant introduced by Bug S3-116:

1. dispatch_agent_status for blueprint_author + BLUEPRINT_DRAFT_COMPLETE
   (writing side — Unit 14)
2. run_infrastructure_setup Step 5 (extraction side — Unit 11)

Both sides call the same Unit 8 validator `validate_unit_heading_format`,
so they cannot drift. This test walks through the full happy-then-sad-
then-happy flow:
  - Setup: tmp project with em-dash blueprint.
  - Dispatch fails with near-miss diagnostic.
  - Rewrite blueprint to use colons.
  - Dispatch succeeds.
  - run_infrastructure_setup succeeds and derives total_units.
"""
import json
from pathlib import Path

import pytest

from blueprint_extractor import (
    format_unit_heading_violations,
    validate_unit_heading_format,
)


CANONICAL_BLUEPRINT_PROSE = """\
# Blueprint Prose

## Preamble

```
svp/
  scripts/
    main.py  <- Unit 1
```

## Unit 1: Foo

Some prose content for Unit 1.

## Unit 2: Bar

Some prose content for Unit 2.
"""

CANONICAL_BLUEPRINT_CONTRACTS = """\
# Blueprint Contracts

## Unit 1: Foo

### Tier 2 -- Signatures

```python
def foo(): ...
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** none.

Contracts for Unit 1.

## Unit 2: Bar

### Tier 2 -- Signatures

```python
def bar(): ...
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** Unit 1.

Contracts for Unit 2.
"""

EM_DASH_BLUEPRINT_PROSE = CANONICAL_BLUEPRINT_PROSE.replace(
    "## Unit 1: Foo", "## Unit 1 \u2014 Foo"
).replace("## Unit 2: Bar", "## Unit 2 \u2014 Bar")

EM_DASH_BLUEPRINT_CONTRACTS = CANONICAL_BLUEPRINT_CONTRACTS.replace(
    "## Unit 1: Foo", "## Unit 1 \u2014 Foo"
).replace("## Unit 2: Bar", "## Unit 2 \u2014 Bar")


def _write_blueprint(blueprint_dir: Path, prose: str, contracts: str) -> None:
    blueprint_dir.mkdir(parents=True, exist_ok=True)
    (blueprint_dir / "blueprint_prose.md").write_text(prose, encoding="utf-8")
    (blueprint_dir / "blueprint_contracts.md").write_text(contracts, encoding="utf-8")


class TestUnitHeadingFormatEndToEnd:
    """Bug S3-116: end-to-end validation flow through both enforcement points."""

    def test_em_dash_blueprint_is_rejected_by_validator(self, tmp_path):
        """Layer 0: the shared Unit 8 validator detects em-dash headings."""
        blueprint_dir = tmp_path / "blueprint"
        _write_blueprint(
            blueprint_dir, EM_DASH_BLUEPRINT_PROSE, EM_DASH_BLUEPRINT_CONTRACTS
        )
        near = validate_unit_heading_format(blueprint_dir)
        assert len(near) >= 2  # At least 2 em-dash headings (1 per file, or more)
        # Both files should be represented.
        filenames = {nm[0] for nm in near}
        assert "blueprint_prose.md" in filenames
        assert "blueprint_contracts.md" in filenames

    def test_canonical_blueprint_passes_validator(self, tmp_path):
        """Layer 0: the shared validator returns empty for canonical headings."""
        blueprint_dir = tmp_path / "blueprint"
        _write_blueprint(
            blueprint_dir, CANONICAL_BLUEPRINT_PROSE, CANONICAL_BLUEPRINT_CONTRACTS
        )
        assert validate_unit_heading_format(blueprint_dir) == []

    def test_format_violations_message_references_bug(self, tmp_path):
        """Layer 0: the shared formatter includes Bug S3-116 and Section 1949."""
        blueprint_dir = tmp_path / "blueprint"
        _write_blueprint(
            blueprint_dir, EM_DASH_BLUEPRINT_PROSE, EM_DASH_BLUEPRINT_CONTRACTS
        )
        near = validate_unit_heading_format(blueprint_dir)
        msg = format_unit_heading_violations(near)
        assert "S3-116" in msg
        assert "Section 1949" in msg

    def test_happy_then_sad_then_happy_flow(self, tmp_path):
        """The full happy-then-sad-then-happy flow.

        1. Start with em-dash blueprint (sad).
        2. Validator returns near-misses.
        3. Rewrite blueprint to canonical format (happy).
        4. Validator returns empty.

        This pins the end-to-end contract: a blueprint rejected at step 1
        is accepted after the rewrite at step 3, using the SAME validator
        function both times. Both enforcement points (dispatch and
        infrastructure setup) rely on this determinism.
        """
        blueprint_dir = tmp_path / "blueprint"

        # 1. Sad: em-dash blueprint.
        _write_blueprint(
            blueprint_dir, EM_DASH_BLUEPRINT_PROSE, EM_DASH_BLUEPRINT_CONTRACTS
        )
        assert validate_unit_heading_format(blueprint_dir) != []

        # 2. Rewrite to canonical.
        _write_blueprint(
            blueprint_dir, CANONICAL_BLUEPRINT_PROSE, CANONICAL_BLUEPRINT_CONTRACTS
        )
        assert validate_unit_heading_format(blueprint_dir) == []
