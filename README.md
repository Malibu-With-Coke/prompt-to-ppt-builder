# Prompt-to-PPT Enterprise Builder

Prompt-to-PPT is a monorepo for generating presentation decks from uploaded source documents and a PowerPoint template.

## Structure

- `frontend/`: React + Vite + Tailwind UI
- `backend/`: AWS Lambda handlers for job creation, upload URLs, and status APIs
- `worker/`: Python pipeline executed by ECS Fargate
- `infra/`: AWS CDK infrastructure for API, storage, Step Functions, and hosting
- `tests/`: Walking Skeleton tests

## Local Development

```powershell
npm run dev
```

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
$env:BEDROCK_MODEL_ID='apac.anthropic.claude-3-5-sonnet-20241022-v2:0'
cdk deploy --require-approval never
```

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

This is configured in [D:\hackerton\infra\infra\infra_stack.py](D:\hackerton\infra\infra\infra_stack.py) via `default_cors_preflight_options.allow_headers`.
