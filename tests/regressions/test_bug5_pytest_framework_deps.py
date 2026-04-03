"""Bug 9: Framework dependency completeness. Toolchain must include test framework."""

from src.unit_27.stub import PYTHON_TOOLCHAIN


def test_python_toolchain_includes_pytest():
    """Python toolchain must list pytest as a dependency."""
    deps = str(PYTHON_TOOLCHAIN)
    assert "pytest" in deps.lower()


def test_python_toolchain_includes_test_runner():
    """Python toolchain must have a test execution command."""
    testing = PYTHON_TOOLCHAIN.get("testing", {})
    assert testing, "Toolchain must have a 'testing' section"


def test_python_toolchain_testing_has_run_command():
    """Testing section must include a run_command template."""
    testing = PYTHON_TOOLCHAIN.get("testing", {})
    assert "run_command" in testing, "testing section must have 'run_command'"
    assert "pytest" in testing["run_command"], "run_command must reference pytest"


def test_python_toolchain_testing_lists_framework_packages():
    """Testing section must list framework_packages including pytest."""
    testing = PYTHON_TOOLCHAIN.get("testing", {})
    packages = testing.get("framework_packages", [])
    assert any("pytest" in p for p in packages), (
        f"framework_packages must include pytest, got {packages}"
    )
