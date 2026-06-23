import uuid
from typing import List

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import MessagesState
from langgraph.store.base import BaseStore
from pydantic import BaseModel, Field

from llm_setup import llm
from prompt import MEMORY_PROMPT, SYSTEM_PROMPT_TEMPLATE, REFINE_PROMPT
from tools import (
    get_time_by_location,
    web_search,
    calculator,
    safe_shell_executor,
    search_wikipedia,
    search_academic_papers,
)

# ── Tools ────────────────────────────────────────────────────────
tools_list = [
    get_time_by_location,
    web_search,
    calculator,
    safe_shell_executor,
    search_wikipedia,
    search_academic_papers,
]

llm_with_tools = llm.bind_tools(tools_list)

# ── Structured output for memory extraction ──────────────────────
class MemoryItem(BaseModel):
    text: str = Field(description="Atomic user memory as a short sentence")
    is_new: bool = Field(
        description="True if this memory is NEW and should be stored. "
                    "False if duplicate / already known."
    )

class MemoryDecision(BaseModel):
    should_write: bool = Field(description="Whether to store any memories")
    memories: List[MemoryItem] = Field(
        default_factory=list,
        description="Atomic user memories to store",
    )

extraction_llm = llm.with_structured_output(MemoryDecision)


# ── Node 1: Remember ────────────────────────────────────────────
def remember_node(
    state: MessagesState,
    config: RunnableConfig,
    store: BaseStore,
) -> MessagesState:
    """Extract and persist new user facts from the latest message."""
    user_id = config["configurable"]["user_id"]
    ns = ("user", user_id, "details")

    # Fetch existing memories
    items = store.search(ns)
    existing_memory = (
        "\n".join(it.value.get("data", "") for it in items)
        if items else "empty"
    )

    last_msg = state["messages"][-1].content
    decision: MemoryDecision | None = extraction_llm.invoke(
        [
            SystemMessage(
                content=MEMORY_PROMPT.format(user_details_content=existing_memory)
            ),
            {"role": "user", "content": last_msg},
        ]
    )

    if decision and decision.should_write:
        for mem in decision.memories:
            if mem.is_new:
                store.put(ns, str(uuid.uuid4()), {"data": mem.text.strip()})

    return {}


# ── Node 2: Chat (raw response with personality) ────────────────
def chat_node(
    state: MessagesState,
    config: RunnableConfig,
    store: BaseStore,
):
    """Generate a raw response using stored memories."""
    user_id = config["configurable"]["user_id"]
    ns = ("user", user_id, "details")

    items = store.search(ns)
    user_details = (
        "\n".join(it.value.get("data", "") for it in items)
        if items else ""
    )

    response = llm.invoke(
        [
            SystemMessage(
                content=SYSTEM_PROMPT_TEMPLATE.format(
                    user_details_content=user_details
                )
            ),
        ]
        + state["messages"]
    )
    return {"messages": [response]}


# ── Node 3: Refine (add personality + tool calls) ───────────────
def refine_node(state: MessagesState):
    """Polish the raw response with humor and personality, handle tool calls."""
    response = llm_with_tools.invoke(
        [
            SystemMessage(content=REFINE_PROMPT),
        ]
        + state["messages"]
    )
    return {"messages": [response]}
