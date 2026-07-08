# pdf2zh / PDFMathTranslate Layout Integration

Use this reference when a paper needs strict layout preservation and local `pdf2zh` is available, or when a local VSCode “PDF Translate” extension has already produced a visually well-aligned mono/dual PDF. The extension output is a layout reference only; translations must still be written by Codex/human and supplied locally.

## Goal

Reuse `pdf2zh`/PDFMathTranslate for geometry, region detection, figures, formulas, and PDF rewriting while preventing any machine-translation call. Codex provides the Chinese text; the engine only places it.

## 1. Check the environment

Run from the skill directory or adjust paths:

```bash
python scripts/check_environment.py --json
```

Required for the pdf2zh path:

- `pdf2zh` command and Python module are available;
- `fitz` / PyMuPDF is available;
- a CJK font such as Source Han Serif or Noto CJK is available;
- `pdftoppm` is available for render-based validation.

If the pdf2zh path is not ready, fall back to the page-object reconstruction strategy in `layout-preservation-notes.md`.

## 2. Inspect the local VSCode PDF Translate extension when relevant

Look for extension folders such as:

```bash
find ~/.vscode ~/.vscode-server ~/.cursor ~/.cursor-server \
  -maxdepth 3 -type d -iname '*pdf*translate*' 2>/dev/null
```

Inspect `package.json` and compiled/source files to confirm whether it invokes `pdf2zh`, which backend it uses, and which options it passes. Treat its generated PDF as a visual reference for spacing, table anchors, and page density only. Do not use its translated text as the final translation.

## 3. Capture source chunks without MT

Create the normal project folder first:

```bash
python scripts/paper_pdf_tools.py init-workdir /path/to/paper.pdf
```

Then run the capture pass:

```bash
python scripts/pdf2zh_capture_chunks.py /path/to/paper.pdf \
  --output-dir /path/to/translated-pdfs/<stem>/.work/pdf2zh-codex/capture \
  --threads 1
```

This monkeypatches `BingTranslator.do_translate`, logs every text chunk to `chunks.json`, and returns placeholders. No external translation service is contacted.

## 4. Fill translations locally

Create a translation mapping from `chunks.json`:

```json
{
  "chunks": [
    {"index": 1, "source": "Abstract", "target": "摘要"},
    {"index": 2, "source": "...", "target": "...Codex 写出的中文..."}
  ]
}
```

Rules:

- Write translations yourself with academic Chinese polish.
- Preserve no-translate identifiers according to the confirmed term policy.
- Keep references/citations where they belong if they are visible in the source chunk.
- Keep figure-internal English unchanged; translate captions/table text outside the image.
- Freeze code/listing/verbatim chunks. If a captured chunk is a code block, YAML/JSON/shell snippet, stack trace, schema listing, algorithm-as-code, or monospace table, set its target equal to the exact source text and mark it in the run notes. Do not translate, reindent, rewrap, or normalize punctuation in that chunk.

## 5. Generate the pdf2zh-layout Chinese intermediate

```bash
python scripts/pdf2zh_codex_driver.py /path/to/paper.pdf \
  --translations /path/to/translations.json \
  --output-dir /path/to/translated-pdfs/<stem>/.work/pdf2zh-codex/codex-out \
  --threads 1
```

The resulting mono PDF is an intermediate. It usually preserves page geometry and figures well, but it still needs visual QA and postprocessing.
Pay special attention to code/listing pages: if pdf2zh has reflowed or restyled code, the intermediate is not final-usable until those source regions are restored.

## 6. Postprocess the intermediate

Start with the generic template:

```bash
python scripts/pdf_postprocess_template.py \
  --source /path/to/paper.pdf \
  --mono /path/to/translated-pdfs/<stem>/.work/pdf2zh-codex/codex-out/<stem>-mono.pdf \
  --output-zh /path/to/translated-pdfs/<stem>/<stem>-zh.pdf \
  --output-interleaved /path/to/translated-pdfs/<stem>/<stem>-zh-en-interleaved.pdf \
  --terms /path/to/translated-pdfs/<stem>/<stem>-terms.tsv \
  --remove-line-numbers \
  --header-policy acm \
  --running-title "Paper running title" \
  --labels-file /path/to/translated-pdfs/<stem>/.work/style-labels.txt \
  --color-citations
```

For difficult pages, copy `pdf_postprocess_template.py` into `.work/scripts/postprocess_<stem>.py` and add per-paper patch functions. Common patches:

- enlarge or shift a table text region;
- redraw a table whose cell text was damaged by pdf2zh;
- restore a code/listing/verbatim region from the source PDF when the intermediate changed indentation, line breaks, alignment, or monospace styling;
- mask review line numbers or dotted artifacts;
- redraw running headers/footers;
- reinforce title, abstract heading, section/subsection headings, table/figure captions, algorithm/listing labels, table headers, paragraph lead labels, and `发现#` labels with real font-level CJK bold/semi-bold. Do not use stroke text, offset fake bold, repeated overprint, or old/new label overlap;
- restore citation/link colors conservatively.

Keep the original figures, plots, and diagram internals unless the user explicitly asks to translate image text.

## 7. Validate and finalize

Render visually important pages before finalizing:

```bash
python scripts/paper_pdf_tools.py validate \
  /path/to/paper.pdf \
  /path/to/translated-pdfs/<stem>/<stem>-zh.pdf \
  /path/to/translated-pdfs/<stem>/<stem>-zh-en-interleaved.pdf \
  --sample-pages 1,2,3,5,6,9,10,13 \
  --fail-on-issue
```

Inspect rendered PNGs. Do not finalize if headings are plain body text, bold labels are black blobs or ghosted from overlapping copies, code/listing regions are reformatted, tables drift, figures disappear, or there is abnormal whitespace. Run the duplicate/overlap bold check from `font-bold-rendering.md` when bold labels were patched.

Then finalize:

```bash
python scripts/paper_pdf_tools.py finalize \
  /path/to/paper.pdf \
  /path/to/translated-pdfs/<stem>/<stem>-zh.pdf \
  /path/to/translated-pdfs/<stem>/<stem>-zh-en-interleaved.pdf \
  /path/to/translated-pdfs/<stem>/<stem>-terms.tsv
```

The final folder should contain only final PDFs, final terminology TSV, and generation statistics.

## Failure modes to report instead of hiding

- `pdf2zh` chunk order changes between capture and generation and cannot be reconciled.
- No suitable CJK font is available.
- The source PDF has broken extraction or scanned pages requiring unstable OCR.
- A table/figure cannot be repaired without changing layout.
- A heading/caption/finding label cannot be styled visibly without overlap.
- A code/listing/verbatim block cannot be preserved without changing the page layout.
