# Handover Document: Prompt-to-PPT Enterprise Builder

This document summarizes the current state of the "Prompt-to-PPT" project to facilitate a seamless transition for the next developer or AI agent.

## 1. Project Overview
A platform that transforms documents (Word/Excel) into professional PowerPoint presentations using an agentic AI pipeline (AWS Lambda + Step Functions + Fargate Worker).

- **Root Directory**: `d:\hackerton`
- **Monorepo Structure**:
  - `frontend/`: React + Vite + Tailwind + Zustand.
  - `backend/`: AWS Lambda (Python).
  - `worker/`: Fargate Container (Python) with 7-stage agent pipeline.
  - `infra/`: Infrastructure as Code (Terraform/CDK) placeholders.
  - `docs/`: Design documents and specifications.

---

## 2. Current Progress & Status

### A. Frontend (`frontend/`)
- **Tech Stack**: React 18, Vite, Tailwind CSS v3, Zustand.
- **UI Design**: Integrated professional "Enterprise Navy" theme generated via Stitch MCP.
- **Pages Implemented**:
  - `UploadPage.tsx`: File upload dropzones and configuration (Tone, Audience, etc.).
  - `JobStatusPage.tsx`: Animated progress ring with mock polling.
  - `HistoryPage.tsx`: Table listing jobs with status badges.
- **State Management**: `useJobStore.ts` manages API parameters and `currentJobId`.
- **Status**: Visuals are 100% migrated from prototypes. Mock logic allows navigating "Upload -> Status -> History". Needs real API integration.

### B. Backend (`backend/`)
- **Tech Stack**: Python (AWS Lambda).
- **Handlers**: Stubs created for `create_job`, `get_job`, `list_jobs`, and `upload_url`.
- **Shared Storage**: `shared/` directory set up for DynamoDB and S3 interactions.
- **Status**: API contract defined but business logic (DB queries, signed URL generation) is currently placeholders.

### C. Worker (`worker/`)
- **Tech Stack**: Python 3.11, Docker.
- **Pipeline**: `PipelineOrchestrator` is set up with placeholders for 7 agents (`DocumentParser` to `ResultUploader`).
- **Status**: Dockerfile and entrypoint ready. Core LLM logic for PPT generation needs implementation.

---

## 3. Key Technical Decisions
1. **Zustand for State**: Chosen for simplicity in managing session tokens and job parameters.
2. **Tailwind v3**: Used for stable utility-first styling with custom design tokens from Stitch.
3. **Python Environment**: Lambda and Worker have separate `requirements.txt` to keep Lambda footprints small.
4. **Mock Polling**: Frontend currently simulates progress; needs to be replaced with `axios` calls to `GET /jobs/{id}`.

---

## 4. Next Steps (Priority Order)
1. **Backend Integration**: Implement real logic in `backend/lambdas/` to interact with DynamoDB and S3.
2. **Frontend Wiring**: Replace mock `handleGenerateClick` in `UploadPage.tsx` with actual `upload_url` and `create_job` calls.
3. **Worker Implementation**: Flesh out the 7-stage agent pipeline in `worker/pipeline/`.
4. **Infra Deployment**: Create Terraform/CDK scripts in `infra/` to provision S3 buckets, DynamoDB tables, and Step Functions.

---

## 5. Development Guide
- **Start Frontend**: `cd frontend && npm run dev` (Port 5173).
- **Check UI Previews**: Static HTML prototypes are at `d:\hackerton\previews\`.
- **Configs**: See `.env.example` in the root.

---
*Handover prepared by Antigravity AI*
