# Security Paper Translate Skill

A Codex skill for translating cybersecurity and related academic paper PDFs into professional Chinese while preserving the original PDF layout. It is designed for papers where formatting matters: two-column layouts, figures, tables, captions, code listings, bold headings, colored citations, and terminology tables.

## What it produces

For an input paper `paper.pdf`, the skill writes final outputs under `translated-pdfs/paper/`:

- `paper-zh.pdf` — Chinese-only content pages plus terminology pages.
- `paper-zh-en-interleaved.pdf` — Chinese page first, then matching English page, repeated for each source page, plus terminology pages.
- `paper-terms.tsv` — source-backed terminology and no-translate policy table.
- `paper-generation-stats.json` and `paper-generation-stats.md` — validation and generation summary.

## Core guarantees

- Codex performs the translation itself; do not call external MT, other LLM APIs, or local LLMs.
- Preserve page size, columns, visual density, figures, tables, captions, bold/italic/color styling, and title hierarchy.
- Preserve code/listing/verbatim regions exactly: no translation, rewrapping, reindentation, line-break changes, or monospace-style loss.
- Use local `pdf2zh` / PDFMathTranslate only as a layout engine when available, with its translator layer replaced by Codex-written local translations.
- Append a sourced terminology table and validate rendered sample pages before claiming completion.

## Repository layout

```text
security-paper-translate/
├── SKILL.md                         # Main skill instructions
├── agents/openai.yaml               # Agent UI metadata
├── references/
│   ├── layout-preservation-notes.md # Layout, style, code-block, and validation rules
│   ├── pdf2zh-layout-integration.md # Local pdf2zh monkeypatch workflow
│   ├── terminology-schema.md        # Terms TSV schema
│   └── translation-standards.md     # Academic/security translation standards
├── scripts/
│   ├── check_environment.py         # Dependency and local extension checks
│   ├── paper_pdf_tools.py           # Inspect, terms, interleave, validate, finalize helpers
│   ├── pdf2zh_capture_chunks.py     # Capture pdf2zh chunks without MT
│   ├── pdf2zh_codex_driver.py       # Run pdf2zh with local Codex translations
│   └── pdf_postprocess_template.py  # Generic postprocess scaffold
└── .github/workflows/validate.yml   # Basic repository validation
```

## Install for Codex

Clone or copy this folder into your Codex skills directory:

```bash
git clone <repo-url> ~/.codex/skills/security-paper-translate
```

Then ask Codex to use `$security-paper-translate` on an English academic paper PDF.

## Runtime dependencies

The helper scripts are intentionally lightweight. Minimum useful environment:

```bash
python -m pip install -r requirements.txt
```

Recommended system tools:

- `pdftoppm` from poppler, for render-based validation.
- `pdf2zh`, optional but recommended for strict layout preservation.
- A CJK font such as Source Han Serif CN or Noto CJK.

Check the local environment with:

```bash
python scripts/check_environment.py --json
```

## Typical agent prompt

```text
Use $security-paper-translate to translate /path/to/paper.pdf. Follow the preflight confirmation, terminology policy, layout-preservation, code-block preservation, validation, and finalize workflow in SKILL.md. Generate Chinese-only and Chinese-first interleaved PDFs under translated-pdfs/<stem>/.
```

## Development validation

Run these checks before committing:

```bash
python -m py_compile scripts/*.py
python scripts/check_environment.py --json >/tmp/security-paper-translate-env.json
python /path/to/skill-creator/scripts/quick_validate.py .
```

## License

No license has been selected in this repository. Add a `LICENSE` file before public distribution if you want others to reuse it under explicit terms.
