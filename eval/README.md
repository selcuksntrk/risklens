# Evaluation protocol

No real-home performance result has been claimed. Synthetic examples exercise the software; they do not validate household safety or demonstrate a physical fix.

1. Copy `manifest.example.json` to ignored `eval/private/manifest.json`. Put private clips below that directory. Assign an anonymous room ID and freeze each room's development/evaluation split. No room may cross splits.
2. Before viewing model answers, record visible objects, relevant conditions and unknown attachments. Record A0 and B0–B4 as specified in `docs/ACCEPTANCE.md`. Hash each clip with SHA-256 and store that hash in the manifest. Set `pre_model_observations_recorded` only after this work.
3. Run `cd backend && .venv/bin/python ../eval/run.py ../eval/private/manifest.json --output ../eval/results/run1`. This explicitly makes paid calls under the same $15/day budget. Same inputs run through Spark-only and full pipelines. Failed runs are preserved. No contributor models.
4. Human reviewers match finding IDs to independently recorded object/relation labels, one physical object/relation per match. Store TP/FP/FN, uncertainty exclusions and reasons in the private review. Unknown anchorage is not a positive label for missing anchorage. Have another reviewer adjudicate disagreements when available; report who reviewed and their expertise.
5. Prepare private review rows using the schema described in `metrics.py`. `attempt_id` identifies the originating clip/verification attempt; avoid duplicating duration/cost when several findings are reviewed. `independently_reviewed` means reviewed against pre-model observations, not necessarily reviewed by an engineer. Mark uncertainty exclusions explicitly in the private review.
6. Run `python eval/metrics.py eval/private/review.json --output eval/anonymous-results.json`. Only anonymous aggregate counts, medians and ranges leave the private directory. Inspect the output before publishing.

Target 3–5 rooms and 10–15 clips; report actual sample size. False confirmations require numerator AND denominator, separately before/after the guard. Report true confirmations and abstention counts too. Do not count an API response as a successful assessment. Do not pool development and evaluation results: provide separate review files and aggregate outputs.

B0/B1/B3/B4 must have no false confirmation before filming a positive demo. Investigate errors and rerun the relevant negative controls. Never weaken guards to make B2 pass. Test changes safely; do not create a hazard for the evaluation.
