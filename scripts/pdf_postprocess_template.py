#!/usr/bin/env python3
"""Reusable postprocess scaffold for pdf2zh-produced Chinese mono PDFs.

It handles generic cleanup used by the successful workflow: margin line-number
removal, optional ACM-style running header redraw, real-font CJK bold label
reinforcement, red citation restoration, terminology-page append, and Chinese-
first interleaving. Per-paper table repairs should be added in a copied project
specific script under translated-pdfs/<stem>/.work/scripts/ rather than in this
shared template.
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import fitz
except Exception as e:
    raise SystemExit(f"ERROR: PyMuPDF/fitz required: {e}")

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
try:
    import paper_pdf_tools
except Exception as e:
    paper_pdf_tools = None
    PAPER_TOOLS_ERROR = e
else:
    PAPER_TOOLS_ERROR = None

DEFAULT_LABELS = [
    "摘要", "1 引言", "2 背景", "3 方法", "4 RQ1", "5 RQ2", "6 RQ3", "7 讨论", "8 相关工作", "9 结论",
    "研究空白。", "本文工作。", "贡献如下：", "关键发现。",
    "发现#1。", "发现#2。", "发现#3。", "发现#4。", "发现#5。", "发现#6。", "发现#7。", "发现#8。",
]


def white(page, rect):
    page.draw_rect(fitz.Rect(rect), color=None, fill=(1, 1, 1), overlay=True)


def choose_font(explicit=None):
    candidates = [explicit] if explicit else []
    candidates += [
        str(Path.home() / ".cache/babeldoc/fonts/SourceHanSerifCN-Regular.ttf"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def choose_bold_font(explicit=None):
    """Return a real bold/semi-bold CJK font when available.

    Bold reinforcement must not use offset/overprint fake bold. If no true
    bold/semi-bold CJK font is available, return None so the caller can avoid
    fake-bold behavior and record the limitation.
    """
    candidates = [explicit] if explicit else []
    candidates += [
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-SemiBold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
        str(Path.home() / ".cache/babeldoc/fonts/SourceHanSerifCN-Bold.ttf"),
        str(Path.home() / ".cache/babeldoc/fonts/SourceHanSerifCN-SemiBold.ttf"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def remove_line_numbers(page, left_width=49, right_width=49, top=78, bottom=724):
    w = page.rect.width
    white(page, (0, top, left_width, bottom))
    white(page, (w - right_width, top, w, bottom))


def draw_acm_header(page, idx, title, conference="Conference’17, July 2017, Washington, DC, USA", author="Anon."):
    white(page, (50, 55, page.rect.width - 50, 73))
    if idx == 0:
        return
    if (idx + 1) % 2 == 0:
        page.insert_text((54, 66), conference, fontsize=6.5, fontname="Times-Roman", color=(0, 0, 0), overlay=True)
        page.insert_text((page.rect.width - 76, 66), author, fontsize=6.5, fontname="Times-Roman", color=(0, 0, 0), overlay=True)
    else:
        page.insert_text((54, 66), title[:110], fontsize=6.5, fontname="Times-Roman", color=(0, 0, 0), overlay=True)
        page.insert_text((page.rect.width - 200, 66), conference, fontsize=6.5, fontname="Times-Roman", color=(0, 0, 0), overlay=True)


def load_labels(path):
    labels = list(DEFAULT_LABELS)
    if path:
        p = Path(path)
        if p.exists():
            labels.extend([ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")])
    # preserve order while deduplicating
    seen = set(); out = []
    for x in labels:
        if x not in seen:
            seen.add(x); out.append(x)
    return out


def is_heading(text):
    return text == "摘要" or bool(re.match(r"^(?:\d+|\d+\.\d+)\s", text))


def bold_overlay(page, box, text, fontfile, fs, erase=False, strong=False):
    """Draw a bold label exactly once with a real bold font.

    `strong` is retained for CLI compatibility but intentionally ignored:
    never fake stronger weight via repeated offset draws.
    """
    if erase:
        white(page, (box.x0 - .6, box.y0 - .5, box.x1 + 4.5, box.y1 + 1.4))
    baseline = box.y1 - 2.0
    kwargs = {"fontsize": fs, "color": (0, 0, 0), "overlay": True}
    if fontfile:
        kwargs.update({"fontname": "CJKBold", "fontfile": fontfile})
    else:
        kwargs.update({"fontname": "Times-Bold"})
    # Single draw only: no stroke render mode, no shadow, no offset duplicate.
    page.insert_text((box.x0, baseline), text, **kwargs)


def reinforce_labels(page, labels, fontfile):
    for text in labels:
        variants = [text, text.replace(" ", "\u00a0"), text.replace("-", "‑")]
        for needle in variants:
            rects = page.search_for(needle)
            if not rects:
                continue
            for r in rects[:4]:
                heading = is_heading(text)
                lead = text.endswith("。") or text.startswith("发现#")
                fs = max(6.8, min(12.2 if heading else 11.2, r.height * .82))
                box = fitz.Rect(r.x0, r.y0 - .8, r.x1 + 2.5, r.y1 + 1.0)
                bold_overlay(page, box, needle, fontfile, fs, erase=(heading or lead), strong=heading)
            break


def color_citations(page, fontfile):
    text = page.get_text("text")
    pats = sorted(set(re.findall(r"\[[0-9,\s]{1,24}\]", text)), key=len, reverse=True)
    for pat in pats[:100]:
        for r in page.search_for(pat):
            white(page, (r.x0 - .2, r.y0 - .2, r.x1 + .2, r.y1 + .4))
            kwargs = {"fontsize": max(4.5, r.height * .75), "color": (.75, 0, 0), "overlay": True}
            if fontfile:
                kwargs.update({"fontname": "CJK", "fontfile": fontfile})
            else:
                kwargs.update({"fontname": "Times-Roman"})
            page.insert_textbox(fitz.Rect(r.x0, r.y0 - .8, r.x1 + 5, r.y1 + 1.0), pat, **kwargs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="original English PDF")
    ap.add_argument("--mono", required=True, help="Chinese mono PDF produced by pdf2zh/Codex driver")
    ap.add_argument("--output-zh", required=True)
    ap.add_argument("--output-interleaved", required=True)
    ap.add_argument("--terms", help="terms TSV to append")
    ap.add_argument("--font", help="CJK font path")
    ap.add_argument("--bold-font", help="real CJK bold/semi-bold font path for headings/labels")
    ap.add_argument("--content-pages", type=int, help="source content page count; defaults to source page count")
    ap.add_argument("--remove-line-numbers", action="store_true")
    ap.add_argument("--header-policy", choices=["none", "acm"], default="none")
    ap.add_argument("--running-title", default="")
    ap.add_argument("--conference", default="Conference’17, July 2017, Washington, DC, USA")
    ap.add_argument("--author", default="Anon.")
    ap.add_argument("--labels-file", help="newline-separated Chinese labels/headings to reinforce")
    ap.add_argument("--color-citations", action="store_true")
    args = ap.parse_args()

    font = choose_font(args.font)
    bold_font = choose_bold_font(args.bold_font)
    if not bold_font:
        print("WARNING: no real CJK bold/semi-bold font found; skipping bold reinforcement rather than using overlap fake-bold.", file=sys.stderr)
    src = fitz.open(args.source)
    doc = fitz.open(args.mono)
    content_pages = args.content_pages or len(src)
    labels = load_labels(args.labels_file)

    for i, page in enumerate(doc[:content_pages]):
        if args.remove_line_numbers:
            remove_line_numbers(page)
        if args.header_policy == "acm":
            draw_acm_header(page, i, args.running_title or Path(args.source).stem, args.conference, args.author)
        if args.color_citations:
            color_citations(page, font)
        if bold_font:
            reinforce_labels(page, labels, bold_font)

    if args.terms:
        if paper_pdf_tools is None:
            raise SystemExit(f"ERROR importing paper_pdf_tools for terms: {PAPER_TOOLS_ERROR}")
        paper_pdf_tools.add_terms_pages(doc, Path(args.terms), font)

    out_zh = Path(args.output_zh); out_zh.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_zh, garbage=4, deflate=True)
    doc.close()

    zh = fitz.open(out_zh)
    inter = fitz.open()
    for i in range(content_pages):
        inter.insert_pdf(zh, from_page=i, to_page=i)
        inter.insert_pdf(src, from_page=i, to_page=i)
    if len(zh) > content_pages:
        inter.insert_pdf(zh, from_page=content_pages, to_page=len(zh) - 1)
    out_inter = Path(args.output_interleaved); out_inter.parent.mkdir(parents=True, exist_ok=True)
    inter.save(out_inter, garbage=4, deflate=True)
    print(json.dumps({"output_zh": str(out_zh), "output_interleaved": str(out_inter), "content_pages": content_pages, "font": font}, ensure_ascii=False))


if __name__ == "__main__":
    main()
