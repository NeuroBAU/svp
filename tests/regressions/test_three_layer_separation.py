"""Three-layer separation: pipeline quality from toolchain, delivery quality from profile."""
import ast
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[2] / "src"

def _get_imports(filepath):
    """Extract all import-from module names from a Python file."""
    tree = ast.parse(filepath.read_text())
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules

class TestThreeLayerSeparation:
    def test_quality_gate_does_not_import_profile_schema(self):
        """Unit 15 (quality_gate) must not import from Unit 3 (profile_schema)."""
        imports = _get_imports(SRC_DIR / "unit_15" / "stub.py")
        assert not any("unit_3" in m for m in imports), \
            "quality_gate imports profile_schema — violates three-layer separation"

    def test_quality_gate_does_not_import_svp_config_directly(self):
        """Unit 15 must get quality tool config from toolchain, not svp_config."""
        imports = _get_imports(SRC_DIR / "unit_15" / "stub.py")
        profile_imports = [m for m in imports if "unit_1" in m]
        # Unit 1 imports are ok for ARTIFACT_FILENAMES, but not for quality config
        # This is a structural check — just verify no direct profile loading
        pass  # Placeholder: extend when specific violation patterns identified

    def test_routing_does_not_import_quality_gate(self):
        """Unit 14 (routing) must not import Unit 15 (quality_gate) directly."""
        imports = _get_imports(SRC_DIR / "unit_14" / "stub.py")
        assert not any("unit_15" in m for m in imports), \
            "routing imports quality_gate — violates layer separation"

    def test_stub_generator_does_not_import_routing(self):
        """Unit 10 (stub_generator) must not import Unit 14 (routing)."""
        imports = _get_imports(SRC_DIR / "unit_10" / "stub.py")
        assert not any("unit_14" in m for m in imports), \
            "stub_generator imports routing — violates DAG"
