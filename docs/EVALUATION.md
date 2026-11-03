# Synthetic development regression — measured results

Release: `v2-5f574344803c`. Manifest: `05a548f6086f3750632d56fb513f41df7d65f2c7577eeb393e8539693e5d5489`.

The submitted release differs from the evaluated one only in frontend wording and layout (`frontend/src`); `backend/app`, prompts, schemas and deployment code are unchanged, so these measurements apply to the deployed pipeline. Release IDs hash the full source set, which is why the ID changed. On November 3 the keyframe count became duration-based (max(6, min(12, ceil(duration/4 s)))). All five Hypersim clips are about 16.7 s, so they still receive exactly 6 keyframes; the measured setting is unchanged for these inputs. Longer real-room clips are not covered by these measurements.

**Five previously used synthetic scenes. Human adjudication is pending. These are operational measurements, not safety accuracy.**

| Variant | Reports / attempts | Complete assessments | Findings reported | Median seconds | Median recorded USD |
|---|---:|---:|---:|---:|---:|
| spark_only | 5/5 | 5 | 16 | 93.0 | 0.055031 |
| full | 5/5 | 5 | 20 | 117.2 | 0.192267 |

The variants have different capabilities. Spark-only lacks tracking and automatically abstains in verification; it is not used as a verification competitor. More findings do not establish higher accuracy.

## Negative controls

| Case | Findings checked | Guarded confirmations | Model calls (findings) | Status |
|---|---:|---:|---:|---|
| B0 | 4 | 0 | 0 | done |
| B1 | 4 | 0 | 4 | done |
| B3 | 4 | 0 | 4 | done |
| B4 | 4 | 0 | 3 | done |

- B0: Exact original file; deterministic hash guard, not model perception.
- B1: Same rendered sequence re-encoded; no physical change or new camera recording.
- B3: Central crop of the unchanged sequence; tests evidence loss, not a new camera recording.
- B4: Different synthetic bedroom and different objects; not a physical change.

B0 is a deterministic same-file check. Other controls may also abstain before a verifier model call. Zero false confirmations in this small synthetic set is not a general reliability guarantee.

## Repeat runs of the demo scene

| Run | Assessment | Findings | Seconds | Recorded USD |
|---|---|---:|---:|---:|
| 1 | complete | 4 | 111.6 | 0.206426 |
| 2 | complete | 5 | 106.1 | 0.182293 |
| 3 | complete | 5 | 120.6 | 0.203345 |

Recorded total: $2.076743; unknown-usage component: $0. Failed attempts: 0. Running: 0.

## Unmeasured

Finding precision/recall and positive physical-change verification are **not measured**. AI-assisted pre-run observations are available; Selçuk must review object/relationship matching before correctness metrics are published.

- Five synthetic scenes reused from development; not an independent benchmark.
- Reported findings and exact-frame boxes are not correctness scores.
- Re-encoding and cropping do not simulate a new real-camera recording.
- No successful physical precaution or real-home performance has been demonstrated.
- Costs are application accounting, including unknown reservations, not a provider invoice.

See [qualitative review notes](QUALITY_NOTES.md) for an observed model overstatement and the limits of the UI wording. These notes are not human accuracy labels.

Selected evidence frames: open the [completed example](https://selcuksntrk--risklens-web.us-east.modal.run/#/scan/hypersimbedroom) (first full run of the demo scene, no new model calls). Each finding shows its exact marked frame and tracking note. Derived images are not committed to Git.

Reproduce using `scripts/fetch_synthetic_eval.py`, `eval/prepare_synthetic.py`, `eval/run.py`, and `eval/summarize_synthetic.py`; see `eval/README.md`. Source media is excluded from Git.
