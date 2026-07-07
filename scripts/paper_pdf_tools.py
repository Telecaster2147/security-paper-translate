#!/usr/bin/env python3
"""Deterministic PDF helpers for layout-preserved academic-paper translation.

This script does not translate. It inspects PDFs, appends terminology pages,
interleaves Chinese/English PDFs, and validates final outputs.
"""
import argparse, csv, json, re, sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except Exception as e:
    print(f"ERROR: PyMuPDF/fitz is required: {e}", file=sys.stderr)
    sys.exit(2)


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def project_dir_for(source_pdf) -> Path:
    src = Path(source_pdf)
    return src.parent / "translated-pdfs" / src.stem


def init_workdir(args):
    root = Path(args.output_dir) if args.output_dir else project_dir_for(args.pdf)
    dirs = [
        root,
        root / ".work" / "inspect",
        root / ".work" / "validation",
        root / ".work" / "terms",
        root / ".work" / "pages",
        root / ".work" / "assets" / "fonts",
        root / ".work" / "scripts",
        root / ".work" / "tests",
    ]
    for d in dirs:
        ensure_dir(d)
    print(json.dumps({"project_dir": str(root), "final_files": [str(root / f"{Path(args.pdf).stem}-zh.pdf"), str(root / f"{Path(args.pdf).stem}-zh-en-interleaved.pdf"), str(root / f"{Path(args.pdf).stem}-terms.tsv"), str(root / f"{Path(args.pdf).stem}-generation-stats.json")], "work_dirs": [str(d) for d in dirs[1:]]}, ensure_ascii=False))


def page_is_blank(page) -> bool:
    return not page.get_text("text").strip() and not page.get_drawings() and not page.get_images(full=True)


def inspect(args):
    pdf = fitz.open(args.pdf)
    outdir = Path(args.outdir) if args.outdir else project_dir_for(args.pdf) / ".work" / "inspect"
    ensure_dir(outdir)
    pages=[]; fonts={}; colors={}
    for i,p in enumerate(pdf):
        page_info={"page": i+1, "size": [round(p.rect.width,2), round(p.rect.height,2)], "rotation": p.rotation,
                   "text_blocks": 0, "image_count": len(p.get_images(full=True)), "blank": page_is_blank(p),
                   "fonts": [], "colors": {}}
        d=p.get_text("dict")
        for b in d.get("blocks",[]):
            if b.get("type")!=0: continue
            page_info["text_blocks"] += 1
            for ln in b.get("lines",[]):
                for sp in ln.get("spans",[]):
                    text=sp.get("text",""); f=sp.get("font",""); c=sp.get("color",0)
                    if f:
                        fonts[f]=fonts.get(f,0)+len(text)
                        if f not in page_info["fonts"]: page_info["fonts"].append(f)
                    colors[str(c)] = colors.get(str(c),0)+len(text)
                    page_info["colors"][str(c)] = page_info["colors"].get(str(c),0)+len(text)
        pages.append(page_info)
    report={"pdf": str(args.pdf), "page_count": len(pdf), "pages": pages,
            "fonts_by_chars": fonts, "colors_by_chars": colors}
    (outdir/"inspect.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.render:
        render_pages = sorted(set([1, len(pdf)] + [int(x) for x in args.render_pages.split(",") if x.strip().isdigit()]))
        for n in render_pages:
            if 1 <= n <= len(pdf):
                pix=pdf[n-1].get_pixmap(matrix=fitz.Matrix(args.zoom,args.zoom), alpha=False)
                pix.save(outdir/f"page-{n:03d}.png")
    print(json.dumps({"page_count": len(pdf), "outdir": str(outdir)}, ensure_ascii=False))


def read_terms(path: Path):
    rows=[]
    if not path or not path.exists(): return rows
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample=f.read(4096); f.seek(0)
        dialect=csv.excel_tab if "\t" in sample else csv.excel
        reader=csv.DictReader(f, dialect=dialect)
        for row in reader:
            if any((v or "").strip() for v in row.values()): rows.append(row)
    return rows


def wrap_text(s, max_units):
    lines=[]; cur=""; units=0.0
    for ch in str(s or ""):
        u=0.55 if ord(ch)<128 else 1.0
        if units+u>max_units and cur:
            lines.append(cur); cur=ch; units=u
        else:
            cur+=ch; units+=u
    if cur: lines.append(cur)
    return lines or [""]


def add_text(page, pos, text, fontfile, fontsize=7, color=(0,0,0), fontname="TermsCJK"):
    kw={"fontname":fontname if fontfile else "Times-Roman", "fontsize":fontsize, "color":color}
    if fontfile: kw["fontfile"]=fontfile
    try:
        page.insert_text(pos, text, **kw)
    except Exception:
        page.insert_text(pos, text.encode("ascii", "ignore").decode("ascii"), fontname="Times-Roman", fontsize=fontsize, color=color)


def add_terms_pages(doc, terms_path: Path, fontfile=None, title="术语汇总表"):
    rows=read_terms(terms_path)
    if not rows: return 0
    width,height = doc[0].rect.width, doc[0].rect.height
    margin=42; y0=72; line_h=10.5
    headers=["english_term","chinese_term","abbreviation","source","meaning","translation_strategy"]
    labels=["英文术语","中文译名","缩写","来源","含义解释","翻译策略"]
    col_fracs=[.17,.16,.08,.13,.27,.19]
    col_x=[margin]
    for fr in col_fracs[:-1]: col_x.append(col_x[-1]+(width-2*margin)*fr)
    col_w=[(width-2*margin)*fr for fr in col_fracs]
    pages=0; p=None; y=0
    def new_page():
        nonlocal p,y,pages
        p=doc.new_page(width=width,height=height); pages+=1; y=y0
        add_text(p,(margin,42),title,fontfile,fontsize=14)
        p.draw_line((margin,56),(width-margin,56),color=(0,0,0),width=.5)
        for x,w,lab in zip(col_x,col_w,labels):
            p.draw_rect(fitz.Rect(x,y-9,x+w,y+5), color=(0,0,0), fill=(.92,.92,.92), width=.3)
            add_text(p,(x+2,y),lab,fontfile,fontsize=7.2)
        y += 12
    new_page()
    for row in rows:
        cells=[]; row_lines=1
        for h,w in zip(headers,col_w):
            lines=wrap_text(row.get(h,""), max(6, int(w/4.2)))
            cells.append(lines); row_lines=max(row_lines,len(lines))
        rh=max(18,row_lines*line_h+5)
        if y+rh > height-45: new_page()
        for x,w,lines in zip(col_x,col_w,cells):
            p.draw_rect(fitz.Rect(x,y-9,x+w,y+rh-9), color=(0,0,0), width=.25)
            yy=y
            for line in lines:
                add_text(p,(x+2,yy),line,fontfile,fontsize=6.8)
                yy += line_h
        y += rh
    return pages


CODE_FONT_RE = re.compile(r"(mono|mon|code|consol|courier|fira|typewriter)", re.I)
IDENT_RE = re.compile(r"^(?:[A-Za-z_$][A-Za-z0-9_.$/@<>:-]*|[A-Za-z]+(?:-[A-Za-z0-9]+)+|\$\{\{.*\}\}|<[^>]+>)$")
PRESERVE_KEYWORDS = {
    "on","if","env","vars","secrets","inputs","outputs","permissions","uses","with","needs","steps","jobs","run",
    "workflow","workflows","runner","runners","job","step","action","actions","github","pull_request",
    "WorkflowIR","JobIR","StepIR","ExpressionRef","trigger_events","with_block","if_cond","step_id","job_id",
    "list","dict","str","Any","None","true","false","null","GITHUB_TOKEN","GITHUB_OUTPUT",
}


def is_code_font(font: str) -> bool:
    return bool(CODE_FONT_RE.search(font or ""))


def clean_literal_token(text: str) -> str:
    t=(text or "").strip()
    # Keep meaningful punctuation inside identifiers but trim prose punctuation around them.
    t=t.strip(" ,;。．，、()（）[]{}'")
    if t.endswith(":") and t.count(":") == 1:
        t=t[:-1]
    return t


def literal_candidate(text: str, font: str) -> bool:
    t=clean_literal_token(text)
    if not t or len(t) > 120 or t == "$":
        return False
    if not is_code_font(font):
        return False
    if t in PRESERVE_KEYWORDS:
        return True
    if IDENT_RE.match(t) and (
        any(ch in t for ch in "_.$/@<>:-") or
        re.search(r"[a-z][A-Z]|[A-Z][a-z]+[A-Z]", t) or
        t.isupper() or
        len(t) <= 4
    ):
        return True
    return False


def line_text(line):
    return "".join(sp.get("text","") for sp in line.get("spans",[])).strip()


def extract_literals(args):
    pdf=fitz.open(args.pdf)
    out_path=Path(args.out) if args.out else project_dir_for(args.pdf) / ".work" / "terms" / f"{Path(args.pdf).stem}-literal-preserve.tsv"
    json_path=Path(args.json) if args.json else out_path.with_suffix(".json")
    ensure_dir(out_path.parent); ensure_dir(json_path.parent)
    occurrences=[]; summary={}
    for pi,p in enumerate(pdf):
        for b in p.get_text("dict").get("blocks",[]):
            if b.get("type")!=0: continue
            for ln in b.get("lines",[]):
                context=line_text(ln)
                for sp in ln.get("spans",[]):
                    font=sp.get("font",""); raw=sp.get("text","")
                    # Split multi-word monospace spans so `env`, `uses`, `permissions` survive as separate no-translate items.
                    parts=re.findall(r"\$\{\{[^}]+\}\}|\$[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_.$/@<>:-]*|<[^>]+>", raw)
                    for part in parts:
                        term=clean_literal_token(part)
                        if not literal_candidate(term, font):
                            continue
                        role="special-font-code-identifier"
                        key=(term, role)
                        rec=summary.setdefault(key, {"english_term":term,"role":role,"count":0,"pages":set(),"fonts":set(),"examples":[]})
                        rec["count"]+=1; rec["pages"].add(pi+1); rec["fonts"].add(font)
                        if len(rec["examples"])<3:
                            rec["examples"].append(context[:240])
                        occurrences.append({"page":pi+1,"term":term,"font":font,"size":round(sp.get("size",0),2),"context":context})
    rows=[]
    for rec in summary.values():
        if rec["count"] < args.min_count:
            continue
        pages=sorted(rec["pages"])
        rows.append({
            "english_term":rec["english_term"],
            "chinese_term":rec["english_term"],
            "abbreviation":"",
            "source":"p."+",".join(map(str,pages[:12]))+("..." if len(pages)>12 else ""),
            "meaning":"特殊字体/代码样式标识符；默认保留英文原文，必要时在正文附近解释。",
            "translation_strategy":"保留英文；不翻译；保持代码字体或等宽/特殊字体样式",
            "count":str(rec["count"]),
            "fonts":";".join(sorted(rec["fonts"])),
            "examples":" | ".join(rec["examples"]),
        })
    rows.sort(key=lambda r: (-int(r["count"]), r["english_term"].lower()))
    fields=["english_term","chinese_term","abbreviation","source","meaning","translation_strategy","count","fonts","examples"]
    with out_path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,dialect=csv.excel_tab); w.writeheader(); w.writerows(rows)
    json_ready=[]
    for rec in summary.values():
        if rec["count"] >= args.min_count:
            json_ready.append({"english_term":rec["english_term"],"role":rec["role"],"count":rec["count"],"pages":sorted(rec["pages"]),"fonts":sorted(rec["fonts"]),"examples":rec["examples"]})
    json_ready.sort(key=lambda r:(-r["count"], r["english_term"].lower()))
    json_path.write_text(json.dumps({"pdf":str(args.pdf),"candidate_count":len(rows),"candidates":json_ready,"occurrences":occurrences[:5000]},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"candidate_count":len(rows),"out":str(out_path),"json":str(json_path)},ensure_ascii=False))


def append_terms(args):
    doc=fitz.open(args.pdf); before=len(doc)
    add_terms_pages(doc, Path(args.terms), args.font)
    doc.save(args.output, garbage=4, deflate=True)
    print(json.dumps({"input_pages": before, "output_pages": len(doc), "output": args.output}, ensure_ascii=False))


def interleave(args):
    src=fitz.open(args.source); zh=fitz.open(args.chinese)
    content_pages=args.content_pages or len(src)
    if len(zh) < content_pages:
        raise SystemExit(f"Chinese PDF has fewer pages ({len(zh)}) than required content pages ({content_pages}).")
    out=fitz.open()
    for i in range(content_pages):
        out.insert_pdf(zh, from_page=i, to_page=i)
        out.insert_pdf(src, from_page=i, to_page=i)
    terms_pages=0
    if args.terms:
        terms_pages=add_terms_pages(out, Path(args.terms), args.font)
    elif len(zh) > content_pages:
        out.insert_pdf(zh, from_page=content_pages, to_page=len(zh)-1)
        terms_pages=len(zh)-content_pages
    out.save(args.output, garbage=4, deflate=True)
    print(json.dumps({"source_pages": len(src), "content_pages": content_pages, "terms_pages": terms_pages, "output_pages": len(out), "output": args.output}, ensure_ascii=False))


def validate(args):
    source=fitz.open(args.source); zh=fitz.open(args.chinese); inter=fitz.open(args.interleaved)
    outdir=Path(args.outdir) if args.outdir else project_dir_for(args.source) / ".work" / "validation"
    ensure_dir(outdir)
    n=len(source); content_pages=args.content_pages or n
    issues=[]
    if len(zh) < content_pages: issues.append(f"zh pages {len(zh)} < expected content pages {content_pages}")
    for i in range(min(n,content_pages,len(zh))):
        if abs(source[i].rect.width-zh[i].rect.width)>0.5 or abs(source[i].rect.height-zh[i].rect.height)>0.5:
            issues.append(f"page size mismatch on zh page {i+1}")
        if page_is_blank(zh[i]): issues.append(f"blank zh page {i+1}")
    expected_min=content_pages*2
    if len(inter) < expected_min: issues.append(f"interleaved pages {len(inter)} < expected pair pages {expected_min}")
    for j,p in enumerate(inter):
        if page_is_blank(p): issues.append(f"blank interleaved page {j+1}")
    sample=sorted(set([1,2,3,content_pages,max(1,content_pages//2)] + [int(x) for x in args.sample_pages.split(",") if x.strip().isdigit()]))
    rendered=[]
    for n0 in sample:
        if 1 <= n0 <= len(zh):
            pix=zh[n0-1].get_pixmap(matrix=fitz.Matrix(args.zoom,args.zoom), alpha=False)
            path=outdir/f"zh-page-{n0:03d}.png"; pix.save(path); rendered.append(str(path))
        ip=(n0-1)*2+1
        if 1 <= ip <= len(inter):
            pix=inter[ip-1].get_pixmap(matrix=fitz.Matrix(args.zoom,args.zoom), alpha=False)
            path=outdir/f"interleaved-page-{ip:03d}.png"; pix.save(path); rendered.append(str(path))
    report={"source_pages":len(source),"zh_pages":len(zh),"interleaved_pages":len(inter),
            "expected_content_pages":content_pages,"issues":issues,"rendered_samples":rendered}
    (outdir/"validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if issues and args.fail_on_issue: sys.exit(1)


def pdf_info(path):
    p=Path(path)
    if not p.exists():
        return {"path": str(p), "exists": False}
    d=fitz.open(p)
    return {"path": str(p), "exists": True, "pages": len(d), "page_size": [float(d[0].rect.width), float(d[0].rect.height)] if len(d) else None, "bytes": p.stat().st_size}


def count_tsv_rows(path):
    p=Path(path)
    if not p.exists(): return 0
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        return max(0, sum(1 for _ in f) - 1)


def finalize(args):
    root=Path(args.output_dir) if args.output_dir else project_dir_for(args.source)
    ensure_dir(root)
    stem=Path(args.source).stem
    validation_path=Path(args.validation_json) if args.validation_json else root/".work"/"validation"/"validation.json"
    stats={
        "paper_stem": stem,
        "source_pdf": str(Path(args.source)),
        "project_dir": str(root),
        "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(),
        "final_outputs": [pdf_info(args.chinese), pdf_info(args.interleaved)],
        "terms_tsv": str(Path(args.terms)) if args.terms else None,
        "term_rows": count_tsv_rows(args.terms) if args.terms else 0,
        "validation_summary": None,
        "cleanup": "kept final PDFs, final terminology TSV, and generation statistics" if not args.keep_work else "kept intermediate .work directory by request",
    }
    if Path(args.source).exists():
        d=fitz.open(args.source); stats["source_pages"]=len(d); stats["source_page_size"]=[float(d[0].rect.width), float(d[0].rect.height)] if len(d) else None
    if validation_path.exists():
        try:
            v=json.loads(validation_path.read_text(encoding="utf-8"))
            stats["validation_summary"]={"issues": v.get("issues", []), "expected_content_pages": v.get("expected_content_pages"), "rendered_sample_count": len(v.get("rendered_samples", []))}
        except Exception as e:
            stats["validation_summary"]={"error": str(e)}
    stats_json=root/f"{stem}-generation-stats.json"
    stats_md=root/f"{stem}-generation-stats.md"
    stats_json.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    lines=[f"# Generation Stats: {stem}", "", f"- Source PDF: `{stats['source_pdf']}`", f"- Source pages: {stats.get('source_pages')}", f"- Terms TSV: `{Path(args.terms).name if args.terms else ''}` ({stats['term_rows']} rows)", "", "## Final outputs"]
    for o in stats["final_outputs"]:
        if o.get("exists"):
            ps=o.get("page_size") or [0,0]
            lines.append(f"- `{Path(o['path']).name}`: {o['pages']} pages, {ps[0]:.0f} x {ps[1]:.0f} pt, {o['bytes']} bytes")
        else:
            lines.append(f"- MISSING: `{o['path']}`")
    lines += ["", "## Validation", f"- Issues: {(stats.get('validation_summary') or {}).get('issues', [])}", "", "## Cleanup", f"- {stats['cleanup']}"]
    stats_md.write_text("\n".join(lines)+"\n", encoding="utf-8")
    if not args.keep_work:
        import shutil
        work=root/".work"
        if work.exists(): shutil.rmtree(work)
    print(json.dumps({"stats_json": str(stats_json), "stats_md": str(stats_md), "kept_work": args.keep_work}, ensure_ascii=False))


def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd", required=True)
    p=sub.add_parser("init-workdir"); p.add_argument("pdf"); p.add_argument("--output-dir"); p.set_defaults(func=init_workdir)
    p=sub.add_parser("inspect"); p.add_argument("pdf"); p.add_argument("--outdir"); p.add_argument("--render", action="store_true"); p.add_argument("--render-pages", default="1,2,3"); p.add_argument("--zoom", type=float, default=1.6); p.set_defaults(func=inspect)
    p=sub.add_parser("extract-literals"); p.add_argument("pdf"); p.add_argument("--out"); p.add_argument("--json"); p.add_argument("--min-count", type=int, default=1); p.set_defaults(func=extract_literals)
    p=sub.add_parser("append-terms"); p.add_argument("pdf"); p.add_argument("terms"); p.add_argument("output"); p.add_argument("--font", help="CJK font path, e.g. Source Han Serif CN"); p.set_defaults(func=append_terms)
    p=sub.add_parser("interleave"); p.add_argument("source"); p.add_argument("chinese"); p.add_argument("output"); p.add_argument("--terms"); p.add_argument("--font"); p.add_argument("--content-pages", type=int); p.set_defaults(func=interleave)
    p=sub.add_parser("validate"); p.add_argument("source"); p.add_argument("chinese"); p.add_argument("interleaved"); p.add_argument("--outdir"); p.add_argument("--content-pages", type=int); p.add_argument("--sample-pages", default="1,2,3"); p.add_argument("--zoom", type=float, default=1.6); p.add_argument("--fail-on-issue", action="store_true"); p.set_defaults(func=validate)
    p=sub.add_parser("finalize"); p.add_argument("source"); p.add_argument("chinese"); p.add_argument("interleaved"); p.add_argument("terms"); p.add_argument("--output-dir"); p.add_argument("--validation-json"); p.add_argument("--keep-work", action="store_true"); p.set_defaults(func=finalize)
    args=ap.parse_args(); args.func(args)

if __name__ == "__main__":
    main()
