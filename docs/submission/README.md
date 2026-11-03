# Submission workspace

The video opens with a real recording of Selçuk's home (personal photos blurred, audio removed); comparison, measurement and the public sample use licensed synthetic footage.

## Start here

1. [Narration and recording sequence](NARRATION.md): English voiceover and seven screen-recording segments.
2. [Selçuk's iPhone and final-review checklist](SELCUK.md): the remaining human actions.
3. [Form-ready copy](FORM.md), [judge answers](JUDGE-QA.md), and [rights record](RIGHTS.md).
4. [Measured evaluation](../EVALUATION.md): current operational results; human correctness review remains separate.

Screen footage is recorded from the live application (headless Google Chrome, 1920×1080): `scripts/record_own_video.py` for the real-home upload path (01–04, 07) and `scripts/record_demo.py` for the synthetic sample (05–06). The selected set is in the ignored `docs/submission/private/footage-final/`; uncut recordings and `recording-log.json` files (release, scan ID, actual duration and cost) are under `private/footage/`. Segment 03 is sped up with an on-screen label that states the factor and the actual duration. Segment 06 shows cards generated from `eval/synthetic-results.json`, not hand-typed numbers. Put voice takes in `docs/submission/private/` as `voice-take-1.m4a` and `voice-take-2.m4a`.

Rehearse with `python3 scripts/assemble_demo.py --silent-preview --captions docs/submission/captions-draft.srt --output docs/submission/output/preview` (silent, never a submission file). Visual QA used emulated desktop/phone viewports (`scripts/visual_qa.py`); a physical iPhone check is still Selçuk's.

The narration is written for 175 seconds. `captions-draft.srt` is a timing guide, not an aligned transcript. Adjust it against the selected voice take before export. The assembly tool checks duration and inputs but cannot certify that the footage matches the narration or that captions are synchronized.

Final platform submission and required declarations are completed by Selçuk. A prepared form, local file, or deployed app is not a submitted entry. Record the final video URL, submission URL/ID and confirmation time in `HANDOFF.md`.
