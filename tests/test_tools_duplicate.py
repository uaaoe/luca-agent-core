from unittest.mock import MagicMock

from app import agent
from app.tools.registry import ToolRegistry


def tool1() -> bool:
    """ Tool1 docstring """
    return True

def tool2() -> bool:
    """ Tool2 docstring """
    return True

def test_duplicate_resolved_tools(monkeypatch):
    test_registry = ToolRegistry()
    first = test_registry.register(tool1)
    second = test_registry.register(tool2)

    model = MagicMock()
    monkeypatch.setattr(agent, "registry", test_registry)
    monkeypatch.setattr(agent, "get_llm", lambda: model)

    agent.resolve_model(["tool1", "tool2", "tool1"])
    model.bind_tools.assert_called_once_with([first,second])
    
