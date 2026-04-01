# Design Document: Prompt-to-PPT Enterprise Builder

| 항목 | 내용 |
|------|------|
| 작성자 | 최정겸 |
| 버전 | v0.1 (Draft) |
| 작성일 | 2026-03-26 |
| 상태 | ? Draft |

---

## 1. 개요 (TL;DR)

사용자가 **회사 템플릿 PPT**와 **Word/Excel 기반 콘텐츠 파일**을 업로드하고 생성 목적을 입력하면,  
시스템이 **회사 템플릿 스타일을 유지한 PPT를 자동 생성**하는 엔터프라이즈 플랫폼이다.

핵심 기술 스택: `React` · `AWS Amplify` · `API Gateway + Lambda` · `Step Functions` · `ECS Fargate` · `Amazon Bedrock Converse API` · `S3` · `DynamoDB`

---

## 2. 배경 및 동기 (Background / Problem Statement)

### 2.1 문제

- 기업 실무에서 PPT 보고서 작성은 반복적이고 시간 소모가 크다.
- 기존 AI 요약 도구는 회사 템플릿 스타일을 유지하지 못한다.
- Word/Excel 원본 데이터를 PPT로 변환하는 과정에 수작업이 많다.

### 2.2 해결 방향

- 템플릿 구조를 파싱해 레이아웃·스타일 규칙을 추출한다.
- Bedrock Converse API로 슬라이드 아웃라인과 본문을 생성한다.
- python-pptx로 템플릿 스타일을 유지한 최종 PPT를 렌더링한다.

---

## 3. 목표 / 비목표 (Goals / Non-Goals)

### ? Goals (MVP 범위)

- [ ] 회사 템플릿 PPT 1종 지원    
- [ ] Word / Excel 파일 1개 입력 지원
- [ ] 5~10장 슬라이드 자동 생성
- [ ] 텍스트 + 차트 중심 렌더링
- [ ] Bedrock 2단계 생성 (아웃라인 → 본문)
- [ ] Job 상태 추적 (PENDING → RUNNING → SUCCEEDED / FAILED)
- [ ] 결과 PPT S3 다운로드

### ? Non-Goals (이번 범위 외)

- 다중 템플릿 지원
- 실시간 협업 편집
- 슬라이드 웹 미리보기
- Knowledge Bases / RAG 연동
- 한국어 이외 언어 최적화

---

## 4. 시스템 설계 (Design)

### 4.1 전체 아키텍처 다이어그램

```text
[React Web (AWS Amplify)]
 ├─ GitHub CI/CD 자동 배포
 ├─ S3 Presigned URL 직접 업로드
 └─ API Gateway 호출
        │
        ▼
[Lambda API Layer]
 ├─ Job 생성
 ├─ DynamoDB 상태 기록 (PENDING)
 └─ Step Functions 실행
        │
        ▼
[Step Functions Standard Workflow]
 └─ ECS Fargate Worker 실행 (.sync)
        │
        ▼
[AWS Secrets Manager] <── [외부 API Key 보안 인출]
        │
        ▼
[ECS Fargate Worker]
 └── PipelineOrchestrator
       ├─ [1] DocumentParserAgent
       │     S3에서 template.pptx / content.docx or .xlsx 다운로드
       │     → templateRules (레이아웃·플레이스홀더·색상·폰트) 추출
       │     → contentSummary (섹션·표·숫자 데이터) 추출
       │
       ├─ [2] OutlineAgent  ← LLM 호출 (Bedrock or OpenAI)
       │     입력: templateRules + contentSummary + userOptions
       │     출력: SlideOutline JSON
       │       { slides: [{ index, title, type, purpose }] }
       │     * type = chart는 Excel 입력 있을 때만 허용
       │
       ├─ [3] SlideWriterAgent  ← LLM 루프 (슬라이드별 개별 호출)
       │     입력: 슬라이드별 outline + 관련 원본 텍스트/숫자
       │     출력: SlideContent JSON
       │       { title, bullets[], chartCaption?, speakerNote? }
       │     * Prompt Caching: 시스템 프롬프트 prefix 재사용
       │
       ├─ [4] ReviewAgent  ← LLM 호출 (품질 검수 + 루프 제어)
       │     입력: 전체 SlideContent + 원본 contentSummary
       │     출력: ReviewResult JSON
       │       { approved: bool, issues: [{ slideIndex, reason }] }
       │     ┌─ approved: true  → 다음 단계 진행
       │     └─ approved: false → SlideWriterAgent로 재진입
       │           (문제 슬라이드만 재생성, 최대 2회 재시도)
       │
       ├─ [5] ChartRendererAgent  (Excel 입력 있을 때만 실행)
       │     입력: Excel 원본 숫자 + SlideContent.chartCaption
       │     출력: 차트 이미지 파일 (matplotlib → PNG)
       │
       ├─ [6] PPTBuilderAgent
       │     입력: templateRules + SlideContent[] + 차트 이미지
       │     출력: output.pptx (python-pptx 플레이스홀더 기반 렌더링)
       │
       └─ [7] ResultUploader
             S3 results/{jobId}/output.pptx 업로드
             S3 temp/{jobId}/outline.json, slides_draft.json 저장
             DynamoDB 상태 → SUCCEEDED / FAILED
        │
        ▼
[S3 Results]
 └─ 사용자 Presigned URL 다운로드
```

### ReviewAgent 루프 흐름

```
OutlineAgent
    ↓
SlideWriterAgent ──────────────────────┐
    ↓                                  │ 재시도 (문제 슬라이드만)
ReviewAgent                            │
    ├─ approved → ChartRenderer → PPTBuilder
    └─ rejected (최대 2회) ────────────┘
         2회 초과 시 → 현재 결과로 강제 진행 (품질 경고 포함)
```

### 4.2 컴포넌트별 역할 요약

| 컴포넌트 | 역할 |
|---------|------|
| React (AWS Amplify) | 파일 업로드, 옵션 입력, 상태 조회, 결과 다운로드 UI 제공 및 CI/CD 자동 배포 |
| API Gateway + Lambda | 얇은 API 계층 (Job 생성, 상태 조회, Presigned URL 발급) |
| Step Functions | Fargate 태스크 실행 오케스트레이션 (.sync 패턴) |
| ECS Fargate Worker | Agent 파이프라인 오케스트레이터 — 하위 Agent들을 순서대로 실행·제어 |
| ↳ DocumentParserAgent | template.pptx 마스터 구조 + Word/Excel 콘텐츠 파싱 |
| ↳ OutlineAgent | LLM 호출 → 슬라이드 구조(제목·타입·목적) JSON 생성 |
| ↳ SlideWriterAgent | LLM 루프 → 슬라이드별 본문(bullets·캡션·메모) 생성 |
| ↳ ReviewAgent | LLM 호출 → 전체 품질 검수, 문제 슬라이드 재생성 루프 제어 (최대 2회) |
| ↳ ChartRendererAgent | Excel 원본 숫자 → matplotlib PNG 차트 (Excel 입력 시만 실행) |
| ↳ PPTBuilderAgent | python-pptx 플레이스홀더 기반 최종 PPT 렌더링 |
| Amazon Bedrock | 보안 모드 LLM 추론 (Claude 3.5, Nova 등) |
| 외부 상용 AI API | 창의 모드 LLM 추론 (OpenAI 등, 사용자 선택 시) |
| AWS Secrets Manager | 외부 상용 AI API Key 암호화 보관 및 런타임 제공 |
| Bedrock Guardrails | 콘텐츠 정책 필터 (입력/출력 모두) |
| S3 | 업로드 파일 저장 / 결과 PPT 저장 |
| DynamoDB | Job 상태 관리 |

---

### 4.3 API 명세 (API Gateway -> Lambda)

### 4.3.0 Client-side UUID 전략 및 병렬 업로드 흐름 (핵심)
* 대용량 파일 다중 업로드를 효율적이고 안전하게 처리하기 위해, 서버가 아닌 **프론트엔드(Client)에서 직접 UUID v4를 주도적으로 생성**하여 `jobId`로 할당합니다.
* **업로드 및 Job 생성 파이프라인 정리:**
  1. **UUID 할당**: 클라이언트가 고유한 `jobId`(UUID v4)를 생성.
  2. **업로드 URL 요청 (병렬)**: 여러 파일(템플릿, 본문 등) 각각에 대해 S3 Presigned URL 발급 (`POST /jobs/upload-url`에 `jobId` 포함) 요청.
  3. **브라우저 → S3 직배송 (병렬)**: 서버(Lambda/API Gateway)를 거치지 않고, 발급받은 URL을 통해 브라우저에서 S3로 직접 파일 덩어리를 병렬로 전송하여 서버 부하 및 타임아웃을 원천 차단.
  4. **Job 생성 위임**: 모든 S3 업로드가 완료되면, 최종적으로 `POST /jobs`를 호출하여 비동기 처리(Step Functions)를 백엔드에 위임하고, 클라이언트는 해당 `jobId`로 상태 폴링 시작.

### 4.3.1 Presigned URL 발급

```
POST /jobs/upload-url

Request Body:
{
  "jobId": "string (UUID v4 from client)",
  "fileType": "template" | "content",
  "fileName": "string",
  "contentType": "application/vnd.openxmlformats-officedocument..."
}

Response:
{
  "uploadUrl": "https://s3.amazonaws.com/...",
  "s3Key": "uploads/{jobId}/{fileName}"
}
```

### 4.3.2 Job 생성

```
POST /jobs

Headers:
  X-Session-Token: {sessionToken}   ← localStorage에서 읽어 전송

Request Body:
{
  "jobId": "string (UUID v4 from client)",
  "templateS3Key": "uploads/{jobId}/template.pptx",
  "contentS3Key":  "uploads/{jobId}/content.docx",
  "options": {
    "tone":   "경영진용" | "공식적" | "간결",
    "target": "경영진" | "팀 내부" | "고객/외부",
    "length": 5 | 10 | 15,
    "notes":  "string (optional)",
    "aiEngine": "bedrock" | "openai"
  }
}

Response:
{
  "jobId": "string (UUID)",
  "status": "PENDING",
  "createdAt": "ISO8601"
}

Status Codes:
  202 Accepted   - Job 생성 성공, 비동기 처리 중
  400 Bad Request
  401 Unauthorized
```

#### 4.3.3 Job 상태 조회

```
GET /jobs/{jobId}

Headers:
  X-Session-Token: {sessionToken}

Response:
{
  "jobId": "string",
  "status": "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED",
  "createdAt": "ISO8601",
  "updatedAt": "ISO8601",
  "errorMessage": "string (FAILED 시만 포함)",
  "resultUrl":   "string (SUCCEEDED 시만 포함, Presigned URL)"
}
```

#### 4.3.4 Job 목록 조회 (히스토리)

```
GET /jobs

Headers:
  X-Session-Token: {sessionToken}   ← 이 토큰으로 DynamoDB FilterExpression 적용

Response:
{
  "jobs": [
    {
      "jobId": "string",
      "status": "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED",
      "createdAt": "ISO8601",
      "updatedAt": "ISO8601"
    }
  ]
}
```

> **구현 방식**: DynamoDB Scan + `FilterExpression: sessionToken = :token`, 결과는 `createdAt` 기준 최신순 정렬
```

---

### 4.4 데이터 모델

#### 4.4.1 DynamoDB: `ppt-jobs` 테이블

| 속성 | 타입 | 설명 |
|------|------|------|
| `jobId` (PK) | String | UUID |
| `sessionToken` | String | 브라우저 localStorage UUID (소유권 식별용) |
| `status` | String | PENDING / RUNNING / SUCCEEDED / FAILED |
| `templateS3Key` | String | S3 경로 |
| `contentS3Key` | String | S3 경로 |
| `resultS3Key` | String | 결과 PPT S3 경로 (완료 후) |
| `options` | Map | tone / target / length / notes / **aiEngine** |
| `errorMessage` | String | 실패 시 에러 메시지 |
| `createdAt` | String | ISO8601 |
| `updatedAt` | String | ISO8601 |
| `ttl` | Number | Epoch (자동 만료, 예: 30일) |

#### 4.4.2 S3 버킷 구조

```
{bucket}/
  uploads/
    {jobId}/
      template.pptx
      content.docx (or content.xlsx)
  results/
    {jobId}/
      output.pptx
  temp/
    {jobId}/
      outline.json        (아웃라인 생성 결과 중간 저장)
      slides_draft.json   (본문 생성 결과 중간 저장)
```

#### 4.4.3 Bedrock 내부 정규화 JSON 구조

```json
{
  "templateRules": {
    "layouts": ["title+content", "title+chart", "section-header"],
    "maxBullets": 4,
    "style": "formal",
    "colorTheme": "TBD (파싱 결과 기반)"
  },
  "contentSummary": {
    "title": "2026 Q1 사업보고",
    "sections": [
      {
        "title": "매출 현황",
        "summary": "전년 동기 대비 18% 증가",
        "dataType": "chart"
      }
    ]
  },
  "userOptions": {
    "tone": "경영진용",
    "target": "경영진",
    "length": 10,
    "notes": "",
    "aiEngine": "bedrock"
  }
}
```

---

### 4.5 Bedrock 호출 전략

#### 1단계: 아웃라인 생성

- **입력**: 템플릿 구조 요약 + 문서 요약 + 사용자 옵션
- **출력**: 슬라이드 수, 제목, 타입(`summary` / `text` / `chart`(Excel 입력 시만) / `table`), 목적
- **Prompt Caching 대상**: 슬라이드 작성 규칙, JSON 출력 스키마, 기업 문체 가이드

#### 2단계: 슬라이드 본문 생성 (슬라이드별 루프)

- **입력**: 슬라이드별 컨텍스트 + 관련 데이터 + 1단계 아웃라인
- **출력**: 제목, bullet 3~5개, 차트 캡션, 발표 메모(선택)
- **Prompt Caching 대상**: 회사 템플릿 규칙, 1단계 결과 prefix

#### (선택) 3단계: 문체 통일 후처리

- 10장 이상인 경우 전체 문체 통일 적용

---

## 5. 비기능 요구사항 (Non-Functional Requirements)

| 항목 | 목표값 | 비고 |
|------|--------|------|
| PPT 생성 소요 시간 | ≤ 3분 (10장 기준) | **TBD** - 실측 필요 |
| 동시 처리 Job 수 | ≥ 10 동시 | Fargate 태스크 수 제한 확인 필요 |
| 업로드 파일 최대 크기 | ≤ 50MB | S3 Presigned URL 제한 기준 |
| API 응답 시간 (Job 생성) | ≤ 1초 | Lambda cold start 포함 |
| 가용성 (SLA) | **TBD** | MVP에서는 단일 리전 |
| 결과 파일 보관 기간 | 30일 (TTL 기반 자동 삭제) | DynamoDB TTL + S3 Lifecycle |
| 지원 리전 | **TBD** | Bedrock 모델 지원 리전 확인 필요 |
| Job 상태 폴링 주기 | **3초** | 프론트엔드 HTTP 폴링 고정값 |

---

## 6. 장애 대응 설계 (Failure Handling)

### 6.1 Fargate 태스크 실패

- Step Functions `.sync` 패턴으로 태스크 실패를 즉시 감지
- Step Functions 재시도 정책: 최대 2회 재시도, Backoff 60초
- 최종 실패 시 DynamoDB 상태 → `FAILED` + 에러 메시지 기록

### 6.2 Bedrock 호출 실패

- Fargate Worker 내부에서 최대 3회 Retry (Exponential Backoff)
- Throttling (`ThrottlingException`) 시 별도 대기 후 재시도
- 최종 실패 시 Worker 자체를 실패로 종료 → Step Functions가 감지

### 6.3 S3 업로드/다운로드 실패

- boto3 기본 재시도 설정 활용 (max_attempts=3)
- 실패 시 Worker 종료 → DynamoDB `FAILED` 처리

### 6.4 Cold Start / 프로비저닝 지연

- Step Functions `.sync`가 태스크 시작까지 폴링하므로 Lambda 직접 호출보다 안전
- Fargate 태스크 시작 지연: 평균 10~30초 (실측 필요, **TBD**)

### 6.5 에러 메시지 노출 정책

실패 시 사용자 UI에는 **단계 정보 포함** 메시지를 표시한다.

| 실패 단계 | 사용자 표시 메시지 |
|-----------|------------------|
| 파일 파싱 실패 | 문서 파싱 중 오류가 발생했습니다. 파일 형식을 확인해주세요. |
| AI 모델 호출 실패 | AI 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. |
| PPT 렌더링 실패 | PPT 생성 중 오류가 발생했습니다. 다시 시도해주세요. |
| Guardrails 차단 | 입력 내용이 보안 정책에 의해 차단되었습니다. 내용을 수정 후 다시 시도해주세요. |
| 기타 알 수 없는 오류 | 처리 중 오류가 발생했습니다. 다시 시도해주세요. |

---

## 7. 보안 설계 (Security)

### 7.1 IAM 역할 최소 권한

| 역할 | 허용 권한 |
|------|----------|
| Lambda Role | `dynamodb:PutItem`, `dynamodb:GetItem`, `states:StartExecution`, `s3:GetObject` (업로드 경로만) |
| Fargate Task Role | `s3:GetObject` (uploads/), `s3:PutObject` (results/, temp/), `dynamodb:UpdateItem`, `bedrock:InvokeModel` |
| Step Functions Role | `ecs:RunTask`, `iam:PassRole` (Fargate Task Role에 한정) |
| Fargate Execution Role | `ecr:GetAuthorizationToken`, `ecr:BatchGetImage`, `logs:CreateLogStream`, `logs:PutLogEvents` |

### 7.2 데이터 보호

- S3 버킷: SSE-S3 또는 SSE-KMS 암호화 적용
- S3 퍼블릭 액세스 완전 차단, Presigned URL로만 접근
- DynamoDB: AWS 관리형 암호화 기본 적용
- Bedrock: 입력 문서를 저장하지 않음 (AWS 공식 문서 기준)

### 7.3 Guardrails 정책

- 콘텐츠 필터: 혐오/폭력/불법 콘텐츠 차단
- 민감 정보 필터: 주민번호·카드번호 등 PII 마스킹
- 금지 주제: **TBD** (프로젝트 성격에 맞게 정의 필요)

---

## 8. 비용 추정 (Cost Estimate)

> ?? 아래는 **MVP 기준 개략 추정**이며, 실제 사용량에 따라 크게 달라질 수 있음.

| 서비스 | 기준 | 월 예상 비용 |
|--------|------|-------------|
| ECS Fargate | 10장 PPT 1건 ? 2vCPU·4GB·3분, 월 500건 | **TBD** (실측 필요) |
| Amazon Bedrock | 모델·토큰 수에 따라 상이 | **TBD** (모델 선정 후 산출) |
| Lambda | 월 500건 × 1초 × 256MB | < $1 (무료 티어 범위) |
| Step Functions | Standard Workflow, 월 500건 | < $1 |
| S3 | 업로드 + 결과 저장, 30일 보관 | **TBD** (파일 크기 실측 후) |
| DynamoDB | On-Demand, 월 500건 | < $1 |
| API Gateway | 월 10,000 요청 기준 | < $1 |
| **합계** | | **TBD** |

> ? **가장 큰 비용 요인**: Bedrock 토큰 비용 + Fargate 실행 시간  
> 모델 선정 및 평균 토큰 수 실측 후 재산출 필요.

---

## 9. 대안 검토 (Alternatives Considered)

### 9.1 Step Functions vs. 직접 Lambda → ECS RunTask 호출

| 항목 | Step Functions | Lambda 직접 호출 |
|------|---------------|----------------|
| 태스크 실패 감지 | `.sync` 패턴으로 즉시 감지 | Polling 로직 직접 구현 필요 |
| 재시도 정책 | 워크플로 수준에서 선언적 설정 | 코드 내 수동 구현 |
| 실행 가시성 | AWS 콘솔에서 상태 추적 가능 | CloudWatch 로그만 의존 |
| 복잡도 | 상태 머신 정의 필요 | 상대적으로 간단 |
| **결론** | ? 채택 | ? 실패 감지 취약 |

### 9.2 ECS Fargate vs. Lambda (PPT 생성 로직)

| 항목 | ECS Fargate | Lambda |
|------|-------------|--------|
| 실행 시간 제한 | 없음 | 최대 15분 |
| 메모리 | 최대 120GB | 최대 10GB |
| 라이브러리 크기 | 제한 없음 | 레이어 포함 250MB |
| 콜드 스타트 | 10~30초 | 수백ms~수초 |
| **결론** | ? 채택 (무거운 라이브러리·긴 실행) | ? 제한 도달 가능성 |

### 9.3 Bedrock Converse API vs. 직접 InvokeModel

| 항목 | Converse API | InvokeModel |
|------|-------------|-------------|
| 모델별 포맷 차이 | 공통 인터페이스 | 모델마다 별도 JSON |
| 모델 교체 용이성 | 높음 | 낮음 (코드 수정 필요) |
| Guardrails 통합 | 기본 지원 | 별도 처리 |
| **결론** | ? 채택 | ? 유지보수 불리 |

---

## 10. 배포 전략 (Deployment Strategy)

### 10.1 인프라 구성 도구

- **TBD**: Terraform 또는 AWS CDK 중 선택 필요

### 10.2 배포 흐름 (MVP)

```
1. ECR에 Fargate Worker 이미지 Push
2. ECS 태스크 정의 업데이트
3. Lambda 함수 배포
4. Step Functions 상태 머신 업데이트
5. API Gateway 배포
6. React 빌드 → S3 + CloudFront 배포
```

### 10.3 롤백 전략

- Lambda: 버전 관리 + 이전 버전 즉시 전환
- ECS 태스크 정의: 이전 리비전으로 Step Functions 수정
- React: S3 이전 버전 파일 복원
- Blue/Green 배포: **TBD** (MVP 이후 적용 검토)

---

## 11. 운영 가시성 (Observability)

### 11.1 CloudWatch 메트릭 (권장)

| 메트릭 | 설명 |
|--------|------|
| `JobSuccessRate` | 성공 Job 수 / 전체 Job 수 |
| `JobDuration` | Fargate 태스크 실행 시간 (p50, p95) |
| `BedrockLatency` | Bedrock API 응답 시간 |
| `FargateTaskFailureCount` | Fargate 태스크 실패 건수 |

### 11.2 알람 기준 (TBD)

- `JobSuccessRate` < 95% → SNS 알림
- `JobDuration` p95 > 5분 → 조사 트리거
- `FargateTaskFailureCount` > 5건/시간 → 즉시 알림

### 11.3 로그 전략

- Fargate Worker: CloudWatch Logs (`/ecs/ppt-worker`)
- Lambda: CloudWatch Logs (`/aws/lambda/ppt-api`)
- 로그 보존 기간: **TBD** (권장: 30일)

---

## 12. 마일스톤 (Milestones)

| 단계 | 내용 | 상태 |
|------|------|------|
| M1 | 아키텍처 설계 확정 + 인프라 초기 구성 | ? 진행 중 |
| M2 | Fargate Worker MVP (파싱 + Bedrock 호출 + PPT 생성) | ? 미시작 |
| M3 | Lambda API + Step Functions 연동 | ? 미시작 |
| M4 | React UI 연동 + E2E 테스트 | ? 미시작 |
| M5 | Guardrails + 보안 점검 | ? 미시작 |
| M6 | 공모전 데모 최종 준비 | ? 미시작 |

---

## 13. 미해결 사항 (Open Questions)

| # | 질문 | 담당 | 기한 |
|---|------|------|------|
| 1 | 사용할 Bedrock 모델 ID 확정 (리전 지원 여부 포함) | TBD | TBD |
| 2 | 배포 리전 확정 | TBD | TBD |
| 3 | 인프라 구성 도구 확정 (Terraform vs CDK) | TBD | TBD |
| 4 | Guardrails 금지 주제 목록 정의 | TBD | TBD |
| 5 | Fargate 태스크 평균 실행 시간 실측 | TBD | M2 이후 |
| 6 | Bedrock 평균 토큰 수 실측 → 비용 재산출 | TBD | M2 이후 |
| 7 | Guardrails 차단 시 사용자 노출 메시지 정의 | TBD | M5 이전 |
| 8 | 손상된 업로드 파일 처리 방식 | TBD | M2 이전 |
| 9 | SLA 목표값 확정 | TBD | TBD |

---

## 14. 참고 자료 (References)

- [Amazon Bedrock Converse API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)
- [Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-how.html)
- [Bedrock Prompt Caching](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)
- [Step Functions - ECS Integration (.sync)](https://docs.aws.amazon.com/step-functions/latest/dg/connect-ecs.html)
- [ECS RunTask API](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_RunTask.html)
- [AWS Fargate](https://docs.amazonaws.cn/en_us/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [aws-ecs-stepfunctions-synchronous-runtask (GitHub Sample)](https://github.com/aws-samples/aws-ecs-stepfunctions-synchronous-runtask)

---

## 부록. AWS 서비스 채택 근거

### Frontend
**AWS Amplify Hosting** — GitHub 연동 CI/CD 자동 배포. 초기 트래픽 적을 때 프리 티어로 비용 최소화.

### AI/LLM
**Amazon Bedrock** — 여러 모델을 단일 Converse API로 호출, 기업 문서 보안성 확보 (입력 데이터 미저장).  
**Bedrock Guardrails** — 입출력 정책 필터. PII 마스킹, 콘텐츠 필터 적용.  
**외부 상용 AI (OpenAI 등, MVP 포함)** — 사용자 선택형 멀티 벤더. API Key는 Secrets Manager 런타임 인출.

### Backend
**AWS Lambda** — 가벼운 API 진입 계층(Job 생성·상태 조회·Presigned URL 발급)만 담당, 서버 운영 불필요.  
**AWS Step Functions** — Fargate Task `.sync` 패턴으로 실패 즉시 감지, 재시도 정책 선언적 설정.  
**Amazon ECS Fargate** — python-pptx/python-docx/matplotlib 등 무거운 라이브러리·긴 실행 시간 처리. Lambda 15분 제한 회피.

### Storage / DB
**Amazon S3** — 업로드 원본·결과 PPT·중간 산출물 저장. Presigned URL로 프론트 직접 연동.  
**Amazon DynamoDB** — Job 상태(PENDING→RUNNING→SUCCEEDED/FAILED) + sessionToken 기반 소유권 관리.  
**AWS Secrets Manager** — OpenAI 모드 선택 시만 런타임 인출. Bedrock 모드에서는 조회 없음.
