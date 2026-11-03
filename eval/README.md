# Evaluation protocol

## November 3 synthetic-only delivery

Five existing Hypersim scenes are **development regression**. All were previously used, including the public example. `synthetic-sources.json` records source URLs, licenses and clip hashes. `synthetic-observations.json` records AI visual observations made before new runs; it is not human/expert ground truth. Selçuk's adjudication remains pending.

```sh
backend/.venv/bin/python scripts/fetch_synthetic_eval.py
python eval/prepare_synthetic.py --source-root eval/data/regression
backend/.venv/bin/python eval/run.py eval/private/synthetic/manifest.json --output eval/results/synthetic-2026-11-03-run1
python eval/summarize_synthetic.py eval/results/synthetic-2026-11-03-run1/runs.private.json
```

The original implementation run used existing `../spikes/data/r` clips. The public downloader above recovers the same original frames using `synthetic-frame-manifest.json`; ffmpeg-version differences can change encoded video bytes. A fresh encoding gets a new frozen manifest and must not be described as byte-identical to the historical run. The legacy `gt.json` filename in reproduced inputs contains source metadata only, not asserted hazard labels.

Preparation freezes video and observation hashes and creates ignored copies and control variants. Use new destination/output directories for later runs. The runner checks all hashes before paid work, preserves started/failed attempts and unknown charges, and stops on service/auth/rate/budget failures. It uses the existing persisted $15/day ledger without increasing the cap. Reconcile an interrupted `running` attempt against saved report/billing before another paid attempt; never count it as successful automatically.

The primary comparison is five clips × two variants. The demo scene has two extra full runs, reported separately. Full-pipeline controls: B0 original bytes, B1 re-encoding, B3 crop, B4 different bedroom. These are synthetic proxies, not physical re-filming. No positive physical-change test exists. Spark-only automatic abstention is not evidence of verifier superiority.

`summarize_synthetic.py` exports operational counts/time/cost and keeps accuracy explicitly unmeasured. Failed calls are included in accounting. To publish correctness metrics, review each finding against frozen observations and images, record uncertainty/exclusions, and use `metrics.py`; never set `independently_reviewed` based only on model output.

## Future real-room validation

No real-home performance result has been claimed. Synthetic examples exercise the software; they do not validate household safety or demonstrate a physical fix.

1. Copy `manifest.example.json` to ignored `eval/private/manifest.json`. Put private clips below that directory. Assign an anonymous room ID and freeze each room's development/evaluation split. No room may cross splits.
2. Before viewing model answers, record visible objects, relevant conditions and unknown attachments. Record A0 and B0–B4 as specified in `docs/ACCEPTANCE.md`. Hash each clip with SHA-256 and store that hash in the manifest. Set `pre_model_observations_recorded` only after this work.
3. Run `cd backend && .venv/bin/python ../eval/run.py ../eval/private/manifest.json --output ../eval/results/run1`. This explicitly makes paid calls under the same $15/day budget. Same inputs run through Spark-only and full pipelines. Failed runs are preserved. No contributor models.
4. Human reviewers match finding IDs to independently recorded object/relation labels, one physical object/relation per match. Store TP/FP/FN, uncertainty exclusions and reasons in the private review. Unknown anchorage is not a positive label for missing anchorage. Have another reviewer adjudicate disagreements when available; report who reviewed and their expertise.
5. Prepare private review rows using the schema described in `metrics.py`. `attempt_id` identifies the originating clip/verification attempt; avoid duplicating duration/cost when several findings are reviewed. `independently_reviewed` means reviewed against pre-model observations, not necessarily reviewed by an engineer. Mark uncertainty exclusions explicitly in the private review.
6. Run `python eval/metrics.py eval/private/review.json --output eval/anonymous-results.json`. Only anonymous aggregate counts, medians and ranges leave the private directory. Inspect the output before publishing.

Target 3–5 rooms and 10–15 clips; report actual sample size. False confirmations require numerator AND denominator, separately before/after the guard. Report true confirmations and abstention counts too. Do not count an API response as a successful assessment. Do not pool development and evaluation results: provide separate review files and aggregate outputs.

B0/B1/B3/B4 must have no false confirmation before filming a positive demo. Investigate errors and rerun the relevant negative controls. Never weaken guards to make B2 pass. Test changes safely; do not create a hazard for the evaluation.
