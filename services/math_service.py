
import ast
import operator as op

operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.USub: op.neg
}

def safe_eval(expr):
    def eval_node(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            return operators[type(node.op)](
                eval_node(node.left),
                eval_node(node.right)
            )
        elif isinstance(node, ast.UnaryOp):
            return operators[type(node.op)](
                eval_node(node.operand)
            )
        else:
            raise TypeError("Unsupported expression")
    return eval_node(ast.parse(expr, mode="eval").body)
