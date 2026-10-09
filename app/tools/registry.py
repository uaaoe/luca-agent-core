"""Centralized Tool Registry for dynamic agent tools."""

from collections.abc import Sequence
import importlib
import inspect
import pkgutil
from typing import Any

from langchain_core.tools import BaseTool, tool


class ToolRegistry:
    """Central registry storing tool metadata, instances, and JSON schemas."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool_or_func: Any) -> Any:
        """
        Register a tool in the registry. Can be used as a decorator or direct call.

        Accepts either a LangChain BaseTool instance or a standard callable function.
        """
        if isinstance(tool_or_func, BaseTool):
            self._tools[tool_or_func.name] = tool_or_func
            return tool_or_func
        elif callable(tool_or_func):
            wrapped_tool = tool(tool_or_func)
            self._tools[wrapped_tool.name] = wrapped_tool
            return wrapped_tool
        else:
            raise TypeError(f"Expected BaseTool or callable, got {type(tool_or_func)}")

    def get_tool(self, name: str) -> BaseTool | None:
        """Lookup a registered tool by name."""
        return self._tools.get(name)

    def get_tools(self, names: Sequence[str] | None = None) -> list[BaseTool]:
        """
        Retrieve tools from the registry.

        If names is provided, returns tools matching the requested names.
        Otherwise, returns all registered tools.
        """
        if names is None:
            return list(self._tools.values())
        return [self._tools[name] for name in names if name in self._tools]

    def list_tools(self) -> list[str]:
        """Return a list of all registered tool names."""
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool exists in the registry."""
        return name in self._tools

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def get_manifest(self) -> list[dict[str, Any]]:
        """
        Extract JSON schema manifest for all registered tools.

        Returns a list of dicts with name, description, and parameter schema.
        """
        manifest: list[dict[str, Any]] = []
        for tool_instance in self._tools.values():
            parameters: dict[str, Any] = {}
            if tool_instance.args_schema is not None:
                if hasattr(tool_instance.args_schema, "model_json_schema"):
                    parameters = tool_instance.args_schema.model_json_schema()
                elif hasattr(tool_instance.args_schema, "schema"):
                    parameters = tool_instance.args_schema.schema()

            manifest.append(
                {
                    "name": tool_instance.name,
                    "description": tool_instance.description or "",
                    "parameters": parameters,
                }
            )
        return manifest

    def auto_discover(self, package_name: str = "app.tools") -> None:
        """
        Dynamically discover and import all tool modules in the given package.
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            return

        package_path = getattr(package, "__path__", None)
        if not package_path:
            return

        for _, module_name, is_pkg in pkgutil.iter_modules(package_path, prefix=f"{package_name}."):
            # Avoid importing registry itself or private modules
            short_name = module_name.split(".")[-1]
            if short_name.startswith("_") or short_name == "registry":
                continue
            importlib.import_module(module_name)


# Global registry singleton
registry = ToolRegistry()
