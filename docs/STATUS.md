# Implementation and validation status — November 1, 2026

Current deployed release: **v2-99bee4f3f001**. [Live application](https://selcuksntrk--risklens-web.us-east.modal.run) · [health/version](https://selcuksntrk--risklens-web.us-east.modal.run/api/health).

This is a tested software prototype and synthetic demo candidate. It is **not** completion of the real-home acceptance tests, an expert safety assessment, a final demo video, or the post-hackathon pilot.

## Implemented

| Plan package | Implementation |
|---|---|
| A — report/evidence | Schema 2; independent complete/partial/incomplete assessment; persistent stages/warnings; observed vs needs_check; separate user context; exact evidence frame and box; same-track/relation deduplication; safe legacy adapter; source/model/settings/prompt/schema/version provenance; no public risk-score gauge |
| B — capture/upload | Video-only permission, optional narration, editable context, preview/retake, stable Blob/key retry, preserved file name/MIME, resource cleanup, decode validation, portrait-compatible proxy processing, bounded multipart upload, durable idempotency before job start |
| C — suggestions/illustrations | Returned-section checks; per-action source links; unverified suggestions blocked in UI and endpoint; embedded AI-image label; original/illustration/re-filmed views distinguished |
| D — re-filming | Candidate-separated views; same physical object, relevant visible physical change, visible before-condition and high confidence required; unchanged source hash rejected before inference; target hazard_id and unchecked findings; immutable attempt history and attempt-specific status polling; no green zero-confirmation summary |
| E — privacy/operations | Random browser session; owner checks on all private routes; explicit read-only public allowlist; administrative legacy recovery; cancellation joined before deletion; 7/30-day retention; independent verification raw age; remote-file deletion/retry; one active + two queued jobs; call-level reservations including retries/Voice/Image; restart interruption; Modal volume commits at persistence boundaries |
| F — example/release | Completed licensed synthetic example; live sample; own-video upload; matching frontend/backend release and health endpoint; pinned production dependencies; clean-source installation check; public README, licenses, evaluation tools, acceptance forms, release runbook and demo storyboard |

The prior local polling/test work was retained and extended. Legacy reports were not rewritten to fabricate evidence. The daily model budget remains $15 by default. No personal room media was published.

## Recorded checks

- **62 backend tests passed**, including original tests, failure contracts, ownership, retention, deletion/cancellation, idempotency, queue/reservations, candidate mismatch, same-file targeted verification, exact-frame evidence, WebM without initial duration metadata, source gates, example allowlist and evaluation split/metrics checks.
- **6 frontend tests passed**: job-specific polling after SSE disconnect, terminal interruption, source gating, neutral zero-confirmation display, retained upload Blob/key/name/MIME, and video continuing after microphone denial with single-use stop and resource cleanup.
- Frontend production build and lint passed. Python compile checks and Git whitespace checks passed.
- Fresh dependency installation in a clean temporary source snapshot: production-only Python dependencies from the lockfile, `npm ci`, matching release build, application startup/health and completed example access passed. The snapshot included only the explicitly licensed generated example, no `.env` or private scans.
- Actual local Meta run on the approved synthetic clip: **83.8 s**, **$0.206694** recorded model cost, four findings requiring checking, assessment complete. Uploaded provider-file cleanup had no pending records afterward.
- Same-file local verification: **0/4 visible changes confirmed**, **$0** additional model calls. This is a deterministic control, not evidence of real-room model performance.
- Deployed sample run: **107.0 s**, **$0.22644** recorded model cost, three findings, assessment complete. Different outputs on the same synthetic clip are not evidence of stable precision/recall; no labelled performance claim is made.
- Live HTTP acceptance passed: release/asset hashes, completed example, Secure/HttpOnly/SameSite session, private upload idempotency/conflict, deletion, private-route denial from a second cookie jar, target-specific same-file verification, unchecked findings/history, and refusal to replay deleted jobs. Disposable synthetic test scans were removed. See [machine-readable live checks](live-check-2026-11-01.json).

Costs are the application's recorded usage, not a provider invoice. The successful-run figures exclude separately recorded failed/unknown calls. No real-home precision/recall or successful physical fix is claimed.

## Still required before final hackathon submission

1. Physical **iPhone/Safari and Android/Chrome** acceptance tests. Automated browser DOM tests do not establish hardware behavior.
2. Real-room **A0 and B0–B4** with observations recorded before model answers. No positive demo filming if B0/B1/B3/B4 has a false confirmation. Target November 1 captures as planned.
3. Actual room-level evaluation (target 3–5 rooms, 10–15 clips) and independent review. Evaluation tools and templates are ready; the dataset and labels have not been fabricated.
4. Reviewed real before/action/re-filmed footage, final ≤2:55 video, accessible video URL and hackathon platform submission. Storyboard/checklist prepared; nothing was submitted to the platform or social media.
5. Visual UI review: the available browser host was unavailable and native computer-use permission was denied. Build, component and HTTP checks passed; desktop visual review was not claimed.

Post-hackathon expert evaluation, advanced re-identification/re-grounding/removal detection, revocable sharing, persistent distributed queue/scheduled cleanup, 5–10 volunteer users, stakeholder interviews and the open-weight auditor remain gated pilot work in [PILOT.md](PILOT.md). They are not listed as completed features.

## Where to continue

- [ACCEPTANCE.md](ACCEPTANCE.md): phone cases and real-room controls.
- [Evaluation protocol](../eval/README.md): frozen manifests, room split and independent adjudication.
- [SUBMISSION.md](SUBMISSION.md): demo storyboard, submission fields and unsent social draft.
- [RELEASE.md](RELEASE.md): release identity, clean setup, live checks and rollback without deleting user data.
