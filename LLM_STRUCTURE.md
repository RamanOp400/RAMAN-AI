# LLM Structure Overview

## High‑Level Pipeline
```
START → remember → chat → refine ⇄ tools → END
```
- **`remember`** – loads any stored facts for the `(user_id, thread_id)` pair from the Postgres checkpoint. It also records new facts that the LLM extracts during the conversation.
- **`chat`** – calls the underlying LLM (e.g., GPT‑OSS) with the **system prompt** that defines the RAMAN AI persona. It produces a *raw* response without any post‑processing.
- **`refine`** – takes the raw response and runs it through a **refine prompt** that:
  1. Applies the RAMAN AI tone (jokes, sentiment‑aware language).
  2. Binds any declared tools (e.g., `safe_shell_executor`).
  3. Streams the final answer token‑by‑token via the `astream_events` API, which FastAPI exposes as an SSE endpoint.
- **`tools`** – a LangGraph `ToolNode` that executes any tool calls returned by `refine`. The only built‑in tool right now is the **human‑in‑the‑loop shell executor** which asks the user for explicit confirmation before running a command.

## Detailed Component Diagram
```mermaid
graph LR
    A[START] --> B[remember]
    B --> C[chat]
    C --> D[refine]
    D -->|needs tool| E[tools]
    E --> D
    D --> F[END]
    style A fill:#f9f,stroke:#333,stroke-width:1px
    style B fill:#bbf,stroke:#333,stroke-width:1px
    style C fill:#bbf,stroke:#333,stroke-width:1px
    style D fill:#bbf,stroke:#333,stroke-width:1px
    style E fill:#ffb,stroke:#333,stroke-width:1px
```

## Memory Persistence
- **Store**: `PostgresStore` – reads/writes the `messages` list for each conversation.
- **Checkpoint**: `PostgresSaver` – snapshots the graph state after each node execution. This enables **exact‑resume** capability when the container restarts.
- Both are configured via the `DB_URI` environment variable (`postgresql://postgres:postgres@postgres:5432/postgres?sslmode=disable`).

## Prompts
### System Prompt (`SYSTEM_PROMPT_TEMPLATE` in `prompt.py`)
```
You are **RAMAN AI**, a witty, human‑like assistant built by Raman Sarkar. You:
- Crack jokes when appropriate.
- Detect and respond to user sentiment.
- Never execute a destructive shell command without asking for confirmation.
```
### Refine Prompt (`REFINE_PROMPT`)
```
Take the raw LLM output and:
1. Apply RAMAN AI’s personality.
2. If the output mentions a tool, bind the tool and request any needed user confirmation.
3. Return a polished, friendly response.
```

## Streaming Flow (`/chat/stream` endpoint)
1. FastAPI receives the request and calls `workflow.astream_events(..., version="v2")`.
2. The `refine` node yields `AIMessageChunk` objects for each token.
3. The endpoint converts each chunk into an SSE ``data: {"token": "..."}`` line.
4. The client receives a live token stream, enabling a typing‑effect UI.

## Safe Shell Execution (`tools.safe_shell_executor`)
- The LLM proposes a command (e.g., `rm -rf /tmp/foo`).
- `refine` includes a **confirmation sub‑prompt**: "Are you sure you want to run `rm -rf /tmp/foo`? (yes/no)".
- The user must reply with `yes` before the command is dispatched.
- This guarantees a **human‑in‑the‑loop** safety net.

## Extending the Pipeline
- **Add new tools**: Create a function in `tools.py` and add it to `tools_list` in `graph.py`. The `refine` node will automatically bind it.
- **Swap the LLM**: Modify `llm_setup.py` to load a different provider; the rest of the graph remains unchanged.
- **Custom memory**: Replace `PostgresStore` with any LangGraph‑compatible store (e.g., Redis, Mongo) without altering other nodes.

---

*This document provides a concise yet complete view of the LLM architecture powering RAMAN AI. It can be used for onboarding new developers or for documentation purposes.*
