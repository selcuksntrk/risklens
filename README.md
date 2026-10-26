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
| *(coming)* Voice capture | Muse Voice Transcribe | Turkish/English narration while filming ("kids sleep here") |
| *(coming)* Fix planner | Muse Spark + FEMA E-74 | Cited, practical fixes |
| *(coming)* Auditor | Muse Spark Open (open weights, Baseten) | Independent second opinion with readable reasoning in the audit trail |
| *(coming)* Fix cards | Muse Image | Your own room, shown fixed |
| *(coming)* Verify-after-fix | SAM 3.1 + Muse Spark | Re-film; proves the hazard is gone |

## Run it (CLI, today)
```bash
cd backend
cp ../.env.example ../.env   # add MODEL_API_KEY
uv run --env-file ../.env python -m app.cli scan path/to/room.mp4 --narration "bedroom, kids sleep here"
uv run --group dev pytest -q
```
Output: `scans/<id>/report.json` plus marked keyframes and evidence images. Requires `ffmpeg`.

## Built during the hackathon
Everything in this repo was written during the event window (Oct 26 – Nov 4 2026); see the commit history.
`backend/app/meta/sam.py` and `spark.py` started from our own Day-1 feasibility spikes (Oct 26).

## Pre-existing / third-party
- SAM request shape follows the Meta Model Cookbook `07_sam/01_api_basics` (MIT, © Meta Platforms, Inc.).
- Libraries: openai (Apache-2.0), meta-sam-parser, Pillow (MIT-CMU), FastAPI (MIT).
- Data: see [`DATA_LICENSES.md`](DATA_LICENSES.md). No raw datasets are committed.

## License
MIT. See [LICENSE](LICENSE).
