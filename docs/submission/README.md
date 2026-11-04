# Submission workspace

The video opens with a real recording of Selçuk's home (personal photos blurred, audio removed); the app's samples add three Muse Image designed scenes (labelled AI-generated); development regression uses licensed Hypersim scenes.

## Start here

1. [Narration and recording sequence](NARRATION.md): English voiceover and seven screen-recording segments.
2. [Selçuk's iPhone and final-review checklist](SELCUK.md): the remaining human actions.
3. [Form-ready copy](FORM.md), [judge answers](JUDGE-QA.md), and [rights record](RIGHTS.md).
4. [Measured evaluation](../EVALUATION.md): current operational results; human correctness review remains separate.

Screen footage is recorded from the live application (headless Google Chrome, 1920×1080, light theme) by `scripts/record_demo.py`: 01 the real home's list of things to check and its top finding, 02 home (question, examples, how each model is used), 03 a new live run of the children's-room test room started from its report (wait shortened, labelled with the factor and actual duration), 04 one finding with FEMA-linked steps and a labelled Muse Image picture of a fix, 05 the same-file guard, 06 the test-rooms card and answer key, 07 the real home's replay and end card. Output: ignored `docs/submission/private/footage-v3/` with `recording-log.json`. Draft captions: `python3 scripts/draft_captions.py`. Put voice takes in `docs/submission/private/` as `voice-take-1.m4a` and `voice-take-2.m4a`.

Rehearse with `python3 scripts/assemble_demo.py --silent-preview --captions docs/submission/captions-draft.srt --output docs/submission/output/preview` (silent, never a submission file). Visual QA used emulated desktop/phone viewports (`scripts/visual_qa.py`); a physical iPhone check is still Selçuk's.

The narration is written for 175 seconds. `captions-draft.srt` is a timing guide, not an aligned transcript. Adjust it against the selected voice take before export. The assembly tool checks duration and inputs but cannot certify that the footage matches the narration or that captions are synchronized.

Final platform submission and required declarations are completed by Selçuk. A prepared form, local file, or deployed app is not a submitted entry. Record the final video URL, submission URL/ID and confirmation time in `HANDOFF.md`.
