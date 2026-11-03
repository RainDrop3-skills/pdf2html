"""Split a lecture PDF into per-page text + PNG files for page-by-page analysis.

Usage:
    python extract_pages.py <pdf> <out_dir> [--dpi 110] [--first N] [--last M] [--no-images]

Outputs in <out_dir>:
    page-001.txt ...   pdftotext -layout output (UTF-8) for each page
    page-001.png ...   rendered page image (pdftoppm), for figures / diagrams / hidden text checks
    summary.json       per-page stats: chars, english_ratio, slide_number guess
    summary.md         same, as a compact table to read first

Requires poppler (pdfinfo, pdftotext, pdftoppm) on PATH.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def page_count(pdf):
    out = run(["pdfinfo", str(pdf)]).decode("utf-8", errors="replace")
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    if not m:
        sys.exit(f"pdfinfo could not read page count of {pdf}")
    return int(m.group(1))


def english_ratio(text):
    latin = len(re.findall(r"[A-Za-z]", text))
    hangul = len(re.findall(r"[가-힣]", text))
    total = latin + hangul
    return round(latin / total, 2) if total else 0.0


def slide_number_guess(text):
    # Slide footers usually end with a bare number on the last non-empty line.
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return None
    m = re.search(r"(\d{1,3})$", lines[-1])
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out_dir")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--last", type=int, default=0)
    ap.add_argument("--no-images", action="store_true")
    args = ap.parse_args()

    for tool in ("pdfinfo", "pdftotext", "pdftoppm"):
        if not shutil.which(tool):
            sys.exit(f"'{tool}' not found. Install poppler (e.g. winget install oschwartz10612.Poppler).")

    pdf = Path(args.pdf)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n = page_count(pdf)
    last = args.last or n

    pages = []
    for i in range(args.first, last + 1):
        txt_path = out / f"page-{i:03d}.txt"
        run(["pdftotext", "-enc", "UTF-8", "-layout", "-f", str(i), "-l", str(i), str(pdf), str(txt_path)])
        text = txt_path.read_text(encoding="utf-8", errors="replace")
        pages.append({
            "page": i,
            "chars": len(text.strip()),
            "english_ratio": english_ratio(text),
            "slide_number": slide_number_guess(text),
        })

    if not args.no_images:
        # pdftoppm names files <prefix>-<page>.png with zero padding based on page count
        run(["pdftoppm", "-png", "-r", str(args.dpi), "-f", str(args.first), "-l", str(last),
             str(pdf), str(out / "img")])
        for f in out.glob("img-*.png"):
            num = int(f.stem.split("-")[-1])
            f.replace(out / f"page-{num:03d}.png")

    summary = {"pdf": str(pdf), "total_pages": n, "pages": pages}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    rows = ["| p | chars | EN비율 | 하단번호 | 비고 |", "|---|---|---|---|---|"]
    for p in pages:
        note = []
        if p["chars"] < 40:
            note.append("텍스트 적음 → 이미지 확인")
        if p["slide_number"] and p["slide_number"] != p["page"]:
            note.append(f"#{p['slide_number']} 어긋남")
        rows.append(f"| {p['page']} | {p['chars']} | {p['english_ratio']} | {p['slide_number'] or ''} | {', '.join(note)} |")
    (out / "summary.md").write_text(
        f"# {pdf.name} ({n} pages)\n\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"{pdf.name}: {n} pages -> {out}")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
