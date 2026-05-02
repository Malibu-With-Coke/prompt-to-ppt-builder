# 미결 사항 정리 (Open Questions)

> `기사/` 폴더를 제외한 문서들을 기준으로, **바이브 코딩에 바로 들어가기 전에 막히는 지점**만 추렸습니다.  
> 결정된 항목은 하단 **[Closed]** 섹션으로 이동합니다.

---

## 결정 현황 요약

| 항목 | 내용 | 상태 |
|---|---|---|
| C1. AI 전략 | 멀티 벤더 라우팅 MVP 포함 | ✅ 확정 |
| C2. HistoryPage 조회 방식 | 관리자 데모형 전체 조회 | ✅ 확정 |
| C3. 파일명 | `open-questions.md` 유지 | ✅ 확정 |
| Q1. Job 상태 조회 | 3초 HTTP 폴링 | ✅ 확정 |
| Q2. Worker 실행 방식 | 배치 스크립트형 컨테이너 | ✅ 확정 |
| Q3. 템플릿 파싱 범위 | 플레이스홀더 위치/크기까지 | ✅ 확정 |
| Q4. 차트 데이터 소스 | Excel 입력 있을 때만 차트 허용 | ✅ 확정 |
| Q5. 옵션 enum | 한국어 라벨 중심 값 | ✅ 확정 |
| Q6. 입력 파일 조합 | `pptx + docx/xlsx 복수 파일` | ✅ 확정 |
| Q7. 중간 산출물 저장 | S3에 저장 (디버깅용) | ✅ 확정 |
| Q8. 실패 메시지 노출 | 단계 정보 포함 표시 | ✅ 확정 |
| Q9. 인증 범위 | 세션 기반 소유권 (로그인 없음, localStorage) | ✅ 확정 |
| Q10. UI 라이브러리 | Tailwind CSS | ✅ 확정 |

---

## 🔴 Open (미결)

> 현재 모든 핵심 항목이 확정됐습니다. 아래 New Issues 답변을 채워주세요.

---

## 🟡 New Issues (문서 통일 작업 중 발견)

문서들을 일관되게 맞추다가 발견한 추가 확인 필요 사항입니다.

### N1. `tone` / `target` 한국어 enum 값 확정 필요

**배경**
- Q5에서 "한국어 라벨 중심 값으로 바꾼다"고 결정됐습니다.
- 그러나 실제 코드 레벨 enum 값이 어떤 문자열인지 아직 미정입니다.

**권장 후보**
```
tone:   "경영진용" | "공식적" | "간결"
target: "경영진"  | "팀 내부" | "고객/외부"
length: 5 | 10 | 15  (숫자는 언어 무관)
```

**질문**
- 위 값으로 확정하면 될까요? 아니면 다른 표현을 쓸까요?

> ✅ 결정:

---

### N2. 멀티 벤더 UI 진입점 위치

**배경**
- C1에서 사용자가 선택 가능한 멀티 벤더 라우팅을 MVP에 포함하기로 결정됐습니다.
- 그런데 현재 `ui-spec.md`와 `wireframe.md`에는 **모델 선택 UI가 없습니다**.

**영향 범위**
- `UploadPage` 옵션 섹션에 "AI 엔진 선택" 항목을 추가해야 합니다.
- 선택지 표시 방식(라디오/드롭다운/토글)도 정해야 합니다.

**질문**
- AI 엔진 선택을 어디에, 어떤 컴포넌트로 넣을까요?
  - A) `OptionsSection` 하단에 라디오 버튼 (`Bedrock (보안 모드)` / `OpenAI (창의 모드)`)
  - B) 고급 옵션 토글 뒤로 숨기기
  - C) 기본값은 Bedrock, 상단 드롭다운에서 변경

> ✅ 결정:

---

### N3. Excel-only 차트 시 docx 입력만 있을 때 차트 슬라이드 처리

**배경**
- Q4에서 "Excel 입력 있을 때만 차트 허용"으로 결정됐습니다.
- 사용자가 `content.docx`만 올렸는데, 아웃라인 생성 결과 슬라이드 타입이 `chart`로 나오면 어떻게 됩니까?

**선택지**
- A) `chart` 타입을 `text` 타입으로 자동 강등
- B) 아웃라인 생성 프롬프트에서 docx 입력 시 `chart` 타입 금지
- C) 오류로 처리

> ✅ 결정:

---

### N4. Presigned URL 만료 시간

**배경**
- `design-doc.md`와 `ui-spec.md` 어디에도 **업로드용, 다운로드용 Presigned URL의 만료 시간**이 명시되어 있지 않습니다.
- 다운로드 URL은 `GET /jobs/{jobId}` 응답에 포함되는데, 만료 후 재요청 플로우가 없습니다.

**질문**
- 업로드 URL 만료 시간: 얼마로 설정하나요? (예: 10분)
- 다운로드 URL 만료 시간: 얼마로 설정하나요? (예: 1시간)
- 만료 후 재발급은 어떻게 하나요? (프론트가 다시 `GET /jobs/{jobId}` 호출 → 신규 URL 반환 방식이 자연스러움)

> ✅ 결정:

---

## ✅ Closed (확정 완료)

<details>
<summary>접기/펼치기</summary>

### C1. AI 전략 ✅

**결정**: C) 사용자가 선택 가능한 멀티 벤더 라우팅까지 MVP 포함  
**반영 범위**: `arch-design.md`, `implementation-plan.md`, `aws-services-summary.md`, `design-doc.md`

---

### C2. HistoryPage 조회 방식 ✅

**결정**: C) 최근 job 전체 조회 (관리자 데모형)  
**반영 범위**: `ui-spec.md` — `GET /jobs` API 추가 명세, DynamoDB Scan 기반 구현

---

### C3. 파일명 ✅

**결정**: `open-questions.md` 유지

---

### Q1. Job 상태 조회 방식 ✅

**결정**: B) 3초 HTTP 폴링  
**반영 범위**: `ui-spec.md` JobStatusPage 폴링 로직 → 5초 → **3초**로 수정

---

### Q2. Fargate Worker 실행 방식 ✅

**결정**: B) 배치 스크립트형 컨테이너 (`main.py` 1회 실행 후 종료)  
**반영 범위**: `implementation-plan.md`, `design-doc.md` Worker 진입점 서술

---

### Q3. 템플릿 파싱 범위 ✅

**결정**: C) 플레이스홀더 위치/크기까지 포함한 마스터 구조  
**반영 범위**: `arch-design.md` 4.4절, `design-doc.md` 4.5절 파싱 상세 추가

---

### Q4. 차트 데이터 소스 ✅

**결정**: C) Excel 입력 있을 때만 차트 허용  
**반영 범위**: `arch-design.md` 5.2절 출력 타입, `design-doc.md` Bedrock 호출 전략

---

### Q5. 옵션 enum ✅

**결정**: 한국어 라벨 중심 값 (N1에서 구체 값 확정 예정)  
**반영 범위**: `design-doc.md` API 명세, `ui-spec.md` UploadPage 상태 정의

---

### Q6. 입력 파일 조합 ✅

**결정**: `pptx + docx/xlsx 복수 파일`  
**현재 구현**:
- 템플릿은 `.pptx` 1개
- 콘텐츠는 `.docx`, `.xlsx`를 섞어서 최대 10개
- 프론트는 `contentFiles: File[]`를 업로드한다.
- 업로드 URL 요청에는 `fileIndex`를 포함한다.
- Job 생성 요청에는 `contentS3Keys` 배열을 보낸다.
- 백엔드는 기존 호환성을 위해 `contentS3Key`도 계속 저장한다.

**반영 범위**: `design-doc.md`, `arch-design.md`, `ui-spec.md`, frontend UploadPage, backend upload/create job handlers

---

### Q7. 중간 산출물 저장 ✅

**결정**: S3에 저장 (디버깅용)

현재 중간 산출물:

```text
temp/{jobId}/parsed_document.json
temp/{jobId}/deck_transform_plan.json
temp/{jobId}/ppt_validation.json
temp/{jobId}/review_report.json
```

**반영 범위**: `design-doc.md` S3 구조, worker orchestrator

---

### Q8. 실패 메시지 노출 수준 ✅

**결정**: B) 단계 정보 포함 표시 (`문서 파싱 실패`, `모델 호출 실패` 등)  
**반영 범위**: `design-doc.md` 6절 장애 대응, `ui-spec.md` JobStatusPage ErrorBox

---

### Q9. 인증 범위 ✅

**결정**: 세션 기반 소유권 — 로그인 없음, `localStorage`에 UUID 자동 발급  
**동작**: 최초 접속 시 브라우저가 `sessionToken`(UUID v4) 생성 → `localStorage` 저장 → 모든 API 요청에 `X-Session-Token` 헤더로 전송  
**반영 범위**: `design-doc.md` DynamoDB 스키마(`sessionToken` 컬럼), `ui-spec.md` `GET /jobs` 필터 방식, `design-doc.md` API 명세

---

### Q10. UI 라이브러리 ✅

**결정**: A) Tailwind CSS  
**반영 범위**: `ui-spec.md` 헤더 메타 정보 수정

</details>
