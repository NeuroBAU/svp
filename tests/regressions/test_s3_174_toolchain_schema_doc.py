"""S3-174 — toolchain manifest schema doc must exist and cover required fields."""
from pathlib import Path
import pytest


def _locate_schema_doc() -> Path:
    """Walk up from this test file to find the schema doc in workspace or repo."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        # Workspace layout
        candidate = parent / "references" / "toolchain_manifest_schema.md"
        if candidate.exists():
            return candidate
        # Repo layout (synced to docs/references/)
        candidate = parent / "docs" / "references" / "toolchain_manifest_schema.md"
        if candidate.exists():
            return candidate
    raise RuntimeError("Could not locate references/toolchain_manifest_schema.md")


REQUIRED_TOP_LEVEL_KEYS = [
    "toolchain_id",
    "language",
    "environment",
    "framework_packages",
    "quality",
    "testing",
    "file_structure",
    "language_architecture_primers",  # NEW IN S3-174
]

REQUIRED_PRIMER_SUBKEYS = [
    "blueprint_author",
    "implementation_agent",
    "test_agent",
    "coverage_review",
    "orchestrator_break_glass",
]


def test_toolchain_manifest_schema_doc_exists():
    schema = _locate_schema_doc()
    assert schema.is_file()
    text = schema.read_text(encoding="utf-8")
    assert len(text) > 100, "schema doc is suspiciously short"


@pytest.mark.parametrize("key", REQUIRED_TOP_LEVEL_KEYS)
def test_toolchain_manifest_schema_doc_mentions_top_level_key(key):
    text = _locate_schema_doc().read_text(encoding="utf-8")
    assert key in text, f"schema doc missing top-level key: {key}"


@pytest.mark.parametrize("subkey", REQUIRED_PRIMER_SUBKEYS)
def test_toolchain_manifest_schema_doc_mentions_primer_subkey(subkey):
    text = _locate_schema_doc().read_text(encoding="utf-8")
    assert subkey in text, f"schema doc missing primer sub-key: {subkey}"


def test_toolchain_manifest_schema_doc_locks_templated_helpers_convention():
    text = _locate_schema_doc().read_text(encoding="utf-8")
    assert "scripts/toolchain_defaults/templates" in text


def test_toolchain_manifest_schema_doc_locks_verify_commands_convention():
    text = _locate_schema_doc().read_text(encoding="utf-8")
    assert "{run_prefix}" in text
    assert "verify_commands" in text
