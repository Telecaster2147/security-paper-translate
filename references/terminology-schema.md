# Terminology TSV Schema

Create `<stem>-terms.tsv` with a header row and these columns:

1. `english_term` - original English term.
2. `chinese_term` - chosen Chinese translation or retained English form.
3. `abbreviation` - abbreviation if any, else empty.
4. `source` - page/section/figure/table/listing where the term appears, e.g. `p.3 §II-A`, `p.5 Fig.2`, `p.7 Table I`.
5. `meaning` - concise explanation in Chinese.
6. `translation_strategy` - e.g. `首次双语后用缩写`, `保留英文产品名`, `代码标识符不译`, `图中术语仅在表中解释`.

Rules:

- Every key paper-specific concept must appear.
- Important terms from figures should be included even if figure-internal English is not translated.
- Include domain terms, method names, attack names, model names, datasets, metrics, security properties, and abbreviations.
- Do not flood the table with ordinary words.
