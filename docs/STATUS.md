# Implementation and validation status — November 4, 2026

**Submitted November 4, 2026.** Final video: https://youtu.be/2tA6bLuztSk

Current release: **v2-f99acb5fa923** (Nov 4, simplified notebook UI, light theme only; earlier: v2-a195e628947c, v2-0d61ff9c7dc7, v2-f04011cd606b, v2-c3a70a9e1077, v2-7cfff1fcf71c). [Live application](https://selcuksntrk--risklens-web.us-east.modal.run) · [health/version](https://selcuksntrk--risklens-web.us-east.modal.run/api/health). The homepage footer shows the same release ID.

This is a tested software prototype, measured on licensed synthetic scenes and demonstrated on one real recording of the author's home. It is **not** an expert safety assessment, a real-home accuracy result or a demonstration of a successful physical precaution.

## Implemented

| Plan package | Implementation |
|---|---|
| A — report/evidence | Schema 2; independent complete/partial/incomplete assessment; persistent stages/warnings; observed (“Reported visible”) vs needs_check; separate user context; exact evidence frame and box; same-track/relation deduplication; safe legacy adapter; source/model/settings/prompt/schema/version provenance; no public risk-score gauge |
| B — capture/upload | Video-only permission, optional narration, editable context, preview/retake, stable Blob/key retry, preserved file name/MIME, resource cleanup, decode validation, portrait-compatible proxy processing, bounded multipart upload, durable idempotency before job start |
| C — suggestions/illustrations | Returned-section checks; per-action source links; unverified suggestions blocked in UI and endpoint; embedded AI-image label; original/illustration/re-filmed views distinguished |
| D — re-filming | Candidate-separated views; same physical object, relevant visible physical change, visible before-condition and high confidence required; unchanged source hash rejected before inference; target hazard_id and unchecked findings; immutable attempt history; no green zero-confirmation summary |
| E — privacy/operations | Random browser session; owner checks on all private routes; read-only public allowlist; 7/30-day retention; remote-file deletion; one active + two queued jobs; call-level reservations; restart interruption; Modal volume commits at persistence boundaries; $15/day model cap |
| F — example/release | Licensed synthetic example opened in one tap without model calls; live sample run; own-video upload; matching frontend/backend release; release runbook |
| G — Nov 3 delivery | Synthetic development regression ([results](EVALUATION.md)); judge-first homepage; model-generated labelling; visual QA fixes; headless-Chrome QA and footage recorder |

## Recorded checks (November 4)

- **`v2-f99acb5fa923`** adds browser caching for public example images and recorded runs (one day; private scans stay `no-store`, tested) and removes the model's placeholder "none" from the film-again screen. 73 backend + 14 frontend tests pass. The server still scales to zero: the first visit after 20 idle minutes waits for a cold start (10–15 s observed), by the owner's choice.
- **Final video:** phone-viewport footage on this release of a new run of the real-home example, through a local server because the deployed app's per-network daily scan limit had been reached: complete, 3 findings, 114 s, $0.27, Muse Image picture shown. An earlier live run of the children's-room test room on the deployed app: complete, 5 findings, 136.3 s, $0.329, all four planted hazards reported. Live-run time varies (100–273 s across recordings).

- **Simplified UI** deployed as `v2-f04011cd606b`, then light theme only as `v2-0d61ff9c7dc7` (dark palette removed; light `color-scheme`, theme colour and manifest): plain-language copy, report as summary + numbered list with one finding per screen, light analysis screen, About page for models/limits/privacy/examples, home process section built from the real run. 14 frontend + 72 backend tests; visual QA (emulated) at 1440/390/360 in light and dark: no page overflow, no text below 13 px. Release check passes ([machine-readable](release-check-2026-11-04.json)).

- **Redesign + samples** deployed as `v2-c3a70a9e1077`: “evidence lens” UI (home gallery, dark live/replay analysis stage, image-led report, capture stage). Samples: the author's real home (blurred, no audio) + three Muse Image designed scenes (18/18 shots passed the Spark QA gate).
- Recorded sample runs (local CLI, same code): real home complete, 3 findings, 100 s, $0.275; living room 6 findings, designed 5/5 matched; children's bedroom 6 findings, 4/4; kitchen/entrance 5 findings, 4/5 (missed the narrowed exit path). Author-matched, one run each; not accuracy for real homes.
- **Production live run** of the children's-bedroom sample: complete, 5 findings, 173 s, $0.316, all 4 designed hazards reported; a second browser session gets 404 on the private scan.
- 72 backend + 13 frontend tests, lint and build pass. Visual QA (headless Chrome emulation, 1440/390/360, light and dark, 5 pages): no horizontal overflow, no text below 13 px; small targets are inline source links, 20 px checkboxes inside 44 px labels and the hidden file input.
- Release check: health/frontend match and public read-only examples ([machine-readable](release-check-2026-11-04.json)).

## Recorded checks (November 3)

- **69 backend tests** and **11 frontend tests** pass; frontend lint and production build pass. Covered: broken/empty video rejected before any model call or quota; idempotent retry reuses one job; private routes deny another session; SSE loss polls only the requested verification and never shows an older result; same-file guard; source gating.
- **Paid live HTTP acceptance** on `v2-1f324db24c9e` (same backend as the current release): 8/8 checks — release/asset hashes, public example without session, secure cookie, upload idempotency/conflict/deletion, live sample (complete, 4 findings, 184.8 s, $0.19), targeted same-file verification with zero confirmations and history, second-cookie-jar denial of private routes, deleted scans not replayed. [Machine-readable](live-check-2026-11-03.json).
- **Release check** on the current release: health, frontend asset hashes and completed example ([machine-readable](release-check-2026-11-03.json)).
- **User-first redesign** (Nov 3): home leads with **Record a room** / **Upload a video** (upload starts on the home screen and hands the file to the capture preview); “View sample report” in the header and a “Try it without filming your home” section keep the sample one tap away. New token-based design system (light/dark), 8 px buttons, numbered how-it-works, report stat row. Live QA in both themes at 1440/390/360 px: no overflow, no text below 13 px; remaining small targets are inline text links and a visually hidden file input. Navigating between screens now starts at the top (hash routes previously kept the old scroll offset). [Machine-readable](release-check-2026-11-03.json). Frontend-only changes since the paid check: wording/layout and de-duplicated guard text.
- **Safari blank-page fix** (`v2-7d20c50353b0`): `index.html` had no `Cache-Control` and a 1970 `Last-Modified`, so Safari reused an old page whose script hash no longer existed after redeploys. Now HTML/manifest are `no-cache` (ETag revalidation) and hashed `/assets/` are `immutable`; backend test added. A browser that already holds the stale page needs one reload.
- **Real-home demonstration:** Selçuk's own 37 s apartment walkthrough (audio removed, photos blurred) uploaded through the live app on `v2-60d4a67b448d`: complete, 3 findings (bedroom wardrobe with suitcases on top, blue suitcase, hallway wardrobe), $0.345. Earlier runs, failures and model errors are listed in [quality notes](QUALITY_NOTES.md). Keyframes now scale with clip length (6–12; synthetic eval clips unchanged at 6). Placeholder “Requested view: none” text is hidden.
- **Synthetic evaluation:** 16 attempts, 0 failures, $2.08 recorded. Spark-only vs full on five scenes, three demo repeats, four negative controls with 0 confirmations. Precision/recall not measured. See [EVALUATION.md](EVALUATION.md).
- **Visual QA (emulated):** headless Chrome at 1440×900, 390×844 and 360×740 (`scripts/visual_qa.py`): no horizontal overflow on home, completed report or capture. Fixed: desktop evidence column showed a black block, 11 px badges, 23 px disclosure toggles, “Scan hypers” header, duplicated same-file reason. Inline source links remain text-height (inline exception). **Emulation is not a physical iPhone/Safari test.**
- **Demo footage (Nov 3 cut, since replaced):** recorded from the live application (new sample run, same-file comparison, cards generated from committed results). Shortened waits carry a visible label with the actual duration. Files stay in the ignored `docs/submission/private/footage/`.

Costs are the application's recorded usage, not a provider invoice.

## Still open after submission

1. Physical **iPhone/Safari** check. Android, camera recording and microphone remain untested and are not claimed.
2. Human review of the synthetic observations before any correctness number is published.
3. X post for the Most Viral prize, if Selçuk chooses to compete.

Real-room A0/B0–B4, the 3–5-room evaluation, expert labels, the open-weight auditor and the volunteer pilot are future work in [PILOT.md](PILOT.md) and [ACCEPTANCE.md](ACCEPTANCE.md); none is listed as completed.

Source: `main` (PR #1 merged November 3, merge commit `e8c6bb6`).

## Where to continue

- [Submission package](submission/README.md) · [Evaluation](EVALUATION.md) · [Release runbook](RELEASE.md) · [Acceptance protocol](ACCEPTANCE.md)
