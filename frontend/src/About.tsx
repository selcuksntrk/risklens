import { useEffect } from 'react'
import { Top } from './components'
import { MODELS } from './ui'

const REPO = 'https://github.com/selcuksntrk/risklens'

/** Everything detailed lives here, so the working screens can stay short. */
export default function About() {
  useEffect(() => {
    const anchor = location.hash.split('#')[2]
    if (anchor) setTimeout(() => document.getElementById(anchor)?.scrollIntoView(), 50)
  }, [])
  return <main className="page">
    <Top><nav aria-label="Main"><a href="#/">Home</a></nav></Top>
    <article className="prose">
      <h1>How RiskLens works</h1>
      <p>Not every earthquake injury comes from the building itself. A wardrobe that tips over, a shelf above a bed or a glass cabinet by the door can hurt people too, and these are things you can do something about today. RiskLens helps you spot them in one room, from a short phone video. I built it in Istanbul, where most of us live with this question.</p>

      <h2>What each model does</h2>
      <table><thead><tr><th>Step</th><th>Model</th><th>What it does</th></tr></thead><tbody>
        <tr><td>Plan</td><td>{MODELS.spark}</td><td>Looks at 6–12 still frames from your video and picks the objects worth checking in this kind of room.</td></tr>
        <tr><td>Follow</td><td>{MODELS.sam}</td><td>Follows each of those objects through the whole video and draws a box on the exact frames where it appears.</td></tr>
        <tr><td>Check</td><td>{MODELS.spark}</td><td>Looks at the boxed frames and writes down what could fall, tip over, break or block the way out. It keeps what it saw apart from what it couldn’t see.</td></tr>
        <tr><td>Next steps</td><td>{MODELS.spark} + FEMA E-74</td><td>Looks up the relevant sections of FEMA E-74, the US guide to non-structural earthquake hazards, and writes steps that link to the section they come from. If a step can’t be linked to a section it read, it isn’t shown.</td></tr>
        <tr><td>Picture (optional)</td><td>{MODELS.image}</td><td>Draws what a fix could look like, on your own photo. Always labelled as an AI picture.</td></tr>
        <tr><td>Voice note (optional)</td><td>Muse Voice Transcribe 1.0</td><td>Turns what you say while filming into a written note about the room.</td></tr>
        <tr><td>Film again</td><td>{MODELS.sam} + {MODELS.spark}</td><td>Compares a new video of one item with the first one. Uploading the same file again is caught by a file check before any model runs.</td></tr>
      </tbody></table>
      <p>The app is React and FastAPI with ffmpeg for video, running on Modal. <a href={REPO} target="_blank" rel="noreferrer">The source code is public.</a></p>

      <h2>What it can and can’t tell you</h2>
      <ul>
        <li>It only sees what your video shows. Hidden fixings, like a strap behind a wardrobe, are reported as unknown, never assumed.</li>
        <li>It is a visual check by AI models, not an inspection by an engineer, and it says nothing about the building’s structure.</li>
        <li>A visible change after a fix doesn’t prove the fix is strong enough.</li>
        <li>The steps come from FEMA guidance, but no engineer has checked each one. Cost and time are rough estimates.</li>
      </ul>

      <h2>Your privacy</h2>
      <ul>
        <li>Your rooms belong to this browser. A link alone doesn’t give anyone else access.</li>
        <li>Videos and still frames are deleted after 7 days, reports after 30 days. You can delete a room at any time from its report.</li>
        <li>Your video is processed by Meta’s AI models. Try not to film people, documents or screens.</li>
      </ul>

      <h2 id="examples">About the examples</h2>
      <p><b>The real home</b> is a 37-second video of my own flat in Istanbul. Personal photos are blurred and the sound is removed. It is shown with my permission; please don’t reuse it.</p>
      <p><b>The three test rooms</b> were made with {MODELS.image}. For each room I wrote down the furniture and the hazards first: a glass display cabinet that isn’t fixed, a shelf above a child’s bed, boxes narrowing the path to the front door. {MODELS.image} then drew six views of the same room, and {MODELS.spark} checked every view to make sure it showed the same room and the planted hazards. The views were turned into a phone-style walkthrough with a label saying it is AI-made.</p>
      <p>Because we know what was planted, each test room shows how many hazards RiskLens found. Results: 5 of 5, 4 of 4, and 4 of 5 (it missed the boxes in the hallway). I matched findings to hazards by hand, one run per room. These are test rooms, not real homes, so this is not an accuracy score.</p>
      <p>Earlier development tests used Hypersim scenes (© Apple Inc., CC BY-SA 3.0). <a href={`${REPO}/blob/main/docs/EVALUATION.md`} target="_blank" rel="noreferrer">Evaluation notes</a> · <a href={`${REPO}/blob/main/DATA_LICENSES.md`} target="_blank" rel="noreferrer">Data and licences</a></p>

      <h2>Built for</h2>
      <p>The Meta AI Developer Hackathon, Indie track, under the theme “Build for Your World”. Built between 26 October and 4 November 2026. Release {import.meta.env.VITE_RISKLENS_VERSION ?? 'dev'}.</p>
    </article>
  </main>
}
