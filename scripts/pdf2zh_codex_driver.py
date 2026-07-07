#!/usr/bin/env python3
"""Run pdf2zh layout preservation with a Codex-supplied local translation map.

This script monkeypatches pdf2zh's BingTranslator.do_translate. The pdf2zh engine
is used only for layout detection/reconstruction; translation strings must be
written by Codex/human and supplied in --translations. No Bing/Google/DeepL/LLM
translation service is contacted by this script.

Accepted translation JSON formats:
  {"chunks": [{"index": 1, "source": "...", "target": "中文..."}, ...]}
  [{"index": 1, "source": "...", "target": "中文..."}, ...]
  {"1": "中文...", "2": "中文..."}
"""
import argparse
import json
from pathlib import Path


def load_pdf2zh():
    try:
        import pdf2zh.translator as translator
        from pdf2zh.pdf2zh import main as pdf2zh_main
    except Exception as e:
        raise SystemExit(f"ERROR: pdf2zh is required: {e}")
    return translator, pdf2zh_main


def load_translations(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "chunks" in raw:
        items = raw["chunks"]
    elif isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        return {int(k): str(v) for k, v in raw.items() if str(k).isdigit()}, {}
    else:
        raise SystemExit("ERROR: unsupported translation JSON format")
    by_index = {}
    by_source = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        idx = it.get("index")
        target = it.get("target") or it.get("translation") or it.get("zh")
        source = it.get("source")
        if target:
            if idx is not None:
                by_index[int(idx)] = str(target)
            if source:
                by_source[str(source)] = str(target)
    return by_index, by_source


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_pdf")
    ap.add_argument("--translations", required=True, help="JSON mapping created from captured chunks with Codex-written targets")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--source-lang", default="en")
    ap.add_argument("--target-lang", default="zh")
    ap.add_argument("--threads", default="1")
    ap.add_argument("--allow-missing", action="store_true", help="fallback to source text when a chunk has no translation")
    ap.add_argument("--skip-subset-fonts", action="store_true")
    ap.add_argument("--extra-pdf2zh-arg", action="append", default=[])
    args = ap.parse_args()

    source = Path(args.source_pdf).resolve()
    outdir = Path(args.output_dir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    by_index, by_source = load_translations(Path(args.translations))
    calls = []

    translator, pdf2zh_main = load_pdf2zh()
    if not hasattr(translator, "BingTranslator"):
        raise SystemExit("ERROR: pdf2zh.translator.BingTranslator not found; inspect pdf2zh version before proceeding")

    def local_translate(self, text):
        idx = len(calls) + 1
        target = by_index.get(idx) or by_source.get(text)
        if target is None:
            if not args.allow_missing:
                raise RuntimeError(f"missing translation for chunk {idx}: {text[:120]!r}")
            target = text
        calls.append({"index": idx, "source": text, "target": target})
        return target

    translator.BingTranslator.do_translate = local_translate
    cmd = [str(source), "-o", str(outdir), "-li", args.source_lang, "-lo", args.target_lang,
           "-s", "bing", "-t", str(args.threads), "--ignore-cache"]
    if args.skip_subset_fonts:
        cmd.append("--skip-subset-fonts")
    cmd.extend(args.extra_pdf2zh_arg)
    pdf2zh_main(cmd)
    calls_path = outdir / "codex-translation-calls.json"
    calls_path.write_text(json.dumps({"source_pdf": str(source), "calls": calls}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"calls": len(calls), "calls_json": str(calls_path), "output_dir": str(outdir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
