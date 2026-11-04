# Form text

Latest text for the Cerebral Valley submission form, using its real fields. The live submission is the record: this file does not prove which version is on the platform.

- **Team name:** RiskLens (Selçuk, solo)
- **Track:** Indie Developer Track
- **Problem statement:** Build for Your World
- **Public GitHub repository:** https://github.com/selcuksntrk/risklens
- **3-minute demo video:** https://youtu.be/2tA6bLuztSk
- **Live product:** https://selcuksntrk--risklens-web.us-east.modal.run

## Project Description

RiskLens (theme: Build for Your World) turns a one-minute phone video of a room into a list of things that could fall, tip over or block your way out in an earthquake. Each finding shows the exact frame and box it is based on, says what the video can't show, and links next steps to FEMA E-74 guidance.

I live in Istanbul, where most of us know an earthquake is a question of when. An engineer can't visit every flat, but a wardrobe that can tip, a shelf above a child's bed or boxes narrowing the way to the door are things a family can deal with today, if someone points them out. The wider problem is well documented: in a study of New Zealand commercial buildings during the 2010-2014 earthquakes, 556 of 947 injuries were attributed to non-structural damage (Yeow et al., 2020). That sample isn't homes, but the hazards are the kind RiskLens looks for.

RiskLens is for families and renters preparing the rooms they live in. It needs a phone and about a minute, with no account and no expert on site. A run costs about $0.30 in model calls, so it can be offered free.

Try it without filming: https://selcuksntrk--risklens-web.us-east.modal.run opens four examples, including my own home, with no model calls. "Run it again live" starts a new run.

Engineering:
- Exact evidence: findings link to a tracked object, frame and box.
- Enforced checks: a next step without a verified FEMA source is blocked in the interface and the endpoint. An identical re-filmed file is caught by a SHA-256 check before any model runs.
- Reliability: idempotent uploads, a bounded job queue, per-call budget reservations, a $15 daily model cap, and polling when live progress drops. Interrupted jobs never silently restart paid calls.
- Privacy: scans belong to a browser session, access is checked on every private route, videos are deleted after 7 days and reports after 30.
- Tests: 73 backend and 14 frontend tests, plus a regression comparing Spark alone with the full pipeline, including negative controls with zero false confirmations.

Evaluation: on three test rooms with planted hazards written down in advance, it found 13 of 14 and did not flag the control items (one run per room, matched by hand). The miss is shown in the app and the demo. These are test scenes, so no accuracy on real homes is claimed.

Limits: it is a visual check, not a building inspection, and says nothing about structural safety. It only sees what the video shows, hidden fixings stay unknown, and the FEMA-linked steps are not reviewed by an engineer. Validation on real before-and-after fixes is future work.

Next: a volunteer pilot in real homes and expert review of findings, to test whether people act on them.

All of the project was built during the event. Third-party code and data are labelled in the README and DATA_LICENSES.md.

## Describe your use of Meta products to build the submitted project

RiskLens is an agent pipeline with verification gates: each model does one job, hands its result to the next, and code checks the result.

1. Muse Spark 1.3 (planner) studies 6-12 still frames and decides which objects matter in this kind of room.
2. SAM 3.1 follows those objects through the whole video, so every finding points to a real box on a real frame.
3. Muse Spark 1.3 (surveyor) reviews the boxed frames and keeps what it could see apart from what it couldn't, such as a hidden wall fixing.
4. Muse Spark 1.3 (fix planner) looks up sections of FEMA E-74 through a tool and writes next steps that cite them. A step that can't be traced to a section it read is withheld.
5. Muse Image 1.0 edits the user's own frame to show what a fix could look like, always labelled as AI-made and never treated as proof.
6. SAM 3.1 + Muse Spark 1.3 compare a re-filmed video with the first one, requiring the same object and a visible change.
7. Muse Voice Transcribe 1.0 turns an optional spoken note about the room into text.

The less obvious use: Meta models also built our test set. I wrote down three Istanbul rooms and their hazards first. Muse Image drew six views of each room, anchored to the first view, and Muse Spark checked every view for the same room and the planted hazards before it was used (18 of 18 passed, 2 on a second attempt). The views became phone-style walkthrough videos, labelled as AI-made, so RiskLens could be tested on content with known answers, including control items placed to see whether they get flagged.

## Why are Meta's models important to your solution?

RiskLens depends on models working together on video.

A chat model alone can describe a room, but it can't show where a hazard is. SAM 3.1 tracks each object through the video, so a finding links to an exact frame and box that a person can check. Muse Spark decides what SAM should look for, then reasons over the marked frames and separates what is visible from what needs checking. Its tool use ties next steps to the FEMA sections it actually read, and the code blocks any step without a source. Muse Image can edit the user's own photo, so a recommendation becomes something a family can picture.

Having all of this behind one API let one developer build it in ten days. A full run took about 2-5 minutes and cost about $0.30 in our recorded runs, low enough to offer it free. That is what could put this kind of check within reach of families who would never hire an expert.

## Partner technologies

Modal hosts the app and its persistent volume. Deploys were fast (about 2 minutes the first time, seconds afterwards).

## X post draft (Selçuk posts this himself)

> I live in Istanbul. So I built RiskLens: film a room for a minute, and Meta's Muse Spark and SAM 3.1 point out what could fall, tip over or block your way out, on the exact video frame, with next steps from FEMA guidance.
>
> It also tells you what it can't see.
>
> Built solo for the @Meta AI Developer Hackathon.
>
> [video] [live link]

Check the correct event account and hashtag on the event page before posting.
