#!/usr/bin/env python3
"""Check that patched bold labels are real-font, non-overlapping text.

This does not judge whether every heading is bold; it verifies the failure mode
that must not occur: same-text bold spans drawn on top of each other, and stroke
/ outline text-rendering markers in page content streams.
"""
import argparse
import json
import sys

import fitz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--content-pages", type=int, help="limit checks to the first N pages")
    ap.add_argument("--font-keyword", action="append", default=["Bold", "SemiBold", "Medium"],
                    help="font-name keyword treated as bold; repeatable")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on-issue", action="store_true")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    pages = min(args.content_pages or len(doc), len(doc))
    spans = []
    for pi in range(pages):
        page = doc[pi]
        for b in page.get_text("dict").get("blocks", []):
            if b.get("type") != 0:
                continue
            for line in b.get("lines", []):
                for s in line.get("spans", []):
                    text = s.get("text", "")
                    font = s.get("font", "")
                    if text.strip() and any(k in font for k in args.font_keyword):
                        spans.append((pi + 1, text, fitz.Rect(s["bbox"]), s.get("size", 0), font))

    overlaps = []
    for i, a in enumerate(spans):
        for b in spans[i + 1:]:
            if a[0] == b[0] and a[1] == b[1] and abs(a[3] - b[3]) < 0.25:
                inter = a[2] & b[2]
                if not inter.is_empty and inter.get_area() > min(a[2].get_area(), b[2].get_area()) * 0.15:
                    overlaps.append({
                        "page": a[0],
                        "text": a[1],
                        "font_a": a[4],
                        "font_b": b[4],
                        "bbox_a": [round(x, 2) for x in a[2]],
                        "bbox_b": [round(x, 2) for x in b[2]],
                    })

    stroke_pages = []
    for i in range(pages):
        xrefs = doc[i].get_contents() or []
        if isinstance(xrefs, int):
            xrefs = [xrefs]
        data = b"".join(doc.xref_stream(x) or b"" for x in xrefs)
        if b" Tr" in data:
            stroke_pages.append(i + 1)

    result = {
        "pdf": args.pdf,
        "checked_pages": pages,
        "bold_like_spans": len(spans),
        "duplicate_or_near_overlap_count": len(overlaps),
        "duplicate_or_near_overlaps": overlaps[:50],
        "render_mode_stroke_marker_pages": stroke_pages,
        "issues": [],
    }
    if overlaps:
        result["issues"].append("duplicate_or_near_overlapping_bold_spans")
    if stroke_pages:
        result["issues"].append("text_rendering_mode_marker_present")
    result["status"] = "pass" if not result["issues"] else "fail"

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"checked_pages: {pages}")
        print(f"bold_like_spans: {len(spans)}")
        print(f"duplicate_or_near_overlap_count: {len(overlaps)}")
        print(f"render_mode_stroke_marker_pages: {stroke_pages}")
    if args.fail_on_issue and result["issues"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
