# Qualitative review notes — synthetic demo

These are AI-assisted review notes, not independent human adjudication or expert validation. Keep them beside the measured operational results.

## Unsupported certainty in a model observation

In the first full run of `ai_048_004_cam_00` (scan `evalf58ad142c366`, finding `h3`), the model described a tall black panel as “leaning unsecured”. The sampled views support **leaning**; the absence of a hidden restraint is not established. The pre-run observations already marked restraint and material unknown. Treat “unsecured” as an overstatement requiring human review. Do not quote it as an established fact in the demo or manually rewrite the historical report to conceal it.

The report UI now identifies observations as model-generated, not expert-reviewed, and labels the `observed` state “Reported visible”. This wording does **not** fix the underlying model error. Prompt instructions already say unseen attachments are unknown; instructions are not a guarantee of adherence. Human review and stronger evidence constraints remain future work.

## Repeatability

The three full runs of the main scene reported four, five and five findings with differing object selection. Preserve all three. The packaged example uses the **first full run**, selected by chronological protocol rather than by the highest finding count. Later results do not retroactively replace its provenance.

## Honest demonstration choices

- Open with the purple shelving observation and its requested attachment view. Explain what is visible and what remains unknown.
- Do not claim a missing restraint, a successful physical precaution, whole-room coverage or earthquake safety.
- Show identical-file rejection as a file-hash control. It does not measure model perception.
- Exact-frame boxes can still be mislocalized or attached to a flawed interpretation; inspect them rather than treating tracking support as correctness.
- Use the operational evaluation table without a precision/recall headline while human adjudication is pending.

## Real-home demonstration (November 3) — not an evaluation

Selçuk recorded a 37 s walkthrough of the apartment (living room, hallway, kitchen, bedroom). Audio was removed and fridge photos blurred before upload. Four runs of essentially the same clip, kept as recorded:

| Run | Keyframes | Findings | Notes |
|---|---:|---|---|
| Local CLI, unblurred copy | 6 (fixed) | 2: bedroom wardrobe (tip-over), “mirrored wardrobe doors” | Suitcases on the wardrobe fell between keyframes and were missed. The “mirror” is not supported by the blurry evidence frame; treat it as an observation error. |
| Local CLI, unblurred copy | 10 (duration-based) | 4: wardrobe, grey suitcase, blue suitcase, pedestal fan | Suitcases found with tracked evidence. The wardrobe text says “doors closed” while a door is visibly ajar. |
| Live app, blurred copy | 10 | 4: blue suitcase, bedroom wardrobe, hallway wardrobe, fan | Footage discarded because the UI printed “Requested view: none” (fixed). |
| Live app, blurred copy (**used in the video**) | 10 | 3: bedroom wardrobe, blue suitcase, hallway wardrobe | Wardrobe text: anchoring “not visible and unknown, not assumed absent”. |

Lessons: a multi-room walkthrough dilutes a single-room planner, and fixed sampling can skip short views; keyframes now scale with duration (6–12). Finding sets differ between runs. No expert reviewed these findings and no physical change was made or verified.
