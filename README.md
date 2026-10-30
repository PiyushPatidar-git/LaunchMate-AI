# LaunchMate AI - Opportunity Scout & Application Builder

Built for the **Best Apps and Agents** track of the Nebius x NVIDIA Global AI Hackathon.
Students enter interests and skills; a traceable six-stage agent finds opportunities, analyses them with
**NVIDIA Nemotron on Nebius Token Factory**, scores fit, plans tasks, drafts an application kit and tracks progress in a local SQLite database.

## Why it fits Best Apps and Agents
A multi-step workflow (not a chatbot): Research -> Analysis -> Fit scoring -> Action planning -> Application kit -> Save & track.
Every stage is shown in the UI; if one fails you see which, and previously saved data is kept.

## Architecture
`app/config.py` settings from `.env` | `app/models.py`, `database.py` SQLite via SQLAlchemy | `app/schemas.py` validation |
`app/services/search.py` Tavily | `ai.py` Nebius (OpenAI SDK) | `workflow.py` the agent stages and kit generation | `core.py` pure helpers (URL dedupe, scoring, CSV/Markdown) |
`app/routes/api.py` REST API | `app/templates`, `app/static` plain HTML/CSS/JS | `tests/` pytest.

## How Nebius and Nemotron are used
`ai.py` uses the OpenAI Python SDK with `NEBIUS_BASE_URL` (default `https://api.tokenfactory.us-central1.nebius.com/v1/`) and
`NEBIUS_MODEL` (default `nvidia/nemotron-3-super-120b-a12b`). Both defaults matched Nebius's public docs when this was written;
re-check them in your Token Factory console. Nemotron is called in Stage 2 (analysis of search snippets) and Stage 5 (kit generation).
If a call fails you get a clear error; there is no silent fallback to another provider.

## How web research fits in
Stage 1 calls the official Tavily API (`TAVILY_API_KEY`). Only returned URLs/snippets are stored. Snippets are treated as untrusted data in prompts.
Deadlines are **never guessed**: they show "unconfirmed" until you enter the date from the official page.

## What works without keys (DEMO MODE)
Dashboard, profile, tasks, sample workspace, DEMO DATA research results (labelled), template-based kits, CSV/Markdown/TXT exports, compare.
## What needs keys
LIVE SEARCH needs `TAVILY_API_KEY`. LIVE AI analysis and AI-written kits need `NEBIUS_API_KEY`.
The header badge shows LIVE AI / LIVE SEARCH only after a real successful request (use **Connections -> Run connection checks**).

## Windows setup
1. Install Python 3.11 or 3.12 from python.org (tick "Add python.exe to PATH") and VS Code.
2. Extract `LaunchMate-AI.zip`, open the `LaunchMate-AI` folder in VS Code, open a terminal (PowerShell).
3. Run: `.\run_windows.bat` (it creates `.venv`, installs requirements, copies `.env.example` to `.env`, starts the server).
   If PowerShell blocks scripts, use `cmd /c run_windows.bat`.
4. Open http://127.0.0.1:8000
5. For live mode: edit `.env`, paste keys after `NEBIUS_API_KEY=` and `TAVILY_API_KEY=`, save, restart the app.

## Run tests
`.\test_windows.bat` (or, inside the venv: `python -m pytest -v`). Tests use mocked external services; they do not call Nebius or Tavily.

## Troubleshooting
- "Python not found": reinstall Python with PATH ticked, reopen the terminal.
- "Nebius request failed": check key, `NEBIUS_MODEL` spelling and that the model is enabled in your Token Factory account.
- "Tavily rejected the API key": regenerate the key.
- Port 8000 busy: change `--port 8000` in `run_windows.bat`.

## Judging demo (about 3 minutes)
Connections -> run checks (show LIVE badges) -> Research with a real goal -> show the workflow trace -> open an opportunity,
explain the score breakdown, set a deadline from the official page -> Generate kit -> edit and download -> Tasks -> Export pack.

## Known limitations
- The score is a keyword heuristic, not a prediction. Tavily snippets can be short or outdated; always confirm on the source.
- No user accounts (single local user). Research runs synchronously per request (the UI stays responsive, but a run can take a minute).
- Compare is a simple table; the timeline view is the "Recent research runs" list, not a graphical chart.
- Nothing is ever submitted for you.
