#!/usr/bin/env python3
"""Check local dependencies for layout-preserved paper translation.

This script does not translate and does not contact the network. It reports the
local PDF/CJK/pdf2zh environment so Codex can decide whether to use the
pdf2zh/PDFMathTranslate layout-preservation path or fall back to manual page
reconstruction.
"""
import argparse
import glob
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

FONT_PATTERNS = [
    "/home/olm/.cache/babeldoc/fonts/SourceHanSerifCN-Regular.ttf",
    "/home/olm/summerintern/.cache/babeldoc/fonts/SourceHanSerifCN-Regular.ttf",
    "/usr/share/fonts/**/*SourceHan*CN*.ttf",
    "/usr/share/fonts/**/*Noto*Serif*CJK*.ttc",
    "/usr/share/fonts/**/*Noto*Sans*CJK*.ttc",
]

EXT_PATTERNS = [
    "~/.vscode/extensions/*pdf*translate*",
    "~/.vscode-server/extensions/*pdf*translate*",
    "~/.cursor/extensions/*pdf*translate*",
    "~/.cursor-server/extensions/*pdf*translate*",
]


def command_version(cmd, version_args=("--version",)):
    path = shutil.which(cmd)
    if not path:
        return {"ok": False, "path": None, "version": None}
    try:
        out = subprocess.run([path, *version_args], text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, timeout=8, check=False).stdout.strip()
    except Exception as e:
        out = f"ERROR: {e}"
    return {"ok": True, "path": path, "version": out.splitlines()[0] if out else ""}


def module_info(name):
    spec = importlib.util.find_spec(name)
    if not spec:
        return {"ok": False, "path": None, "version": None}
    version = None
    try:
        mod = __import__(name)
        version = getattr(mod, "__version__", None)
    except Exception as e:
        version = f"import-error: {e}"
    return {"ok": True, "path": spec.origin, "version": version}


def find_fonts():
    hits = []
    for pat in FONT_PATTERNS:
        hits.extend(glob.glob(os.path.expanduser(pat), recursive=True))
    seen = []
    for h in hits:
        p = str(Path(h))
        if p not in seen and Path(p).exists():
            seen.append(p)
    return seen


def find_pdf_translate_extensions():
    hits = []
    for pat in EXT_PATTERNS:
        hits.extend(glob.glob(os.path.expanduser(pat)))
    out = []
    for h in sorted(set(hits)):
        p = Path(h)
        pkg = p / "package.json"
        out.append({"path": str(p), "has_package_json": pkg.exists()})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="print machine-readable JSON only")
    args = ap.parse_args()
    report = {
        "commands": {
            "pdf2zh": command_version("pdf2zh"),
            "pdftoppm": command_version("pdftoppm", ("-v",)),
            "qpdf": command_version("qpdf", ("--version",)),
        },
        "python_modules": {
            "fitz": module_info("fitz"),
            "pdf2zh": module_info("pdf2zh"),
            "pdfminer": module_info("pdfminer"),
            "pypdf": module_info("pypdf"),
        },
        "cjk_fonts": find_fonts(),
        "pdf_translate_extensions": find_pdf_translate_extensions(),
    }
    required_ok = report["python_modules"]["fitz"]["ok"] and bool(report["cjk_fonts"])
    pdf2zh_ok = report["commands"]["pdf2zh"]["ok"] and report["python_modules"]["pdf2zh"]["ok"]
    report["summary"] = {
        "basic_pdf_postprocess_ready": required_ok,
        "pdf2zh_layout_ready": pdf2zh_ok,
        "recommended_cjk_font": report["cjk_fonts"][0] if report["cjk_fonts"] else None,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not required_ok:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
