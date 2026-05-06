# Design Document: Prompt-to-PPT Enterprise Builder

| 항목 | 내용 |
|---|---|
| 작성자 | 최정경 |
| 버전 | v0.3 |
| 작성일 | 2026-05-02 |
| 상태 | Draft |

---

## 1. 개요

Prompt-to-PPT Enterprise Builder는 사용자가 PowerPoint 템플릿과 하나 이상의 Word/Excel 기반 콘텐츠 파일을 업로드하면, 템플릿 스타일을 유지한 발표 자료를 자동으로 생성하는 서비스다.

현재 프로젝트는 다음 두 가지 흐름을 함께 지원한다.

- 일반 생성 흐름: 사용자가 직접 `pptx + docx/xlsx 복수 파일`을 업로드해서 Job을 생성
- 데모 흐름: 업로드 없이 `Try Demo PPT` 버튼으로 내장 샘플 자산을 사용해 즉시 결과 PPT를 생성

---

## 2. 목표

### 2.1 MVP 목표

- 템플릿 PPT 1종 업로드 지원
- 콘텐츠 파일 복수 업로드 지원 (`docx`, `xlsx`, 최대 10개)
- Job 생성, 상태 추적, 결과 다운로드 UI 제공
- AWS 상에서 비동기 파이프라인 실행
- 데모 모드에서 업로드 없이 샘플 PPT 즉시 생성

### 2.2 비목표

- 다중 템플릿 동시 비교
- 실시간 공동 편집
- 슬라이드 단위 시각 편집기
- 완성된 RAG/Knowledge Base 연동
- 다국어 최적화

---

## 3. 현재 아키텍처 요약

### 3.1 프론트엔드

- React + Vite + Tailwind CSS
- Zustand 기반 상태 관리
- AWS Amplify Hosting으로 배포
- GitHub 브랜치 기반 자동 배포

### 3.2 백엔드

- API Gateway + Lambda
- S3 Presigned URL 발급
- DynamoDB Job 저장 및 상태 관리
- Step Functions를 통한 워커 실행

### 3.3 워커

- ECS Fargate 기반 Python 워커
- 현재 구현 상태:
  - 업로드된 템플릿 PPT의 실제 슬라이드와 텍스트 shape 구조 파싱
  - 업로드된 Word/Excel 콘텐츠 복수 파일 파싱
  - DOCX heading/table/report 구조 요약
  - XLSX workbook/sheet/table/chart/formula-aware 요약
  - LLM 기반 템플릿 변환 계획 생성
  - shape별 fit hint 기반 짧은 replacement 유도
  - 템플릿 슬라이드에 LLM 결과를 in-place 치환
  - PPT 구조 QA 및 선택적 렌더 smoke test
  - ReviewAgent 기반 후처리 QA
  - 결과 PPT 업로드 및 다운로드 URL 연결

---

## 4. 전체 흐름

```text
[React Web / Amplify]
  -> API Gateway
  -> Lambda
      -> S3 Presigned URL 발급
      -> DynamoDB에 Job 저장
      -> Step Functions 실행
          -> ECS Fargate Worker 실행
              -> 문서 파싱
              -> LLM 템플릿 변환
              -> PPT 치환 빌드
              -> PPT 검증 및 후처리 QA
              -> 결과 업로드
  -> 결과 상태 조회
  -> 결과 PPT 다운로드
```

---

## 5. Job 처리 흐름

### 5.1 일반 업로드 흐름

1. 프론트가 `jobId`를 생성한다.
2. 프론트가 `POST /jobs/upload-url`로 업로드 URL을 요청한다.
3. 브라우저가 S3에 템플릿과 하나 이상의 콘텐츠 파일을 직접 업로드한다.
4. 프론트가 `POST /jobs`로 Job을 생성한다.
5. Lambda가 DynamoDB에 `PENDING` 상태를 기록한다.
6. Lambda가 Step Functions를 시작한다.
7. Step Functions가 ECS Fargate 워커를 실행한다.
8. 워커가 템플릿 PPT와 모든 콘텐츠 문서를 파싱한다.
9. LLM이 템플릿의 각 텍스트 shape에 들어갈 새 문구와 Excel chart/table update intent를 생성한다.
10. 워커가 기존 템플릿 슬라이드의 shape를 직접 치환해 결과 PPT를 만든다.
11. 워커가 PPT 구조 QA, 선택적 렌더 smoke test, 후처리 QA를 수행한다.
12. 프론트가 `GET /jobs/{jobId}`를 폴링하며 상태를 표시하고 완료 시 다운로드한다.

### 5.2 데모 흐름

1. 사용자가 `Try Demo PPT` 버튼을 누른다.
2. 프론트가 `POST /jobs`에 `demoPreset: "excel"`을 포함해 요청한다.
3. Lambda가 `backend/demo_assets/`의 샘플 파일을 S3에 배치한다.
4. Lambda가 워커를 거치지 않고 데모 결과 PPT를 즉시 연결한다.
5. Job 상태를 `SUCCEEDED`로 저장하고 `resultS3Key`를 기록한다.
6. 프론트는 상태 페이지로 이동하고 즉시 다운로드 가능한 결과 URL을 받는다.

---

## 6. 주요 API

### 6.1 업로드 URL 발급

`POST /jobs/upload-url`

요청 예시:

```json
{
  "jobId": "uuid",
  "fileType": "template",
  "fileName": "template.pptx",
  "contentType": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
}
```

콘텐츠 파일을 여러 개 올릴 때는 `fileIndex`를 사용한다. `fileIndex`는 0부터 시작하며 S3 key는 `content-01`, `content-02`처럼 안정적으로 생성된다.

```json
{
  "jobId": "uuid",
  "fileType": "content",
  "fileName": "metrics.xlsx",
  "fileIndex": 1,
  "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}
```

응답 예시:

```json
{
  "uploadUrl": "https://...",
  "s3Key": "uploads/{jobId}/template.pptx"
}
```

### 6.2 Job 생성

`POST /jobs`

일반 요청 예시:

```json
{
  "jobId": "uuid",
  "templateS3Key": "uploads/{jobId}/template.pptx",
  "contentS3Keys": [
    "uploads/{jobId}/content-01.docx",
    "uploads/{jobId}/content-02.xlsx"
  ],
  "options": {
    "tone": "공식적",
    "target": "팀 내부",
    "length": 10,
    "notes": "",
    "aiEngine": "bedrock"
  }
}
```

`contentS3Key` 단일 필드는 기존 호환성을 위해 유지된다. 새 클라이언트는 `contentS3Keys` 배열을 사용한다.

데모 요청 예시:

```json
{
  "jobId": "uuid",
  "demoPreset": "excel",
  "options": {
    "tone": "공식적",
    "target": "팀 내부",
    "length": 10,
    "notes": "",
    "aiEngine": "bedrock"
  }
}
```

### 6.3 Job 상태 조회

`GET /jobs/{jobId}`

응답 예시:

```json
{
  "jobId": "uuid",
  "status": "SUCCEEDED",
  "createdAt": "2026-04-01T12:41:36Z",
  "updatedAt": "2026-04-01T12:41:36Z",
  "pipelineStage": "DEMO_RESULT_READY",
  "resultUrl": "https://..."
}
```

### 6.4 Job 목록 조회

`GET /jobs`

세션 토큰 기준으로 사용자 Job 목록을 반환한다.

---

## 7. 인증 및 세션 전략

- 별도 로그인 없이 브라우저 `localStorage`에 `sessionToken`을 저장한다.
- 모든 API 요청은 `X-Session-Token` 헤더를 포함한다.
- Lambda는 이 토큰을 기준으로 Job 소유권을 구분한다.

### CORS 주의사항

브라우저 기반 호출에서는 `X-Session-Token`이 preflight 대상 헤더이므로, API Gateway CORS 허용 헤더에 반드시 포함되어야 한다.

현재 허용 헤더 설정의 기준 파일은 다음과 같다.

- `infra/infra/infra_stack.py`

이 설정이 빠지면 브라우저에서는 실제 백엔드가 정상이어도 `Network Error`로 보일 수 있다.

---

## 8. 데이터 모델

### 8.1 DynamoDB `ppt-jobs`

주요 속성:

- `jobId` (PK)
- `sessionToken`
- `status`
- `templateS3Key`
- `contentS3Key`
- `contentS3Keys`
- `resultS3Key`
- `pipelineStage`
- `options`
- `errorMessage`
- `createdAt`
- `updatedAt`
- `ttl`

### 8.2 S3 구조

```text
uploads/{jobId}/template.pptx
uploads/{jobId}/content-01.docx
uploads/{jobId}/content-02.xlsx
results/{jobId}/output.pptx
temp/{jobId}/parsed_document.json
temp/{jobId}/deck_transform_plan.json
temp/{jobId}/ppt_validation.json
temp/{jobId}/review_report.json
```

### 8.3 데모 자산

```text
backend/demo_assets/
  demo_template.pptx
  demo_content.xlsx
  demo_result.pptx
```

---

## 9. 워커 파이프라인

### 9.1 현재 단계

1. Document Parser
2. LLM Template Transformer
3. PPT Builder
4. PPT Validation
5. Review Agent
6. Result Uploader

### 9.2 Document Parser

Document Parser는 MarkItDown을 사용하지 않는다. 변환기 기반 Markdown 보조 입력은 로컬 테스트에서 긴 대기와 파일 락 문제가 있어 런타임 경로에서 제거했다.

현재 기준은 다음과 같다.

- PPTX template: 슬라이드 수, 크기, layout, text shape, shapeId, 위치, font/color theme
- DOCX: title, heading outline, paragraph section, table preview, style counts, report signals
- XLSX: workbook profile, sheet profile, sample rows, numeric columns, formula cells, structured Excel tables, embedded chart metadata
- Multi-source: `documentType: "multi"`, `documents`, flattened `sections`, `workbookProfiles`, `documentProfiles`

MarkItDown 비교 결과는 다음과 같다.

- PPTX: 슬라이드 텍스트를 Markdown으로 읽기 좋게 펼치지만, 템플릿 치환에 필요한 `shapeId`, 위치, 크기, 폰트, 색상, layout 정보가 없다.
- DOCX: heading/table Markdown 품질은 좋지만, report signals, heading outline, table profile 같은 결정적 구조 필드는 프로젝트 파서가 더 적합하다.
- XLSX: 시트별 Markdown table은 깔끔하지만, chart metadata, formula cells, numeric columns, workbook profile을 source of truth로 쓰기 어렵다.

따라서 MarkItDown은 런타임 필수 단계가 아니라, timeout과 cache가 있는 선택적 분석/디버깅 도구로만 고려한다.

### 9.3 LLM 중심 생성 방식

일반 업로드 흐름은 더 이상 generic 새 슬라이드를 조립하는 방식이 아니다.
업로드된 템플릿 PPT를 기준 구조로 삼고, 각 슬라이드의 텍스트 shape 목록을 LLM에 전달한다.
LLM은 다음 정보를 반환한다.

- `deckTitle`
- `strategy`
- slide별 `slideIndex`
- slide별 `sourceFocus`
- slide별 `speakerNotes`
- slide별 `shapeId -> replacement text`
- slide별 `chartUpdates`
- slide별 `tableUpdates`

워커는 이 결과를 바탕으로 원본 템플릿 슬라이드의 텍스트를 in-place 치환한다.

각 text shape에는 `fit` hint가 함께 전달된다.

- `role`
- `maxChars`
- `maxLines`
- `areaIn2`

LLM은 shape 크기에 맞춰 짧은 replacement를 생성하고, 상세 설명은 speaker notes로 이동해야 한다.

### 9.4 PPT 검증 및 후처리 QA

PPT Builder 뒤에는 `PPTValidationAgent`와 `ReviewAgent`가 연결된다.

- `PPTValidationAgent`
  - PPTX를 다시 열어 slide/text shape 구조 확인
  - out-of-bounds, long text, high text density 검사
  - AWS worker 환경에서는 LibreOffice + Poppler 기반 render smoke test 수행
- `ReviewAgent`
  - 누락된 text replacement 검사
  - Excel numeric data가 있는데 chart/table update intent가 없는 경우 warning
  - render 실패는 error
  - `high_text_density`는 error로 승격해 `needs_retry` 처리

현재 pipeline stage는 다음과 같다.

- `DOCUMENT_PARSING`
- `LLM_TEMPLATE_TRANSFORMATION`
- `PPT_BUILDING`
- `PPT_VALIDATION`
- `PPT_REVIEW`
- `RESULT_UPLOADING`
- `RESULT_READY`

데모 흐름에서는 별도 fast-path로 다음 상태를 사용한다.

- `DEMO_RESULT_READY`

---

## 10. 배포 구조

### 10.1 현재 운영 방식

- 프론트: AWS Amplify Hosting
- 백엔드/인프라: AWS CDK -> CloudFormation
- 리전: `ap-northeast-2`

### 10.2 Git 브랜치 전략

- `main`
  - 기본 운영 브랜치
  - Amplify production 브랜치
- `codex/demo-one-click-ppt`
  - 데모 피드백용 분리 브랜치
  - Amplify preview 브랜치

### 10.3 데모 프리뷰 URL

- `https://codex-demo-one-click-ppt.d2qzosqvodzspp.amplifyapp.com/upload`

---

## 11. 보안 및 권한

### 11.1 Lambda 권한

- DynamoDB 읽기/쓰기
- Step Functions 실행
- S3 업로드 URL 생성 및 데모 자산 기록

### 11.2 Fargate Task 권한

- S3 읽기/쓰기
- DynamoDB 읽기/쓰기
- Bedrock Invoke
- 필요 시 Secrets Manager 읽기

### 11.3 데이터 보호

- S3는 Presigned URL 기반 직접 업로드/다운로드
- 퍼블릭 버킷 접근 금지
- 세션 토큰 기반 Job 접근 제한

---

## 12. 현재 한계

- 일반 업로드 흐름은 LLM 기반 템플릿 텍스트 치환까지 지원한다.
- Excel chart/table update intent는 생성하지만, 템플릿 native chart/table 데이터 실제 갱신은 아직 제한적이다.
- `needs_retry` 판정은 가능하지만, 문제 shape만 재요청하는 자동 LLM retry loop는 아직 구현 전이다.
- 현재 MVP는 원본 템플릿의 slide count/order/layout을 유지하는 것을 우선한다.
- 데모 흐름은 초기 피드백 수집을 위한 fast-path로 유지한다.

---

## 13. 다음 단계

1. Excel native chart/table 갱신 고도화
2. `high_text_density`/render failure 기반 LLM 자동 재시도 루프 추가
3. HistoryPage 기능 고도화
4. CloudWatch 알람 및 운영 모니터링 추가
5. Amplify 커스텀 도메인 연결
