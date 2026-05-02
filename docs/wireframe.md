# Wireframe: Prompt-to-PPT Enterprise Builder

## 1. UploadPage

```text
┌─────────────────────────────────────────────────────────────┐
│ Prompt-to-PPT                         Upload  History       │
├─────────────────────────────────────────────────────────────┤
│ Create PPT                                                  │
│                                                             │
│ Source files                                                │
│ ┌─────────────────────────┐ ┌─────────────────────────────┐ │
│ │ Template PPT            │ │ Content files               │ │
│ │ Drop or click           │ │ Drop or click               │ │
│ │ .pptx                   │ │ .docx / .xlsx, up to 10     │ │
│ └─────────────────────────┘ └─────────────────────────────┘ │
│                                                             │
│ Selected files                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ template.pptx                                      [x]  │ │
│ │ content-01.docx                                    [x]  │ │
│ │ content-02.xlsx                                    [x]  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Options                                                     │
│ Tone:    [Executive] [Formal] [Concise]                    │
│ Target:  [Management] [Internal Team] [Customer/External]  │
│ Length:  [5] [10] [15]                                     │
│ Engine:  [Bedrock] [OpenAI]                                │
│ Notes:   ┌───────────────────────────────────────────────┐ │
│          │ Optional instructions                         │ │
│          └───────────────────────────────────────────────┘ │
│                                                             │
│ [Generate PPT]                                              │
│ Progress: ███████████░░░░ 65%                               │
└─────────────────────────────────────────────────────────────┘
```

## 2. JobStatusPage

```text
┌─────────────────────────────────────────────────────────────┐
│ Prompt-to-PPT                         Upload  History       │
├─────────────────────────────────────────────────────────────┤
│ PPT Generation Status                                       │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Job ID: 7d7f...                                        │ │
│ │ Status: RUNNING                                        │ │
│ │ Stage: PPT_VALIDATION                                  │ │
│ │                                                         │ │
│ │ DOCUMENT_PARSING              ✓                        │ │
│ │ LLM_TEMPLATE_TRANSFORMATION   ✓                        │ │
│ │ PPT_BUILDING                  ✓                        │ │
│ │ PPT_VALIDATION                ●                        │ │
│ │ PPT_REVIEW                    ○                        │ │
│ │ RESULT_UPLOADING              ○                        │ │
│ │                                                         │ │
│ │ Created: 2026-05-02 14:32                              │ │
│ │ Updated: 2026-05-02 14:34                              │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Succeeded

```text
┌─────────────────────────────────────────────────────────────┐
│ Status: SUCCEEDED                                           │
│ Stage: RESULT_READY                                         │
│ [Download result PPT]                                       │
└─────────────────────────────────────────────────────────────┘
```

### Failed

```text
┌─────────────────────────────────────────────────────────────┐
│ Status: FAILED                                              │
│ Stage: PPT_REVIEW                                           │
│ Error: Generated PPT failed QA review: high_text_density    │
│ [Try again]                                                 │
└─────────────────────────────────────────────────────────────┘
```

## 3. HistoryPage

```text
┌─────────────────────────────────────────────────────────────┐
│ Prompt-to-PPT                         Upload  History       │
├─────────────────────────────────────────────────────────────┤
│ PPT History                                                 │
│                                                             │
│ ┌──────────────┬───────────┬──────────────────┬──────────┐ │
│ │ Job ID       │ Status    │ Created          │ Action   │ │
│ ├──────────────┼───────────┼──────────────────┼──────────┤ │
│ │ 7d7f...      │ Completed │ 2026-05-02 14:32 │ Download │ │
│ │ 53aa...      │ Running   │ 2026-05-02 13:10 │ View     │ │
│ │ 91bc...      │ Failed    │ 2026-05-01 19:45 │ View     │ │
│ └──────────────┴───────────┴──────────────────┴──────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 4. User Journey

```text
/upload
  -> upload template.pptx
  -> upload one or more DOCX/XLSX source files
  -> POST /jobs
  -> /jobs/:jobId
      -> poll until RESULT_READY or FAILED
      -> download output.pptx
```
