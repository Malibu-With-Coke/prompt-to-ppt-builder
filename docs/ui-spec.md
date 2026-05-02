# UI Spec: Prompt-to-PPT Enterprise Builder

| Field | Value |
|---|---|
| Version | v0.3 |
| Updated | 2026-05-02 |
| Framework | React + Vite |
| State | Zustand |
| Router | React Router |
| Styling | Tailwind CSS |

---

## 1. Routes

```text
/upload       UploadPage
/jobs/:jobId  JobStatusPage
/history      HistoryPage
```

`/` redirects to `/upload`.

---

## 2. UploadPage

### Purpose

The upload page creates a generation job from one PPTX template and one or more DOCX/XLSX source files.

### State

```typescript
templateFile: File | null
contentFiles: File[]
tone: string
target: string
length: number
notes: string
aiEngine: "bedrock" | "openai"
uploadProgress: number
isSubmitting: boolean
errorMessage: string | null
```

### File Rules

| Field | Extensions | Count | Notes |
|---|---|---:|---|
| templateFile | `.pptx` | 1 | Template layout and style source of truth |
| contentFiles | `.docx`, `.xlsx` | 1-10 | Multiple source documents can be synthesized together |

### Submit Flow

```text
1. POST /jobs/upload-url for template
2. PUT template.pptx to S3
3. For each content file:
   3-1. POST /jobs/upload-url with fileIndex
   3-2. PUT content file to S3
4. POST /jobs with templateS3Key and contentS3Keys
5. Navigate to /jobs/:jobId
```

Content upload key examples:

```text
uploads/{jobId}/content-01.docx
uploads/{jobId}/content-02.xlsx
```

### UX Rules

- Enable generation only when one template file and at least one content file are selected.
- Show selected content files as a list.
- Support removing each content file independently.
- Disable submit while upload/job creation is running.
- Validate file extension and max content-file count before calling the API.

---

## 3. JobStatusPage

### Purpose

The status page polls a job, shows the current pipeline stage, and provides a result download when the job succeeds.

### Status Model

```typescript
status: "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED"
pipelineStage?:
  | "DOCUMENT_PARSING"
  | "LLM_TEMPLATE_TRANSFORMATION"
  | "PPT_BUILDING"
  | "PPT_VALIDATION"
  | "PPT_REVIEW"
  | "RESULT_UPLOADING"
  | "RESULT_READY"
  | "DEMO_RESULT_READY"
```

### Polling

- `PENDING` or `RUNNING`: keep polling `GET /jobs/:jobId`.
- `SUCCEEDED` or `FAILED`: stop polling.
- `SUCCEEDED`: show result download button.
- `FAILED`: show `errorMessage` and a retry link back to `/upload`.

---

## 4. HistoryPage

### Purpose

The history page lists jobs for the current browser session.

### API

- `GET /jobs`
- Include `X-Session-Token` on every request.

### UX Rules

- Sort by most recent creation time.
- Provide a view action for every job.
- Provide a download action for succeeded jobs.
- Show an empty state with a link to `/upload` when there are no jobs.

---

## 5. API Common

Create a UUID session token on first browser visit and persist it in `localStorage`.

```typescript
const token = localStorage.getItem("sessionToken") ?? crypto.randomUUID();
```

All API requests include:

```text
X-Session-Token: {sessionToken}
```

API Gateway CORS must explicitly allow this header.
