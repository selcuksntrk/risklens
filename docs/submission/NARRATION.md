# English narration and screen-recording sequence (Nov 4, simplified light release)

No face camera or music. Read naturally; do not rush technical names. Pronounce SAM as “Sam”, FEMA as “fee-muh”, Muse as “mews”, E-74 as “E seventy-four”.

The final cut is built by `scripts/compose_demo.py` (2:32): phone-viewport footage on the left, the run's real data on the right, captions from the voice take. Footage comes from `scripts/record_phone.py` in `private/footage-v5/`; `recording-log.json` holds scan IDs, times and costs.

- **Live run:** the real-home example run through a local server on the same release (`v2-f99acb5fa923`) with the same Meta models, because the deployed app's per-network daily scan limit had been reached. Complete, 3 findings, 114 s, $0.27.
- **Masks in the opening and the tracking beat:** real SAM 3.1 output on the same video, from a separate 15 fps run (`private/hero/`, drawn by `scripts/render_sam_hero.py`). Nothing is hand-placed.
- **Test rooms:** every matched count is one designed scene, author-matched; never call it accuracy.

Check every sentence against the selected footage before export.

## 01 · 00:00–00:15 · A real finding in my home

This is my bedroom in Istanbul. RiskLens found this wardrobe with suitcases on top. It can't see if it's fixed to the wall, so it asks you to check.

## 02 · 00:15–00:35 · Built for my world

I live in Istanbul. Here, getting ready for an earthquake also means looking at what is inside our homes. Film one room for less than a minute, or upload a video. Or open one of four examples.

## 03 · 00:35–01:15 · Three Meta models, each with one job

This is a live run. We shortened the waiting. First, Muse Spark looks at some frames and decides which objects matter in this room. Then SAM 3.1 follows each object through the whole video. So every finding points to a real frame and a real box. Then Spark looks at the marked frames. It separates what it can see from what needs checking. Last, it reads FEMA E-74 guidance to write the next steps.

## 04 · 01:15–01:45 · Evidence and next steps

Every finding shows what the video shows, and what is still unknown. Each next step links to the FEMA section the model really read. If that check fails, we show no steps. Muse Image can draw what a fix could look like, but it doesn't prove your room is safe.

## 05 · 01:45–02:10 · A change needs new evidence

After a fix, you film the item again. The same video cannot prove a change, and RiskLens checks that before any model runs. A real change needs the same object and a visible difference.

## 06 · 02:10–02:35 · Testing on known content

I made three test rooms with Muse Image, with hazards placed on purpose. Spark checked every view. RiskLens found five of five, four of four, and four of five. It missed boxes that narrow the way to the door. This is a test, not an accuracy claim.

## 07 · 02:35–02:55 · Close

RiskLens is a visual check, not a building inspection. It shows the evidence, it's honest about what it can't see, and it helps you decide what to look at next. One room at a time.

## End-card links

- Product: https://selcuksntrk--risklens-web.us-east.modal.run
- Source: https://github.com/selcuksntrk/risklens
