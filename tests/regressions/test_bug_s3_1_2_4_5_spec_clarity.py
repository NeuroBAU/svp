"""
Regression test for Bugs S3-1, S3-2, S3-4, S3-5: Spec and blueprint must contain
clarified wording for state_hash timing and stub sentinel injection.
"""
from pathlib import Path

SPEC_PATH = Path(__file__).parent.parent.parent / "specs" / "stakeholder_spec.md"
CONTRACTS_PATH = Path(__file__).parent.parent.parent / "blueprint" / "blueprint_contracts.md"

def test_spec_state_hash_clarifies_previous_file_state():
    """S3-1/S3-5: state_hash must reference 'previous file state' or 'before the current write'."""
    spec = SPEC_PATH.read_text().lower()
    assert "previous" in spec or "before the current write" in spec, (
        "Spec must clarify state_hash is hash of previous file state"
    )

def test_spec_sentinel_injection_invariant():
    """S3-2/S3-4: Spec must mandate sentinel injection from LANGUAGE_REGISTRY."""
    spec = SPEC_PATH.read_text().lower()
    assert "sentinel injection" in spec or "stub_sentinel" in spec, (
        "Spec must document sentinel injection invariant"
    )

def test_blueprint_unit5_hash_timing():
    """S3-1/S3-5: Blueprint Unit 5 must clarify hash timing."""
    contracts = CONTRACTS_PATH.read_text().lower()
    assert "previous" in contracts or "before" in contracts, (
        "Blueprint must clarify save_state hash timing"
    )

def test_blueprint_sentinel_from_registry():
    """S3-2/S3-4: Blueprint must reference LANGUAGE_REGISTRY sentinel."""
    contracts = CONTRACTS_PATH.read_text().lower()
    assert "stub_sentinel" in contracts or "language_registry" in contracts, (
        "Blueprint must reference sentinel from LANGUAGE_REGISTRY"
    )
