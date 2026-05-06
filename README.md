# Prompt-to-PPT Enterprise Builder

Prompt-to-PPT is a monorepo for generating presentation decks from uploaded DOCX/XLSX source files and a PowerPoint template.

The current worker keeps the uploaded template deck as the layout source of truth, parses multiple content files, asks an LLM for shape-level replacement text plus chart/table update intent, builds a new PPTX in-place, and runs post-build QA.

## Structure

- `frontend/`: React + Vite + Tailwind UI
- `backend/`: AWS Lambda handlers for job creation, upload URLs, and status APIs
- `worker/`: Python pipeline executed by ECS Fargate
- `infra/`: AWS CDK infrastructure for API, storage, Step Functions, and hosting
- `tests/`: Walking Skeleton tests

## Current Pipeline

```text
Upload template.pptx + one or more content files
  -> parse PPT template text shapes
  -> parse DOCX heading/table/report structure
  -> parse XLSX workbook/sheet/table/chart/formula structure
  -> LLM creates text replacements plus chart/table update intent
  -> PPT builder replaces template text in-place
  -> PPT validation audits density/bounds and optionally renders with LibreOffice
  -> ReviewAgent flags QA issues before upload
```

Supported source files:

- `.docx`: headings, paragraphs, table previews, report signals
- `.xlsx`: workbook profile, sheets, sample rows, numeric columns, formulas, Excel tables, embedded chart metadata

MarkItDown is intentionally not used in the runtime path. Exact structured parsers are the source of truth.

Recent parser comparison against MarkItDown:

- PPTX: MarkItDown is useful for reading slide text, but it does not provide `shapeId`, position, font, color, or layout metadata required for in-place template replacement.
- DOCX: MarkItDown produces readable Markdown, but the project parser provides stable heading/table/report structure.
- XLSX: MarkItDown produces clean Markdown tables, but the project parser preserves workbook profile, numeric columns, formulas, and chart/table metadata needed for update intent.

## Local Development

```powershell
npm run dev
```

## Tests

```powershell
python -B -m unittest tests.test_walking_skeleton
```

Use `-B` on Windows to avoid `.pyc` cache file lock noise when tests are run near other Python commands.

## Frontend Build

```powershell
$env:VITE_API_BASE_URL='https://example.execute-api.ap-northeast-2.amazonaws.com/prod/'
npm run build
```

## AWS Deployment

The backend and infrastructure are deployed with AWS CDK.

```powershell
cd infra
$env:CDK_DEFAULT_ACCOUNT='123456789012'
$env:CDK_DEFAULT_REGION='ap-northeast-2'
$env:AI_ENGINE='bedrock'
$env:BEDROCK_MODEL_ID='global.anthropic.claude-sonnet-4-5-20250929-v1:0'
cdk deploy --require-approval never
```

The worker Docker image installs LibreOffice and Poppler so `PPTValidationAgent` can run a render smoke test in AWS. Local machines without `soffice/libreoffice` and `pdftoppm` will still run the structural PPT audit, but render validation is reported as skipped.

## Amplify Frontend Hosting

`amplify.yml` is configured so AWS Amplify Hosting builds only the `frontend/` workspace from this monorepo.

## Current Deployment Split

- Frontend hosting: AWS Amplify Hosting
- Backend and infrastructure: AWS CDK -> CloudFormation
- API base URL: `https://px5m3uz2sa.execute-api.ap-northeast-2.amazonaws.com/prod/`

## Branch-Based Demo Preview

- Production branch: `main`
- Demo preview branch: `codex/demo-one-click-ppt`
- Demo preview URL: `https://codex-demo-one-click-ppt.d2qzosqvodzspp.amplifyapp.com/upload`

The demo branch adds a one-click flow on the upload page so reviewers can generate a sample PPT without uploading their own files.

### Demo Behavior

- Clicking `Try Demo PPT` creates a job with `demoPreset: "excel"`
- The backend injects bundled demo assets from `backend/demo_assets/`
- The job is completed through a backend fast-path and returns a downloadable sample PPT

### Important CORS Note

Amplify preview builds call the API with the `X-Session-Token` header. API Gateway CORS must explicitly allow this header or the browser will show a generic `Network Error` even when the backend itself is healthy.

This is configured in `infra/infra/infra_stack.py` via `default_cors_preflight_options.allow_headers`.
