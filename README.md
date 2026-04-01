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
$env:BEDROCK_MODEL_ID='anthropic.claude-3-5-sonnet-20241022-v2:0'
cdk deploy --require-approval never
```

## Amplify Frontend Hosting

`amplify.yml` is configured so AWS Amplify Hosting builds only the `frontend/` workspace from this monorepo.
