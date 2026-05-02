---
name: prompt-to-ppt-quality
description: Improve and validate a Prompt-to-PPT worker pipeline that transforms uploaded PPTX templates with DOCX or XLSX source files. Use when working on document parsing, spreadsheet profiling, template shape extraction, LLM transform prompts, PPTX text replacement, or post-build quality checks for the hackerton Prompt-to-PPT project.
---

# Prompt-to-PPT Quality

Use this skill to improve the worker pipeline without replacing its core product contract: preserve the uploaded PowerPoint template, transform source content into concise slide copy, and write replacements back into the original deck.

## Project Fit

The current pipeline is:

```text
DocumentParser -> DeckTransformAgent -> PPTBuilder -> ResultUploader
```

Keep this shape unless the user explicitly asks for a larger rewrite. Prefer adding better source profiles, transform-plan fields, and validation gates around the existing flow.

## Workflow

1. Profile the uploaded source document.
   - Use `scripts/source_profile.py <input.docx|input.xlsx> --out parsed.json`.
   - For DOCX, preserve heading hierarchy, paragraph samples, and table previews.
   - For XLSX, inspect sheets, formulas, tables, numeric columns, and chart-friendly ranges.

2. Inspect the PPTX template or generated deck.
   - Use `scripts/pptx_audit.py <deck.pptx> --out audit.json`.
   - Capture slide size, layouts, text shapes, placeholders, fonts, colors, and text-fit risk warnings.

3. Feed compact, structured facts to the LLM.
   - Keep `shapeId` as the stable replacement key.
   - Include source profile summaries instead of raw document dumps.
   - Ask for concise copy that fits existing shape bounds.
   - For XLSX inputs, ask for metric, trend, table, and chart update intent in addition to text replacements when the builder supports it.

4. Build in place.
   - Preserve slide count, order, and layout.
   - Preserve run style where possible.
   - Do not rasterize text or rebuild the whole deck unless the user asks for a new deck engine.

5. Validate after build.
   - Run `scripts/pptx_audit.py` on the output deck.
   - Treat out-of-bounds shapes, unusually dense text, empty required replacements, missing fonts, and stale template text as review items.
   - If rendering tools are available, render slides to PNGs and visually inspect them before delivery or deployment.

## Integration Guidance

- Add a `PPT_VALIDATION` stage after `PPT_BUILDING` when product quality matters.
- Store intermediate JSON under `temp/{jobId}/` so failures can be inspected from S3.
- Keep deterministic scripts separate from LLM prompts. Scripts should extract facts; the LLM should decide narrative and wording.
- Use `python-pptx` for template inspection and in-place edits in the current MVP. Do not switch to a full deck-generation engine unless preserving uploaded templates is no longer required.
- Use `openpyxl` with both formula and cached-value passes for XLSX profiling. `data_only=True` alone loses formula intent.
- Use `python-docx` for DOCX structure extraction. Do not rely only on raw paragraph text when tables and headings matter.

## Script Contracts

### `scripts/source_profile.py`

```powershell
python skills/prompt-to-ppt-quality/scripts/source_profile.py input.xlsx --out parsed.json
python skills/prompt-to-ppt-quality/scripts/source_profile.py input.docx --out parsed.json
```

Output: JSON with `documentType`, `title`, `sections`, and file-specific metadata.

Use it to replace or supplement `DocumentParser._parse_docx` and `DocumentParser._parse_xlsx`.

### `scripts/pptx_audit.py`

```powershell
python skills/prompt-to-ppt-quality/scripts/pptx_audit.py template.pptx --out template_audit.json
python skills/prompt-to-ppt-quality/scripts/pptx_audit.py output.pptx --out output_audit.json
```

Output: JSON with `slideWidth`, `slideHeight`, `slides`, `fonts`, `colors`, and `warnings`.

Use it before LLM planning for template rules and after `PPTBuilder` for QA.

## Quality Gates

Block or retry generation when:

- The LLM omits replacement text for a non-empty template text shape.
- A generated text shape has high fit risk in `pptx_audit.py`.
- The source profile has no usable sections.
- An XLSX profile contains numeric data but the transform plan treats it only as prose.
- The output deck still contains obvious stale template terms that conflict with the source period, company, quarter, or metric.

Allow with warning when:

- Rendering tools are unavailable and only structural PPTX inspection was possible.
- A chart/table update intent exists but the builder only supports text replacement.
- Font substitution cannot be checked in the runtime.
