# Delivery status and final handoff

Do not mark pending checks complete without evidence.

| Item | Status / evidence |
|---|---|
| Merge PR #1 into `main` | Done Nov 3 (merge commit `e8c6bb6`); `main` = release `v2-d7c7fa4d38b3`; repo, EVALUATION and submission links return 200 logged out |
| Synthetic-only product and submission copy | Prepared |
| Pre-model observations | AI visual review recorded; human adjudication pending |
| Measured evaluation | See `docs/EVALUATION.md` and `eval/synthetic-results.json` |
| Automated tests and release checks | See `docs/STATUS.md` |
| Desktop/mobile visual QA | Done in emulation (1440/390/360 px, headless Chrome): no overflow; fixes shipped in `v2-d7c7fa4d38b3`. Physical phone pending |
| Actual application screen recording | Done: `private/footage/01–07.mp4` from live `v2-d7c7fa4d38b3`, new run `86be749a131d` (complete, 3 findings, 172.8 s server time, $0.21); same-file guard 0 confirmed / 1 not assessable |
| Selçuk's two English voice takes | Pending |
| Caption alignment and final 1080p MP4 | Pending voice; silent rehearsal cut at `output/preview/` (175 s). Draft timings are not final subtitles |
| iPhone/Safari model, iOS, release | Pending |
| iPhone test outcomes | Pending |
| Current detailed rules / form declarations | Pending authenticated review |
| Login-free video URL | Pending |
| Submitted project URL / ID | Pending |
| Submission confirmation timestamp | Pending |

Final publication sequence: verify release and public branch → finish voice/screens → align captions and export → review on phone → upload and test video link → complete platform fields/declarations → record submission confirmation.
