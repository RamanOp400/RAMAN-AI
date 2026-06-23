import math
import ast
import operator
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.tools.shell.tool import ShellTool
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools import ArxivQueryRun
from langgraph.types import interrupt

# ── Safe math operators for calculator ───────────────────────────
_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(node):
    """Recursively evaluate an AST node using only whitelisted operations."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value!r}")
    if isinstance(node, ast.BinOp):
        op_func = _SAFE_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op_func(_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op_func = _SAFE_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op_func(_safe_eval(node.operand))
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _SAFE_FUNCS:
            func = _SAFE_FUNCS[node.func.id]
            args = [_safe_eval(a) for a in node.args]
            return func(*args)
        raise ValueError(f"Unsupported function call: {ast.dump(node.func)}")
    if isinstance(node, ast.Name) and node.id in _SAFE_FUNCS:
        val = _SAFE_FUNCS[node.id]
        if isinstance(val, (int, float)):
            return val
        raise ValueError(f"'{node.id}' is a function, not a constant")
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


# ── Tools ────────────────────────────────────────────────────────

@tool
def get_time_by_location(timezone_string: str = "Asia/Kolkata") -> str:
    """
    Returns the current date and time for a specific location.

    Args:
        timezone_string: IANA timezone (e.g. 'Asia/Kolkata', 'Europe/London').
                         Defaults to 'Asia/Kolkata'.
    """
    try:
        local_time = datetime.now(ZoneInfo(timezone_string))
        formatted = local_time.strftime("%A, %d %B %Y at %I:%M %p")
        return f"The current date and time in {timezone_string} is: {formatted}"
    except Exception:
        return (
            f"Error: Could not find timezone '{timezone_string}'. "
            "Use a standard IANA timezone format."
        )


@tool
def web_search(query: str) -> str:
    """
    Performs a web search using DuckDuckGo and returns the results.

    Args:
        query: The search query string.
    """
    try:
        results = DuckDuckGoSearchRun().invoke({"query": query})
        return f"Search results for '{query}':\n{results}"
    except Exception as e:
        return f"Error performing web search: {e}"


@tool
def calculator(expression: str) -> str:
    """
    Safely calculates mathematical expressions.
    Supports +, -, *, /, //, **, %, and functions like sqrt, abs, log, sin, cos, tan.

    Args:
        expression: A math expression string (e.g. '15 * (4 + 2) / 3' or 'sqrt(144)').
    """
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree)
        return f"The answer to {expression} is {result}"
    except Exception as e:
        return f"Error: Could not calculate '{expression}'. Details: {e}"


# ── Shell tool with human-in-the-loop ────────────────────────────
_raw_shell = ShellTool()
_raw_shell.description = (
    "FOR INTERNAL/ADMINISTRATIVE USE ONLY. Executes commands in the system shell. "
    "Use ONLY when explicitly asked to run terminal tasks."
)


@tool
def safe_shell_executor(command: str) -> str:
    """
    Executes a system shell command after human approval.

    Args:
        command: The exact shell command string to execute.
    """
    human_decision = interrupt(
        f"\n⚠️ ALERT: The agent wants to execute: `{command}`\n"
        f"Approve this execution? (Type 'yes' to proceed): "
    )

    if str(human_decision).strip().lower() == "yes":
        try:
            result = _raw_shell.invoke(command)
            return f"Execution successful:\n{result}"
        except Exception as e:
            return f"Shell execution failed: {e}"
    return "Execution blocked by human."


@tool
def search_wikipedia(query: str) -> str:
    """Search Wikipedia for factual summaries about people, places, or concepts."""
    return WikipediaAPIWrapper(top_k_results=1).run(query)


_arxiv_tool = ArxivQueryRun()


@tool
def search_academic_papers(query: str) -> str:
    """
    Searches the Arxiv database for scientific papers and academic research.

    Args:
        query: The topic or keyword to search (e.g. 'Reinforcement Learning').
    """
    try:
        result = _arxiv_tool.invoke(query)
        if not result or result.strip() == "":
            return f"No academic papers found on Arxiv for: '{query}'."
        return f"Research papers found:\n\n{result}"
    except Exception as e:
        return f"Error querying the Arxiv database: {e}"