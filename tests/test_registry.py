"""Tests for the registry module.

A client could receive a successful response with a schema that tells it 
to send the wrong type or omit a required argument.
"""

from app.tools.registry import ToolRegistry


def greet(name: str, times: int = 1) -> str:
    """Repeat a greeting."""
    return " ".join([f"Hello, {name}!"] * times)

def test_registry():
    registry = ToolRegistry()
    registry.register(greet)
    manifest = registry.get_manifest()
    assert len(manifest) == 1
    assert manifest[0]["name"] == "greet"
    assert manifest[0]["description"] == "Repeat a greeting."

    parameters = manifest[0]["parameters"]
    assert parameters["properties"]["name"]["type"] == "string"
    assert parameters["properties"]["times"]["type"] == "integer"
    assert parameters["properties"]["times"]["default"] == 1
    assert parameters["required"] == ["name"]
