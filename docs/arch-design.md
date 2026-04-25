# Architecture Design: Prompt-to-PPT Enterprise Builder

## 1. 목적

이 문서는 Prompt-to-PPT 프로젝트의 현재 아키텍처를 발표용 관점에서 짧고 명확하게 설명하기 위한 문서다.
상세 API, 데이터 모델, 운영 규칙은 `docs/design-doc.md`를 기준 문서로 사용한다.

---

## 2. 한 줄 요약

사용자가 PPT 템플릿과 문서를 올리면, 프론트가 Job을 생성하고, 백엔드가 비동기 워커를 실행해 LLM이 템플릿 슬라이드의 텍스트 shape를 새 콘텐츠로 치환하는 구조다.

현재는 초기 데모 피드백을 위해 업로드 없이 결과를 바로 보여주는 데모 브랜치도 함께 운영한다.

---

## 3. 상위 아키텍처

```text
[React Frontend / Amplify]
  -> [API Gateway]
    -> [Lambda APIs]
      -> [DynamoDB]
      -> [S3]
      -> [Step Functions]
        -> [ECS Fargate Worker]
          -> [S3 Temp/Result]
```

---

## 4. 컴포넌트 역할

### 4.1 Frontend

- React + Vite + Tailwind CSS
- 파일 업로드, 옵션 선택, Job 상태 조회, 결과 다운로드 UI 제공
- AWS Amplify Hosting으로 배포
- GitHub 브랜치 푸시 시 자동 배포

### 4.2 API Layer

- API Gateway + Lambda
- Presigned URL 발급
- Job 생성
- Job 상태 조회
- Job 목록 조회
- 데모 fast-path 처리

### 4.3 Storage

- S3
  - 업로드 파일 저장
  - 중간 산출물 저장
  - 최종 PPT 저장
- DynamoDB
  - Job 상태 저장
  - 세션 토큰 기준 소유권 관리

### 4.4 Orchestration

- Step Functions
- ECS Fargate 워커 실행 및 상태 연결

### 4.5 Worker

- Python 기반 파이프라인
- 현재 구현 범위
  - 템플릿 PPT 슬라이드/텍스트 shape 파싱
  - Word/Excel 콘텐츠 파싱
  - LLM 기반 템플릿 변환 계획 생성
  - 원본 템플릿 슬라이드 in-place 텍스트 치환
  - 결과 PPT 업로드

---

## 5. 일반 생성 흐름

```text
1. 사용자가 template.pptx + content.docx/xlsx 업로드
2. 프론트가 S3 Presigned URL 요청
3. 브라우저가 S3에 직접 업로드
4. 프론트가 POST /jobs 호출
5. Lambda가 DynamoDB에 PENDING 저장
6. Lambda가 Step Functions 실행
7. Step Functions가 Fargate Worker 실행
8. Worker가 템플릿과 콘텐츠를 파싱
9. LLM이 각 템플릿 text shape의 새 문구를 생성
10. Worker가 템플릿 슬라이드를 직접 치환해 결과 PPT 생성
11. 프론트가 GET /jobs/{jobId} 폴링
12. 완료 시 결과 PPT 다운로드
```

---

## 6. 데모 생성 흐름

```text
1. 사용자가 Try Demo PPT 클릭
2. 프론트가 POST /jobs with demoPreset='excel' 호출
3. Lambda가 demo_assets를 S3에 배치
4. Lambda가 데모 결과 PPT를 바로 연결
5. Job을 SUCCEEDED로 저장
6. 프론트가 결과 다운로드 링크를 즉시 표시
```

### 데모 브랜치 목적

- 초기 사용자 피드백을 빠르게 받기 위함
- 실제 업로드 없이도 서비스 느낌을 바로 보여주기 위함
- 미완성 워커 단계와 무관하게 데모 경험을 안정적으로 제공하기 위함

---

## 7. 배포 구조

### 7.1 현재 운영 분리

- 프론트 배포: Amplify Hosting
- 백엔드/인프라 배포: CDK -> CloudFormation

### 7.2 브랜치 전략

- `main`
  - 기본 운영 브랜치
- `codex/demo-one-click-ppt`
  - 데모 전용 브랜치
  - Amplify preview URL로 별도 노출

### 7.3 데모 URL

- `https://codex-demo-one-click-ppt.d2qzosqvodzspp.amplifyapp.com/upload`

---

## 8. 보안 포인트

- 로그인 대신 `sessionToken` 기반 소유권 분리
- 모든 API 요청에 `X-Session-Token` 사용
- S3는 Presigned URL 기반 직접 접근
- API Gateway CORS는 `X-Session-Token` 헤더를 반드시 허용해야 함

---

## 9. 현재 강점

- 프론트와 백엔드가 실제 AWS 상에서 연결되어 있다.
- 업로드 기반 Job 생성 골격이 이미 동작한다.
- 데모 브랜치에서는 한 번의 클릭으로 결과 PPT를 보여줄 수 있다.
- Step Functions + Fargate 구조로 확장 가능한 백엔드 기반이 준비돼 있다.
- 일반 업로드 플로우는 LLM이 템플릿 text shape별 replacement plan을 만들고, 워커가 원본 PPT 양식을 유지한 채 치환한다.

---

## 10. 현재 한계

- Excel native chart/table 데이터 갱신은 아직 제한적이다.
- 현재 MVP는 템플릿의 slide count/order/layout을 유지하는 변환에 초점을 둔다.
- 데모 fast-path는 피드백 수집용으로 계속 유지한다.

---

## 11. 권장 다음 단계

1. Excel native chart/table 갱신 고도화
2. LLM 변환 품질 평가 및 재시도 루프 추가
3. 운영 모니터링과 알람 구성
4. 커스텀 도메인 연결
5. 데모 브랜치 기능의 메인 반영 여부 결정
