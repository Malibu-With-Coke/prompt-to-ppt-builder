# Deployment Notes

## Current Deployment Split

- Frontend hosting is deployed with AWS Amplify Hosting.
- Backend and infrastructure are deployed with AWS CDK through CloudFormation.
- The live API base URL is `https://px5m3uz2sa.execute-api.ap-northeast-2.amazonaws.com/prod/`.

## Branch Strategy

- `main`
  - Production-oriented branch
  - Amplify production branch
- `codex/demo-one-click-ppt`
  - Isolated demo branch for feedback collection
  - Amplify preview branch
  - Used to test one-click PPT generation without manual uploads

## Demo Preview

- Preview URL: `https://codex-demo-one-click-ppt.d2qzosqvodzspp.amplifyapp.com/upload`
- The upload page exposes a `Try Demo PPT` action.
- Clicking the button creates a job with `demoPreset: "excel"`.
- The backend injects packaged demo assets from `backend/demo_assets/`.
- The backend fast-path marks the job as `SUCCEEDED` and returns a downloadable sample PPT.

## CORS Note

Amplify browser requests include the `X-Session-Token` header. API Gateway preflight responses must allow that header explicitly.

If `X-Session-Token` is missing from the CORS allow-list:

- direct API calls may still work
- browser requests fail with a generic `Network Error`
- the demo button appears broken even though the backend is healthy

The current CORS source of truth is [infra_stack.py](D:\hackerton\infra\infra\infra_stack.py).

## Operational Reminder

- Frontend-only changes: push to GitHub and let Amplify rebuild
- Backend or infrastructure changes: run `cdk deploy` from `infra/`
- Demo branch changes should stay isolated until they are intentionally merged into `main`
