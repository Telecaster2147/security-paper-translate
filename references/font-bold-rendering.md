# Font-Level Bold Rendering for Chinese PDFs

Use this reference whenever patching title hierarchy, section headings, captions, table headers, listing labels, `Finding#`/`发现#` labels, or bold lead phrases in a translated PDF.

## Hard rule

Chinese bold must be rendered by selecting a real bold/semi-bold CJK font and drawing the text once.

Forbidden:

- stroke/outline text rendering (`render_mode=1` or `render_mode=2`);
- drawing the same text multiple times at tiny offsets;
- shadow/offset “fake bold”;
- keeping old normal text underneath a newly drawn bold label;
- duplicate/overlap overprint that creates ghosting or heavy blobs.

If true CJK bold is unavailable, use the closest real font weight available and record the limitation. Do not fake weight by overlap.

## Recommended font selection

Prefer, in order:

1. a font matching the body family with a real bold/semi-bold face, e.g. Source Han Serif/Sans CN Bold or SemiBold;
2. Noto Serif/Sans CJK Bold or SemiBold, e.g. `NotoSerifCJK-SemiBold.ttc`;
3. another locally available CJK font whose actual face name indicates Bold/SemiBold/Medium.

Use `pdffonts <pdf>` after generation to verify that the real bold font is embedded, for example `Noto Serif CJK JP SemiBold`.

## Clean replacement pattern

When reinforcing a label already present in the PDF:

1. Locate the exact label span/region.
2. Test that the replacement text fits and the font supports all glyphs.
3. Redact or white-fill the old label region with a small margin.
4. Register the real bold font.
5. Draw the replacement **exactly once** with default fill rendering.

PyMuPDF pattern:

```python
page.add_redact_annot(rect, fill=(1, 1, 1))
page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
page.insert_font(fontname="CJKBold", fontfile="/path/to/NotoSerifCJK-SemiBold.ttc")
page.insert_text((x, y), text, fontname="CJKBold", fontsize=fs, color=(0, 0, 0), overlay=True)
```

Do not pass a stroke render mode. Do not draw a second copy.

## Removing old overlap-bold artifacts

If a previous output already used overlapping fake bold:

1. Extract spans with `page.get_text("dict")`.
2. Cluster spans on the same page with the same text, similar size, and near-identical coordinates.
3. For clusters with more than one matching span, redact the union rectangle.
4. Redraw one clean run using the real bold CJK font.

Validation should then report:

- zero duplicate/near-overlapping same-text bold spans;
- zero stroke text-rendering markers on patched pages;
- real bold font embedded by `pdffonts`;
- rendered crops show no ghosting.

## Minimal overlap/stroke validation snippet

```python
import fitz

doc = fitz.open("paper-zh.pdf")
spans = []
for pi, page in enumerate(doc):
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            for s in line.get("spans", []):
                if "Bold" in s.get("font", "") or "SemiBold" in s.get("font", ""):
                    if s.get("text", "").strip():
                        spans.append((pi + 1, s["text"], fitz.Rect(s["bbox"]), s.get("size", 0)))

overlaps = []
for i, a in enumerate(spans):
    for b in spans[i + 1:]:
        if a[0] == b[0] and a[1] == b[1] and abs(a[3] - b[3]) < 0.25:
            inter = a[2] & b[2]
            if not inter.is_empty and inter.get_area() > min(a[2].get_area(), b[2].get_area()) * 0.15:
                overlaps.append((a[0], a[1]))

stroke_pages = []
for i, page in enumerate(doc):
    xrefs = page.get_contents() or []
    if isinstance(xrefs, int):
        xrefs = [xrefs]
    data = b"".join(doc.xref_stream(x) or b"" for x in xrefs)
    if b" Tr" in data:
        stroke_pages.append(i + 1)

assert not overlaps, overlaps
assert not stroke_pages, stroke_pages
```
