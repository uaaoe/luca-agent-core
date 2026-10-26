"""AST-based evaluator for arithmetic expressions.

``eval`` cannot be made safe by clearing ``__builtins__``: attribute and
subscript access on literals escapes the sandbox (for example
``().__class__.__base__.__subclasses__()`` reaches ``__import__``). This
module parses the expression instead and walks the tree, accepting only
numeric literals and the operators in the allow-lists below. Everything
else raises :class:`UnsafeExpressionError`.
"""

import ast
import operator
from typing import Final

#: Longest accepted expression, in characters.
MAX_EXPRESSION_LENGTH: Final = 500

#: Largest accepted ``**`` exponent magnitude. Keeps ``9**9**9`` from
#: pinning a CPU or exhausting memory.
MAX_ABS_EXPONENT: Final = 1000

_BINARY_OPERATORS: Final = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}

_UNARY_OPERATORS: Final = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_NODE_LABELS: Final = {
    ast.Attribute: "attribute access",
    ast.Await: "await",
    ast.BoolOp: "boolean operators",
    ast.Call: "function calls",
    ast.Compare: "comparisons",
    ast.Dict: "dict literals",
    ast.DictComp: "dict comprehensions",
    ast.GeneratorExp: "generator expressions",
    ast.IfExp: "conditional expressions",
    ast.JoinedStr: "f-strings",
    ast.Lambda: "lambda",
    ast.List: "list literals",
    ast.ListComp: "list comprehensions",
    ast.NamedExpr: "assignment expressions",
    ast.Set: "set literals",
    ast.SetComp: "set comprehensions",
    ast.Slice: "slices",
    ast.Starred: "starred expressions",
    ast.Subscript: "subscript access",
    ast.Tuple: "tuple literals",
}


class UnsafeExpressionError(ValueError):
    """Raised when an expression contains anything outside the allow-list."""


def evaluate(expression: str) -> int | float:
    """Evaluate ``expression`` and return its numeric result.

    Accepts numeric literals, parentheses, unary ``+``/``-`` and the binary
    operators ``+ - * / % **``. Raises :class:`UnsafeExpressionError` for
    anything else, and the usual arithmetic errors (for example
    :class:`ZeroDivisionError`) for invalid arithmetic.
    """
    if not isinstance(expression, str):
        raise UnsafeExpressionError(f"expected a string, got {type(expression).__name__}")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise UnsafeExpressionError(f"expression longer than {MAX_EXPRESSION_LENGTH} characters")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpressionError(f"invalid syntax: {exc.msg}") from exc

    result = _evaluate_node(tree.body)
    if isinstance(result, complex):
        raise UnsafeExpressionError("result is not a real number")
    return result


def _evaluate_node(node: ast.AST) -> int | float:
    """Recursively evaluate an allow-listed node."""
    if isinstance(node, ast.Constant):
        # bool is an int subclass and is rejected explicitly so that
        # True/False cannot be used as arithmetic operands.
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise UnsafeExpressionError(f"{type(node.value).__name__} literals are not allowed")
        return node.value

    if isinstance(node, ast.UnaryOp):
        unary = _UNARY_OPERATORS.get(type(node.op))
        if unary is None:
            raise UnsafeExpressionError(f"unary operator {type(node.op).__name__} is not allowed")
        return unary(_evaluate_node(node.operand))

    if isinstance(node, ast.BinOp):
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)
        if isinstance(node.op, ast.Pow):
            return _power(left, right)
        binary = _BINARY_OPERATORS.get(type(node.op))
        if binary is None:
            raise UnsafeExpressionError(f"operator {type(node.op).__name__} is not allowed")
        return binary(left, right)

    raise UnsafeExpressionError(f"{_label(node)} is not allowed")


def _power(left: float, right: float) -> int | float:
    """Exponentiation with a bound on the exponent magnitude."""
    if abs(right) > MAX_ABS_EXPONENT:
        raise UnsafeExpressionError(f"exponent magnitude above {MAX_ABS_EXPONENT} is not allowed")
    return operator.pow(left, right)


def _label(node: ast.AST) -> str:
    """Human-readable name for a rejected node."""
    if isinstance(node, ast.Name):
        return f"name {node.id!r}"
    return _NODE_LABELS.get(type(node), f"{type(node).__name__} expressions")
