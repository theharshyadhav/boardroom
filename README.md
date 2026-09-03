# BoardMind — The AI Executive Decision Intelligence Platform

A working prototype: **Next.js + TypeScript frontend**, **FastAPI + Python backend**,
built and tested end-to-end (not just written — see "What's actually been tested" below).

BoardMind turns fragmented business data into explainable executive decisions. It
answers *what changed, why, how certain we are, what to do, and what happens if we do it*
— and it keeps a hard line between **deterministic computation** (pandas, DuckDB,
scikit-learn, NetworkX — no model calls) and the **LLM narrative layer** (which only
ever phrases numbers the deterministic layer already computed; it never calculates
anything itself).

## Quick start

You need Python 3.11+ and Node 18+.

**Fastest path — one command:**
```bash
./dev.sh
```
This creates the backend virtualenv, installs both sets of dependencies, generates
`.env` files on first run, and starts both servers. Ctrl+C stops both cleanly. This
has been tested cold (deleted venv, deleted `.env` files, deleted `node_modules`) and
confirmed to bring up a working app end to end. Windows: use WSL or Git Bash, or run
the two services manually below.

**Manual path (two terminals), if you want more control:**

*Terminal 1 — backend:*
```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # optional — see "LLM narrative" below
uvicorn app.main:app --reload --port 8000
```
Leave this running. Visit `http://localhost:8000/api/health` to confirm — you should see `{"status":"ok"}`.
Interactive API docs are auto-generated at `http://localhost:8000/docs`.

*Terminal 2 — frontend:*
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```
Open `http://localhost:3000` — you'll land on the login screen. Pick any of the four
demo roles (no password) and you're in.

## LLM narrative (optional)

The Executive Summary, Boardroom debate, and Q&A chat call an LLM. **Without any API
key configured, the app runs completely — every number, chart, and recommendation
works — and narrative text falls back to a clearly-labeled deterministic summary.**
This is intentional: a demo shouldn't depend on having a funded API key on hand.

To turn on live narration, put a key in `backend/.env`:
```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```
`LLM_PROVIDER` can be `anthropic`, `groq`, `gemini`, or `openrouter` — swap providers
without touching any call site. **Honesty note:** only the `anthropic` path was
actually tested against a live API in this environment, because the sandbox this
project was built in can reach `api.anthropic.com` but not `api.groq.com`,
`generativelanguage.googleapis.com`, or `openrouter.ai`. The Groq/Gemini/OpenRouter
implementations follow their documented REST APIs and *should* work, but verify them
yourself before relying on them live on stage — Anthropic is the only provider this
codebase has been proven against with a real network call.


## Troubleshooting

**`pip install` tries to compile pandas/numpy from source and fails** (common on
Windows — errors mentioning `meson.build`, `vswhere.exe`, or a missing C compiler):
this means pip couldn't find a prebuilt wheel for your exact Python version. Fix:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```
`requirements.txt` uses minimum-version constraints (not exact pins) specifically so
pip can resolve to whatever version *does* have a wheel for your platform — this was
hit and fixed during development, and is now tested clean from a fresh venv with
pandas 3.0 / numpy 2.5 / Python 3.12. If it still fails, upgrading pip first (as
above) resolves the vast majority of these cases, since older pip versions are
worse at finding compatible wheels.

## Architecture

```
7 simulated data sources (sales, inventory, marketing, reviews, competitor,
weather, news — daily/hourly/weekly cadences, one coherent injected anomaly:
a monsoon-driven South India inventory shortage)
        │
        ▼
DuckDB SQL — harmonization + semantic KPI layer         ┐
        │                                                │
        ▼                                                │
Statistics — material change detection (scanning          │  100% deterministic
z-score detector, not a naive fixed window)                │  zero LLM calls
        │                                                  │
        ▼                                                  │
scikit-learn — driver decomposition (price/volume split,  │
normalized anomaly-weighted attribution)                  │
        │                                                  │
        ▼                                                  │
NetworkX — evidence graph (source → KPI → event)           │
        │                                                  │
        ▼                                                  │
Confidence engine — weighted score (freshness, history,   │
completeness, agreement, evidence count)                  │
        │                                                  │
        ▼                                                  │
Recommendation + Simulation engines (templated /           │
formula-based, fully transparent)                          ┘
        │
        ▼
LLM narrative layer (Claude, via provider abstraction) — ONLY stage that
calls a model, and only to phrase the numbers above in prose
        │
        ▼
Next.js dashboard (React Flow diagrams, Recharts, Framer Motion, SQLite-
backed feedback loop)
```

## Project structure

```
README.md
dev.sh                    one-command startup for both services (tested cold)
backend/
  app/
    data_gen.py        1. simulated data sources
    analytics.py        2-4. DuckDB semantic KPI layer + material change detection
    driver_analysis.py  5. scikit-learn driver decomposition
    evidence_graph.py   NetworkX evidence graph
    confidence.py        6-7. confidence engine
    material_events.py  ties detection + drivers + confidence together
    recommendations.py  8. recommendation engine
    simulation.py        9. simulation engine
    narrative.py + llm_provider.py   10. LLM narrative layer (provider-agnostic)
    feedback.py          SQLite-backed feedback loop
    roles.py             RBAC definitions
    routers/              one FastAPI router per feature area
  tests/test_api.py      12 end-to-end tests
frontend/
  src/app/
    login/                demo role picker
    (dashboard)/           authenticated shell (sidebar, mobile nav)
      page.tsx              Dashboard
      insights/             Recommendations + Q&A
      evidence/             Evidence Explorer (React Flow traceability graph)
      boardroom/             Multi-agent boardroom
      simulator/             Decision Simulator
      telemetry/              Runtime Telemetry
      settings/               Access, personas, architecture
  src/components/          KPI cards, charts, driver/evidence diagrams, ui/ primitives
  src/lib/                  typed API client, auth context, types, utils
```

