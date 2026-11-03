# Form-ready project copy

Use the current platform's actual field lengths. This document is not a completed submission.

**Name:** RiskLens

**Track:** Indie Developer

**Theme:** Build for Your World

**Tagline:** Room findings linked to visual evidence, source-backed precautions, and explicit uncertainty.

**Short description:** RiskLens is an earthquake-preparedness prototype built in Istanbul. It uses Muse Spark and SAM to review sampled room views, connect findings to tracked objects, and suggest precautions linked to FEMA guidance. The demo video opens with a real recording of the author's bedroom in Istanbul (suitcases stacked on a tall wardrobe). Visitors can explore four samples without filming their homes: that real recording plus three Istanbul rooms designed with Muse Image, each with hazards placed on purpose and an answer key.

**Problem and impact:** Preparing a room involves deciding which visible conditions deserve attention, what remains unknown, and which guidance supports a next step. RiskLens brings those pieces into one inspectable workflow. Its intended users are people preparing their living spaces. This submission demonstrates the workflow on one real home recording and on synthetic interiors (Hypersim for development regression; three Muse Image designed scenes where RiskLens matched 5/5, 4/4 and 4/5 designed hazards in one author-matched run each). It does not establish real-home accuracy, behavior change or reduced losses.

**How it works / Meta models:** Muse Spark 1.3 selects tracking concepts, reviews marked frames and uses a bounded FEMA lookup workflow to prepare source-linked suggestions. SAM 3.1 tracks candidate objects through the clip and supports exact-frame evidence. Experimental comparison uses SAM and Spark with deterministic checks for identity and visible change. Muse Voice Transcribe and Muse Image are optional implemented features; neither is needed for this submitted demo, and generated illustrations are never verification evidence. No open-weight bonus eligibility is claimed.

**What makes it different:** The product connects findings to object evidence, records source access, withholds unsupported actionable suggestions, and distinguishes missing evidence from confirmed changes. The contribution is the inspectable multi-step workflow. We do not claim to be the first property-inspection or earthquake-preparedness application.

**Built during the event:** Video ingestion and progress reporting; model orchestration; tracking and marked evidence; observed/needs-check report contract; source-checked suggestions; experimental comparison safeguards; session ownership and deletion; metered model calls; licensed public example; reproducible release and evaluation tooling; user-first record/upload home screen; duration-based keyframe sampling. Commit history and README identify the event work and third-party components. Development began after the October 26 kickoff.

**Evaluation:** See the linked measured report for five previously used synthetic scenes, same-input Spark-only/full runs, repeated demo runs and negative controls. The report includes failures and cost/time accounting. This is development regression, not an independent benchmark. Human correctness adjudication and positive physical-change testing are pending. Do not replace these qualifications with an accuracy percentage.

**Limitations:** Sampled views can miss objects or relationships. Hidden attachment conditions are unknown. Source-linked suggestions are not expert approval. A visible change does not certify installation adequacy. No structural inspection, earthquake prediction, calibrated risk score or insurance decision is provided.

**Links:**

- Live product: https://selcuksntrk--risklens-web.us-east.modal.run
- Public source: https://github.com/selcuksntrk/risklens
- Evaluation: https://github.com/selcuksntrk/risklens/blob/main/docs/EVALUATION.md
- Demo video: **pending actual screen recording, Selçuk's voice, review and upload**
- Team: Selçuk; confirm the platform's participant identity rather than inventing profile details.

**Bonus positioning:** The implemented agent workflow may be described where the form asks. Do not claim open-weight execution or add models purely for a bonus. Social posting is not part of the automated submission work.
