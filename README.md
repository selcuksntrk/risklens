# RiskLens

**Film a room for a minute. RiskLens finds the earthquake hazards inside it, shows you how to fix them, and verifies the fix, as an insurer-grade survey.**

Most earthquake injuries come from what's *inside* the home: shelves that tip, frames above beds, TVs that fly, furniture that blocks the exit.
RiskLens turns a phone video into a non-structural hazard survey with evidence frames, FEMA-grounded fixes, an independent audit trail, and before/after proof once you fix things.

> Theme: **Build for Your World**. Built in Istanbul for homes in earthquake cities everywhere.
> RiskLens surveys non-structural hazards (furniture, fixtures, contents) only. It does **not** assess the structural safety of a building.

Status: 🚧 in progress (Meta Global AI Developer Hackathon, Oct 26 – Nov 4 2026)

## How it works
| Step | Meta model | Role |
|---|---|---|
| Planner agent | **Muse Spark 1.3** | Looks at the room and decides what to track, with alternate wordings when segmentation finds nothing |
| Perception | **SAM 3.1** | Tracks every planned object through the video with stable IDs |
| Surveyor agent | **Muse Spark 1.3** | Reasons over set-of-marks keyframes: what can fall onto the bed, block the exit, tip over or shatter |
| Voice capture | **Muse Voice Transcribe** | Live Turkish/English narration while filming ("kids sleep here"), streamed through a server-side proxy |
| Fix planner agent | **Muse Spark 1.3** + FEMA E-74 tool | Looks up FEMA E-74 sections through a function tool, then writes cited, practical fixes (DIY vs professional, cost, time); citations it didn't read are dropped |
| *(coming)* Auditor | Muse Spark Open (open weights, Baseten) | Independent second opinion with readable reasoning in the audit trail |
| Fix cards | **Muse Image** | "Show it fixed": edits a crop of *your own* evidence frame (around the SAM box) to show the recommended fix; on demand and cached ($0.01) |
| Verify-after-fix | **SAM 3.1** + **Muse Spark 1.3** | Re-film after fixing: SAM re-finds each object (with alternate wordings), a verifier agent compares before/after. A deterministic guard only allows "verified fixed" when SAM re-found the object *and* it is the same physical object; risk score before → after |

## Run it
Requires `ffmpeg`, [uv](https://docs.astral.sh/uv/) and Node 20+. Put `MODEL_API_KEY` in `.env` (see `.env.example`).
```bash
# web app: one server for API + PWA at http://localhost:8000
(cd frontend && npm install && npm run build)
cd backend && uv run --env-file ../.env uvicorn app.main:app --port 8000

# frontend dev with hot reload (proxies /api to :8000)
cd frontend && npm run dev

# CLI: one room video -> scans/<id>/report.json + marked keyframes + evidence images
cd backend && uv run --env-file ../.env python -m app.cli scan path/to/room.mp4 --narration "bedroom, kids sleep here"

# tests (no API calls)
cd backend && uv run --group dev pytest -q
```
The phone camera needs HTTPS: open the app through an HTTPS tunnel or the deployed URL.

## Built during the hackathon
Everything in this repo was written during the event window (Oct 26 – Nov 4 2026); see the commit history.
`backend/app/meta/sam.py` and `spark.py` started from our own Day-1 feasibility spikes (Oct 26).

## Pre-existing / third-party
- SAM request shape follows the Meta Model Cookbook `07_sam/01_api_basics` (MIT, © Meta Platforms, Inc.).
- Libraries: openai (Apache-2.0), meta-sam-parser, Pillow (MIT-CMU), FastAPI (MIT).
- Data: see [`DATA_LICENSES.md`](DATA_LICENSES.md). No raw datasets are committed.

## License
MIT. See [LICENSE](LICENSE).
