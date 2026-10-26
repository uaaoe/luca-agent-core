"""Tests for the safe expression evaluator behind ``calculate_metric`` (issue #4).

The malicious cases all reach code execution through ``eval`` with
``{"__builtins__": {}}``; each one must come back as an error message
instead of a result.
"""

import pytest

from app.tools._safe_expr import (
    MAX_ABS_EXPONENT,
    MAX_EXPRESSION_LENGTH,
    UnsafeExpressionError,
    evaluate,
)
from app.tools.calculator import calculate_metric

# The escape chain that returned live classes (and then ``__import__``) before
# the fix: ``().__class__.__base__.__subclasses__()`` -> ``catch_warnings``
# -> ``__globals__`` -> ``__builtins__`` -> ``__import__``.
SANDBOX_ESCAPE = (
    "[c for c in ().__class__.__base__.__subclasses__() if c.__name__ == 'catch_warnings']"
    "[0]()._module.__builtins__['__import__']('os').popen('id').read()"
)

VALID_EXPRESSIONS = [
    ("2 + 3 * 4", 14),
    ("(1 + 2) * 3", 9),
    ("7 / 2", 3.5),
    ("10 % 3", 1),
    ("2 ** 10", 1024),
    ("2 ** -2", 0.25),
    ("1.5 * 2", 3.0),
    ("-5 + 2", -3),
    ("-(3 * 4)", -12),
    ("+7", 7),
]

INVALID_EXPRESSIONS = [
    # name lookups and imports
    "__import__('os')",
    "__import__('os').getcwd()",
    "os.system('id')",
    "open('/etc/passwd').read()",
    "eval('1 + 1')",
    "exec('x = 1')",
    "globals()",
    "vars()",
    "len('x')",
    "print(1)",
    "getattr(1, 'real')",
    "x",
    # attribute and subscript access
    "().__class__",
    "().__class__.__base__.__subclasses__()",
    "(1).__class__.__mro__[1]",
    "'abc'.upper()",
    "[1, 2][0]",
    SANDBOX_ESCAPE,
    # literals and syntax outside arithmetic
    "True",
    "False",
    "None",
    "'abc'",
    "[1, 2]",
    "{'a': 1}",
    "(1, 2)",
    "lambda: 1",
    "1 if 1 else 2",
    "1 < 2",
    "1 and 2",
    "x := 1",
    "[x for x in [1]]",
    "{x for x in [1]}",
    "{x: x for x in [1]}",
    "(x for x in [1])",
    "f'{1}'",
    "1 +",
]


@pytest.mark.parametrize(("expression", "expected"), VALID_EXPRESSIONS)
def test_evaluate_returns_correct_result(expression, expected):
    assert evaluate(expression) == expected


@pytest.mark.parametrize(("expression", "expected"), VALID_EXPRESSIONS)
def test_tool_reports_correct_result(expression, expected):
    assert calculate_metric.invoke({"expression": expression}) == f"Calculation result: {expected}"


@pytest.mark.parametrize("expression", INVALID_EXPRESSIONS)
def test_evaluate_rejects_expression(expression):
    with pytest.raises(UnsafeExpressionError):
        evaluate(expression)


@pytest.mark.parametrize("expression", INVALID_EXPRESSIONS)
def test_tool_returns_error_message_for_rejected_expression(expression):
    output = calculate_metric.invoke({"expression": expression})
    assert output.startswith("Calculation error:")
    assert "Calculation result" not in output


def test_evaluate_reports_unexpected_node_type_by_name():
    with pytest.raises(UnsafeExpressionError, match="attribute access is not allowed"):
        evaluate("().__class__")

    with pytest.raises(UnsafeExpressionError, match="function calls is not allowed"):
        evaluate("__import__('os')")

    with pytest.raises(UnsafeExpressionError, match="name 'x' is not allowed"):
        evaluate("x")


def test_evaluate_rejects_expression_over_length_limit():
    expression = "1 + " * MAX_EXPRESSION_LENGTH
    with pytest.raises(UnsafeExpressionError, match="longer than"):
        evaluate(expression)


def test_evaluate_rejects_oversized_exponent():
    with pytest.raises(UnsafeExpressionError, match="exponent magnitude"):
        evaluate(f"2 ** {MAX_ABS_EXPONENT + 1}")

    # The guard is on the exponent, so the nested form is rejected too.
    with pytest.raises(UnsafeExpressionError, match="exponent magnitude"):
        evaluate("9 ** 9 ** 9")


def test_evaluate_rejects_non_string_input():
    with pytest.raises(UnsafeExpressionError, match="expected a string"):
        evaluate(123)  # type: ignore[arg-type]


def test_tool_reports_arithmetic_errors():
    assert calculate_metric.invoke({"expression": "1 / 0"}) == "Calculation error: division by zero"
