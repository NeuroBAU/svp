"""
Regression test for Bug S3-10: stub generator must assign default values
to module-level annotated constants for importability.
"""
import ast
from stub_generator import generate_stub
from language_registry import LANGUAGE_REGISTRY


def test_dict_constant_gets_empty_dict_default():
    """S3-10: Dict-annotated constant must get {} default."""
    source = 'REGISTRY: Dict[str, Any]\n'
    parsed = ast.parse(source)
    config = LANGUAGE_REGISTRY["python"]
    result = generate_stub(parsed, "python", config)
    assert "REGISTRY: Dict[str, Any] = {}" in result


def test_list_constant_gets_empty_list_default():
    """S3-10: List-annotated constant must get [] default."""
    source = 'ITEMS: List[int]\n'
    parsed = ast.parse(source)
    config = LANGUAGE_REGISTRY["python"]
    result = generate_stub(parsed, "python", config)
    assert "ITEMS: List[int] = []" in result


def test_str_constant_gets_empty_string_default():
    """S3-10: str-annotated constant must get empty string default."""
    source = 'NAME: str\n'
    parsed = ast.parse(source)
    config = LANGUAGE_REGISTRY["python"]
    result = generate_stub(parsed, "python", config)
    assert 'NAME: str = ""' in result


def test_other_constant_gets_none_default():
    """S3-10: Unknown type constant must get None default."""
    source = 'THING: SomeCustomType\n'
    parsed = ast.parse(source)
    config = LANGUAGE_REGISTRY["python"]
    result = generate_stub(parsed, "python", config)
    assert "THING: SomeCustomType = None" in result


def test_constant_with_existing_value_preserves_it():
    """S3-10: Constants that already have values should keep them."""
    source = 'COUNT: int = 42\n'
    parsed = ast.parse(source)
    config = LANGUAGE_REGISTRY["python"]
    result = generate_stub(parsed, "python", config)
    assert "COUNT: int = 42" in result
