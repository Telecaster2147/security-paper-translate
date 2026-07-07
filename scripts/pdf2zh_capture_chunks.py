#!/usr/bin/env python3
"""Capture pdf2zh translation chunks without using machine translation.

The script monkeypatches pdf2zh's BingTranslator.do_translate so pdf2zh can run
its layout/text-segmentation pipeline while every "translation" call is logged
locally and answered with a harmless placeholder. It must be run only for chunk
capture, never as a final translation output generator.
"""
import argparse
import json
import sys
from pathlib import Path


def load_pdf2zh():
    try:
        import pdf2zh.translator as translator
        from pdf2zh.pdf2zh import main as pdf2zh_main
    except Exception as e:
        raise SystemExit(f"ERROR: pdf2zh is required for capture: {e}")
    return translator, pdf2zh_main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_pdf")
    ap.add_argument("--output-dir", required=True, help="temporary output directory for pdf2zh artifacts and chunks.json")
    ap.add_argument("--source-lang", default="en")
    ap.add_argument("--target-lang", default="zh")
    ap.add_argument("--threads", default="1")
    ap.add_argument("--skip-subset-fonts", action="store_true")
    ap.add_argument("--extra-pdf2zh-arg", action="append", default=[], help="repeatable raw extra argument passed to pdf2zh")
    args = ap.parse_args()

    source = Path(args.source_pdf).resolve()
    outdir = Path(args.output_dir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    chunks_path = outdir / "chunks.json"
    calls = []

    translator, pdf2zh_main = load_pdf2zh()
    if not hasattr(translator, "BingTranslator"):
        raise SystemExit("ERROR: pdf2zh.translator.BingTranslator not found; inspect pdf2zh version before proceeding")

    def fake_translate(self, text):
        idx = len(calls) + 1
        calls.append({"index": idx, "source": text, "target": "", "note": "captured; fill target with Codex-written Chinese"})
        return f"[[CAPTURE_{idx}]]"

    translator.BingTranslator.do_translate = fake_translate
    cmd = [str(source), "-o", str(outdir), "-li", args.source_lang, "-lo", args.target_lang,
           "-s", "bing", "-t", str(args.threads), "--ignore-cache"]
    if args.skip_subset_fonts:
        cmd.append("--skip-subset-fonts")
    cmd.extend(args.extra_pdf2zh_arg)

    try:
        pdf2zh_main(cmd)
    finally:
        chunks_path.write_text(json.dumps({"source_pdf": str(source), "chunks": calls}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"chunks": len(calls), "chunks_json": str(chunks_path), "output_dir": str(outdir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
