# Bedrock 반영 최종 아키텍처 문서 v2

> **이 문서의 역할**: 발표·심사용 아키텍처 설명서입니다.  
> 구현 상세(API 명세, DB 스키마, 장애 처리)는 `design-doc.md`를 참조하세요.  
> UI 컴포넌트 설계는 `ui-spec.md`를 참조하세요.

## 1) 프로젝트 개요

### 1.1 프로젝트명(가칭)

**Prompt-to-PPT Enterprise Builder**

### 1.2 서비스 한 줄 정의

사용자가 **회사 템플릿 PPT**와 **Word/Excel 기반 콘텐츠 파일**을 업로드하고 생성 목적(보고용/발표용/경영진용 등)을 입력하면, 시스템이 **회사 템플릿 스타일을 유지한 PPT를 자동 생성**하는 플랫폼이다.

### 1.3 핵심 차별점

이 서비스는 단순한 “문서 요약”이 아니라, **템플릿 구조 분석 + 문서 의미 파악 + 슬라이드 구조 생성 + 차트 시각화 + 최종 PPT 렌더링**을 하나의 파이프라인으로 자동화한다. Bedrock의 **Converse API**, **Guardrails**, **Prompt Caching** 같은 기능은 구조화된 슬라이드 생성 워크플로에 잘 맞고, Fargate는 무거운 문서 처리/렌더링 작업을 서버 관리 없이 실행할 수 있다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-call.html), [\[docs.amazonaws.cn\]](https://docs.amazonaws.cn/en_us/AmazonECS/latest/developerguide/AWS_Fargate.html), [\[aws.amazon.com\]](https://aws.amazon.com/documentation-overview/fargate/)

***

## 2) 아키텍처 목표

이 아키텍처는 다음 목표를 만족하도록 설계한다.

*   **기업 문서 보안성**: 업로드된 문서와 결과물을 AWS 내부 권한 체계로 보호한다. Bedrock은 Converse 요청에 제공된 텍스트/이미지/문서를 저장하지 않고 응답 생성에만 사용한다고 문서화되어 있어, 기업 문서 기반 활용 시 설명력이 높다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/)
*   **확장 가능한 생성 파이프라인**: 템플릿 파싱, 문서 파싱, LLM 생성, PPT 렌더링을 분리해 이후 기능 확장이나 품질 개선이 쉽도록 한다. Converse API는 모델 간 일관된 인터페이스를 제공하므로, 이후 모델 교체나 상위 모델 추가 적용도 유리하다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-call.html)
*   **운영 안정성**: Fargate 작업을 단순 비동기 호출이 아니라 Step Functions 기반으로 추적해 “요청은 성공했지만 실제 태스크는 실패한 상태”를 줄인다. ECS `RunTask`는 HTTP 200이 반환되어도 `Failures`가 존재하거나 실제 태스크 시작이 지연/실패할 수 있어, `.sync` 기반 오케스트레이션이 유리하다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_RunTask.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/step-functions/latest/dg/connect-ecs.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/step-functions/latest/dg/integrate-optimized.html)

***

## 3) 최종 권장 아키텍처

## 3.1 전체 구성도

```text
[React Web (AWS Amplify)]
 ├─ GitHub CI/CD 자동 배포
 ├─ S3 Presigned URL 직접 업로드
 └─ API Gateway 호출
        │
        ▼
[Lambda API Layer]
 ├─ Job 생성
 ├─ DynamoDB 상태 기록
 └─ Step Functions 실행
        │
        ▼
[Step Functions Standard Workflow]
 └─ ECS Fargate Worker 실행 (.sync)
        │
        ▼
[AWS Secrets Manager] <── [외부 API Key 인출용]
        │
        ▼
[ECS Fargate Worker]
 ├─ S3에서 template.pptx 다운로드
 ├─ S3에서 content.docx / content.xlsx 다운로드 (택1)
 ├─ PPT/Word/Excel 파싱 (플레이스홀더 위치/크기 포함 마스터 구조 파싱)
 ├─ 멀티 벤더 AI 라우팅 (사용자 선택: Bedrock / OpenAI)
 │   ├─ 1차: 아웃라인 생성
 │   ├─ 2차: 슬라이드 본문 생성
 │   └─ (선택) 3차: 문체 정리/최종 보정
 ├─ Guardrails 적용 (Bedrock 사용 시)
 ├─ 차트 렌더링 (Excel 입력 있을 때만 활성화, matplotlib)
 ├─ python-pptx로 PPT 생성 (플레이스홀더 기반 렌더링)
 └─ S3 결과 업로드 + DynamoDB 상태 업데이트
        │
        ▼
[S3 Results]
 └─ 사용자 다운로드
```

## 3.2 설계 의도

이 구조에서 **Lambda는 얇은 API 계층**, **Step Functions는 상태 오케스트레이션**, **Fargate는 실제 무거운 작업 실행기**, **Bedrock은 생성형 AI 추론 런타임** 역할을 맡는다. 이렇게 분리하면 각 컴포넌트의 책임이 명확해지고, 공모전 발표에서도 아키텍처 논리가 깔끔해진다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/step-functions/latest/dg/connect-ecs.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/step-functions/latest/dg/integrate-optimized.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html), [\[docs.amazonaws.cn\]](https://docs.amazonaws.cn/en_us/AmazonECS/latest/developerguide/AWS_Fargate.html)

***

## 4. 컴포넌트 상세 설계

## 4.1 프론트엔드 (React + AWS Amplify)

프론트엔드는 다음 역할을 수행한다.

*   템플릿 PPT + Word/Excel 파일 업로드
*   생성 옵션 입력
    *   목적: 보고용 / 발표용 / 경영진용
    *   길이: 5장 / 10장 / 15장
    *   톤: 공식적 / 간결 / 설득형
*   Job 상태 조회
*   결과 PPT 다운로드

### 설계 포인트

대용량 업로드를 API 서버가 직접 받기보다 **S3 pre-signed URL 업로드**를 사용하면 API 계층 부담을 줄이고 업로드 경로를 단순화할 수 있다.
추가로 웹 어플리케이션은 **AWS Amplify Hosting**을 사용하여 GitHub 저장소와 연동, 코드 푸시만으로 `CI/CD 배포 자동화`를 이루고, CDN(CloudFront)을 통해 비용 효율적인 서버리스 호스팅을 구현한다.

***

## 4.2 API Layer (API Gateway + Lambda)

Lambda API Layer는 다음 기능만 수행하는 **얇은 진입 계층**으로 설계한다.

*   Presigned URL 발급
*   Job 생성
*   DynamoDB 상태 초기화 (`PENDING`)
*   Step Functions 실행
*   Job 상태 조회
*   결과 다운로드 URL 반환

### 왜 얇게 두는가

문서 파싱, LLM 호출, PPT 렌더링 같은 작업은 Lambda보다 Fargate가 적합하다. Fargate는 서버리스 컨테이너 환경으로 CPU/메모리만 정의하면 컨테이너를 실행할 수 있고, 서버/클러스터 관리 부담이 없다. 또한 각 Task가 자체 격리 경계를 가지므로 워크로드 분리 측면에서도 유리하다. [\[docs.amazonaws.cn\]](https://docs.amazonaws.cn/en_us/AmazonECS/latest/developerguide/AWS_Fargate.html), [\[aws.amazon.com\]](https://aws.amazon.com/documentation-overview/fargate/)

***

## 4.3 오케스트레이션 계층 (Step Functions)

이 프로젝트에서는 **Step Functions Standard Workflow**를 권장한다.

### 이유

Step Functions는 ECS/Fargate에 대해 **Run a Job (`.sync`) 통합 패턴**을 지원하고, 태스크 완료까지 기다리며 실패를 워크플로 차원에서 처리할 수 있다. AWS 문서상 Express Workflows는 동일한 통합 패턴을 모두 지원하지 않으며, `.sync` 기반의 안정적 작업 추적은 Standard 쪽이 적합하다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/step-functions/latest/dg/connect-ecs.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/step-functions/latest/dg/integrate-optimized.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html)

### 권장 상태 흐름

```text
CreateJob
  -> RunFargateTask (.sync)
      -> Success: Update SUCCEEDED
      -> Failure: Update FAILED
```

### 이 계층이 중요한 이유

ECS `RunTask`는 비동기적이며, 문서상 태스크 정의 리비전 해석/권한/프로비저닝 타이밍 문제 때문에 후속 상태 확인이 중요하다. 따라서 Step Functions로 ECS 태스크 실행을 감싸면 재시도 정책과 에러 핸들링을 구조적으로 넣기 좋다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_RunTask.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/step-functions/latest/dg/connect-ecs.html), [\[github.com\]](https://github.com/aws-samples/aws-ecs-stepfunctions-synchronous-runtask)

***

## 4.4 실행 계층 (ECS Fargate Worker)

Fargate Worker는 실제 업무 로직의 핵심이다.

### 담당 작업 — Agent 파이프라인

Fargate Worker 내부는 **7개 Agent를 순서대로 실행하는 파이프라인**으로 구성된다.

| Agent | 역할 |
|---|---|
| DocumentParserAgent | template.pptx 마스터 구조 + Word/Excel 파싱 |
| OutlineAgent | LLM 호출 → 슬라이드 구조 JSON (제목·타입·목적) |
| SlideWriterAgent | LLM 루프 → 슬라이드별 본문 (bullets·캡션·메모) |
| **ReviewAgent** | **LLM 호출 → 품질 검수 + 문제 슬라이드 재생성 루프 (최대 2회)** |
| ChartRendererAgent | Excel 숫자 → matplotlib PNG (Excel 입력 시만) |
| PPTBuilderAgent | python-pptx 플레이스홀더 기반 최종 렌더링 |
| ResultUploader | S3 업로드 + 중간 산출물 저장 + DynamoDB 상태 갱신 |

### ReviewAgent 루프 동작

```
SlideWriterAgent 완료
    ↓
ReviewAgent (전체 슬라이드 품질 검수)
    ├─ approved: true  → ChartRenderer → PPTBuilder
    └─ approved: false → 문제 슬라이드만 SlideWriterAgent 재실행
                              최대 2회 재시도
                              초과 시 현재 결과로 강제 진행
```

ReviewAgent가 있으면 단순 "1회 생성"이 아니라 **자기 교정(self-correction) 루프**가 돌기 때문에, 발표에서 "AI Agent 오케스트레이션"으로 설명할 수 있다.

### Fargate가 적합한 이유

문서 파싱(`python-docx`, `openpyxl`, `pandas`), 차트 렌더링(`matplotlib`), PPT 생성(`python-pptx`)은 무거운 라이브러리와 긴 실행 시간을 요구할 수 있다. Fargate는 이런 컨테이너 워크로드를 서버 운영 없이 실행하도록 설계된 서비스이므로, Lambda보다 이 프로젝트와 궁합이 좋다. [\[docs.amazonaws.cn\]](https://docs.amazonaws.cn/en_us/AmazonECS/latest/developerguide/AWS_Fargate.html), [\[aws.amazon.com\]](https://aws.amazon.com/documentation-overview/fargate/), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/run-event-driven-and-scheduled-workloads-at-scale-with-aws-fargate.html)

***

## 5) Bedrock 통합 설계

## 5.1 왜 Bedrock인가

Bedrock은 여러 모델 공급자에 대한 추론 인터페이스를 제공하며, 특히 **Converse API**는 메시지 기반 모델에 대해 **공통 요청 구조**를 제공한다. 따라서 모델마다 전용 JSON 포맷을 따로 맞추기보다, `messages`, `system`, `inferenceConfig`, `guardrailConfig`, `toolConfig` 같은 공통 필드를 활용해 구조화된 생성 파이프라인을 만들 수 있다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-call.html)

***

## 5.2 Bedrock 호출 전략

이 프로젝트에서는 **2단계 생성 전략**을 권장한다.

### 1단계: 아웃라인 생성

입력:

*   템플릿 구조 요약
*   Word/Excel 요약 내용
*   사용자 옵션(톤/길이/대상)

출력:

*   슬라이드 수
*   슬라이드 제목
*   슬라이드 타입(`summary`, `text`, `chart`(Excel 입력 시만), `table`)
*   각 슬라이드 목적

### 2단계: 슬라이드 본문 생성

입력:

*   슬라이드별 컨텍스트
*   관련 문단/표/숫자 데이터
*   대상/톤/길이

출력:

*   제목
*   bullet 3\~5개
*   차트 캡션
*   발표 메모(선택)

### 선택 3단계: 문체 통일

긴 PPT의 경우 마지막에 전체 슬라이드 문체를 통일하는 후처리를 넣을 수 있다.

### 이유

Converse API는 대화형 메시지 구조와 시스템 지시문을 지원하므로, “아웃라인 → 세부 생성”처럼 **다단계 생성 품질 제어**에 적합하다. 한 번에 전체 PPT를 생성하는 것보다 구조 안정성과 검증 가능성이 높다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-call.html)

***

## 5.3 모델 선택 방향

**MVP 결정: 사용자가 AI 엔진을 직접 선택하는 멀티 벤더 라우팅을 MVP에 포함한다.**

- **Bedrock 모드**: 기업 문서 보안이 중요한 경우. Converse API 기반, Guardrails 적용.
- **OpenAI 모드**: 창의성·최신 지식이 필요한 경우. Secrets Manager에서 API Key 런타임 인출.

사용자는 `UploadPage` 옵션 섹션에서 AI 엔진을 선택하며, Worker는 선택값을 환경변수로 전달받아 라우팅한다.

### 추천 운영 방식

*   **빠른 아웃라인 생성용 모델**
*   **품질 위주의 최종 문안 생성용 모델**

이처럼 단계별로 다른 모델을 쓰는 구조도 가능하며, Converse의 일관된 인터페이스 덕분에 코드 복잡도를 크게 늘리지 않고 설계할 수 있다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-call.html)

***

## 5.4 Guardrails 적용

Bedrock Guardrails는 **입력과 출력 모두를 정책 기반으로 평가**할 수 있으며, 콘텐츠 필터, 금지 주제, 민감 정보 필터, 워드 필터 등을 구성할 수 있다. 입력 단계에서 차단되면 모델 추론을 건너뛰고, 출력이 정책을 위반하면 차단/마스킹이 가능하다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-how.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)

### 본 프로젝트 적용 방안

*   업로드 문서의 민감 정보 노출 가능성 완화
*   결과 PPT의 부적절한 표현 방지
*   발표 시 “Responsible AI” 설계 포인트로 활용

***

## 5.5 Prompt Caching

Bedrock Prompt Caching은 **반복되는 긴 컨텍스트**가 많은 워크로드에서 지연과 입력 토큰 비용을 줄이는 기능이다. 캐시 가능한 prompt prefix를 재사용하므로, 동일한 시스템 프롬프트나 템플릿 규칙을 반복 사용하는 생성 파이프라인에 적합하다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)

### 본 프로젝트에서 캐싱 후보

*   회사 템플릿 규칙
*   슬라이드 작성 규칙
*   JSON 출력 스키마
*   기업 문체 가이드

특히 슬라이드별로 개별 생성하는 구조는 동일한 prefix를 반복 사용하게 되므로 Prompt Caching과 궁합이 좋다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)

***

## 6) 데이터 흐름 설계

## 6.1 입력 데이터

*   `template.pptx`
*   `content.docx` 또는 `content.xlsx`
*   `promptOptions`
    *   tone
    *   target
    *   length
    *   notes

## 6.2 내부 정규화 예시

```json
{
  "templateRules": {
    "layouts": ["title+content", "title+chart"],
    "maxBullets": 4,
    "style": "formal"
  },
  "contentSummary": {
    "title": "2026 Q1 사업보고",
    "sections": [
      {
        "title": "매출 현황",
        "summary": "전년 동기 대비 18% 증가"
      }
    ]
  },
  "userOptions": {
    "tone": "executive",
    "length": "brief"
  }
}
```

### 의미

이 정규화 계층은 파서와 LLM을 분리하는 핵심이다. Word/Excel/PPT 템플릿의 원본 구조를 그대로 LLM에 넣기보다, **LLM 친화적인 JSON 중간 표현**으로 바꾸면 디버깅과 재사용성이 좋아진다.

***

## 7) 저장소 및 상태 관리

## 7.1 S3

*   `uploads/` : 원본 템플릿/문서 저장
*   `results/` : 최종 PPT 저장
*   `temp/` : 필요 시 중간 산출물 저장

## 7.2 DynamoDB

Job 상태 관리용 테이블을 둔다.

권장 상태:

*   `PENDING`
*   `RUNNING`
*   `SUCCEEDED`
*   `FAILED`

### 이유

비동기 생성형 작업은 반드시 상태 기반으로 관리되어야 한다. 사용자는 업로드 후 즉시 결과를 받는 것이 아니라 “생성 중 → 완료 → 다운로드” 흐름을 밟게 되므로, Job 중심 상태 모델이 필요하다.

***

## 8) 보안 및 IAM 설계

## 8.1 Bedrock 접근 권한

Converse API 호출에는 `bedrock:InvokeModel` 권한이 필요하며, 스트리밍을 쓸 경우 `bedrock:InvokeModelWithResponseStream`도 고려해야 한다. 또한 모델 액세스는 현재 적절한 AWS Marketplace 권한 하에서 자동화되어 있지만, 일부 제3자 모델은 최초 사용 시 구독/사전 조건 검증이 필요할 수 있고 Anthropic 계열은 FTU 제출이 필요할 수 있다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-call.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html), [\[aws.amazon.com\]](https://aws.amazon.com/blogs/security/simplified-amazon-bedrock-model-access/)

## 8.2 권장 역할

*   **Lambda Role**
    *   DynamoDB Job 생성/조회
    *   Step Functions 실행
    *   Presigned URL 발급용 S3 접근
*   **Fargate Task Role**
    *   S3 원본 읽기/결과 쓰기
    *   DynamoDB 상태 업데이트
    *   Bedrock Invoke 권한
*   **Execution Role**
    *   ECR 이미지 Pull
    *   CloudWatch Logs 전송

***

## 9) 운영 및 확장 전략

## 9.1 초기 MVP 범위

*   PPT 템플릿 1종 지원
*   Word/Excel 1개 입력 지원
*   5\~10장 자동 PPT 생성
*   텍스트/차트 중심 렌더링
*   Bedrock 2단계 생성

## 9.2 확장 로드맵

*   템플릿 다중 지원
*   Knowledge Bases 기반 사내 공통 문구/RAG 확장
*   Prompt Management 연동
*   협업 편집 UI
*   슬라이드별 웹 미리보기

### Knowledge Bases를 나중에 붙이는 이유

Bedrock Knowledge Bases는 RAG 기반으로 사내 데이터/문서를 검색해 응답 정확도를 높이고, 근거(citation)도 제공할 수 있다. 다만 현재 프로젝트는 사용자가 매번 Word/Excel을 직접 올리는 구조이므로, MVP에서는 필수 요소가 아니고 **조직 공통 지식 확장 단계**에서 붙이는 것이 자연스럽다.

***

## 9.3 Fargate Cold Start 최적화 로드맵

MVP는 비용 효율을 위해 On-Demand `RunTask` 방식을 사용하며, 초기 구동 지연(약 30초~1분)이 발생한다. 프로덕션 전환 시 아래 순서로 개선한다.

1. **Warm Pool 패턴** — SQS + ECS Service로 전환, 상시 1대 구동 → 큐 수신 즉시 처리
2. **Lambda/Fargate 분기 라우팅** — 3장 이하 가벼운 요청은 Lambda, 무거운 렌더링만 Fargate
3. **AWS SOCI 적용** — 이미지 전체 다운로드 없이 백그라운드 스트리밍으로 Cold Start 50% 단축

***

## 10) 공모전 발표용 핵심 메시지

이 아키텍처는 단순한 “문서 요약 AI”가 아니라, 다음을 동시에 만족한다.

1.  **기업형 문서 자동화**  
    템플릿 구조를 이해하고 회사 스타일을 유지한다.

2.  **생성형 AI의 실무 적용**  
    Bedrock Converse 기반으로 슬라이드 구조와 문안을 생성한다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)

3.  **안정적 실행 구조**  
    ECS Fargate + Step Functions `.sync`로 무거운 작업을 안정적으로 수행한다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/step-functions/latest/dg/connect-ecs.html), [\[docs.amazonaws.cn\]](https://docs.amazonaws.cn/en_us/AmazonECS/latest/developerguide/AWS_Fargate.html)

4.  **책임 있는 AI**  
    Guardrails와 권한 제어를 통해 기업 문서 사용 시의 안전성을 고려한다. [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-how.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/)

***

# 최종 결론

이 프로젝트의 **최종 권장 구조**는 다음과 같다.

*   **Frontend**: React + S3 Presigned Upload
*   **API 계층**: API Gateway + Lambda
*   **오케스트레이션**: Step Functions Standard Workflow
*   **실행 계층**: ECS Fargate Worker
*   **LLM 런타임**: Amazon Bedrock Converse API
*   **보호 계층**: Bedrock Guardrails
*   **최적화 계층**: Prompt Caching
*   **저장소/상태**: S3 + DynamoDB

이 구조는 AWS 공식 기능 범위 안에서 **문서 파싱 → 구조화 → LLM 생성 → PPT 렌더링 → 결과 배포**까지 설계적으로 자연스럽고, 공모전용 데모로도 충분히 설득력 있다. Fargate의 서버리스 컨테이너 특성과 Bedrock의 통합 추론 인터페이스, Step Functions의 `.sync` 기반 작업 추적을 조합하면 “기업형 생성형 AI 문서 자동화 플랫폼”이라는 메시지를 강하게 만들 수 있다. [\[docs.amazonaws.cn\]](https://docs.amazonaws.cn/en_us/AmazonECS/latest/developerguide/AWS_Fargate.html), [\[aws.amazon.com\]](https://aws.amazon.com/documentation-overview/fargate/), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/step-functions/latest/dg/connect-ecs.html), [\[docs.aws.amazon.com\]](https://docs.aws.amazon.com/step-functions/latest/dg/integrate-optimized.html)

***

원하면 다음 단계로 바로 이어서 아래 중 하나를 만들 수 있어:

1.  **이 문서를 기반으로 한 공모전 제출용 PPT 목차**
2.  **AWS 아키텍처 다이어그램(발표 슬라이드용)**
3.  **Terraform/CDK 기준 인프라 구성안**
4.  **Bedrock 프롬프트 설계서**
5.  **FastAPI + Fargate 워커 폴더 구조 설계**

원하면 다음 답변에서 바로  
**“공모전 제출용 PPT 목차 + 발표 메시지”** 버전으로 이어서 정리해줄게.
