# Infra Deployment Guide

This CDK app provisions the backend MVP E2E stack for Prompt-to-PPT.

## What It Creates
- S3 bucket for uploads, temp artifacts, and results
- DynamoDB table for job state
- ECS Cluster + Fargate task definition for the real worker container
- Step Functions state machine that runs the worker with `.sync`
- Lambda APIs for upload URL, create job, get job, and list jobs
- API Gateway REST API

Frontend hosting is handled separately by AWS Amplify Hosting.

## Defaults
- Region default: `ap-northeast-2`
- Deployment target: single account, single region MVP
- Worker AI default: `bedrock`

## Required Environment Variables
Set these before `cdk synth` / `cdk deploy`:

```powershell
$env:CDK_DEFAULT_ACCOUNT='123456789012'
$env:CDK_DEFAULT_REGION='ap-northeast-2'
$env:AI_ENGINE='bedrock'
$env:BEDROCK_MODEL_ID='apac.anthropic.claude-3-5-sonnet-20241022-v2:0'
$env:LLM_MAX_TOKENS='6000'
# Optional only if using OpenAI mode:
$env:OPENAI_SECRET_NAME='ppt-builder/openai-api-key'
```

## Deploy
```powershell
cd infra
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cdk bootstrap aws://$env:CDK_DEFAULT_ACCOUNT/$env:CDK_DEFAULT_REGION
cdk synth
cdk deploy
```

## Outputs
After deploy, collect these CloudFormation outputs:
- `ApiBaseUrl`
- `BucketName`
- `JobsTableName`
- `StateMachineArn`
- `ClusterName`

Use `ApiBaseUrl` as the frontend `VITE_API_BASE_URL` value in Amplify.

## Post-Deploy Validation
1. Call `POST /jobs/upload-url` for template and content.
2. Upload both files to the signed S3 URLs.
3. Call `POST /jobs`.
4. Confirm a Step Functions execution starts.
5. Confirm the ECS task starts and CloudWatch logs show `entrypoint.py` running.
6. Confirm DynamoDB `pipelineStage` reaches `RESULT_READY`.
7. Confirm `GET /jobs/{jobId}` returns `SUCCEEDED` and a `resultUrl` for the same `X-Session-Token`.
