"""Regression test for Bug S3-50: Pass 2 repo must contain environment.yml."""
from pathlib import Path

PASS2_REPO = Path(__file__).parent.parent.parent.parent / "svp2.2-pass2-repo"

def test_pass2_repo_has_environment_yml():
    """S3-50: Pass 2 repo must contain environment.yml."""
    if not PASS2_REPO.exists():
        import pytest
        pytest.skip("Pass 2 repo not present")
    assert (PASS2_REPO / "environment.yml").exists(), "Pass 2 repo missing environment.yml"
