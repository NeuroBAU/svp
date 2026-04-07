"""Regression test for Bug S3-100: run_tests_main wrong toolchain keys."""
import inspect
import json
from pathlib import Path


def test_run_tests_main_reads_testing_key():
    """S3-100: run_tests_main must read from toolchain['testing'], not toolchain['test']."""
    from routing import run_tests_main
    source = inspect.getsource(run_tests_main)
    assert '"testing"' in source or "'testing'" in source, (
        "run_tests_main must read test command from toolchain['testing'] section"
    )
    assert '.get("test",' not in source, (
        "run_tests_main must NOT use toolchain.get('test', ...) — use 'testing'"
    )


def test_run_tests_main_reads_run_command_key():
    """S3-100: run_tests_main must read 'run_command', not 'command'."""
    from routing import run_tests_main
    source = inspect.getsource(run_tests_main)
    assert '"run_command"' in source or "'run_command'" in source, (
        "run_tests_main must read toolchain['testing']['run_command']"
    )


def test_run_tests_main_reads_run_prefix_from_environment():
    """S3-100: run_tests_main must read run_prefix from environment section."""
    from routing import run_tests_main
    source = inspect.getsource(run_tests_main)
    assert '"environment"' in source or "'environment'" in source, (
        "run_tests_main must read run_prefix from toolchain['environment']"
    )


def test_run_tests_main_normalizes_test_path_placeholder():
    """S3-100: run_tests_main must normalize {test_path} to {target}."""
    from routing import run_tests_main
    source = inspect.getsource(run_tests_main)
    assert "test_path" in source and "target" in source, (
        "run_tests_main must normalize {test_path} placeholder to {target}"
    )


def test_toolchain_defaults_use_testing_key():
    """S3-100: Production toolchain JSON files must use 'testing' key."""
    defaults_dir = Path(__file__).parent.parent.parent / "scripts" / "toolchain_defaults"
    for json_file in defaults_dir.glob("*.json"):
        data = json.loads(json_file.read_text())
        if "testing" in data:
            assert "run_command" in data["testing"], (
                f"{json_file.name} has 'testing' but missing 'run_command'"
            )
        assert "test" not in data or isinstance(data.get("test"), str), (
            f"{json_file.name} must not have a 'test' dict section — use 'testing'"
        )
