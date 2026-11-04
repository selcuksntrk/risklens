# RiskLens

Film a room, review visible earthquake-related findings with evidence, read source-linked precautions, and re-film to compare a visible change. **A prototype for screening sampled views, not a building inspection, earthquake prediction, installation certificate or insurance risk score.**

Theme: **Build for Your World**. Built in Istanbul for people preparing their homes for earthquakes.

**Demo video (2:32):** https://youtu.be/2tA6bLuztSk

**Try it:** [open RiskLens](https://selcuksntrk--risklens-web.us-east.modal.run) and **Record a room** or **Upload a video**. To explore without filming your home, open one of the four examples on the home page: the author's real flat in Istanbul or one of three test rooms made with Muse Image. Each report opens instantly without new model calls; **Replay the analysis** plays back the recorded run, and **Run it again live** starts a new Meta model run (outcomes and latency vary). **How it works** explains each model, the limits and privacy.

**Hackathon delivery:** [measured synthetic regression](docs/EVALUATION.md) · [submission package](docs/submission/README.md) · [source on main](https://github.com/selcuksntrk/risklens). The demo video opens with a real recording of the author's home in Istanbul (a demonstration, not an evaluation; see [quality notes](docs/QUALITY_NOTES.md)); the three Muse Image test rooms carry answer keys, and development regression uses Hypersim scenes. Physical iPhone review remains open; the platform submission was sent on November 4 ([handoff](docs/submission/HANDOFF.md)). Real-world physical-change validation has not been completed.

The application distinguishes observed conditions from details that need another view. An unseen attachment is unknown; a visible bracket does not establish adequate installation. Technical failures cannot become a “low risk” result. Assessment completeness describes the analysis stages, not whole-room coverage or safety.

The existing deployment is [RiskLens on Modal](https://selcuksntrk--risklens-web.us-east.modal.run). Check `/api/health` against the local `VERSION` before treating a deployment as this revision. See [implementation and validation status](docs/STATUS.md) for outstanding release gates.

## How it works

| Component | Model / technology | Actual task |
|---|---|---|
| Capture | Browser camera / gallery | Video-only permission, optional microphone, editable context, preview, retry with the same upload key |
| Planner | Muse Spark 1.3 | Select tracking concepts and alternate wording from sampled keyframes (about one per 4 s, 6–12 per clip) |
| Tracking | SAM 3.1 | Track candidate instances within this clip; cross-clip identity is not guaranteed |
| Surveyor | Muse Spark 1.3 | Describe visible findings and uncertainty in marked keyframes |
| Recommendations | Muse Spark 1.3 + FEMA E-74 lookup | Cite sections actually returned by the lookup, with per-action references |
| Optional narration | Muse Voice Transcribe 1.0 | Live transcription through a server-side proxy; gallery audio is not automatically transcribed |
| Optional illustration | Muse Image 1.0 | Explain a sourced precaution with an image visibly labelled “AI-generated illustration”; never verification evidence |
| Designed sample scenes | Muse Image 1.0 + Muse Spark 1.3 | `scripts/generate_scenes.py`: generate each room from a scene bible with designed hazards (answer key), anchor every view to the establishing shot, and gate each shot on a Spark consistency/visibility check (all 18 shots passed; 2 needed a second attempt) |
| Re-filming | SAM 3.1 + Muse Spark 1.3 + deterministic guards | Compare a selected candidate with original evidence; require same-object identity, a relevant visible change and high confidence |

```mermaid
flowchart LR
  V[Phone video] --> F[ffmpeg: keyframes and proxy]
  F --> P[Muse Spark 1.3<br/>planner: what to track]
  P --> S[SAM 3.1<br/>tracks objects through the video]
  S --> M[Boxed frames]
  M --> U[Muse Spark 1.3<br/>surveyor: visible vs unknown]
  U --> X[Muse Spark 1.3 + FEMA E-74 lookup<br/>source-checked next steps]
  X --> R[Report: frame, unknowns, steps]
  R -. on request .-> I[Muse Image 1.0<br/>labelled picture of a fix]
  R -. film again .-> C[SHA-256 guard, then SAM 3.1 + Muse Spark 1.3<br/>same object, visible change]
  T[Scene description with planted hazards] --> G[Muse Image 1.0<br/>six anchored views]
  G --> Q[Muse Spark 1.3<br/>QA gate per view]
  Q --> W[Test-room walkthrough video]
  W -. public example with answer key .-> V
```

React/TypeScript frontend → FastAPI → bounded job queue → ffmpeg → Meta models → atomic JSON reports and evidence on a Modal Volume. One container, one active scan/verification, two queued jobs. Restarted jobs are interrupted, never silently restarted with paid calls. SSE shows progress; persistent job endpoints and polling recover state after disconnects.

`fixed` is an internal compatibility value. The UI says **Change visible**. It does not mean earthquake safety or adequate mounting has been certified. Reinterpretation of an incorrect original finding is manual review, not a completed precaution. Identical videos, untracked findings, missing objects and uncertain identity cannot automatically close a finding. Similar candidates retain separate IDs and evidence frames.

Recommendations link to source sections; this is **not expert validation of each action**. Unsupported actions are withheld. Costs and times are estimates. Source recommendations and installation conditions still require expert evaluation in the pilot.

## Local setup

Requirements: Python 3.11+, Node 22+, ffmpeg/ffprobe, and uv. Copy `.env.example` to `.env`, then set `MODEL_API_KEY`. Never put keys in frontend variables.

```sh
cd backend
uv sync --frozen
cd ../frontend
npm ci
cd ..
python3 scripts/build_release.py
cd backend
uv run --env-file ../.env uvicorn app.main:app --port 8000
```

Open `http://localhost:8000`. Phone camera access requires HTTPS. `npm run dev` in `frontend` proxies `/api` to port 8000. Production frontend and backend share one origin. See `scripts/phone.sh` for local phone testing.

```sh
# Tests use temporary storage and mocked model APIs; no paid requests.
cd backend
uv run --group dev pytest -q
cd ../frontend
npm test
npm run lint
npm run build
```

Offline CLI (reports remain quarantined from web access):

```sh
cd backend
uv run --env-file ../.env python -m app.cli scan /path/to/room.mp4 --narration "Bedroom; attachment conditions unknown"
uv run --env-file ../.env python -m app.cli verify SCAN_ID /path/to/refilmed.mp4 --hazard-id h1
```

Only the first 90 seconds of an uploaded video are processed; camera recordings stop at 60 seconds. The report records processed duration and media settings. No unmeasured room-coverage percentage is shown.

## Privacy and cost controls

New scans belong to a random browser session stored in an HttpOnly, Secure (production), SameSite=Lax cookie. The scan ID is a locator, not a credential. Ownership is enforced for reports, lists, evidence, events, verification, illustrations and deletion. Clearing cookies removes normal browser access. The admin recovery tool requires filesystem access and an existing owned scan; there is no claim-by-ID endpoint.

Source videos, proxies and extracted frames: **7 days**. Reports and evidence: **30 days**. Expired private content is inaccessible immediately; physical cleanup runs at startup and hourly while the server is active. Verification raw media has its own creation timestamp. Deletion cancels and joins active writers before removing derived data. Explicitly packaged licensed examples have a separate indefinite demo policy. Personal scans are never automatically featured.

Videos are processed by Meta's API. Uploaded provider file IDs are recorded and deletion is requested after use, with retries for failed deletion; one-day provider expiry is the fallback requested at upload. This does not assert deletion guarantees beyond the provider's API behavior. Standard models only; contributor models are rejected for room screening and evaluation.

Each model call reserves budget before dispatch. Actual usage settles reservations; unknown or failed usage conservatively keeps the estimate. Voice and Image use the same ledger. The default daily cap remains **$15**, with daily scan/network limits. Estimates are not an audited provider invoice. Deployment must remain single-process/single-container until the pilot replaces this ledger and queue with shared infrastructure.

## Example and evaluation

The home page offers **four samples**, each with a precomputed report (no new model calls), an **analysis replay** of its recorded run (stored timeline events on a compressed clock, labelled as a replay) and an optional new live run:

| Sample | Source | Recorded run |
|---|---|---|
| Real home, Istanbul | The author's own 37 s phone video (photos blurred, audio removed); shown with permission, no reuse licence | complete · 3 findings · 100 s · $0.275 |
| Designed living room | Muse Image scene with 5 designed hazards + 1 secured control | complete · 6 findings · designed hazards matched **5/5** |
| Designed children's bedroom | Muse Image scene with 4 designed hazards + 1 low-risk control | complete · 6 findings · matched **4/4** |
| Designed kitchen and entrance | Muse Image scene with 5 designed hazards + 1 secured control | complete · 5 findings · matched **4/5** (missed the boxes narrowing the path to the front door; flagged the fridge, which was not designed) |

Designed scenes are rendered into phone-style 1080×1920 walkthroughs (`scripts/render_walkthrough.py`: handheld drift, whip pans, sensor noise, an “AI-generated scene · Muse Image” label on every frame). Answer-key matches are author-matched from each finding's object and evidence box (`examples/matches/`), one run per scene, and pending a second human check. They show the pipeline on known content; they are **not** an accuracy measurement for real homes. The model reviewing generated images is a known limitation.

The packaging tool publishes only videos whose SHA-256 is in the committed registry `examples/sources.json` and schema-2 reports produced from that same file. Source media and generated examples are excluded from Git. See [data licenses](DATA_LICENSES.md), `scripts/fetch_example.py`, `scripts/package_example.py`, and [evaluation protocol](eval/README.md).

There is no claimed real-home precision, recall, safety percentage or successful physical fix. The current delivery uses five previously used Hypersim scenes for **development regression**, not an independent benchmark. The same inputs run through Spark-only and the full pipeline; demo repetitions and limited synthetic negative controls are reported separately. Human correctness review remains pending. Real-room A0/B0–B4 and the 3–5-room pilot are future validation, not completed entry evidence. See [acceptance tests](docs/ACCEPTANCE.md).

Context for the problem: a study of New Zealand commercial buildings during the 2010–2014 earthquakes reported 556 of 947 injuries attributable to non-structural damage ([Yeow et al., 2020](https://doi.org/10.1177/8755293019900775)). This specific sample is not a universal estimate for homes or all earthquakes.

## Release and submission

`python3 scripts/build_release.py` derives one release ID from the application sources and lockfiles, builds the frontend with it, and writes `VERSION` and `release.json`. The backend health endpoint returns that version and supported report schema. [Release runbook](docs/RELEASE.md) covers clean installation, deployment, negative access checks and rollback without deleting user data.

[Demo storyboard and submission checklist](docs/SUBMISSION.md) routes to the delivery package: a real recording of the author's home (personal photos blurred, audio removed, never committed) opens the video; the synthetic sample covers comparison and measurement. The final video is at https://youtu.be/2tA6bLuztSk. Physical-phone review remains pending. The open-weight auditor, expert labels, advanced re-identification, revocable sharing and volunteer pilot are **future work**, gated by evidence in [pilot protocol](docs/PILOT.md).

## Event work and third-party material

Application development began during the Oct 26–Nov 4, 2026 event window. Commit history records the implemented changes. Initial SAM/Spark integration grew out of feasibility spikes written after kickoff. Contributor API models are not used for real-room data.

Built during the hackathon (all of `backend/`, `frontend/src/`, `deploy/`, `eval/`, `scripts/`):

- Video ingestion, proxy encoding and live progress timeline (SSE with polling fallback).
- Nov 4 interface: plain-language, light, mobile-first “surveyor's notebook” design. Home explains each Meta model with the real run's data; report is a numbered list with one finding per screen (photo, what couldn't be seen, FEMA-linked steps); analysis and replay show the boxed SAM frames; an About page holds models, limits, privacy, examples and licences.
- Designed sample scenes: Muse Image generation gated by Muse Spark QA, phone-style walkthrough renderer, hash-checked sample registry and recorded-run replay.
- Spark planner → SAM 3.1 tracking → Spark surveyor on marked frames; observed vs. needs-check report contract with exact-frame evidence.
- FEMA E-74 lookup tool and source-checked suggestions; unsupported actions withheld.
- Re-filming comparison with SHA-256 same-file guard, same-object/relevant-change/confidence requirements and attempt history.
- Browser-session ownership, deletion, retention, idempotent uploads, bounded queue, per-call budget reservations, Modal deployment and content-derived release IDs.
- Licensed synthetic example packaging, synthetic development-regression runner/summary (Nov 3), and headless-Chrome visual QA and demo-footage recorders (`scripts/cdp.py`, `scripts/visual_qa.py`, `scripts/record_demo.py`, `scripts/record_own_video.py`, using the locally installed Google Chrome).
- User-first interface (Nov 3): record/upload on the home screen, sample one tap away, token-based light/dark design system; duration-based keyframe sampling; cache headers that keep Safari from loading stale builds.

The SAM request grammar follows Meta's Model Cookbook (MIT, © Meta Platforms, Inc.). The frontend started from the Vite React/TypeScript template. Dependencies include React/Vite (MIT), openai (Apache-2.0), Pillow (MIT-CMU), FastAPI (MIT), uvicorn/websockets (BSD), and python-multipart (Apache-2.0). ffmpeg is an external program; its build has its own LGPL/GPL licensing. The demo video's captions and titles use Archivo and IBM Plex Mono (SIL OFL); neither ships with the app. FEMA source excerpts, Hypersim evaluation assets and the sample videos have separate notices in [DATA_LICENSES.md](DATA_LICENSES.md).

Application code: MIT, see [LICENSE](LICENSE). Hypersim-derived assets are CC BY-SA 3.0, not relicensed under the application license.
