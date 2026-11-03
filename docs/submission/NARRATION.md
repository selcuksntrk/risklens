# English narration and screen-recording sequence

Target: 2:55. No face camera or music. Record two complete voice takes. Read naturally; do not rush technical names. Pronounce SAM as “Sam” and FEMA as “fee-muh”.

Footage for every segment is already recorded from the live app (`private/footage/01–07.mp4`; see `recording-log.json`). The segment 03 run took 184 s from click to report; the footage shows it at 5.8× with a label. Segment 06 shows the generated evaluation and model-role cards.

This script avoids unmeasured accuracy claims. The final reviewer must check every sentence against the selected actual footage and the evaluation report.

## 01 · 00:00–00:15 · The evidence first

I’m Selçuk, building in Istanbul. Earthquake preparation includes the things inside a room. RiskLens connects a visible finding to its evidence and a practical next step. This room is synthetic, from Hypersim.

**Record:** Open the completed report and show one clearly supported finding and its evidence image. Keep “Precomputed synthetic example” visible. Do not describe unknown anchorage as missing anchorage.

## 02 · 00:15–00:35 · Your room first, or the sample

I built this for people preparing their own homes, under the Build for Your World theme. You start by recording or uploading a short video of one room. If you'd rather not share your home, the sample report opens instantly, or you can run the sample through Meta's models again, as I do here.

**Record:** Homepage with “Record a room” and “Upload a video” first, scroll to “Try it without filming your home”, then start a genuinely new sample run. Capture the whole run separately so timing and outcome can be checked.

## 03 · 00:35–01:15 · Why these models work together

Muse Spark first selects objects worth examining. SAM tracks candidate objects through the video. Spark then reviews sampled frames with those objects marked, connecting findings to specific visual evidence. The report separates observations from details that need checking. A connection hidden behind furniture is unknown, not proof that the furniture is unsecured. Waiting is shortened here; the audit trail records the actual processing time and model cost.

**Record:** Actual planner, tracking and surveyor stages, followed by corresponding evidence. Show “Recorded run · waiting shortened” when compressing waits. Never animate fabricated model results.

## 04 · 01:15–01:45 · Source-linked next steps

For a finding, RiskLens looks up relevant FEMA guidance. Suggestions link to sections actually returned by that lookup. If the source check fails, actionable instructions are withheld. These links show what the model read; they are not expert approval. Installation conditions still need appropriate assessment. The aim is to make the next question and the supporting evidence easy to understand.

**Record:** A source-supported suggestion and its linked section. Show the exact corresponding finding. Open the source page only if reachable; otherwise show the stored citation without claiming the external page opened.

## 05 · 01:45–02:10 · Do not mistake repetition for progress

Comparison also needs evidence. Uploading the original video cannot demonstrate a new physical change. That check uses the file hash, not model perception. We also test unchanged rendered footage and a different synthetic room. Those are limited regression controls, not real-world before-and-after validation.

**Record:** Actual identical-file verification and its refusal to confirm a change. Label “Same-file guard · no verifier model call”. Only show additional controls whose saved results have been checked.

## 06 · 02:10–02:35 · What we measured

The evaluation compares Spark-only and the full pipeline on five synthetic scenes previously used in development. We record failures, completion, time and cost, and repeat the main scene to expose variation. More findings do not automatically mean better accuracy. Human correctness review and positive physical-change validation remain unfinished.

**Record:** Actual evaluation table, repeat-run counts, and the model-role card (generated from committed results). Do not label completion as accuracy or choose only successful runs.

## 07 · 02:35–02:55 · Close

RiskLens is a visual screening prototype, not a building inspection or safety certificate. The public example is ready to explore, and the code documents what was built during the hackathon. Find the evidence, understand the uncertainty, and decide what needs a closer look.

**Record:** Completed report and final card with live URL and public source branch. Keep the synthetic-data and prototype labels readable.

## End-card links

- Product: https://selcuksntrk--risklens-web.us-east.modal.run
- Source: https://github.com/selcuksntrk/risklens
- Hypersim: https://github.com/apple-aiml-research/ml-hypersim

## Video description / credits

RiskLens — built during the Meta Global AI Developer Hackathon, Indie Developer / Build for Your World. Working prototype using Muse Spark 1.3 and SAM 3.1 for evidence-linked visual screening and source-linked precautions. Demonstration inputs are synthetic; no real home or successful physical precaution is shown. Waiting may be shortened and is labeled. Human correctness adjudication and real-world physical-change validation remain pending.

Hypersim © Apple Inc. / Roberts et al., ICCV 2021. Source: https://github.com/apple-aiml-research/ml-hypersim. Licensed under CC BY-SA 3.0: https://creativecommons.org/licenses/by-sa/3.0/. Modifications: preview frames assembled into video, resized/re-encoded, sampled and marked with object boxes. Derived Hypersim imagery retains CC BY-SA 3.0; the application code is MIT. FEMA E-74 references identify guidance read by the model and imply no endorsement. No music.
