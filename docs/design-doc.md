# Design Document: Prompt-to-PPT Enterprise Builder

| 항목 | 내용 |
|---|---|
| 작성자 | 최정경 |
| 버전 | v0.2 |
| 작성일 | 2026-04-01 |
| 상태 | Draft |

---

## 1. 개요

Prompt-to-PPT Enterprise Builder는 사용자가 PowerPoint 템플릿과 Word 또는 Excel 기반 콘텐츠 파일을 업로드하면, 템플릿 스타일을 유지한 발표 자료를 자동으로 생성하는 서비스다.

현재 프로젝트는 다음 두 가지 흐름을 함께 지원한다.

- 일반 생성 흐름: 사용자가 직접 `pptx + docx/xlsx`를 업로드해서 Job을 생성
- 데모 흐름: 업로드 없이 `Try Demo PPT` 버튼으로 내장 샘플 자산을 사용해 즉시 결과 PPT를 생성

---

## 2. 목표

### 2.1 MVP 목표

- 템플릿 PPT 1종 업로드 지원
- 콘텐츠 파일 1종 업로드 지원 (`docx` 또는 `xlsx`)
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
  - 1단계 문서 파싱 시작 구현 완료
  - 2단계 LLM 프롬프트 생성 시작 구현 완료
  - 3~7단계는 순차 확장 예정

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
              -> 프롬프트 생성
              -> 이후 단계 확장 예정
  -> 결과 상태 조회
  -> 결과 PPT 다운로드
```

---

## 5. Job 처리 흐름

### 5.1 일반 업로드 흐름

1. 프론트가 `jobId`를 생성한다.
2. 프론트가 `POST /jobs/upload-url`로 업로드 URL을 요청한다.
3. 브라우저가 S3에 템플릿과 콘텐츠 파일을 직접 업로드한다.
4. 프론트가 `POST /jobs`로 Job을 생성한다.
5. Lambda가 DynamoDB에 `PENDING` 상태를 기록한다.
6. Lambda가 Step Functions를 시작한다.
7. Step Functions가 ECS Fargate 워커를 실행한다.
8. 워커가 문서를 파싱하고 중간 결과를 S3와 DynamoDB에 저장한다.
9. 프론트가 `GET /jobs/{jobId}`를 폴링하며 상태를 표시한다.

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
  "contentS3Key": "uploads/{jobId}/content.docx",
  "options": {
    "tone": "공식적",
    "target": "팀 내부",
    "length": 10,
    "notes": "",
    "aiEngine": "bedrock"
  }
}
```

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
uploads/{jobId}/content.docx
uploads/{jobId}/content.xlsx
results/{jobId}/output.pptx
temp/{jobId}/parsed_document.json
temp/{jobId}/outline_request.json
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

### 9.1 목표 단계

1. Document Parser
2. Outline Prompt Generator
3. Slide Writer
4. Review Agent
5. Chart Renderer
6. PPT Builder
7. Result Uploader

### 9.2 현재 구현 상태

- Document Parser: 시작 구현 완료
- Outline Prompt Generator: 시작 구현 완료
- 이후 단계: 미구현

### 9.3 현재 성공 기준

실제 업로드 흐름에서는 현재 다음 상태까지를 우선 목표로 한다.

- `DOCUMENT_PARSING`
- `OUTLINE_PROMPT_GENERATION`
- `OUTLINE_PROMPT_READY`

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

- 워커 3~7단계가 아직 완성되지 않았다.
- 일반 업로드 흐름은 최종 PPT 생성까지 아직 닫히지 않았다.
- 데모 흐름은 실제 파이프라인 완료 전 초기 피드백 수집을 위한 fast-path다.

---

## 13. 다음 단계

1. 워커 3~7단계 구현
2. 실제 업로드 흐름의 `SUCCEEDED` 완료까지 연결
3. HistoryPage 기능 고도화
4. CloudWatch 알람 및 운영 모니터링 추가
5. Amplify 커스텀 도메인 연결
