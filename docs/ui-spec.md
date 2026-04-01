# UI 명세서: Prompt-to-PPT Enterprise Builder

| 항목 | 내용 |
|------|------|
| 버전 | v0.1 |
| 작성일 | 2026-03-17 |
| 프레임워크 | React 18 |
| 상태관리 | Zustand (또는 React Context) |
| 라우팅 | React Router v6 |
| UI 라이브러리 | Tailwind CSS |
| HTTP 클라이언트 | Axios |

---

## 1. 전체 페이지 라우팅

```
/upload             → UploadPage        (메인 진입점)
/jobs/:jobId        → JobStatusPage
/history            → HistoryPage
```

### 라우팅 규칙

- `/` 접근 시 → `/upload` 리다이렉트
- 존재하지 않는 경로 → 404 컴포넌트 표시

---

## 2. 페이지별 상세 명세

---

### 2.1 UploadPage (`/upload`)

#### 목적
템플릿 PPT + 콘텐츠 파일 업로드 및 생성 옵션 입력 후 Job 생성

#### 컴포넌트 트리
```
UploadPage
├── Header (공통)
├── UploadSection
│   ├── TemplateFileDropzone
│   │   ├── FileIcon
│   │   ├── FileNameLabel (파일 선택 후)
│   │   └── RemoveFileButton (파일 선택 후)
│   └── ContentFileDropzone
│       ├── FileIcon
│       ├── FileNameLabel (파일 선택 후)
│       └── RemoveFileButton (파일 선택 후)
├── OptionsSection
│   ├── ToneSelector       (radio: 경영진용 | 공식적 | 간결)
│   ├── TargetSelector     (radio: 경영진 | 팀 내부 | 고객/외부)
│   ├── LengthSelector     (radio: 5 | 10 | 15)
│   ├── AiEngineSelector   (radio: Bedrock (보안 모드) | OpenAI (창의 모드))
│   └── NotesTextarea      (optional)
├── SubmitButton
├── UploadProgressBar (조건부)
└── ErrorMessage (조건부)
```

#### 상태 (State)
| 상태명 | 타입 | 초기값 | 설명 |
|--------|------|--------|------|
| `templateFile` | File \| null | `null` | 선택된 템플릿 PPT |
| `contentFile` | File \| null | `null` | 선택된 Word/Excel (택1) |
| `tone` | string | `"공식적"` | 문체 옵션 |
| `target` | string | `"팀 내부"` | 대상 독자 |
| `length` | number | `10` | 슬라이드 수 |
| `notes` | string | `""` | 추가 지시사항 |
| `aiEngine` | string | `"bedrock"` | AI 엔진 선택 (`"bedrock"` \| `"openai"`) |
| `uploadProgress` | number | `0` | 업로드 진행률 (0~100) |
| `isSubmitting` | boolean | `false` | Job 생성 요청 중 |
| `errorMessage` | string \| null | `null` | 에러 메시지 |

#### 이벤트 / 동작
| 이벤트 | 동작 |
|--------|------|
| 파일 드래그&드롭 또는 클릭 선택 | 파일 유효성 검사 후 state 저장 |
| SubmitButton 클릭 | 업로드 → Job 생성 → `/jobs/:jobId` 이동 |
| RemoveFileButton 클릭 | 해당 파일 state 초기화 |

#### 파일 유효성 검사
| 파일 | 허용 확장자 | 최대 크기 |
|------|------------|----------|
| templateFile | `.pptx` | 50MB |
| contentFile | `.docx`, `.xlsx` | 50MB |

#### API 연동 순서 (Submit 시)
```
1. POST /jobs/upload-url  (templateFile용 Presigned URL 요청)
2. PUT {uploadUrl}        (S3에 templateFile 직접 업로드)
3. POST /jobs/upload-url  (contentFile용 Presigned URL 요청)
4. PUT {uploadUrl}        (S3에 contentFile 직접 업로드)
5. POST /jobs            (Job 생성 요청)
6. 응답의 jobId로 /jobs/:jobId 이동
```

#### UX 규칙
- 두 파일 모두 선택해야 Submit 버튼 활성화
- 업로드 중 진행률 바 표시
- 업로드 중 버튼 비활성화
- 파일 크기 초과 시 즉시 에러 표시 (서버 요청 없이 클라이언트 검사)

---

### 2.2 JobStatusPage (`/jobs/:jobId`)

#### 목적
Job 처리 상태를 실시간으로 표시하고, 완료 시 결과 PPT 다운로드 제공

#### 컴포넌트 트리
```
JobStatusPage
├── Header (공통)
├── StatusCard
│   ├── JobIdLabel
│   ├── StatusBadge         (PENDING | RUNNING | SUCCEEDED | FAILED)
│   ├── CreatedAtLabel
│   ├── UpdatedAtLabel
│   ├── ProgressAnimation   (PENDING | RUNNING 시)
│   ├── DownloadButton      (SUCCEEDED 시)
│   ├── ErrorBox            (FAILED 시)
│   └── RetryButton         (FAILED 시, /upload로 이동)
└── BackToHistoryLink
```

#### 상태 (State)
| 상태명 | 타입 | 초기값 | 설명 |
|--------|------|--------|------|
| `job` | JobResponse \| null | `null` | Job 상세 정보 |
| `isLoading` | boolean | `true` | 초기 로딩 |
| `errorMessage` | string \| null | `null` | 조회 에러 |

#### JobResponse 타입
```typescript
interface JobResponse {
  jobId: string;
  status: "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED";
  createdAt: string;       // ISO8601
  updatedAt: string;       // ISO8601
  errorMessage?: string;   // FAILED 시
  resultUrl?: string;      // SUCCEEDED 시, Presigned URL
}
```

#### 폴링 로직
| 조건 | 동작 |
|------|------|
| status = PENDING \| RUNNING | 3초마다 `GET /jobs/:jobId` 호출 |
| status = SUCCEEDED \| FAILED | 폴링 중지 |
| 페이지 언마운트 | 폴링 중지 (cleanup) |

#### API 연동
- `GET /jobs/:jobId`

#### UX 규칙
- PENDING: "PPT 생성을 준비하고 있습니다..." + 애니메이션
- RUNNING: "슬라이드를 생성하고 있습니다..." + 프로그레스 애니메이션
- SUCCEEDED: 다운로드 버튼 표시 (resultUrl은 Presigned URL, 직접 링크)
- FAILED: 에러 메시지 + "다시 시도하기" 버튼 (/upload 이동)
- 탭을 벗어났다 돌아와도 폴링 재개

---

### 2.3 HistoryPage (`/history`)

#### 목적
전체 Job 목록 조회

#### 컴포넌트 트리
```
HistoryPage
├── Header (공통)
├── JobListTable
│   ├── TableHeader
│   └── JobListRow (반복)
│       ├── JobIdCell
│       ├── StatusBadge
│       ├── CreatedAtCell
│       ├── ActionCell
│       │   ├── ViewButton    → /jobs/:jobId 이동
│       │   └── DownloadButton (SUCCEEDED 시)
└── EmptyState (Job 없을 때)
```

#### 상태 (State)
| 상태명 | 타입 | 초기값 | 설명 |
|--------|------|--------|------|
| `jobs` | JobSummary[] | `[]` | Job 목록 |
| `isLoading` | boolean | `true` | 목록 로딩 중 |
| `errorMessage` | string \| null | `null` | 조회 에러 |

#### JobSummary 타입
```typescript
interface JobSummary {
  jobId: string;
  status: "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED";
  createdAt: string;
  updatedAt: string;
}
```

#### API 연동
- `GET /jobs` → `X-Session-Token` 헤더 기준으로 **내 Job만** 조회 (DynamoDB FilterExpression, 최신순 정렬)

#### UX 규칙
- createdAt 기준 최신순 정렬
- 빈 목록이면 "아직 생성된 PPT가 없습니다. 지금 만들어보세요!" + /upload 링크
- SUCCEEDED Job의 DownloadButton 클릭 → GET /jobs/:jobId로 resultUrl 조회 후 다운로드

---

## 3. 공통 컴포넌트

### 3.1 Header
```
Header
├── Logo (클릭 시 /upload)
├── NavLinks
│   ├── "새 PPT 만들기" → /upload
│   └── "히스토리" → /history
```

### 3.2 StatusBadge
| status 값 | 색상 | 표시 텍스트 |
|-----------|------|------------|
| PENDING | 회색 | 대기 중 |
| RUNNING | 파란색 | 생성 중 |
| SUCCEEDED | 초록색 | 완료 |
| FAILED | 빨간색 | 실패 |

### 3.3 LoadingSpinner
- 범용 로딩 인디케이터
- size props: `sm` | `md` | `lg`

### 3.4 ErrorMessage
- 빨간색 박스 + 아이콘
- `message` props 필수

---

## 4. 전역 상태관리 설계 (Zustand 기준)

```typescript
// sessionStore — 앱 최초 마운트 시 초기화
interface SessionStore {
  sessionToken: string;  // localStorage에서 읽거나 최초 생성
}

// 초기화 로직 (App.tsx 등 최상위에서 1회 실행)
const token = localStorage.getItem("sessionToken") ?? (() => {
  const t = crypto.randomUUID();
  localStorage.setItem("sessionToken", t);
  return t;
})();

// jobStore (UploadPage → JobStatusPage 간 jobId 전달용)
interface JobStore {
  currentJobId: string | null;
  setCurrentJobId: (id: string) => void;
}
```

> **모든 API 요청**에 `X-Session-Token: {sessionToken}` 헤더를 자동 포함한다.

---

## 5. API 공통 설정

```typescript
// api.ts
const axiosInstance = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL,
});

// 모든 요청에 X-Session-Token 자동 주입
axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem("sessionToken");
  if (token) config.headers["X-Session-Token"] = token;
  return config;
});
```

---

## 6. 환경변수 목록 (`.env`)

```
REACT_APP_API_BASE_URL=https://{api-gateway-id}.execute-api.{region}.amazonaws.com/prod
REACT_APP_S3_REGION=ap-northeast-2
```

---

## 7. DesignDoc 대비 추가 필요한 API

| 추가 API | 설명 |
|---------|------|
| `GET /jobs` | 사용자 Job 목록 조회 (HistoryPage용) |

---

## 8. 미결 사항 (Open Questions)

| # | 질문 | 상태 |
|---|------|------|
| 1 | UI 라이브러리 확정 | ✅ Tailwind CSS |
| 2 | HistoryPage Job 목록 페이지네이션 필요 여부 | ⬜ 미결 (N4 참고) |
| 3 | 모바일 반응형 지원 여부 | ⬜ 미결 |
| 4 | 다운로드 후 Presigned URL 만료 시 재발급 플로우 | ⬜ 미결 (open-questions N4 참고) |
| 5 | AI 엔진 선택 UI 위치·컴포넌트 형태 | ⬜ 미결 (open-questions N2 참고) |
