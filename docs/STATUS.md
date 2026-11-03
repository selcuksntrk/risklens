# Implementation and validation status — November 3, 2026

Submitted release candidate: **v2-32d643efff70**. [Live application](https://selcuksntrk--risklens-web.us-east.modal.run) · [health/version](https://selcuksntrk--risklens-web.us-east.modal.run/api/health). The homepage footer shows the same release ID.

This is a tested software prototype demonstrated on licensed synthetic scenes. It is **not** an expert safety assessment, a real-home accuracy result or a demonstration of a successful physical precaution.

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

## Recorded checks (November 3)

- **68 backend tests** and **9 frontend tests** pass; frontend lint and production build pass. Covered: broken/empty video rejected before any model call or quota; idempotent retry reuses one job; private routes deny another session; SSE loss polls only the requested verification and never shows an older result; same-file guard; source gating.
- **Paid live HTTP acceptance** on `v2-1f324db24c9e` (same backend as the current release): 8/8 checks — release/asset hashes, public example without session, secure cookie, upload idempotency/conflict/deletion, live sample (complete, 4 findings, 184.8 s, $0.19), targeted same-file verification with zero confirmations and history, second-cookie-jar denial of private routes, deleted scans not replayed. [Machine-readable](live-check-2026-11-03.json).
- **Release check** on `v2-aa81598cfef3`: health, frontend asset hashes and completed example.
- **User-first redesign** (`v2-aa81598cfef3`): home leads with **Record a room** / **Upload a video** (upload starts on the home screen and hands the file to the capture preview); “View sample report” in the header and a “Try it without filming your home” section keep the sample one tap away. New token-based design system (light/dark), 8 px buttons, numbered how-it-works, report stat row. Live QA in both themes at 1440/390/360 px: no overflow, no text below 13 px; remaining small targets are inline text links and a visually hidden file input. Navigating between screens now starts at the top (hash routes previously kept the old scroll offset). [Machine-readable](release-check-2026-11-03.json). Frontend-only changes since the paid check: wording/layout and de-duplicated guard text.
- **Safari blank-page fix** (`v2-7d20c50353b0`): `index.html` had no `Cache-Control` and a 1970 `Last-Modified`, so Safari reused an old page whose script hash no longer existed after redeploys. Now HTML/manifest are `no-cache` (ETag revalidation) and hashed `/assets/` are `immutable`; backend test added. A browser that already holds the stale page needs one reload.
- **Synthetic evaluation:** 16 attempts, 0 failures, $2.08 recorded. Spark-only vs full on five scenes, three demo repeats, four negative controls with 0 confirmations. Precision/recall not measured. See [EVALUATION.md](EVALUATION.md).
- **Visual QA (emulated):** headless Chrome at 1440×900, 390×844 and 360×740 (`scripts/visual_qa.py`): no horizontal overflow on home, completed report or capture. Fixed: desktop evidence column showed a black block, 11 px badges, 23 px disclosure toggles, “Scan hypers” header, duplicated same-file reason. Inline source links remain text-height (inline exception). **Emulation is not a physical iPhone/Safari test.**
- **Demo footage:** recorded from the live application by `scripts/record_demo.py` (new sample run, same-file comparison, cards generated from committed results). Shortened waits carry a visible label with the actual duration. Files stay in the ignored `docs/submission/private/footage/`.

Costs are the application's recorded usage, not a provider invoice.

## Still required before submission (owner: Selçuk)

1. Physical **iPhone/Safari** check with the supplied synthetic file ([checklist](submission/SELCUK.md)). Android, camera recording and microphone remain untested and are not claimed.
2. Two English voice takes; caption alignment; final 1080p export via `scripts/assemble_demo.py`; phone review of the export.
3. Human review of the synthetic observations if any correctness number is to be published (otherwise publish none).
4. Authenticated rules/form review, login-free video URL, platform submission and confirmation record in [HANDOFF](submission/HANDOFF.md).

Real-room A0/B0–B4, the 3–5-room evaluation, expert labels, the open-weight auditor and the volunteer pilot are future work in [PILOT.md](PILOT.md) and [ACCEPTANCE.md](ACCEPTANCE.md); none is listed as completed.

Source: `main` (PR #1 merged November 3, merge commit `e8c6bb6`).

## Where to continue

- [Submission package](submission/README.md) · [Evaluation](EVALUATION.md) · [Release runbook](RELEASE.md) · [Acceptance protocol](ACCEPTANCE.md)
