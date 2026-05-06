# Handover Document: Prompt-to-PPT Enterprise Builder

This document summarizes the current state of the Prompt-to-PPT project for the next developer or AI agent.

## 1. Project Overview

Prompt-to-PPT transforms an uploaded PowerPoint template plus one or more DOCX/XLSX source files into a new PPTX. The current implementation preserves the uploaded template's slide count, order, layout, fonts, and text shape structure, then replaces stale text in-place using an LLM-generated transform plan.

- Root directory: `D:\Coding\hackerton`
- Frontend: React + Vite + Tailwind
- Backend: AWS Lambda API handlers
- Worker: Python ECS/Fargate pipeline
- Infra: AWS CDK
- Tests: `tests/test_walking_skeleton.py`

## 2. Current Status

### Frontend

- Upload page supports one template PPTX and multiple DOCX/XLSX content files.
- Content uploads use `fileIndex`, producing stable S3 keys such as `content-01.docx` and `content-02.xlsx`.
- Job creation sends `contentS3Keys` while retaining compatibility with legacy `contentS3Key`.
- Status page includes worker stages through `PPT_VALIDATION` and `PPT_REVIEW`.

### Backend

- Upload URL APIs support template uploads and indexed content uploads.
- Job creation accepts `contentS3Keys` arrays.
- DynamoDB records store both legacy `contentS3Key` and new `contentS3Keys`.
- Demo fast-path remains available for bundled demo assets.

### Worker

Current worker flow:

```text
DocumentParser
  -> DeckTransformAgent
  -> PPTBuilder
  -> PPTValidationAgent
  -> ReviewAgent
  -> ResultUploader
```

Document parsing:

- PPTX template: slide count, dimensions, layouts, text shape IDs, text positions, fonts, colors
- DOCX: title, heading outline, paragraph sections, table previews, style counts, report signals
- XLSX: workbook profile, sheet summaries, sample rows, numeric columns, formula cells, structured tables, embedded chart metadata
- Multi-file input: combined `documentType: "multi"` with flattened sections plus per-source `documents`, `documentProfiles`, and `workbookProfiles`

LLM transform:

- Produces `deckTitle`, `strategy`, slide-level `sourceFocus`, `speakerNotes`, and `shapeId -> text` replacements.
- Also supports `chartUpdates` and `tableUpdates` intent for Excel-derived content.
- Each template text shape now includes a `fit` hint with `role`, `maxChars`, `maxLines`, and `areaIn2` so the LLM keeps copy within the original box.

PPT QA:

- `PPTValidationAgent` audits generated PPTX files for bounds, text length, and text density.
- In AWS worker images, LibreOffice + Poppler enable render smoke tests.
- `ReviewAgent` checks replacement coverage, Excel update intent, render status, and PPT validation warnings.
- `high_text_density` is promoted to an error so the review status becomes `needs_retry`.

## 3. Important Technical Decisions

- MarkItDown is intentionally removed from the runtime path. DOCX/XLSX structured parsers are the source of truth.
- Native chart/table updates are not yet applied to the PPTX; the LLM currently emits chart/table update intent for future builder work.
- The MVP keeps the template slide count, order, and layout unchanged.
- The demo fast-path remains for feedback and quick previews.
- MarkItDown was compared against the project parser on sample PPTX/DOCX/XLSX files. It is good for human-readable Markdown text, especially DOCX and plain XLSX tables, but it drops metadata needed for this product: PPT shape IDs/positions/styles and Excel chart/formula/workbook structure.

## 4. Verification

Current baseline:

```powershell
python -B -m unittest tests.test_walking_skeleton
```

Recent local verification covered:

- DOCX + XLSX multi-file upload contract
- worker orchestration with validation and review stages
- template text replacement preserving style
- shape fit hints in DeckTransformAgent
- `high_text_density` becoming `needs_retry`
- parser comparison against MarkItDown with the project parser remaining the runtime source of truth

For frontend:

```powershell
cd frontend
npm run build
```

On this Windows environment, `npm run build` may need to run outside the sandbox because Vite can hit `spawn EPERM` during config bundling.

## 5. Known Gaps

1. Automatic retry loop is not implemented yet. `ReviewAgent` can mark `needs_retry`, but `Orchestrator` currently fails the job instead of asking the LLM to shorten only problematic shapes.
2. Excel native chart/table updates are intent-only. `PPTBuilder` still performs text replacement only.
3. Local render validation is skipped unless LibreOffice and Poppler are installed. AWS worker images include them.
4. Demo fast-path uses static bundled output and should be kept conceptually separate from the full worker path.

## 6. Recommended Next Steps

1. Add targeted LLM retry for `high_text_density` and render failures.
2. Implement native chart/table update handling in `PPTBuilder`.
3. Add integration tests around multi-source parsing with real sample files.
4. Add CloudWatch alarms around failed jobs and render validation failures.
5. Decide whether the demo branch behavior should be merged into `main` or remain isolated.
