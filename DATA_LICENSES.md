# Data licenses

RiskLens uses only openly licensed data that allows commercial use and modification. Raw data is **never** committed;
download scripts fetch it at run time.

| Dataset | Used for | License | Source |
|---|---|---|---|
| Hypersim (Apple) | Evaluation clips + 3D ground truth (hazard objects, "above bed", "near door", tall furniture) | CC BY-SA 3.0 | https://github.com/apple/ml-hypersim |
| FEMA E-74, *Reducing the Risks of Nonstructural Earthquake Damage* (Dec 2012), 14 home-relevant sections | Grounding for fix recommendations; condensed causes/mitigation text committed as `backend/app/knowledge/fema_e74.json` (rebuild: `python -m app.knowledge.build_fema`) | US federal work (public domain) | https://www.fema.gov/ · section PDFs via https://femae74.atcouncil.org/ |
| Mozilla Common Voice Turkish *(planned)* | Turkish speech-recognition check | CC0 (do not re-host; do not identify speakers) | https://commonvoice.mozilla.org/ |
| İBB Açık Veri earthquake scenario data *(planned)* | Neighborhood seismic context | İBB Açık Veri Lisansı v1.0 | https://data.ibb.gov.tr/ |
| Demo footage | Demo video and examples | Filmed by the author in their own home | — |

Derived datasets we publish from Hypersim (e.g. eval labels) are shared under CC BY-SA 3.0.
