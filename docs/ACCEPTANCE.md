# Acceptance record — hackathon delivery and future real tests

**November 3 delivery decision:** measurement and negative controls use licensed synthetic footage. The demo video opens with one real recording of the author's home, analysed by the same release as a demonstration (runs and errors in [quality notes](QUALITY_NOTES.md)); it is not an A0–B4 acceptance result. The real-room table below is a future validation protocol, not a claim of completed work or an official entry requirement. A physical iPhone/Safari check has not been recorded for this delivery. Camera recording, microphone behavior and Android hardware remain untested unless separately recorded. Desktop/phone-size visual QA was run in headless-Chrome emulation on November 3 (see [status](STATUS.md)); emulation is not a physical-device result.

Synthetic negative controls are recorded in [evaluation results](EVALUATION.md): B0 same file, B1 re-encoding, B3 crop and B4 different rendered room. They do not replace real-camera tests. No synthetic B2 physical success is permitted.

Future physical-validation protocol: test on physical iPhone/Safari and Android/Chrome when consented real-room work resumes. Record device, OS/browser version, application release, timestamp, case ID, observed outcome and artifact location. Do not put private clips or narration in Git.

## Mobile cases (run on both phones)

| Case | Procedure | Required outcome | iPhone | Android |
|---|---|---|---|---|
| C1 | Allow video, deny optional microphone | Video recording and typed context still work | Pending | Pending |
| C2 | Record portrait, stop twice quickly | One preview; correct orientation; one upload | Pending | Pending |
| C3 | Upload MOV/MP4/WebM from gallery | Original name/MIME preserved; editable context; no claim of gallery transcription | Pending | Pending |
| C4 | Disconnect network during upload; reconnect; Retry upload | Same Blob/key, one paid job, no lost preview | Pending | Pending |
| C5 | Leave while recording and while previewing | Camera/mic indicators stop; recorder/socket/audio context/Blob URL cleaned | Pending | Pending |
| C6 | Retake after preview | New recording/key; previous Blob URL released | Pending | Pending |
| C7 | Unavailable MediaRecorder | Gallery upload remains available | Pending | Pending |
| C8 | Upload empty/non-video/corrupt file | Clear rejection before model calls | Pending | Pending |
| C9 | Lose SSE connection during verification | Poll only requested verify_id; old result never substituted | Pending | Pending |

## Ground truth and re-filming

Write observations before viewing model output. Record object identity, exact visible relationship, whether an attachment is visible, and unknowns. No inferred absence of anchors, wall material, weight or mounting strength. Do not manufacture hazards. Physical work is performed by the user appropriately, with expert help where needed.

| Case | Input | Expected behavior | Actual result |
|---|---|---|---|
| A0 | Original room | Visible observations and unknown details separated | Pending |
| B0 | Exact original file | Zero new changes confirmed | Pending real-room run; automated identical-source guard tested |
| B1 | Same room, new angle/light, no physical change | No false confirmation | Pending |
| B2 | Real visible precaution, same object | Narrow relevant change may be confirmed; no installation certificate | Pending |
| B3 | Poor/occluded attachment view | Need another view or manual review | Pending |
| B4 | Different similar object | No false confirmation | Pending |

**If B0/B1/B3/B4 yields a false confirmation, stop positive-demo filming.** Investigate, correct, and repeat the affected negative controls. Do not weaken guards to pass B2. A deterministic mocked test does not replace these real model evaluations.

Acceptance notes per attempt: input SHA-256, original finding ID, before/after observations, model verdict, guarded verdict, evidence actually selected, reviewer, uncertainty, elapsed seconds, recorded/unknown cost, and release ID. Keep each attempt separately, including failures. A completed HTTP request is not an accepted result.
