# Layout Preservation Notes

Use these notes when implementing the per-paper Chinese page builder.

## Preferred technical pattern

1. Open the source PDF with PyMuPDF (`fitz`).
2. Before translating, run `extract-literals` to build a no-translate candidate list from code/special fonts. Show the list to the user with categories and Chinese meanings before full translation. For each source page, collect text spans with:
   - `bbox`, `origin`, text, font, size, flags, color;
   - line/block grouping and reading order;
   - source page drawings/images/vector objects.
3. Reuse the original page's non-text objects wherever possible. Avoid rasterizing a whole page unless there is no other option.
4. Redraw translated Chinese text in the original text regions. For double-column papers, preserve column boundaries and original block ordering.
5. Use a CJK font such as Source Han Serif CN by default, and report the chosen font to the user.
6. Preserve original style by mapping source styled spans to translated spans:
   - bold/medium flags or font names -> real CJK bold/semi-bold font selection; never use overlapped copies, stroke text, or offset shadows to fake weight;
   - italic flags/font names -> italic for Latin terms or mild emphasis for CJK;
   - non-black citation/link colors -> character-level recoloring of matching citations/cross-references/identifiers;
   - table/figure colors -> keep the original objects.

## Required style map and style gate

Before generating final PDFs, create `.work/style-map.tsv` with these columns:

`page`, `source_text`, `target_text`, `bbox_or_anchor`, `style_kind`, `font_size`, `color`, `preservation_method`, `validated`.

Include at least:

- paper title, authors/affiliation style, abstract heading, section headings, subsection headings;
- table captions, figure captions, table headers, row/column group labels;
- bold lead phrases such as contribution labels, method labels, threat labels, and `Finding#` / `发现#`;
- theorem/definition/algorithm/listing labels and other structured-paper labels;
- italic lead headings and special title-case phrases;
- colored citations, cross references, URLs, repository names, and links;
- monospace/code-font identifiers that must remain code-like;
- full code/listing/verbatim regions that must remain visually and textually unchanged.

Treat this TSV as a required implementation contract. Do not finalize while any important item is missing, unstyled, erased, visually blobbed, or in the wrong column/region.

## Headings, captions, and bold labels

- Draw headings and bold labels as independent styled runs, not as the first words inside a plain body paragraph.
- Keep original title hierarchy: title > section > subsection > paragraph lead. Use size plus real font weight (Bold/SemiBold/Medium faces) to make these levels visibly distinct.
- Treat missing heading/bold hierarchy as a hard validation failure. If the title, abstract heading, section/subsection heading, table/figure caption, algorithm/listing label, paragraph lead, or `Finding#`/`发现#` label appears as normal body text, patch it before finalizing.
- Use a real bold/semi-bold CJK font. Do not simulate bold with tiny offsets, repeated drawing, stroke/outline rendering, or duplicate overlays. If only a regular CJK font is available, report the limitation and use the closest real weight; do not fake weight by overlap.
- When replacing an existing heading/label, first remove the old label region, then draw the replacement once. Old text plus new bold text in the same pixels is a failed output.
- For inline bold leads such as `研究空白。`, `本文工作。`, `发现#1。`, or `数据层：`, mask only the lead phrase and redraw it, or draw it in a separate region before the rest of the line. Do not bold the whole paragraph unless the source did.
- Never mask first and hope insertion succeeds. First measure or test-fit the styled text. Then mask the exact phrase region and redraw. If fitting fails, undo/regenerate the page rather than leaving a blank label.

## Code, listing, and verbatim regions

- Detect code/listing/verbatim blocks during inspection and record them in `.work/style-map.tsv` as `code-block`, `listing`, `algorithm-code`, `yaml-json`, `shell`, or `schema`.
- Preserve these regions exactly: original text, indentation, line breaks, punctuation, alignment, monospace/code font, font size, and block geometry.
- Do not translate code comments, string literals, schema keys, YAML/JSON fields, shell commands, stack traces, or algorithm pseudocode unless the user explicitly requests it for a separate explanatory artifact. The paper PDF should preserve the source code block.
- Do not let pdf2zh or any text-replacement engine rewrap code. If the intermediate output changes a code block, copy the original code region back from the source PDF during postprocessing or mask the mutated region and redraw the original code with matching monospace geometry.
- Translate listing captions and surrounding prose separately from the code block. The caption may be Chinese, but the code body must stay unchanged.
- Validate code-heavy pages visually. Reject the output if code becomes proportional text, gets centered, loses indentation, line breaks change, or prose overlaps the code box.

## Table/figure anchoring and density

- Preserve the source anchors for tables and figures. A table originally in the upper-left column should stay in that region; a right-column table should not be centered full-page unless the source did so.
- When replacing table text, rebuild the grid/cells at the original coordinates or preserve the original non-text grid and only replace cell text. Avoid leaving the English table under the Chinese caption.
- Avoid abnormal whitespace: after redrawing a table or figure, surrounding prose should start near the original vertical band. If the source page is dense, the Chinese page should also be visually dense.
- Captions must remain near their original object. Do not allow captions to overlap page headers, footers, other captions, or table bodies.

## Avoid known failure modes

- Do not create a fresh prose-only PDF with generic fonts; it will lose the paper layout.
- Do not reformat code/listing/verbatim blocks. Code preservation is part of layout preservation.
- Do not colorize an entire Chinese span just because a tiny English citation was colored. Chinese extraction often groups a whole line into one span.
- Do not over-bold whole paragraphs. If exact coordinate matching fails, semantically bold only labels, contribution leads, subsection names, table headers, or corresponding emphasized phrases.
- Do not lose visible heading hierarchy by putting `3 方法`, `3.1 研究概览`, table captions, or `发现#` labels into normal-weight prose.
- Do not fix missing bold by repeatedly overdrawing text, offsetting copies, stroking text, or leaving overlapped old/new labels. Use a real bold/semi-bold font and a single draw per label.
- Do not erase a heading/caption/label before confirming its replacement will render in the target box.
- Do not accept a PDF just because text extraction and page-count validation pass; visual style validation is mandatory.
- Do not stretch line spacing to absorb long translations. Prefer concise Chinese, then slight font reduction.
- Do not translate text inside images; record important image terms in the terminology table.
- Do not translate prose-inline identifiers rendered in monospace/special fonts after the user confirms them as identifiers. Preserve both the string and a code-like visual style in Chinese output. If a matching string is used as ordinary prose elsewhere, handle it by context.

## Character-level color restoration

When the source uses red citations or blue repository/action identifiers, redraw only the matched character range:

- Red candidates: `[12]`, `[3, 4]`, `Fig. 2`, `Table I`, `§ IV-A`, Chinese equivalents `图 2`, `表 I`.
- Blue candidates: concrete repository/action names such as `openai/codex-action`, filenames such as `action.yml`, token names such as `GITHUB_TOKEN`.
- Mask the exact character boxes with white before redrawing colored glyphs; otherwise colored text may sit on top of black text and appear unchanged.
- Keep this conservative. It is better to miss a minor color than to introduce false colors in prose.

## Validation focus pages

Always render and inspect:

- first page/title/abstract;
- a dense body page;
- a figure page;
- a table page;
- a code/listing/verbatim-heavy page when the paper contains one;
- a page with colored citations/cross references;
- a page with bold contribution labels or subsection labels;
- final terminology page.

For pages where bold labels were patched, also run the overlap/stroke validation in `font-bold-rendering.md`: duplicate/near-overlapping same-text bold span count must be zero, and patched content must not use text-rendering-mode stroke/outline markers.
