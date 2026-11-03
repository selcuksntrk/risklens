# Data and source notices

| Material | Actual use | License / attribution | Source |
|---|---|---|---|
| Hypersim, scene `ai_048_004`, camera `cam_00` | Synthetic walkthrough sample and early engineering checks | © Apple Inc.; Creative Commons Attribution-ShareAlike 3.0 Unported | [Dataset](https://github.com/apple-aiml-research/ml-hypersim), [license](https://creativecommons.org/licenses/by-sa/3.0/) |
| Hypersim scenes `ai_018_005`, `ai_036_006`, `ai_048_004`, `ai_048_005`, `ai_051_002` | Synthetic development regression and negative controls | © Apple Inc.; CC BY-SA 3.0; previously used in development | [Per-clip source/hash registry](eval/synthetic-sources.json) |
| FEMA E-74, December 2012, 14 selected sections | Condensed source text for recommendation lookup | U.S. federal work; preserve source attribution and separately attributed illustrations if reused | [FEMA E-74](https://www.fema.gov/emergency-managers/risk-management/earthquake/training/fema-e-74), [section site](https://femae74.atcouncil.org/) |
| Future real-home clips | Private acceptance tests, subject to the participant's consent | No public license granted; not included in the public example or repository | Created by participating users |

Hypersim sample modifications: 100 tonemapped preview images assembled into a 6 fps H.264 clip, resized/re-encoded for processing, sampled evidence images marked with object boxes. Derived imagery and distributed dataset annotations remain under CC BY-SA 3.0. Indicate synthetic status and these modifications alongside any published clip. The application MIT license does not replace that asset license.

Regression controls additionally re-encode or centrally crop the original clip. They depict no physical change and retain the asset license. Model findings are not ground truth; AI observations and pending human review are identified separately. See [submission rights record](docs/submission/RIGHTS.md) before ownership or organizer-reuse declarations.

Attribution: Mike Roberts, Jason Ramapuram, Anurag Ranjan, Atulit Kumar, Miguel Angel Bautista, Nathan Paczan, Russ Webb, and Joshua M. Susskind. *Hypersim: A Photorealistic Synthetic Dataset for Holistic Indoor Scene Understanding*, ICCV 2021. [Paper](https://arxiv.org/abs/2011.02523).

Download tools fetch licensed data at runtime. No private source media is committed. FEMA section URLs/pages remain attached to recommendations. A source link documents what the model read, not an endorsement by FEMA or an engineer.

Common Voice, municipal seismic data and other proposed datasets are not currently integrated and are not listed as implemented capabilities.
