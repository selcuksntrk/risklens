# English narration and screen-recording sequence (Nov 4, "evidence lens" release)

Target: 2:55. No face camera or music. Record two complete voice takes. Read naturally; do not rush technical names. Pronounce SAM as “Sam”, FEMA as “fee-muh”, Muse as “mews”.

Footage is recorded from the live app by `scripts/record_demo.py` into `private/footage-v2/01–07.mp4` (segment lengths 15/20/40/30/25/25/20 s, as `scripts/assemble_demo.py` expects). See `private/footage-v2/recording-log.json` for scan IDs, times and costs.

- **01:** the packaged report of Selçuk's real home recording (blurred, no audio), labelled on every frame.
- **03:** a genuinely new live run of the designed children's-bedroom sample. The wait is shortened, with a label stating the actual duration.
- **06:** the designed-scenes card and the living-room answer key. Every matched count is one designed scene, author-matched; never call it accuracy.

Check every sentence against the selected footage before export.

## 01 · 00:00–00:15 · A real finding in my home

This is my bedroom in Istanbul. RiskLens flagged the wardrobe with suitcases on top, and it says what it can't see: whether it's anchored is unknown, not assumed.

## 02 · 00:15–00:35 · Built for my world

In Istanbul, earthquake preparation includes what is inside our homes. Film one room for under a minute, or upload a video. Or try one of four samples, no filming needed.

## 03 · 00:35–01:15 · Three Meta models, each with one job

Here is a live run, with the waiting shortened. Muse Spark looks at sampled frames and plans which objects matter in this room. SAM 3.1 tracks each of those objects through the whole video, so every finding points to a real frame and a real box. Then Spark surveys the marked frames, separating what is visible from what needs checking, and looks up FEMA E-74 guidance for the next steps.

## 04 · 01:15–01:45 · Evidence and next steps

Every finding shows what the video shows and what is still unknown. Each next step links to the FEMA section the model actually read; if that source check fails, no instructions are shown. Muse Image can illustrate a recommendation, always labelled as AI-generated, never as proof.

## 05 · 01:45–02:10 · A change needs new evidence

After a fix, you re-film the item. Uploading the same video again cannot prove anything changed. That check is a file hash, before any model call. Real before-and-after validation is still future work.

## 06 · 02:10–02:35 · Testing on known content

I also designed three Istanbul rooms with hazards placed on purpose, made with Muse Image and checked view by view with Spark. RiskLens matched five of five, four of four, and four of five, missing a blocked path to the door. Designed scenes, not an accuracy claim.

## 07 · 02:35–02:55 · Close

RiskLens is a visual screening tool, not a building inspection. It finds the evidence, is honest about what it cannot see, and helps you decide what needs a closer look, one room at a time.

## End-card links

- Product: https://selcuksntrk--risklens-web.us-east.modal.run
- Source: https://github.com/selcuksntrk/risklens
