import ast
import operator as op
from typing import Union

# ---------------------------------------------------------------------------
# Supported operators
# ---------------------------------------------------------------------------

_OPERATORS = {
    ast.Add:      op.add,
    ast.Sub:      op.sub,
    ast.Mult:     op.mul,
    ast.Div:      op.truediv,
    ast.FloorDiv: op.floordiv,   # supports 10 // 3
    ast.Mod:      op.mod,
    ast.Pow:      op.pow,
    ast.USub:     op.neg,
}

# Guard against expressions like 2 ** 9999999 freezing the event loop.
_MAX_EXPONENT = 1000


class MathError(ValueError):
    """Raised for unsafe or unsupported expressions — always has a user-friendly message."""


def safe_eval(expr: str) -> Union[int, float]:
    """
    Safely evaluate a numeric arithmetic expression string.

    Supports: + - * / // % ** and unary negation.
    Does NOT support: variables, function calls, bitwise ops, comparisons.

    Raises MathError with a readable message on:
      - Division by zero
      - Exponent too large (> 1000)
      - Unsupported syntax (variables, calls, etc.)
      - Invalid / unparseable expression
    """
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError:
        raise MathError(f"Invalid expression: `{expr}`")

    return _eval_node(tree.body)


def _eval_node(node: ast.expr) -> Union[int, float]:
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise MathError("Only numeric constants are supported.")
        return node.value

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise MathError(f"Unsupported operator: `{ast.dump(node.op)}`")

        left  = _eval_node(node.left)
        right = _eval_node(node.right)

        # Guard: exponent size
        if op_type is ast.Pow:
            if isinstance(right, float) and not right.is_integer():
                pass  # fractional powers are fine (e.g. 8 ** 0.5)
            elif abs(right) > _MAX_EXPONENT:
                raise MathError(
                    f"Exponent too large (max {_MAX_EXPONENT}). "
                    f"Got `{right}`."
                )

        # Guard: division by zero
        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise MathError("Division by zero.")

        return _OPERATORS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        if type(node.op) not in _OPERATORS:
            raise MathError(f"Unsupported unary operator: `{ast.dump(node.op)}`")
        return _OPERATORS[type(node.op)](_eval_node(node.operand))

    raise MathError(
        "Unsupported expression. Only basic arithmetic is allowed "
        "(+, -, *, /, //, %, **)."
    )
