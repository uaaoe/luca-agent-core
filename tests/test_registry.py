"""Tests for the registry module.

A client could receive a successful response with a schema that tells it 
to send the wrong type or omit a required argument.
"""

import importlib
import pkgutil
from types import SimpleNamespace

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

def test_registry_auto_discover(monkeypatch):
    module_record = []

    def import_module(module_name: str):
        """Fake import module by name."""
        module_record.append(module_name)
        if module_name == "app.tools":
            return SimpleNamespace(__path__=["fake_path"])

    def iter_modules(path, prefix="package_name."):
        """Fake iter_modules to yield one entry each for calculator, _safe_expr, registry."""
        yield (None, f"{prefix}calculator", False)
        yield (None, f"{prefix}_safe_expr", False)
        yield (None, f"{prefix}registry", False)

    monkeypatch.setattr(importlib,"import_module", import_module)
    monkeypatch.setattr(pkgutil,"iter_modules", iter_modules)

    registry = ToolRegistry()
    registry.auto_discover()
    assert module_record == [
        "app.tools",
        "app.tools.calculator",
    ]