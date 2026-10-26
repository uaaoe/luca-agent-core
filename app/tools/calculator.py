from langchain_core.tools import tool

from app.tools._safe_expr import evaluate
from app.tools.registry import registry


@registry.register
@tool
def calculate_metric(expression: str) -> str:
    """Safely calculate basic mathematical expressions."""
    # Tool assertion: validate input before evaluation
    assert expression and isinstance(expression, str), "Sanity Check: Expression must be a non-empty string"

    try:
        result = evaluate(expression)
        return f"Calculation result: {result}"
    except (
        ArithmeticError,
        TypeError,
        ValueError,
    ) as exc:
        # ValueError covers UnsafeExpressionError, which is raised for
        # anything outside the arithmetic allow-list.
        return f"Calculation error: {exc!s}"
