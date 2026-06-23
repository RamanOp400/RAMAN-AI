import asyncio
from langgraph.store.postgres import PostgresStore
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from main import DB_URI, graph_def

async def check():
    with PostgresStore.from_conn_string(DB_URI) as store:
        async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
            workflow = graph_def.compile(store=store, checkpointer=checkpointer)
            config = {"configurable": {"user_id": "date_test", "thread_id": "date_test_thread"}}
            state = await workflow.aget_state(config)
            for m in state.values.get("messages", []):
                tc = getattr(m, "tool_calls", [])
                print(f"[{m.__class__.__name__}] (tool_calls={tc}): {m.content}")

asyncio.run(check())
