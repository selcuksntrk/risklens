# Delivery status and final handoff

Do not mark pending checks complete without evidence.

| Item | Status / evidence |
|---|---|
| Merge PR #1 into `main` | Done Nov 3 (merge commit `e8c6bb6`); `main` = release `v2-d7c7fa4d38b3`; repo, EVALUATION and submission links return 200 logged out |
| Nov 4 redesign + samples | Merged to `main`, deployed as `v2-f99acb5fa923`: simplified light-only plain-language UI; real home + 3 Muse Image test rooms with answer keys 5/5, 4/4, 4/5 |
| Submission copy (real-home opening + synthetic sample) | Prepared |
| Pre-model observations | AI visual review recorded; human adjudication pending |
| Measured evaluation | See `docs/EVALUATION.md` and `eval/synthetic-results.json` |
| Automated tests and release checks | See `docs/STATUS.md` |
| Desktop/mobile visual QA | Done in emulation on the live redesign (1440/390/360 px, light and dark, headless Chrome): no overflow, no text below 13 px. Physical phone pending |
| Actual application screen recording | Done Nov 4 on live `v2-f99acb5fa923`: `private/footage-v3/01–07.mp4` (01 real home's list and top finding; 02 home; 03 new live run of the children's-room test room, complete, 5 findings, 136.3 s, $0.329, wait shortened 4.9× with label; 04 FEMA steps + labelled Muse Image picture, wait shortened with label; 05 same-file guard, upload shortened with label; 06 test-rooms card + answer key; 07 real-home replay + end card). Details in `footage-v3/recording-log.json`. Earlier sets kept in `footage-v2/`, `footage-final/` |
| Selçuk's English voice takes | Done Nov 4: two takes recorded; the second is used, by the owner's choice without the “always labelled as AI-made” and “not tested on real fixes” lines (the on-screen label and the form cover these) |
| Caption alignment and final 1080p MP4 | Done Nov 4: `output/review-1/risklens-review.mp4` (175 s, burned-in captions, `scripts/align_voice.py` + `scripts/assemble_demo.py --burn-captions`) |
| iPhone/Safari model, iOS, release | Pending |
| iPhone test outcomes | Pending |
| Current detailed rules / form declarations | Pending authenticated review |
| Login-free video URL | https://youtu.be/5rq5IBgD-AE (unlisted; opens without login, 175 s, 1080p) |
| Submitted project URL / ID | Pending |
| Submission confirmation timestamp | Pending |

Final publication sequence: verify release and public branch → finish voice/screens → align captions and export → review on phone → upload and test video link → complete platform fields/declarations → record submission confirmation.
