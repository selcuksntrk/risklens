# Delivery status and final handoff

Do not mark pending checks complete without evidence.

| Item | Status / evidence |
|---|---|
| Merge PR #1 into `main` | Done Nov 3 (merge commit `e8c6bb6`); `main` = release `v2-d7c7fa4d38b3`; repo, EVALUATION and submission links return 200 logged out |
| Nov 4 redesign + samples | Merged to `main` and deployed as `v2-c3a70a9e1077` (evidence-lens UI; real home + 3 Muse Image designed samples with answer keys 5/5, 4/4, 4/5) |
| Submission copy (real-home opening + synthetic sample) | Prepared |
| Pre-model observations | AI visual review recorded; human adjudication pending |
| Measured evaluation | See `docs/EVALUATION.md` and `eval/synthetic-results.json` |
| Automated tests and release checks | See `docs/STATUS.md` |
| Desktop/mobile visual QA | Done in emulation on the live redesign (1440/390/360 px, light and dark, headless Chrome): no overflow, no text below 13 px. Physical phone pending |
| Actual application screen recording | Done Nov 4 on live `v2-c3a70a9e1077`: `private/footage-v2/01–07.mp4` (01 real-home sample report; 03 new live run of the designed children's bedroom, complete, 5 findings, 178 s, $0.325, wait shortened 7.8× with label; 04 FEMA steps + labelled Muse Image illustration, wait shortened 6× with label; 05 same-file guard, 0 confirmed / 1 not assessable, upload shortened 5× with label; 06 designed-scenes card + answer key; 07 real-home replay + end card). Re-cuts listed in `footage-v2/recording-log.json`. Previous set kept in `footage-final/` |
| Selçuk's two English voice takes | Pending |
| Caption alignment and final 1080p MP4 | Pending voice; silent rehearsal cut at `output/preview-v2/` (175 s) with `captions-draft.srt` from `scripts/draft_captions.py`. Draft timings are not final subtitles |
| iPhone/Safari model, iOS, release | Pending |
| iPhone test outcomes | Pending |
| Current detailed rules / form declarations | Pending authenticated review |
| Login-free video URL | Pending |
| Submitted project URL / ID | Pending |
| Submission confirmation timestamp | Pending |

Final publication sequence: verify release and public branch → finish voice/screens → align captions and export → review on phone → upload and test video link → complete platform fields/declarations → record submission confirmation.
