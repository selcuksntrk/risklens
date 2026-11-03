# English narration and screen-recording sequence

Target: 2:55. No face camera or music. Record two complete voice takes. Read naturally; do not rush technical names. Pronounce SAM as “Sam” and FEMA as “fee-muh”.

Footage is recorded from the live app (`private/footage-final/01–07.mp4`):

- **01–04: real recording of Selçuk's home in Istanbul**, uploaded through “Upload a video” on release `v2-60d4a67b448d` (scan `b3adc4b6c841`, 3 findings, 184 s click-to-report, $0.345; see `private/footage/real/recording-log.json`). Personal photos on the fridge are blurred; audio was removed before upload. Every frame carries the label “Real recording · Selçuk's home, Istanbul · personal photos blurred”. The wait in 03 is shown at 6× with a label stating the actual duration.
- **05–06: public synthetic sample and measured results.** 05 is the same-file guard on a sample run; 06 shows cards generated from `eval/synthetic-results.json`.
- **07:** the “Try it without filming your home” section and the end card.

This script avoids unmeasured accuracy claims. The real-home run is a demonstration, not an evaluation result. Check every sentence against the selected footage before export.

## 01 · 00:00–00:15 · A real finding in my home

This is my bedroom in Istanbul. RiskLens flagged the wardrobe with two suitcases stacked on top. And it says what it cannot see: whether the wardrobe is anchored to the wall is unknown, not assumed.

**Footage:** the wardrobe finding with its tracked evidence frame and the “not assumed absent” wording.

## 02 · 00:15–00:35 · Your own room first

In Istanbul, earthquake preparation includes what is inside our homes. I built RiskLens for people like me, under the Build for Your World theme. You record or upload a short video of one room and add optional context.

**Footage:** home screen (Record a room / Upload a video), upload, video preview, typed context, “Use video”.

## 03 · 00:35–01:15 · Why these models work together

Here is the real run, with the waiting shortened. Muse Spark looks at sampled frames and decides which objects are worth examining. SAM 3.1 tracks each of those objects through the whole video, so every finding is tied to an exact frame and box. Spark then reviews the marked frames and separates what is visible from what needs checking. Here it found the bedroom wardrobe, the suitcases on top, and a second wardrobe in the hallway. The actual time and model cost are kept in the audit trail.

**Footage:** planner, SAM tracking chips and keyframe strip, surveyor and fix planner, then the report.

## 04 · 01:15–01:45 · Source-linked next steps

Each next step links to the FEMA E-74 section the model actually read. Here: film where the wardrobe meets the wall, keep the top clear in the meantime, and ask a professional if anchoring cannot be confirmed. If a source check fails, RiskLens withholds actionable instructions. The links show what was read; they are not expert approval.

**Footage:** the wardrobe finding's suggestions and FEMA links (stored citations; the PDF is not opened).

## 05 · 01:45–02:10 · A change needs new evidence

You can re-film after making a change. But uploading the original video again cannot prove anything changed. That check is a file hash, not model perception, shown here on the public synthetic sample. Real before-and-after validation is still future work.

**Footage:** same-file comparison on a synthetic sample run, labelled “Same-file guard · SHA-256 match · no verifier model call”.

## 06 · 02:10–02:35 · What we measured

We measured the pipeline on five synthetic scenes previously used in development: Spark only versus Spark with SAM, repeated runs, and negative controls with zero false confirmations. We record failures, time and cost. More findings do not automatically mean better accuracy, and human correctness review is still pending.

**Footage:** generated evaluation card, then the model-role card.

## 07 · 02:35–02:55 · Close

RiskLens is a visual screening tool, not a building inspection. If you would rather not film your home, the sample report is one tap away. Find the evidence, understand what is unknown, and decide what needs a closer look.

**Footage:** “Try it without filming your home”, then the end card with live URL and repository.

## End-card links

- Product: https://selcuksntrk--risklens-web.us-east.modal.run
- Source: https://github.com/selcuksntrk/risklens
- Hypersim: https://github.com/apple-aiml-research/ml-hypersim

## Video description / credits

RiskLens — built during the Meta Global AI Developer Hackathon, Indie Developer / Build for Your World. Working prototype using Muse Spark 1.3 and SAM 3.1 for evidence-linked visual screening and source-linked precautions.

The opening shows a real recording of the author's home in Istanbul, analysed live by the deployed app; personal photos are blurred and no physical change is shown. Findings are model-generated and were not expert-reviewed. Waiting is shortened and labelled. The comparison and measurement sections use synthetic scenes; human correctness review and real-world physical-change validation remain pending.

Hypersim © Apple Inc. / Roberts et al., ICCV 2021. Source: https://github.com/apple-aiml-research/ml-hypersim. Licensed under CC BY-SA 3.0: https://creativecommons.org/licenses/by-sa/3.0/. Modifications: preview frames assembled into video, resized/re-encoded, sampled and marked with object boxes. Derived Hypersim imagery retains CC BY-SA 3.0; the application code is MIT. FEMA E-74 references identify guidance read by the model and imply no endorsement. No music.
