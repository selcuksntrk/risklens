# Submission workspace

- [Form text](FORM.md), [judge answers](JUDGE-QA.md) and [rights record](RIGHTS.md)
- [Narration and how the video was made](NARRATION.md)
- [Delivery record](HANDOFF.md)
- [Measured evaluation](../EVALUATION.md)

The final video is built by `scripts/compose_demo.py` from phone-viewport footage (`scripts/record_phone.py`), real SAM 3.1 masks (`scripts/render_sam_hero.py`) and the author's voice (`scripts/align_voice.py`). Source media stays in the ignored `docs/submission/private/` folder.

The video opens with a real recording of Selçuk's home (personal photos blurred, audio removed). The app's examples add three Muse Image test rooms, labelled as AI-made. Development regression uses licensed Hypersim scenes.
