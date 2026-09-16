from langchain_core.tools import tool
from app.tools.registry import registry


@registry.register
@tool
def calculate_metric(expression: str) -> str:
    """Safely calculate basic mathematical expressions."""
    # Tool assertion: validate input before evaluation
    assert expression and isinstance(expression, str), "Sanity Check: Expression must be a non-empty string"

    try:
        allowed = {"__builtins__": {}}
        result = eval(expression, allowed, {})
        return f"Calculation result: {result}"
    except Exception as exc:
        return f"Calculation error: {str(exc)}"
