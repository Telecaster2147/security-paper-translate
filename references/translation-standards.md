# Translation Standards

## Style

- Write in rigorous, readable academic Chinese.
- Prefer natural Chinese syntax over literal English structure.
- Keep claims, uncertainty, scope, and limitations exactly as in the source.
- Preserve numbered claims, contributions, assumptions, theorem/proof structure, evaluation results, percentages, metrics, dataset names, and citations.
- Do not omit caveats or weaken security implications.

## Terminology

- Use professional cybersecurity and systems terminology.
- On first occurrence of a key term, use `中文译名（English Term, ABBR）` when useful.
- Keep established names in English when translation would reduce clarity: project names, product names, repository names, API names, protocol names, code identifiers, commands, package names, and file paths.
- For ambiguous terms, choose a stable translation and record it in the TSV. If the term is domain-specific and uncertain, ask the user.

## Do-not-translate defaults

- Code blocks, shell commands, YAML/JSON keys/values when they are identifiers, file paths, repository/action names, package names, dataset names, tool names, API endpoints, environment variables, token names, CVE IDs, CWE IDs, RFC names, and references.
- Any source span rendered in a code, monospace, typewriter, or otherwise special identifier font should be a no-translate candidate when it functions as an identifier. Examples: `permissions`, `env`, `uses`, `needs`, `outputs`, `WorkflowIR`, `trigger_events`, `with_block`. Before full translation, present these candidates with category, source, and Chinese meaning for user confirmation. Translate the surrounding prose, not the identifier itself. If the same string appears as an ordinary prose word elsewhere, translate by context rather than blindly freezing every occurrence.
- Appendices and bibliography/reference entries unless explicitly requested.
- Text embedded inside images/figures; instead record important terms in the terminology table with page/figure source.

## Security-paper preferences

Common translations, adjust by context:

- vulnerability: 漏洞
- exploit: 利用 / 攻击利用
- threat model: 威胁模型
- adversary / attacker: 攻击者
- privilege escalation: 权限提升
- taint analysis: 污点分析
- source / sink: source / sink, or 源点 / 汇点 when the paper uses formal data-flow terminology
- sanitization / sanitizer: 净化 / 净化器, or 过滤 / 防护条件 by context
- workflow / runner / job / step: often keep English in GitHub Actions context, or translate as 工作流 / runner / 作业 / 步骤 when readability benefits

## Quality bar

A good result should read like a Chinese security conference paper, not like sentence-by-sentence machine translation. Use a two-pass process when the user enables it: first produce a faithful translation, then polish for natural academic Chinese. If maintaining exact layout conflicts with verbose translation, make the Chinese concise first; only then reduce font size slightly.
