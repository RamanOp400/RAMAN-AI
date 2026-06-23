import os
import json
from contextlib import asynccontextmanager

from langgraph.graph import START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.store.postgres import PostgresStore
from langgraph.checkpoint.postgres import PostgresSaver
from graph import remember_node, chat_node, refine_node, tools_list
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessageChunk


class ChatRequest(BaseModel):
    message: str = Field(..., description="user message")
    user_id: str = Field(..., description="user id")
    thread_id: str = Field(..., description="thread id")


# ── Build the 3-node graph ───────────────────────────────────────
# Flow: START → remember → chat → refine ⇄ tools → END
graph_def = StateGraph(MessagesState)
graph_def.add_node("remember", remember_node)
graph_def.add_node("chat", chat_node)
graph_def.add_node("refine", refine_node)
graph_def.add_node("tools", ToolNode(tools=tools_list))

graph_def.add_edge(START, "remember")
graph_def.add_edge("remember", "chat")
graph_def.add_edge("chat", "refine")
graph_def.add_conditional_edges("refine", tools_condition)
graph_def.add_edge("tools", "refine")

# ── Database ─────────────────────────────────────────────────────
DB_URI = os.getenv(
    "DB_URI",
    "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable",
)


# ── FastAPI lifespan (manages DB connections) ────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open store & checkpointer on startup, close on shutdown."""
    with PostgresStore.from_conn_string(DB_URI) as store, \
         PostgresSaver.from_conn_string(DB_URI) as checkpointer:
        store.setup()
        checkpointer.setup()
        app.state.workflow = graph_def.compile(store=store, checkpointer=checkpointer)
        yield


app = FastAPI(title="RAMAN AI", lifespan=lifespan)


# ── Regular endpoint (full response) ────────────────────────────
@app.post("/chat")
def chat(req: ChatRequest, request: Request):
    workflow = request.app.state.workflow
    config = {"configurable": {"user_id": req.user_id, "thread_id": req.thread_id}}
    result = workflow.invoke(
        {"messages": [HumanMessage(content=req.message)]},
        config,
    )
    return {"response": result["messages"][-1].content}


# ── Streaming endpoint (SSE, token by token) ────────────────────
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    workflow = request.app.state.workflow
    config = {"configurable": {"user_id": req.user_id, "thread_id": req.thread_id}}

    async def event_generator():
        async for event in workflow.astream_events(
            {"messages": [HumanMessage(content=req.message)]},
            config=config,
            version="v2",
        ):
            kind = event["event"]

            # Stream tokens from the refine node (final response)
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    data = json.dumps({"token": chunk.content})
                    yield f"data: {data}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Health check ────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "name": "RAMAN AI"}
