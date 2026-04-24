# Phase 문서

이 폴더는 각 Phase의 작업 문서를 담는다. 한 Phase당 4개의 문서가 생성된다.

## 파일 명명 규칙

```
phase{N}_brief.md       — Architect가 작성. Phase의 목표·산출물·종료 조건 정의.
phase{N}_plan.md        — Builder가 작성. brief를 받아 세부 구현 계획 수립.
phase{N}_completion.md  — Builder가 작성. Phase 종료 시 결과 보고.
phase{N}_audit.md       — Auditor가 작성. 헌법 부합 여부 평가.
```

예시:
- `phase1_brief.md`
- `phase1_plan.md`
- `phase1_completion.md`
- `phase1_audit.md`

## 작성 시점

| 문서          | 시점              | 작성자    |
| ------------- | ----------------- | --------- |
| brief         | Phase 시작 전     | Architect |
| plan          | brief 승인 직후   | Builder   |
| completion    | Phase 작업 완료 후 | Builder   |
| audit         | completion 직후   | Auditor   |

## brief 템플릿

```markdown
# Phase N: [제목]

## 목표
한 문장으로 Phase의 목표를 정의.

## 배경 / 컨텍스트
이 Phase가 왜 지금 필요한가? 이전 Phase와 어떻게 연결되는가?

## 산출물 (Deliverables)
- 구체적인 산출물 목록
- 각 산출물의 검증 방법

## 인터페이스
이 Phase가 다른 Phase와 만나는 지점.
- 입력 (이전 Phase에서 받음)
- 출력 (다음 Phase로 넘김)
GLOSSARY.md의 어느 부분을 따르는지 명시.

## 종료 조건
다음 Phase로 넘어가기 위해 충족해야 할 조건들.
- [ ] 조건 1
- [ ] 조건 2

## 헌법 관련 주의사항
이 Phase에서 특히 신경 써야 할 헌법 원칙.

## 리스크
예상되는 어려움과 대응 방안.

## 추정 기간
N주 (전업 기준)
```

## plan 템플릿

```markdown
# Phase N 구현 계획

## brief 요약
Phase의 핵심 목표 1~2줄.

## 작업 분해 (WBS)
구체적인 작업 항목을 순서대로 나열.
- [ ] 작업 1: 설명, 예상 1일
- [ ] 작업 2: ...

## 기술적 결정사항
구현 시 내릴 기술적 선택들. 큰 결정은 ADR로 별도 기록.

## 파일 구조 변경
새로 생성할 파일/폴더, 수정할 파일.

## 테스트 계획
어떻게 검증할 것인가.

## 일일 진행 체크포인트
주요 마일스톤.
```

## completion 템플릿

```markdown
# Phase N 완료 보고

## 완성된 산출물
brief의 산출물 목록과 매핑.

## 종료 조건 충족 여부
- [x] 조건 1: 충족 (근거: ...)
- [x] 조건 2: 충족
- [ ] 조건 3: 미충족 (사유: ...)

## 발견된 이슈
구현 중 발견된 예상 외 이슈와 처리 방법.

## 다음 Phase에 영향 줄 변경사항
- 인터페이스 변경 (GLOSSARY.md 갱신 여부)
- 새 ADR (04_DECISIONS.md 갱신)
- 환경 변경

## 메트릭
- 소요 시간: N일
- LLM 호출 수 / 비용: $X (해당 시)
- 추가된 코드 라인 수
- 추가/수정된 테이블 수

## 회고
잘된 점, 개선할 점.
```

## audit 템플릿

```markdown
# Phase N 감사 보고서

## 감사 범위
검토한 문서 목록.

## 헌법 부합 여부
헌법의 각 절대 원칙을 점검.
- §2.1 LLM 직접 주문 금지: 부합 / 위반 / 해당 없음
- §2.2 계층 분리: 부합 / 위반 / 해당 없음
- §2.5 구조화 출력: ...

## 시나리오 진척도
이 Phase로 SCENARIO.md의 어느 부분이 구현 가능해졌는가.

## 인터페이스 일관성
GLOSSARY.md 정의와 실제 구현이 일치하는가.

## 발견된 위험
헌법·시나리오·아키텍처에서 벗어난 부분이 있는가.

## 권고 사항
다음 Phase 진입 전 보완해야 할 것.

## 종합 의견
- ✅ 통과 / ⚠️ 조건부 통과 / ❌ 보완 후 재감사
```

---

*Phase 문서는 영속 기록이다. 한 번 작성하면 삭제하지 않는다. 문제가 발견되면 새 문서를 추가한다.*
