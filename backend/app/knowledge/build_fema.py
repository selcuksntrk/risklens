"""Build `fema_e74.json`: the FEMA E-74 sections RiskLens cites, reduced to causes + mitigation guidance.

FEMA E-74 "Reducing the Risks of Nonstructural Earthquake Damage: A Practical Guide" (Dec 2012) is a US federal
publication (public domain). Section PDFs are served by the Applied Technology Council's online edition.

    uv run python -m app.knowledge.build_fema [--pdf-dir DIR]     # needs `pdftotext` (poppler)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

BASE = "https://femae74.atcouncil.org/docman/abbreviated/"
# id -> (title, path); only components found in homes
SECTIONS = {
    "6.3.2.3": ("Glazed interior partitions", "section-6-3/23-16-femae-74-chapter6-3-2-3"),
    "6.4.2.4": ("Water heaters", "section-6-4/53-46-femae-74-chapter6-4-2-4"),
    "6.4.9.3": ("Pendant light fixtures", "section-6-4/63-57-femae-74-chapter6-4-9-3"),
    "6.4.9.4": ("Heavy light fixtures", "section-6-4/64-58-femae-74-chapter6-4-9-4"),
    "6.5.1.1": ("Light duty shelving", "section-6-5/72-65-femae-74-chapter6-5-1-1"),
    "6.5.2.1": ("Bookshelves", "section-6-5/74-67-femae-74-chapter6-5-2-1"),
    "6.5.3.3": ("Desktop computers and accessories", "section-6-5/78-71-femae-74-chapter6-5-3-3"),
    "6.5.3.4": ("Televisions and video monitors, wall-mounted", "section-6-5/79-72-femae-74-chapter6-5-3-4"),
    "6.5.5.1": ("File cabinets", "section-6-5/81-74-femae-74-chapter6-5-5-1"),
    "6.5.5.3": ("Miscellaneous furniture and fixtures", "section-6-5/83-76-femae-74-chapter6-5-5-3"),
    "6.5.6.1": ("Shelf-mounted items", "section-6-5/84-77-femae-74-chapter6-5-6-1"),
    "6.5.6.2": ("Desktop, countertop items", "section-6-5/85-78-femae-74-chapter6-5-6-2"),
    "6.5.6.3": ("Fragile artwork", "section-6-5/86-79-femae-74-chapter6-5-6-3"),
    "6.5.6.4": ("Fire extinguisher and cabinet", "section-6-5/87-80-femae-74-chapter6-5-6-4"),
}
OUT = Path(__file__).with_name("fema_e74.json")
SOURCE = ("FEMA E-74, Reducing the Risks of Nonstructural Earthquake Damage: A Practical Guide (FEMA, December 2012). "
          "US federal work, public domain.")

NOISE = re.compile(r"Available at: http|Last Modified:|^FEMA E-74\s+6:|^Figure \d|^\s*\(.*courtesy.*\)\s*$|^\s*$")
PAGE = re.compile(r"Page (6-\d+)")


def section_text(pdf: Path) -> tuple[str, str]:
    raw = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True, text=True).stdout
    pages = PAGE.findall(raw)
    lines = [l.strip() for l in raw.splitlines() if not NOISE.search(l)]
    text = re.sub(r"[•]", "\n-", "\n".join(lines))   # PDF bullet glyphs -> " -" markers
    text = re.sub(r"\s+", " ", text)
    return text, (f"{pages[0]}–{pages[-1]}" if pages else "")


def between(text: str, start: str, ends: list[str]) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    i += len(start)
    j = min([k for k in (text.find(e, i) for e in ends) if k > 0] or [len(text)])
    return text[i:j].strip(" -")


def bullets(text: str) -> list[str]:
    return [b.strip() for b in text.split(" -") if len(b.strip()) > 20]


def build(pdf_dir: Path) -> dict:
    out = {"source": SOURCE, "sections": []}
    for sid, (title, _) in SECTIONS.items():
        text, pages = section_text(pdf_dir / f"{sid.replace('.', '-')}.pdf")
        summary = between(text, title, ["Provisions", "Typical Causes of Damage"])
        causes = between(text, "Typical Causes of Damage", ["DAMAGE EXAMPLES", "Seismic Mitigation Considerations"])
        mitigation = between(text, "Seismic Mitigation Considerations",
                             ["MITIGATION DETAILS", "MITIGATION EXAMPLES", "Mitigation Examples"])
        out["sections"].append({"id": sid, "title": title, "pages": pages, "summary": summary[:600],
                                "causes": bullets(causes), "mitigation": bullets(mitigation),
                                "url": BASE + SECTIONS[sid][1]})
    return out


def download(dest: Path) -> None:
    for sid, (_, path) in SECTIONS.items():
        target = dest / f"{sid.replace('.', '-')}.pdf"
        if not target.exists():
            urllib.request.urlretrieve(BASE + path, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", type=Path, help="reuse already-downloaded section PDFs")
    args = parser.parse_args()
    pdf_dir = args.pdf_dir or Path(tempfile.mkdtemp(prefix="fema-e74-"))
    download(pdf_dir)
    data = build(pdf_dir)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    for s in data["sections"]:
        print(f"{s['id']:<8} {s['title']:<48} causes={len(s['causes'])} mitigation={len(s['mitigation'])} pages={s['pages']}")


if __name__ == "__main__":
    main()
