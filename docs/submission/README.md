# Submission workspace

The video opens with a real recording of Selçuk's home (personal photos blurred, audio removed); the app's samples add three Muse Image designed scenes (labelled AI-generated); development regression uses licensed Hypersim scenes.

## Start here

1. [Narration and recording sequence](NARRATION.md): English voiceover and seven screen-recording segments.
2. [Selçuk's iPhone and final-review checklist](SELCUK.md): the remaining human actions.
3. [Form-ready copy](FORM.md), [judge answers](JUDGE-QA.md), and [rights record](RIGHTS.md).
4. [Measured evaluation](../EVALUATION.md): current operational results; human correctness review remains separate.

Screen footage is recorded from the live application (headless Google Chrome, 1920×1080) by `scripts/record_demo.py` (Nov 4 storyboard): 01 real-home sample report, 02 home and samples, 03 a new live run of the designed children's bedroom (wait shortened, labelled with the factor and actual duration), 04 evidence, FEMA next steps and a labelled Muse Image illustration, 05 same-file guard, 06 designed-scenes card (from `examples/generated/catalog.json`) and answer key, 07 real-home analysis replay and end card. Output: ignored `docs/submission/private/footage-v2/` with `recording-log.json`. Captions draft: `python3 scripts/draft_captions.py`. Put voice takes in `docs/submission/private/` as `voice-take-1.m4a` and `voice-take-2.m4a`.

Rehearse with `python3 scripts/assemble_demo.py --silent-preview --captions docs/submission/captions-draft.srt --output docs/submission/output/preview` (silent, never a submission file). Visual QA used emulated desktop/phone viewports (`scripts/visual_qa.py`); a physical iPhone check is still Selçuk's.

The narration is written for 175 seconds. `captions-draft.srt` is a timing guide, not an aligned transcript. Adjust it against the selected voice take before export. The assembly tool checks duration and inputs but cannot certify that the footage matches the narration or that captions are synchronized.

Final platform submission and required declarations are completed by Selçuk. A prepared form, local file, or deployed app is not a submitted entry. Record the final video URL, submission URL/ID and confirmation time in `HANDOFF.md`.
