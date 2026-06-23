import math
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
# import numexpr  

from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun, ArxivQueryRun, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools.shell.tool import ShellTool

# ── Global API Initializations (Fixes the memory/performance issue) ──
_raw_shell = ShellTool()
_raw_shell.description = "FOR INTERNAL/ADMINISTRATIVE USE ONLY."

_arxiv_tool = ArxivQueryRun()

# Initialize Wikipedia exactly ONCE, not on every function call
_wiki_client = WikipediaAPIWrapper(top_k_results=2, doc_content_chars_max=2000)
_wiki_tool = WikipediaQueryRun(api_wrapper=_wiki_client)
_web_search_tool = DuckDuckGoSearchRun()

# ── The Optimized Tools ──────────────────────────────────────────────

@tool
def get_current_date_and_time(timezone_string: str = "Asia/Kolkata") -> str:
    """
    Acts as your internal clock. Use this whenever the user asks for the current date, time, or day of the week.
    Args:
        timezone_string: IANA timezone (e.g. 'Asia/Kolkata', 'Europe/London'). Defaults to 'Asia/Kolkata' if not specified.
    """
    try:
        # Try using ZoneInfo
        tz = ZoneInfo(timezone_string)
        local_time = datetime.now(tz)
    except Exception:
        # Fallback for Asia/Kolkata if ZoneInfo fails
        if timezone_string == "Asia/Kolkata":
            tz = timezone(timedelta(hours=5, minutes=30))
            local_time = datetime.now(tz)
        else:
            return f"Error: Could not find timezone '{timezone_string}'."
    
    return f"The current date and time in {timezone_string} is: {local_time.strftime('%A, %d %B %Y at %I:%M %p')}"

@tool
def web_search(query: str) -> str:
    """
    Performs a live web search using DuckDuckGo. 
    Use this for recent events, news, or general internet lookups.
    Args:
        query: The optimized search query string.
    """
    try:
        search = DuckDuckGoSearchRun()
        results = search.run(query)
        if not results:
            return f"No results found for '{query}'."
        return f"Search results for '{query}':\n{results}"
    except Exception as e:
        return f"Error performing web search: {str(e)}"

@tool
def calculator(expression: str) -> str:
    """
    Calculates complex mathematical expressions.
    Call this tool whenever you need to perform arithmetic or math logic.
    Args:
        expression: A math expression string (e.g. '15 * (4 + 2) / 3').
    """
    try:
        # Using Python's built-in eval for zero-dependency math calculation
        result = eval(expression)
        return f"The answer to {expression} is {result}"
    except Exception as e:
        return f"Error: Could not calculate '{expression}'. Details: {str(e)}"

@tool
def safe_shell_executor(command: str, user_confirmed: bool = False) -> str:
    """
    Executes a system shell command. 
    You MUST first set user_confirmed=False. This will return a prompt that you must show the user.
    Once the user explicitly types "yes" in the chat to confirm the exact command, you can call this tool again with user_confirmed=True to actually execute it.

    Args:
        command: The exact shell command string to execute.
        user_confirmed: Set to False initially. Set to True ONLY after the user has explicitly approved the command in the chat.
    """
    if not user_confirmed:
        return f"SYSTEM NOTIFICATION: You must ask the user: 'Are you sure you want to run `{command}`? (yes/no)'. Do not execute it until they say yes."
        
    try:
        return f"Execution successful:\n{_raw_shell.invoke(command)}"
    except Exception as e:
        return f"Shell execution failed: {str(e)}"

@tool
def search_wikipedia(query: str) -> str:
    """
    Searches Wikipedia for factual, historical, or biographical summaries.
    Use this for deep knowledge lookups rather than general web searches.
    Args:
        query: The topic, person, or concept to search for.
    """
    try:
        return _wiki_tool.invoke(query)
    except Exception as e:
        return f"Wikipedia search failed: {str(e)}"

@tool
def search_academic_papers(query: str) -> str:
    """
    Searches the Arxiv database specifically for scientific papers and academic research.
    Args:
        query: The topic or keyword to search (e.g. 'Reinforcement Learning').
    """
    try:
        result = _arxiv_tool.invoke(query)
        if not result or result.strip() == "":
            return f"No academic papers found on Arxiv for: '{query}'."
        return f"Research papers found:\n\n{result}"
    except Exception as e:
        return f"Error querying the Arxiv database: {str(e)}"

