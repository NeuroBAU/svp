# Blueprint Extractor -- Unit 5
# Extracts unit definitions and upstream contract signatures from the blueprint.

import re
from typing import Optional, Dict, Any, List
from pathlib import Path


class UnitDefinition:
    """A single unit's complete definition extracted from the blueprint."""
    unit_number: int
    unit_name: str
    artifact_category: str    # e.g., "Python script", "Markdown (AGENT.md files)"
    description: str          # Tier 1
    signatures: str           # Tier 2 code block (raw Python)
    invariants: str           # Tier 2 invariants code block
    error_conditions: str     # Tier 3
    behavioral_contracts: str # Tier 3
    dependencies: List[int]   # upstream unit numbers

    def __init__(self, **kwargs: Any) -> None:
        self.unit_number = kwargs.get("unit_number", 0)
        self.unit_name = kwargs.get("unit_name", "")
        self.artifact_category = kwargs.get("artifact_category", "")
        self.description = kwargs.get("description", "")
        self.signatures = kwargs.get("signatures", "")
        self.invariants = kwargs.get("invariants", "")
        self.error_conditions = kwargs.get("error_conditions", "")
        self.behavioral_contracts = kwargs.get("behavioral_contracts", "")
        self.dependencies = kwargs.get("dependencies", [])


def _extract_code_block(text: str) -> str:
    """Extract the content of the first fenced code block in text."""
    match = re.search(r"```[a-zA-Z]*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _parse_dependencies_section(text: str) -> List[int]:
    """Parse a dependencies section to extract upstream unit numbers."""
    # Look for patterns like "Unit N" references or "(no deps)"
    if not text.strip() or "None" in text.split("\n")[0] or "(no deps)" in text:
        return []
    # Find all "Unit N" references
    matches = re.findall(r"\*\*Unit\s+(\d+)", text)
    return [int(m) for m in matches]


def _parse_dependencies_from_graph(blueprint_text: str, unit_number: int) -> List[int]:
    """Parse dependencies from the dependency graph section of the blueprint."""
    # Look for the dependency graph section
    graph_match = re.search(r"### Dependency Graph\s*\n```\n(.*?)```", blueprint_text, re.DOTALL)
    if not graph_match:
        return []
    graph_text = graph_match.group(1)
    # Find the line for this unit
    pattern = rf"Unit\s+{unit_number}:.*?depends on:\s*([\d,\s]+)"
    match = re.search(pattern, graph_text)
    if match:
        deps_str = match.group(1)
        return [int(d.strip()) for d in deps_str.split(",") if d.strip()]
    # Check for "(no deps)" pattern
    pattern_no_deps = rf"Unit\s+{unit_number}:.*?\(no deps\)"
    if re.search(pattern_no_deps, graph_text):
        return []
    return []


def _split_units(blueprint_text: str) -> List[tuple]:
    """Split blueprint text into unit sections. Returns list of (unit_number, unit_name, section_text)."""
    # Pattern: ## Unit N: Name
    pattern = r"^## Unit (\d+):\s*(.+)$"
    matches = list(re.finditer(pattern, blueprint_text, re.MULTILINE))
    if not matches:
        return []

    result = []
    for i, match in enumerate(matches):
        unit_number = int(match.group(1))
        unit_name = match.group(2).strip()
        start = match.start()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(blueprint_text)
        section_text = blueprint_text[start:end]
        result.append((unit_number, unit_name, section_text))
    return result


def _extract_section(text: str, heading_pattern: str) -> str:
    """Extract content under a ### heading until the next ### heading or end of text."""
    pattern = rf"^{heading_pattern}\s*$"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    # Find next ### heading or --- separator or end
    next_heading = re.search(r"^###\s|^---\s*$", text[start:], re.MULTILINE)
    if next_heading:
        end = start + next_heading.start()
    else:
        end = len(text)
    return text[start:end].strip()


def _parse_unit_section(unit_number: int, unit_name: str, section_text: str,
                        full_blueprint: str) -> UnitDefinition:
    """Parse a unit section into a UnitDefinition."""
    # Extract artifact_category from **Artifact category:** line
    artifact_match = re.search(r"\*\*Artifact category:\*\*\s*(.+)", section_text)
    artifact_category = artifact_match.group(1).strip() if artifact_match else ""

    # Extract Tier 1 -- Description
    description = _extract_section(section_text, r"### Tier 1 -- Description")

    # Extract Tier 2 -- Signatures (note: em-dash)
    signatures_section = _extract_section(section_text, r"### Tier 2 \u2014 Signatures")
    signatures = _extract_code_block(signatures_section) if signatures_section else ""

    # Extract Tier 2 -- Invariants (try em-dash first, then double-hyphen)
    invariants_section = _extract_section(section_text, r"### Tier 2 \u2014 Invariants")
    if not invariants_section:
        invariants_section = _extract_section(section_text, r"### Tier 2 -- Invariants")
    invariants = _extract_code_block(invariants_section) if invariants_section else ""

    # Extract Tier 3 -- Error Conditions
    error_conditions = _extract_section(section_text, r"### Tier 3 -- Error Conditions")

    # Extract Tier 3 -- Behavioral Contracts
    behavioral_contracts = _extract_section(section_text, r"### Tier 3 -- Behavioral Contracts")

    # Extract dependencies from Tier 3 -- Dependencies section
    deps_section = _extract_section(section_text, r"### Tier 3 -- Dependencies")
    dependencies = _parse_dependencies_section(deps_section)

    # If no dependencies found from a dedicated section, check behavioral contracts
    # for inline "- Dependencies: [1, 2]" patterns
    if not dependencies and behavioral_contracts:
        dep_match = re.search(r"Dependencies:\s*\[([^\]]*)\]", behavioral_contracts)
        if dep_match:
            dep_str = dep_match.group(1).strip()
            if dep_str:
                dependencies = [int(d.strip()) for d in dep_str.split(",") if d.strip()]

    # If still no dependencies, try the dependency graph
    if not dependencies:
        dependencies = _parse_dependencies_from_graph(full_blueprint, unit_number)

    return UnitDefinition(
        unit_number=unit_number,
        unit_name=unit_name,
        artifact_category=artifact_category,
        description=description,
        signatures=signatures,
        invariants=invariants,
        error_conditions=error_conditions,
        behavioral_contracts=behavioral_contracts,
        dependencies=dependencies,
    )


def parse_blueprint(blueprint_path: Path) -> List[UnitDefinition]:
    """Read the full blueprint and parse all unit definitions into UnitDefinition instances."""
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")

    blueprint_text = blueprint_path.read_text(encoding="utf-8")
    unit_sections = _split_units(blueprint_text)

    if not unit_sections:
        raise ValueError("Blueprint has no parseable unit definitions")

    result = []
    for unit_number, unit_name, section_text in unit_sections:
        unit_def = _parse_unit_section(unit_number, unit_name, section_text, blueprint_text)
        result.append(unit_def)

    assert len(result) > 0, "Blueprint must contain at least one unit"
    assert all(u.unit_number > 0 for u in result), "All unit numbers must be positive"

    return result


def extract_unit(blueprint_path: Path, unit_number: int) -> UnitDefinition:
    """Return a single unit's definition. Delegates to parse_blueprint internally."""
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")
    if unit_number < 1:
        raise ValueError(f"Unit {unit_number} not found in blueprint")

    units = parse_blueprint(blueprint_path)
    for unit in units:
        if unit.unit_number == unit_number:
            assert unit.unit_number == unit_number, "Extracted unit number must match request"
            assert len(unit.signatures) > 0, "Unit must have non-empty signatures"
            return unit

    raise ValueError(f"Unit {unit_number} not found in blueprint")


def extract_upstream_contracts(
    blueprint_path: Path, unit_number: int
) -> List[Dict[str, str]]:
    """Return Tier 2 signatures for all units listed in the requested unit's dependencies."""
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")
    if unit_number < 1:
        raise ValueError(f"Unit {unit_number} not found in blueprint")

    units = parse_blueprint(blueprint_path)
    units_by_number = {u.unit_number: u for u in units}

    if unit_number not in units_by_number:
        raise ValueError(f"Unit {unit_number} not found in blueprint")

    target_unit = units_by_number[unit_number]
    result = []
    for dep_number in target_unit.dependencies:
        if dep_number in units_by_number:
            dep_unit = units_by_number[dep_number]
            result.append({
                "unit_number": str(dep_number),
                "unit_name": dep_unit.unit_name,
                "signatures": dep_unit.signatures,
            })

    return result


def build_unit_context(
    blueprint_path: Path, unit_number: int
) -> str:
    """Produce a formatted string containing the unit's full definition followed by upstream contracts."""
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")
    if unit_number < 1:
        raise ValueError(f"Unit {unit_number} not found in blueprint")

    unit = extract_unit(blueprint_path, unit_number)
    upstream = extract_upstream_contracts(blueprint_path, unit_number)

    parts = []
    parts.append(f"## Unit {unit.unit_number}: {unit.unit_name}")
    parts.append("")

    if unit.description:
        parts.append("### Tier 1 -- Description")
        parts.append("")
        parts.append(unit.description)
        parts.append("")

    if unit.signatures:
        parts.append("### Tier 2 \u2014 Signatures")
        parts.append("")
        parts.append("```python")
        parts.append(unit.signatures)
        parts.append("```")
        parts.append("")

    if unit.invariants:
        parts.append("### Tier 2 \u2014 Invariants")
        parts.append("")
        parts.append("```python")
        parts.append(unit.invariants)
        parts.append("```")
        parts.append("")

    if unit.error_conditions:
        parts.append("### Tier 3 -- Error Conditions")
        parts.append("")
        parts.append(unit.error_conditions)
        parts.append("")

    if unit.behavioral_contracts:
        parts.append("### Tier 3 -- Behavioral Contracts")
        parts.append("")
        parts.append(unit.behavioral_contracts)
        parts.append("")

    if upstream:
        parts.append("## Upstream Contracts")
        parts.append("")
        for contract in upstream:
            parts.append(f"### Unit {contract['unit_number']}: {contract['unit_name']}")
            parts.append("")
            parts.append("```python")
            parts.append(contract["signatures"])
            parts.append("```")
            parts.append("")

    result = "\n".join(parts)
    assert len(result) > 0, "Unit context must be non-empty"
    return result
