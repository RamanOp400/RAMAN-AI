# RAMAN AI

## What is RAMAN AI?

**RAMAN AI** is a premium, human‑like conversational assistant built by **Raman Sarkar**. It can:
- Talk with a playful, witty tone (cracks jokes, understands sentiment).
- Remember user facts across sessions using a Postgres‑backed checkpoint.
- Safely execute shell commands **only after explicit confirmation**.
- Stream responses token‑by‑token via Server‑Sent Events (SSE).

---

## Quick Start (Docker)

```powershell
# Clone the repo (if needed) and go to the project folder
cd c:\Users\hp\Desktop\raman_chat_bot

# Build and start the containers (Postgres + FastAPI app)
docker compose up -d --build

# Verify the service is up
docker compose logs app -f   # you should see Uvicorn running on http://0.0.0.0:8000
```

### Health‑check
```powershell
curl http://localhost:8000/health
```
> Returns `{"status":"ok","name":"RAMAN AI"}`

### Chat (full response)
```powershell
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d "{\"message\":\"Hey RAMAN, who am I?\",\"user_id\":\"u1\",\"thread_id\":\"t5\"}"
```

### Chat (streaming response)
```powershell
curl -N -X POST http://localhost:8000/chat/stream \
     -H "Content-Type: application/json" \
     -d "{\"message\":\"Tell me a joke!\",\"user_id\":\"u1\",\"thread_id\":\"t5\"}"
```
> The output is a series of SSE `data:` lines containing individual tokens.

---

## Project Structure

```
raman_chat_bot/
├─ .env                # environment variables (DB_URI, etc.)
├─ .dockerignore
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
├─ main.py             # FastAPI entry point, lifespan, endpoints
├─ graph.py            # LangGraph node definitions (remember, chat, refine)
├─ prompt.py           # System prompt (RAMAN persona) & refine prompt
├─ tools.py            # Safe shell executor with human‑in‑the‑loop confirmation
├─ llm_setup.py        # LLM model loading utilities
├─ README.md           # **You are reading it!**
└─ LLM_STRUCTURE.md    # Detailed diagram & explanation of the LLM pipeline
```

---

## Core Concepts

### 1. 3‑Node LangGraph Pipeline
- **remember** – loads/updates user memories in Postgres.
- **chat** – generates a raw LLM response.
- **refine** – runs the response through the RAMAN persona prompt, binds tools, and streams tokens.

The graph flow is `START → remember → chat → refine ⇄ tools → END`.

### 2. Memory Persistence
- **PostgresStore** and **PostgresSaver** are used as a store and checkpoint respectively.
- Memories survive container restarts and are keyed by `user_id` & `thread_id`.

### 3. Safe Shell Tool
- Implemented in `tools.safe_shell_executor`.
- The LLM must state the command and ask **"Are you sure? (yes/no)"**.
- Execution proceeds only after a **yes** reply, preventing accidental deletions.

---

## Development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate   # on Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
Make sure a Postgres instance is reachable and `DB_URI` is set in `.env`.

---

## License & Credits

MIT License – feel free to fork and extend.
Built with love by **Raman Sarkar**, AI Engineer.

---

## Contact

- GitHub: https://github.com/ramansarkar/raman_chat_bot
- Email: raman.sarkar@example.com
