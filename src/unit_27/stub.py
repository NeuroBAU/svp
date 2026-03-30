"""Unit 27: Project Templates.

Language-specific toolchain default files, delivery quality templates,
and the pipeline ruff.toml configuration. Provides render_template for
{{variable_name}} placeholder substitution.

Dependencies: Unit 2.
"""

import re
from typing import Any, Dict

# ---------------------------------------------------------------------------
# PYTHON_TOOLCHAIN -- python_conda_pytest.json content
# ---------------------------------------------------------------------------
PYTHON_TOOLCHAIN: Dict[str, Any] = {
    "toolchain_id": "python_conda_pytest",
    "environment": {
        "tool": "conda",
        "run_prefix": "conda run -n {env_name}",
        "create_command": "conda create -n {env_name} python={python_version} -y",
        "install_command": "conda run -n {env_name} pip install {packages}",
        "install_dev": "conda run -n {env_name} pip install -e .",
        "cleanup_command": "conda env remove -n {env_name} -y",
    },
    "quality": {
        "formatter": {
            "tool": "ruff",
            "format": "{run_prefix} ruff format {target}",
            "check": "{run_prefix} ruff format --check {target}",
        },
        "linter": {
            "tool": "ruff",
            "light": "{run_prefix} ruff check --select E,F,I --fix {target}",
            "heavy": "{run_prefix} ruff check --fix {target}",
            "check": "{run_prefix} ruff check {target}",
            "unused_exports": "{run_prefix} ruff check {target} --select F811",
        },
        "type_checker": {
            "tool": "mypy",
            "check": "{run_prefix} mypy {flags} {target}",
            "unit_flags": "--ignore-missing-imports",
            "project_flags": "",
        },
        "packages": ["ruff", "mypy"],
        "gate_a": ["formatter.format", "linter.light"],
        "gate_b": [
            "formatter.format",
            "linter.heavy",
            "type_checker.check",
        ],
        "gate_c": [
            "formatter.check",
            "linter.check",
            "type_checker.check",
        ],
    },
    "testing": {
        "tool": "pytest",
        "run_command": "{run_prefix} python -m pytest {test_path} -v",
        "run_coverage": (
            "{run_prefix} python -m pytest {test_path} -v "
            "--cov={module} --cov-report=term-missing"
        ),
        "framework_packages": ["pytest", "pytest-cov"],
        "file_pattern": "test_*.py",
        "collection_error_indicators": [
            "ERROR collecting",
            "ImportError",
            "ModuleNotFoundError",
            "SyntaxError",
            "no tests ran",
            "collection error",
        ],
        "pass_fail_pattern": "(\\d+) passed",
        "unit_flags": "-v --tb=short",
        "project_flags": "-v",
    },
    "packaging": {
        "tool": "setuptools",
        "manifest_file": "pyproject.toml",
        "build_backend": "setuptools.build_meta",
        "validate_command": "{run_prefix} pip install -e .",
    },
    "vcs": {
        "tool": "git",
        "commands": {
            "init": "git init",
            "add": "git add {files}",
            "commit": 'git commit -m "{message}"',
            "status": "git status",
        },
    },
    "language": {
        "name": "python",
        "extension": ".py",
        "version_constraint": ">=3.9",
        "signature_parser": "ast",
        "stub_body": "raise NotImplementedError",
    },
    "file_structure": {
        "source_dir_pattern": "src/unit_{n}",
        "test_dir_pattern": "tests/unit_{n}",
        "source_extension": ".py",
        "test_extension": ".py",
    },
}


# ---------------------------------------------------------------------------
# R_TOOLCHAIN -- r_renv_testthat.json content
# ---------------------------------------------------------------------------
R_TOOLCHAIN: Dict[str, Any] = {
    "toolchain_id": "r_renv_testthat",
    "environment": {
        "tool": "renv",
        "run_prefix": "Rscript -e",
        "create_command": "Rscript -e 'renv::init()'",
        "install_command": "Rscript -e 'renv::install(\"{package}\")'",
        "cleanup_command": 'Rscript -e "renv::deactivate()"',
    },
    "quality": {
        "formatter": {
            "tool": "styler",
            "format": "Rscript -e 'styler::style_dir(\"R/\")'",
            "check": 'Rscript -e \'styler::style_dir("R/", dry="check")\'',
        },
        "linter": {
            "tool": "lintr",
            "light": "Rscript -e 'lintr::lint_dir(\"R/\")'",
            "heavy": "Rscript -e 'lintr::lint_dir(\"R/\")'",
            "check": "Rscript -e 'lintr::lint_dir(\"R/\")'",
        },
        "type_checker": {
            "tool": "none",
        },
        "packages": ["lintr", "styler"],
        "gate_a": ["formatter.format"],
        "gate_b": ["formatter.format", "linter.light"],
        "gate_c": ["formatter.check", "linter.check"],
    },
    "testing": {
        "tool": "testthat",
        "run_command": "Rscript -e 'testthat::test_dir(\"tests/testthat\")'",
        "run_coverage": "Rscript -e 'covr::package_coverage()'",
        "framework_packages": ["testthat", "covr"],
        "file_pattern": "test-*.R",
        "collection_error_indicators": [
            "Error in library",
            "there is no package called",
            "could not find function",
        ],
        "unit_flags": "",
        "project_flags": "",
    },
    "packaging": {
        "tool": "devtools",
        "manifest_file": "DESCRIPTION",
        "build_backend": "devtools::build",
        "validate_command": "Rscript -e 'devtools::check()'",
    },
    "vcs": {
        "tool": "git",
        "commands": {
            "init": "git init",
            "add": "git add {files}",
            "commit": 'git commit -m "{message}"',
            "status": "git status",
        },
    },
    "language": {
        "name": "r",
        "extension": ".R",
        "version_constraint": ">=4.0",
        "stub_body": "stop('Not implemented')",
    },
    "file_structure": {
        "source_dir_pattern": "R",
        "test_dir_pattern": "tests/testthat",
        "source_extension": ".R",
        "test_extension": ".R",
    },
}


# ---------------------------------------------------------------------------
# PIPELINE_RUFF_TOML -- ruff.toml content string
# ---------------------------------------------------------------------------
PIPELINE_RUFF_TOML: str = """\
line-length = 88
target-version = "py311"

[lint]
select = ["E", "F", "W", "I"]
ignore = []

[format]
quote-style = "double"
indent-style = "space"
"""


# ---------------------------------------------------------------------------
# DELIVERY_QUALITY_TEMPLATES -- per-language quality config templates
# ---------------------------------------------------------------------------
DELIVERY_QUALITY_TEMPLATES: Dict[str, Dict[str, str]] = {
    "python": {
        "ruff.toml.template": """\
line-length = {{line_length}}
target-version = "py311"

[lint]
select = ["E", "F", "W", "I"]
ignore = []

[format]
quote-style = "double"
indent-style = "space"
""",
        "flake8.template": """\
[flake8]
max-line-length = {{line_length}}
extend-ignore = E203,W503
exclude =
    .git,
    __pycache__,
    build,
    dist
""",
        "mypy.ini.template": """\
[mypy]
python_version = {{python_version}}
warn_return_any = True
warn_unused_configs = True
ignore_missing_imports = {{ignore_missing_imports}}
""",
        "pyproject_black.toml.template": """\
[tool.black]
line-length = {{line_length}}
target-version = ["py311"]
""",
    },
    "r": {
        "lintr.template": """\
linters: linters_with_defaults(
    line_length_linter({{line_length}}),
    object_name_linter(styles = "snake_case")
  )
""",
        "styler.template": """\
style <- styler::tidyverse_style(
  indent_by = {{indent_by}}
)
""",
    },
}


# ---------------------------------------------------------------------------
# render_template
# ---------------------------------------------------------------------------
def render_template(
    template_content: str,
    variables: Dict[str, str],
) -> str:
    """Substitute ``{{variable_name}}`` placeholders in *template_content*.

    Parameters
    ----------
    template_content : str
        Template text with ``{{variable_name}}`` placeholders.
    variables : dict
        Mapping of variable names to replacement values.

    Returns
    -------
    str
        Rendered template with all placeholders substituted.

    Raises
    ------
    ValueError
        If any ``{{...}}`` placeholders remain unresolved after
        substitution.
    """
    # Find all placeholder names in the original template
    original_placeholders = set(re.findall(r"\{\{(\w+)\}\}", template_content))

    # Check for unresolved placeholders (present in template but not in variables)
    unresolved = original_placeholders - set(variables.keys())
    if unresolved:
        raise ValueError(
            f"Unresolved template placeholders: {', '.join(sorted(unresolved))}"
        )

    # Perform substitution
    result = template_content
    for name, value in variables.items():
        result = result.replace("{{" + name + "}}", str(value))

    return result
