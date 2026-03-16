# Blueprint Extractor -- Unit 5
# Zero dependencies: standalone parser.
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class UnitDefinition:
    """Parsed unit definition from the blueprint."""

    unit_number: int
    unit_name: str
    artifact_category: str
    description: str
    signatures: str
    invariants: str
    error_conditions: str
    behavioral_contracts: str
    dependencies: List[int]

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


# ----------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------

_UNIT_HEADING_RE = re.compile(r"^##\s+Unit\s+(\d+):\s*(.+)$", re.MULTILINE)

_TIER_HEADING_RE = re.compile(
    r"^###\s+Tier\s+(\d+)\s*[-\u2014\u2013]+\s*(.*)$",
    re.MULTILINE,
)

_ARTIFACT_RE = re.compile(
    r"\*\*Artifact\s+category:\*\*\s*(.+)$",
    re.MULTILINE,
)

_DEP_UNIT_RE = re.compile(r"\*\*Unit\s+(\d+)")


def _resolve_content(
    blueprint_dir: Path,
    contracts_path: Optional[Path] = None,
) -> str:
    """Read blueprint content, handling both API styles.

    Accepts either:
    - A directory path (globs *.md files inside it)
    - A file path (reads that file, plus optional
      contracts_path)
    """
    if blueprint_dir.is_dir():
        md_files = sorted(blueprint_dir.glob("*.md"))
        if not md_files:
            raise FileNotFoundError(
                f"No .md files found in blueprint directory: {blueprint_dir}"
            )
        parts: list[str] = []
        for p in md_files:
            parts.append(p.read_text(encoding="utf-8"))
        return "\n\n".join(parts)

    if blueprint_dir.is_file():
        content = blueprint_dir.read_text(encoding="utf-8")
        if contracts_path is not None and (contracts_path.is_file()):
            extra = contracts_path.read_text(encoding="utf-8")
            content = content + "\n\n" + extra
        return content

    raise FileNotFoundError(f"Blueprint directory not found: {blueprint_dir}")


def _split_units(
    content: str,
) -> List[Dict[str, Any]]:
    """Split combined content into per-unit sections."""
    matches = list(_UNIT_HEADING_RE.finditer(content))
    if not matches:
        raise ValueError("Blueprint has no parseable unit definitions")

    # Merge sections for the same unit number
    # (prose + contracts may both have ## Unit N:).
    raw_by_num: Dict[int, Dict[str, Any]] = {}
    order: list[int] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        num = int(m.group(1))
        name = m.group(2).strip()
        raw = content[start:end]
        if num in raw_by_num:
            raw_by_num[num]["raw"] += "\n\n" + raw
        else:
            raw_by_num[num] = {
                "unit_number": num,
                "unit_name": name,
                "raw": raw,
            }
            order.append(num)

    return [raw_by_num[n] for n in order]


def _extract_artifact_category(raw: str) -> str:
    m = _ARTIFACT_RE.search(raw)
    return m.group(1).strip() if m else ""


def _extract_tier_sections(
    raw: str,
) -> Dict[str, str]:
    """Extract content under each ### Tier heading."""
    tier_matches = list(_TIER_HEADING_RE.finditer(raw))
    sections: Dict[str, str] = {}
    for i, m in enumerate(tier_matches):
        tier_num = m.group(1)
        label = m.group(2).strip().lower()
        start = m.end()
        end = len(raw)
        if i + 1 < len(tier_matches):
            end = tier_matches[i + 1].start()
        # Also cap at next ## Unit heading.
        next_unit = _UNIT_HEADING_RE.search(raw, m.end())
        if next_unit and next_unit.start() < end:
            end = next_unit.start()

        block = raw[start:end].strip()
        key = _tier_key(tier_num, label)
        # Merge if key already exists (e.g. from
        # multiple files with same tier headings).
        if key in sections:
            sections[key] += "\n\n" + block
        else:
            sections[key] = block
    return sections


def _tier_key(tier_num: str, label: str) -> str:
    """Map tier number + label to field name."""
    if tier_num == "1":
        return "description"
    if tier_num == "2":
        if "invariant" in label:
            return "invariants"
        return "signatures"
    # tier_num == "3"
    if "error" in label:
        return "error_conditions"
    if "depend" in label:
        return "dependencies_raw"
    if "behav" in label or "contract" in label:
        return "behavioral_contracts"
    return f"tier3_{label}"


def _parse_dependencies(raw: str) -> List[int]:
    """Extract dependency unit numbers from raw text."""
    dep_section = ""
    tier_matches = list(_TIER_HEADING_RE.finditer(raw))
    for i, m in enumerate(tier_matches):
        label = m.group(2).strip().lower()
        if "depend" in label:
            start = m.end()
            end = len(raw)
            if i + 1 < len(tier_matches):
                end = tier_matches[i + 1].start()
            next_unit = _UNIT_HEADING_RE.search(raw, m.end())
            if next_unit and next_unit.start() < end:
                end = next_unit.start()
            dep_section = raw[start:end].strip()
            break

    if not dep_section:
        return []
    # Check all lines; "None." means no deps.
    stripped = dep_section.strip().rstrip(".")
    if stripped.lower() == "none":
        return []

    nums = _DEP_UNIT_RE.findall(dep_section)
    return sorted(set(int(n) for n in nums))


def _build_unit_def(
    unit_info: Dict[str, Any],
) -> UnitDefinition:
    raw = unit_info["raw"]
    sections = _extract_tier_sections(raw)
    return UnitDefinition(
        unit_number=unit_info["unit_number"],
        unit_name=unit_info["unit_name"],
        artifact_category=_extract_artifact_category(raw),
        description=sections.get("description", ""),
        signatures=sections.get("signatures", ""),
        invariants=sections.get("invariants", ""),
        error_conditions=sections.get("error_conditions", ""),
        behavioral_contracts=sections.get("behavioral_contracts", ""),
        dependencies=_parse_dependencies(raw),
    )


# ----------------------------------------------------------
# Public API
# ----------------------------------------------------------


def parse_blueprint(
    blueprint_dir: Path,
    include_tier1: bool = True,
    contracts_path: Optional[Path] = None,
) -> List[UnitDefinition]:
    """Parse all unit definitions from the blueprint.

    Args:
        blueprint_dir: Path to blueprint directory or
            a single blueprint .md file.
        include_tier1: Whether to include Tier 1
            description content.
        contracts_path: Optional path to a second .md
            file containing Tier 2/3 content.
    """
    content = _resolve_content(blueprint_dir, contracts_path)
    raw_units = _split_units(content)
    result: List[UnitDefinition] = []
    for info in raw_units:
        ud = _build_unit_def(info)
        if not include_tier1:
            ud.description = ""
        result.append(ud)
    return result


def extract_unit(
    blueprint_dir: Path,
    unit_number: int,
    include_tier1: bool = True,
    contracts_path: Optional[Path] = None,
) -> UnitDefinition:
    """Extract a single unit definition."""
    units = parse_blueprint(
        blueprint_dir,
        include_tier1=include_tier1,
        contracts_path=contracts_path,
    )
    for u in units:
        if u.unit_number == unit_number:
            return u
    raise ValueError(f"Unit {unit_number} not found in blueprint")


def extract_upstream_contracts(
    blueprint_dir: Path,
    unit_number: int,
    include_tier1: bool = True,
    contracts_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Return Tier 2 signatures for upstream deps."""
    target = extract_unit(
        blueprint_dir,
        unit_number,
        include_tier1=True,
        contracts_path=contracts_path,
    )
    all_units = parse_blueprint(
        blueprint_dir,
        include_tier1=include_tier1,
        contracts_path=contracts_path,
    )
    unit_map = {u.unit_number: u for u in all_units}
    contracts: List[Dict[str, Any]] = []
    for dep_num in target.dependencies:
        dep = unit_map.get(dep_num)
        if dep is None:
            continue
        entry: Dict[str, Any] = {
            "unit_number": str(dep.unit_number),
            "unit_name": dep.unit_name,
            "signatures": dep.signatures,
        }
        if include_tier1:
            entry["description"] = dep.description
        contracts.append(entry)
    return contracts


def build_unit_context(
    blueprint_dir: Path,
    unit_number: int,
    include_tier1: bool = True,
    contracts_path: Optional[Path] = None,
) -> str:
    """Build formatted context string for a task prompt."""
    unit = extract_unit(
        blueprint_dir,
        unit_number,
        include_tier1=True,
        contracts_path=contracts_path,
    )
    upstream = extract_upstream_contracts(
        blueprint_dir,
        unit_number,
        include_tier1=include_tier1,
        contracts_path=contracts_path,
    )

    lines: list[str] = []
    lines.append(f"## Unit {unit.unit_number}: {unit.unit_name}")
    lines.append("")
    if unit.artifact_category:
        lines.append(f"**Artifact category:** {unit.artifact_category}")
        lines.append("")

    if include_tier1 and unit.description:
        lines.append("### Tier 1 -- Description")
        lines.append("")
        lines.append(unit.description)
        lines.append("")

    if unit.signatures:
        lines.append("### Tier 2 -- Signatures")
        lines.append("")
        lines.append(unit.signatures)
        lines.append("")

    if unit.invariants:
        lines.append("### Tier 2 -- Invariants")
        lines.append("")
        lines.append(unit.invariants)
        lines.append("")

    if unit.error_conditions:
        lines.append("### Tier 3 -- Error Conditions")
        lines.append("")
        lines.append(unit.error_conditions)
        lines.append("")

    if unit.behavioral_contracts:
        lines.append("### Tier 3 -- Behavioral Contracts")
        lines.append("")
        lines.append(unit.behavioral_contracts)
        lines.append("")

    if upstream:
        lines.append("## Upstream Dependencies")
        lines.append("")
        for dep in upstream:
            lines.append(f"### Unit {dep['unit_number']}: {dep['unit_name']}")
            lines.append("")
            if include_tier1 and dep.get("description"):
                lines.append(dep["description"])
                lines.append("")
            if dep.get("signatures"):
                lines.append("#### Tier 2 -- Signatures")
                lines.append("")
                lines.append(dep["signatures"])
                lines.append("")

    result = "\n".join(lines)
    assert len(result) > 0, "Unit context must be non-empty"
    return result
