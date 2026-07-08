# Security Paper Translate Skill

Security Paper Translate 是一个 Codex skill，用于把网络安全及相关方向的英文学术论文 PDF 翻译成专业中文，同时尽可能保持原始 PDF 版式。它特别适合对格式要求高的论文：双栏排版、图表、表格、标题层级、代码块、加粗、彩色引用和术语表都需要保真。

## 输出内容

对于输入论文 `paper.pdf`，skill 会在 `translated-pdfs/paper/` 下生成：

- `paper-zh.pdf`：中文单独版内容页，并在末尾追加术语表。
- `paper-zh-en-interleaved.pdf`：中文页在前、对应英文页在后，逐页交错，并在末尾追加术语表。
- `paper-terms.tsv`：带来源页码的术语表和不翻译策略表。
- `paper-generation-stats.json` 与 `paper-generation-stats.md`：生成和验证统计信息。

## 核心保证

- 翻译由 Codex 自己完成；禁止调用外部机翻、其他 LLM API 或本地 LLM。
- 保持页面尺寸、栏布局、视觉密度、图表、表题、标题层级、粗体/斜体/颜色等原始设计。
- 代码、listing、verbatim 区域必须原样保留：不翻译、不重排缩进、不改行、不改变 monospace/code 样式。
- 中文标题和重点加粗必须使用真实 CJK Bold/SemiBold 字体；禁止用重复叠画、描边、阴影、偏移多画等方式伪造粗体。
- 可以复用本地 `pdf2zh` / PDFMathTranslate 的版式保持能力，但只能作为布局引擎；翻译层必须替换为 Codex 写好的本地翻译。
- 必须追加有来源的术语表，并在最终回答前渲染抽样页验证。

## 仓库结构

```text
security-paper-translate/
├── SKILL.md                         # skill 主说明
├── agents/openai.yaml               # Agent UI 元数据
├── references/
│   ├── font-bold-rendering.md       # 真实字体加粗与验证规则
│   ├── layout-preservation-notes.md # 版式、样式、代码块和验证规则
│   ├── pdf2zh-layout-integration.md # 本地 pdf2zh monkeypatch 工作流
│   ├── terminology-schema.md        # 术语 TSV schema
│   └── translation-standards.md     # 学术/安全论文翻译标准
├── scripts/
│   ├── check_environment.py         # 依赖和本地扩展检查
│   ├── check_pdf_bold_integrity.py  # 检查加粗重叠/描边伪粗体问题
│   ├── paper_pdf_tools.py           # inspect、术语表、interleave、validate、finalize 工具
│   ├── pdf2zh_capture_chunks.py     # 无机翻捕获 pdf2zh chunks
│   ├── pdf2zh_codex_driver.py       # 用 Codex 本地翻译驱动 pdf2zh 布局引擎
│   └── pdf_postprocess_template.py  # 通用 PDF 后处理模板
└── .github/workflows/validate.yml   # 基础仓库验证
```

## 安装到 Codex

把该仓库 clone 或复制到 Codex skills 目录：

```bash
git clone <repo-url> ~/.codex/skills/security-paper-translate
```

之后在 Codex 中要求使用 `$security-paper-translate` 翻译英文论文 PDF 即可。

## 运行依赖

辅助脚本尽量保持轻量。最低 Python 依赖：

```bash
python -m pip install -r requirements.txt
```

推荐系统工具：

- `pdftoppm`：来自 poppler，用于渲染抽样页做视觉验证。
- `pdffonts`：来自 poppler，用于检查嵌入字体。
- `pdf2zh`：可选，但强烈推荐用于严格版式保持。
- CJK 字体，例如 Source Han Serif CN 或 Noto CJK；强烈建议安装真实 CJK Bold/SemiBold 字体。

检查本地环境：

```bash
python scripts/check_environment.py --json
```

## 典型 Agent 提示词

```text
Use $security-paper-translate to translate /path/to/paper.pdf. Follow the preflight confirmation, terminology policy, layout-preservation, code-block preservation, real-font bold rendering, validation, and finalize workflow in SKILL.md. Generate Chinese-only and Chinese-first interleaved PDFs under translated-pdfs/<stem>/.
```

## 开发验证

提交前建议运行：

```bash
python -m py_compile scripts/*.py
python scripts/check_environment.py --json >/tmp/security-paper-translate-env.json
python /path/to/skill-creator/scripts/quick_validate.py .
```

如果生成 PDF 时修补过标题或重点加粗，还应运行：

```bash
python scripts/check_pdf_bold_integrity.py /path/to/paper-zh.pdf --fail-on-issue
```
