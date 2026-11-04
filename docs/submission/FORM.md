# Form-ready project copy

Paste-ready text for the Cerebral Valley submission form. Check each field's length limit on the real form; shorter versions are given where a limit is likely. This is not a completed submission.

## Basics

- **Name:** RiskLens
- **Track:** Indie Developer
- **Theme:** Build for Your World
- **Team:** Selçuk (solo). Use the platform's participant identity.
- **Live product:** https://selcuksntrk--risklens-web.us-east.modal.run
- **Source code:** https://github.com/selcuksntrk/risklens
- **Demo video:** https://youtu.be/5rq5IBgD-AE
- **Evaluation notes:** https://github.com/selcuksntrk/risklens/blob/main/docs/EVALUATION.md

## Tagline

Film a room. See what could fall in an earthquake, with the exact frame and what to do next.

## Short description

RiskLens turns a one-minute phone video of a room into a list of things that could fall, tip over or block your way out in an earthquake. Each finding shows the exact frame it is based on, says what the video can't show, and links next steps to FEMA guidance. Built in Istanbul with Muse Spark, SAM 3.1 and Muse Image.

## Problem and impact

I live in Istanbul, where most of us know an earthquake is a question of when. What we can't easily tell is what to do about it at home. An engineer can't visit every flat, but a wardrobe that tips over, a shelf above a child's bed or boxes narrowing the way to the front door are things a family can deal with today, if someone points them out.

RiskLens is for people preparing the rooms they live in. It needs a phone and about a minute, with no account and no expert on site. The problem is wider than one city: in a study of New Zealand commercial buildings during the 2010–2014 earthquakes, 556 of 947 injuries were attributed to non-structural damage (Yeow et al., 2020). That sample isn't homes, and RiskLens hasn't yet been tested for behaviour change or reduced harm; a volunteer pilot is the next step.

## How it uses Meta's models

Each model does the part it is best at, and each hands its result to the next:

- **Muse Spark 1.3 (planner)** studies 6–12 still frames and decides which objects matter in this kind of room.
- **SAM 3.1** follows those objects through the whole video, so every finding points to a real box on a real frame.
- **Muse Spark 1.3 (surveyor)** reviews the boxed frames and keeps what it could see apart from what it couldn't, such as a hidden wall fixing.
- **Muse Spark 1.3 (fix planner)** looks up sections of FEMA E-74 through a tool and writes next steps that cite them. A step that can't be traced to a section it read is withheld.
- **Muse Image 1.0** draws what a fix could look like, always labelled as AI-made and never treated as proof.
- **SAM 3.1 + Muse Spark 1.3 (film again)** compare a new video of an item with the first one, requiring the same object and a visible change.
- **Muse Voice Transcribe 1.0** turns a spoken note about the room into text (optional).

**The less obvious use: Meta models built our test set.** To test on content with known answers, I wrote down three Istanbul rooms and their hazards first. Muse Image drew six views of each room, anchored to the first view, and Muse Spark checked every view for the same room and the planted hazards before it was used (18 of 18 passed, 2 on a second attempt). The views became phone-style walkthrough videos, labelled as AI-made. RiskLens then found 5 of 5, 4 of 4 and 4 of 5 planted hazards. It missed the boxes narrowing a hallway, and that miss is shown in the app.

## Technical depth

- Exact-frame evidence: findings link to a tracked object and frame, not just a description of the room.
- Source checks are enforced in code: unsupported suggestions are blocked in the interface and the endpoint.
- Re-filming guards: an identical file is caught by a SHA-256 check before any model runs, and a change needs the same object, a relevant visible difference and high confidence.
- Reliability: bounded job queue, idempotent uploads, per-call budget reservations, a $15 daily model cap, polling fallback for live progress, and interrupted jobs that never silently restart paid calls.
- Privacy: private scans belong to a browser session, access is checked on every private route, videos are deleted after 7 days and reports after 30. Public examples come from a hash-checked list, so a private scan can't become public by its ID.
- Measured: 73 backend and 14 frontend tests, plus a synthetic regression comparing Spark-only with the full pipeline, including negative controls with zero false confirmations.

## Evaluation

Three Muse Image test rooms with planted hazards: 13 of 14 found (one run per room, matched by hand). Five Hypersim scenes provide development regression, with failures, time and cost recorded. These are test scenes, so no accuracy on real homes is claimed. Positive before-and-after validation of a physical fix is future work.

## Limitations

It only sees what the video shows, and can miss objects or relationships. Hidden fixings are reported as unknown. It is not a building inspection and says nothing about structural safety. FEMA-linked steps are not reviewed by an engineer. A visible change does not prove a fix is adequate. Repeated runs can return somewhat different findings, and a run can take longer than the usual 2–3 minutes.

## Built during the event

All of it, from the October 26 kickoff: video processing and live progress, model orchestration, tracking and evidence frames, source-checked next steps, re-filming checks, privacy and budget controls, the test-room generator and its QA gate, recorded-run replay, and the interface. Third-party code and data (the SAM request grammar from Meta's cookbook, open-source dependencies, FEMA E-74 excerpts, Hypersim scenes) are labelled in the README and `DATA_LICENSES.md`.

## Bonus fields (only if the form asks)

- **Best Agentic:** planner, tracker, surveyor and tool-using fix planner with verification gates. Fair to mention.
- **Open weights:** no open-weight model is used; do not claim it.
- **Most Viral:** add the X post link once posted.

## X post draft (Selçuk posts this himself, after submitting)

> I live in Istanbul. So I built RiskLens: film a room for a minute, and Meta's Muse Spark and SAM 3.1 point out what could fall, tip over or block your way out, on the exact video frame, with next steps from FEMA guidance.
>
> It also tells you what it can't see.
>
> Built solo for the @Meta AI Developer Hackathon.
>
> [video] [live link]

Check the correct event account and hashtag on the event page before posting.
