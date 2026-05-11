# Phase 2 작업 지침서 (Brief)

> **이 문서는 Phase 2 진입 전 사용자가 읽는 문서다.**  
> Phase 2를 한 번에 끝내기 위한 모든 결정과 정보를 한 곳에 모은다.  
> 작성: 2026-05-09 (Architect 세션, Phase 1 종료 직후)  
> 갱신: Phase 2 진행 중 큰 결정이나 발견이 있을 때만 (작은 진행 사항은 `phase2_progress.md`에 기록)  
> SSoT: 이 문서는 Phase 2 한정 SSoT다. 기간 끝나면 `_meta/phases/`로 옮긴 채 사실상 동결된다.

---

## §0. 본 문서의 위상

`_meta/`의 다른 거버넌스 문서들과 Phase 2 brief의 관계:

| 문서 | 역할 | 본 brief와의 관계 |
|---|---|---|
| `00_CONSTITUTION.md` | 헌법 (변경 불가, 위배 발견 시 정지) | Phase 2는 §2.1·§2.2·§2.5 모두 준수. Phase 2A 메일 발송은 §2.1에 위배되지 않음(주문 실행 아님) |
| `01_ARCHITECTURE.md` | 4계층 정의 | Phase 2A는 계층 3 (시각화·발송), Phase 2B는 계층 1·2 보강 |
| `02_SCENARIO.md` | 사용자 시나리오 | 매일 아침 메일을 보고 수동 매매 결정 — Phase 2A로 첫 충족 |
| `03_ROADMAP.md` | 단계별 계획 | 본 brief는 Phase 2 (3~5일)의 **확장**이다. Phase 2A는 ROADMAP 본질, Phase 2B는 Phase 1 인계 sprint 통합으로 추가됨 |
| `04_DECISIONS.md` | ADR | Phase 2 진행 중 발생하는 결정은 새 ADR 또는 ADR-014 §1 카테고리에 따른 본문 수정으로 처리 |
| `05_GLOSSARY.md` | 용어·인터페이스 사전 | (5)/(6) 함수 결과를 메일·엑셀에 표시할 때 본 사전 형식 준수 |
| `06_CURRENT_STATE.md` | 현재 위치 한 페이지 | Phase 2 종료 시 갱신. Phase 1 종료 시점에 Phase 2 진입 준비 상태 명시 |
| `phase1_brief.md` | Phase 1 brief | Phase 1 종료 후 영구 보존. Phase 2 brief는 phase1_brief의 §10 (역할 분담)·§11 (범위)·§9.3 (헌법 자동 점검) 5종 검토 양식을 그대로 계승 |
| `phase1_progress.md` | Phase 1 진행 기록 | Phase 1.3 운영 결과(167행)와 §11.4-bis 4 항목이 Phase 2 sprint 입력 |
| `phase1_classification_logic_review.md` | Phase 1 분류 로직 조사 보고서 | Builder 자체 작성, Phase 2 분류 체계 개편 입력 (특히 §1.2 watch vs ignore 경계 + §6.4 entry 세분화 후처리) |
| `operational_queue.md` | 운영 작업 큐 | Q-004 대기. Phase 2 진입 전 또는 sprint 내 처리 |

본 brief는 sprint 단위로 작업을 명시한다. 각 sprint는 독립 commit/PR 단위이며, 시작 전·종료 후 phase2_progress.md에 보고를 추가한다.

---

## §1. Phase 2 통합 목표

### 1.1 한 줄 정의

**Phase 2A** (ROADMAP 본질) — 매일 아침 LLM 분석 결과를 사용자에게 메일로 자동 발송한다 (엑셀 첨부).

**Phase 2B** (Phase 1 인계 sprint) — Phase 1 미해결 이슈와 후속 sprint를 일괄 처리한다.

두 트랙은 **병렬 진행 가능**하다. 단, Phase 2A의 Sprint 1·2 (엑셀 + 메일 핵심)는 우선 완료하고, 그다음 Phase 2A Sprint 3 (자동 발송)와 Phase 2B sprint를 병렬로 진행한다.

### 1.2 Phase 2 종료 조건

다음 모두 충족 시 Phase 2 종료:

1. **Phase 2A 종료 조건**:
   - 매일 정해진 시각(예: KR 09:00 / US 17:00 KST 또는 사용자 결정)에 자동으로 메일이 발송된다
   - 사용자가 메일만 봐도 그날의 entry/watch 후보를 파악할 수 있다
   - 헌법 §2.1 준수 (LLM 직접 주문 실행 금지)
   - 헌법 §2.5 준수 (메일 발송 기록 영구 보존)

2. **Phase 2B 종료 조건** (sprint별 종료 기준 §3 참조):
   - Sprint A (entry-side 평가): §9.2 기준 1 (entry 10개 70%+ 합리적) 정식 충족 또는 자연 누적 부족 시 운용적 완화 사유 명시
   - Sprint B (Evaluator 권고 + KnownWarning 카테고리 확장): boundary 결정성 + severity 매핑 + revisit_condition 신설 + earnings warning + VCP 정량화 + KnownWarning analytical quality 10종 검토 결과 산출
   - Sprint C (ADR-015 구현): us_sync_symbol_master.py 보강 + override 테이블 + Q-004 후속 정밀화 완료
   - Sprint D (분류 안정성 모니터링): multi-evaluated 종목 일관성 정량 측정 결과 산출
   - Sprint E ((5) prompt v3 + (6) prompt v1.2 검토): 자연 누적 데이터 기반 v3/v1.2 작업 여부 결정 (Phase 1.1.15 외부 평가 후속 5종 + Phase 1.3 발견 4종 + KnownWarning analytical quality 10종 통합)
   - Sprint F (운영 부수 정리): database_schema.md 갱신 의무 명문화 + alembic.ini 자격증명 env 참조 + ADR-011/012 재검토 시점 점검

3. **Auditor 세션 PASS** — 헌법 §2.1·§2.2·§2.5·§3.1·§4 점검 (phase1_brief §9.3 5종 양식 계승)

### 1.3 Phase 2 비목표

- 페이퍼 트레이딩 / 실거래 (Phase 6)
- 대시보드 LLM 카드 표시 (Phase 3)
- Q&A 에이전트 (Phase 4)
- 백테스트 (Phase 5)
- 외부 접속 설정 (Phase 3에서 결정)

---

## §2. 진입 조건

다음 모두 충족 시 Phase 2 진입:

- [x] Phase 1 §9.1 게이트 14/14 통과 (2026-05-08, `phase1_progress.md` "Phase 1 종료 보고")
- [x] Phase 1 §9.2 운용적 완화 처리 + Evaluator 1차 평가 7건 100% 합리
- [x] Phase 1 코드 작업 완료 (`phase1/1.3-daily-analysis` 브랜치, Auditor PASS 후 머지)
- [x] _meta/ 거버넌스 6건 일괄 갱신 완료 (2026-05-09 Architect 세션 + Builder phase2/governance-update 브랜치)
- [x] ADR-014 (ADR 갱신 정책) + ADR-015 (ADR-013 확장) 채택 (2026-05-09)
- [x] Phase 2 brief 작성 완료 (본 문서)
- [ ] Auditor 세션 PASS (Phase 1 헌법 5종 점검) — Phase 2 sprint 진입 직전 필수
- [ ] Phase 1 코드 머지 (apps/, db/) — Auditor PASS 후 통합 머지
- [ ] 사용자가 본 brief를 검토하고 승인

---

## §3. Sprint 단위 작업 명세

각 sprint는 독립 commit/PR 단위. sprint 간 의존성은 명시.

### Sprint 1 (Phase 2A): 엑셀 템플릿 + 생성 함수

**목표**: 일일 분석 결과를 엑셀 파일로 생성한다.

**산출물**:
- `apps/llm-analysis/exporters/excel_exporter.py` — `daily_analysis_kr/us` + 부수 정보를 엑셀로 출력
- 엑셀 템플릿 디자인 — 시트 3개:
  - Sheet 1 "Entry 후보" — `classification='entry'` 종목 + entry_params 17필드 + key reasoning 발췌
  - Sheet 2 "Watch 후보" — `classification='watch'` 종목 + reasoning 요약 + revisit 단서
  - Sheet 3 "전체 분석" — KR + US 전 분석 결과 (classification, confidence, key_facts 일부)
- 단위 테스트 — sample 데이터로 엑셀 생성 정확성 검증
- CLI 진입점 — `apps/llm-analysis/run_excel_export.py --date YYYY-MM-DD --region kr|us|both`

**의존성**: 없음 (Phase 1 결과만 입력)

**완료 기준**:
- 임의 거래일에 대해 엑셀 생성 성공
- 엑셀이 사용자가 메일에서 열어 핵심 정보 파악할 수 있는 형태
- entry_params 17필드 모두 표기 (단, 너무 빽빽하면 핵심 6~8필드만 + 나머지는 contextual)

**예상 소요**: 1~2일

**참고**:
- openpyxl 기반 (의존성 추가)
- (5)/(6) 결과의 표시 형식은 `05_GLOSSARY.md` Part B (LLM 호출 인터페이스) 준수
- Phase 1.3 167행 표본으로 시각적 검증

---

### Sprint 2 (Phase 2A): SMTP 메일 발송 함수 + 첨부

**목표**: Sprint 1의 엑셀을 메일에 첨부하여 발송한다.

**산출물**:
- `apps/llm-analysis/exporters/email_sender.py` — SMTP 발송 (gmail SMTP 또는 사용자 선택)
- 메일 본문 템플릿 — 핵심 entry 후보 1~3건 요약 (full content는 첨부)
- 자격증명 관리 — env 또는 `~/.config/.../email_credentials` (settings.yaml 외부)
- CLI 진입점 — `apps/llm-analysis/run_email_send.py --date YYYY-MM-DD --region kr|us|both --to user@example.com`
- 단위 테스트 — mock SMTP로 발송 흐름 검증

**의존성**: Sprint 1 (엑셀 첨부 필요)

**완료 기준**:
- 임의 거래일 분석 결과를 메일 발송 성공 (사용자 자기 메일로 테스트)
- 메일 본문에서 그날 entry 후보 즉시 파악 가능
- 자격증명이 SSoT 외부에 위치 (코드·git에 노출 안 됨)
- 헌법 §2.5 준수 — 발송 기록(timestamp, recipient, attached_filename) DB 또는 로그에 영구 저장

**예상 소요**: 1일

**참고**:
- gmail은 앱 비밀번호 또는 OAuth 2.0 필요 (Phase 2A 범위에서 결정)
- KR 메일 발송 시 한글 인코딩 (UTF-8) 확인
- 메일 발송 실패 시 재시도 정책 (Phase 1 settings.yaml retry 패턴 계승)

---

### Sprint 3 (Phase 2A): 자동 발송 스케줄

**목표**: Sprint 2의 메일 발송을 매일 자동 트리거한다.

**산출물**:
- Windows Task Scheduler 작업 추가 — `EmailSend_KR`(매일 22:00 KST) + `EmailSend_US`(매일 17:00 KST 또는 사용자 결정)
- 또는 `LLMAnalysis_*` 스케줄에 메일 발송을 chain (분석 완료 직후)
- 사용자 PowerShell 스크립트 `run_email_today.ps1` (수동 트리거용)
- 모니터링 — 메일 발송 실패 시 사용자에게 어떻게 알릴지 (로그 파일 + 다음 날 메일 본문에 어제 실패 표시)

**의존성**: Sprint 2

**완료 기준**:
- 7거래일 자동 발송 성공
- 사용자가 매일 아침 메일을 보고 그날의 후보 파악 가능
- 발송 실패 시 인지 가능 (로그 또는 메일)

**예상 소요**: 1일

**참고**:
- ADR-012 자동 트리거 패턴 계승 (Task Scheduler + 모니터링)
- `LLMAnalysis_*` 작업 종료 후 chain하면 가장 깨끗 — 단, 분석이 실패한 날 메일 발송은 어떻게 할지 결정 (전날 분석으로 fallback or skip + notify)

---

### Sprint A (Phase 2B): entry-side 정량 평가 + §9.2 기준 1 정식 충족

**목표**: Phase 1.3에서 entry 0건으로 운용적 완화 처리된 §9.2 기준 1을 자연 누적으로 정식 충족한다.

**산출물**:
- 자연 누적 entry 종목 추적 — Phase 2 시장 환경에서 entry 분류 발생 즉시 Evaluator 입력
- Evaluator 평가 지속 — entry 10개 누적 시 종합 평가 (70% 이상 합리 검증)
- entry 정확도 측정 보고 — `_meta/phases/phase2_progress.md` 안에 또는 별도 `_meta/eval/phase2_entry_eval.md`

**의존성**: Phase 1.3 운영 종료 (이미 완료) + Phase 2 시장 환경에서 자연 entry 발생

**완료 기준**:
- entry 10개 이상 자연 누적
- Evaluator 평가에서 70% 이상 합리 검증
- 합리 미달 entry 패턴 분석 — 약점 도출 시 Sprint E (prompt v3) 입력

**예상 소요**: 누적 시점 대기 (Phase 2 시장 환경 의존, 2~4주 가능)

**참고**:
- Phase 1.3은 froth 시장으로 entry 자연 발생률 낮음. Phase 2에서 발생률 자연 회복 기대
- 4주 누적 후에도 entry 부족 시 운용적 완화 재검토 — Phase 2 종료 게이트에 별도 명시
- Evaluator 평가 양식: `phase1_progress.md` 1.3.10 §10.2 평가 표 양식 계승

---

### Sprint B (Phase 2B): Evaluator 권고 + KnownWarning 카테고리 확장 처리

**목표**: Phase 1.3.10 Evaluator 1차 평가에서 도출된 5종 약점 권고 + 작업 3 (2026-05-09) 발견 KnownWarning enum 카테고리 확장 검토. **6종 항목**.

**산출물 (6종 항목)**:

1. **boundary 결정성** — "얼마나 확장되어야 extended_from_ma인가" 등 정량 경계 명시
   - 후보 1: Prompt v3에 boundary 표 추가 (예: pivot 5%↑ → extended)
   - 후보 2: revisit_condition 필드 신설 (watch 분류에 부수 정보)
   - 산출물: 결정 보고 (Sprint E 입력)

2. **severity 매핑** — risk_flag 12종 enum의 severity 표 명문화 (low/med/high)
   - 산출물: severity_map.yaml (apps/llm-analysis/config/) 또는 Pydantic enum 확장
   - 본 항목은 6번(KnownWarning analytical quality 10종)과 연계 검토

3. **revisit_condition 필드 신설** — watch 분류에 "어떤 조건 충족 시 entry 재평가" 명시
   - 결정: daily_analysis_kr/us 스키마 확장? 또는 reasoning 본문에 자유 형식?
   - 산출물: ADR (스키마 확장 시) 또는 prompt v3 지시 (reasoning 본문 시)

4. **earnings warning** — 분석 시점에 가까운 earnings 일정 known_warning 자동 발행
   - 산출물: 분석 시 earnings calendar lookup + auto-emit warning 추가 (Sprint E prompt v3 영역)

5. **VCP 정량화** — VCP 패턴 인식 정량 기준 (변동성 축소 N% 이상 등)
   - 산출물: 결정 보고 + 실현 가능 시 prompt v3에 정량 기준 추가

6. **KnownWarning enum 카테고리 확장 검토** — 현재 v1.1은 "operational decision" 중심 (size 조정·stop buffer 보정 등). 추가 카테고리 후보 "analytical quality" 10종:
   - `low_rs_rating` (RS rating < 80)
   - `late_in_advance_sequence` (4번째 이상 베이스)
   - `narrow_base_for_size` (베이스 좁아 정상 size 추천 어려움)
   - `no_clear_handle` (cup_with_handle handle 미형성)
   - `prior_uptrend_borderline` (Stage 2 진입 직전 25~30% 경계)
   - `risk_reward_below_2x` ((target - pivot) / (pivot - stop) < 2.0)
   - `lone_signal_no_leadership_group` (동일 섹터·테마 함께 돌파 종목 없음)
   - `catalyst_age_exceeds_4w` (catalyst 4주 전 초과)
   - `weekly_chart_choppy` (주봉 wide-and-loose)
   - `extended_above_pivot` (현 종가 pivot 5% 이상 추격)
   - 본 항목은 Architect 세션 (2026-05-09) 작업 3 (GLOSSARY 갱신) 시 식별된 backlog. Architect가 추론으로 작성한 enum 10종이 코드의 실제 enum 10종 (operational decision 중심)과 카테고리 불일치 — 코드 SSoT 채택. analytical quality 10종은 의미상 가치 있어 sprint 입력으로 보존.
   - 검토 항목: (a) 추가 enum이 prompt v3 소비 가능한지 (b) Pydantic 모델 KnownWarning Literal 확장 (c) (5)/(6) prompt에 명시적 발행 조건 정의 (d) Sprint B 2번 severity 매핑과 통합
   - 산출물: 결정 보고 (Sprint E prompt v3 입력)

**의존성**: Sprint A의 entry 누적 시점에 일부 6종 약점 재검증 가능

**완료 기준**:
- 6종 모두 처리 결정 (구현 또는 backlog 이관 명시)
- 각 결정에 대한 ADR 또는 brief 갱신

**예상 소요**: 항목별 0.5~2일 (총 5~9일)

**참고**:
- `phase1_progress.md` 1.3.10 §10.4 부수 발견 5종 약점 표 참조
- Sprint E (prompt v3)에 영향 — 본 sprint를 우선 처리

---

### Sprint C (Phase 2B): ADR-015 구현 — Fund Vehicle 분류 보강

**목표**: ADR-015 §2 us_sync_symbol_master.py 보강 + override 테이블 신설 + Q-004 후속 정밀화.

**산출물**:

1. **us_sync_symbol_master.py 보강** (계층 1 (1))
   - 다중 소스 cross-check (FDR/yfinance + NASDAQ trader screener / ETF.com / ICI)
   - 휴리스틱 재분류 — 심볼 패턴 / Name 기반 / 거래량·AUM 기반
   - 분류 불일치 시 fund vehicle 쪽으로 안전 채택

2. **us_symbol_master_override 테이블 신설** (DB 스키마 변경)
   - ADR-010 §1 3종 산출물 패턴: Alembic + raw SQL + 운영 큐
   - (symbol, override_type, reason, set_by, set_at) 형식
   - us_sync_symbol_master.py가 override 테이블 조회 후 반영

3. **Q-004 후속 정밀화**
   - 12건 일괄 ETF 정정 후, 본 sprint에서 LEVERAGED_ETF / CEF 등 세분화 정정 (필요 시)
   - B.5.5 발견 6건 (EMF, RMT, CEE, KF, CAF) 점검 + override 테이블에 등록

4. **회고 (ADR-015 §5)**
   - us_symbol_master 분류 정확도 측정 — 100건 random sample 외부 소스 cross-check 일치율
   - 4 카테고리 false positive·false negative 측정
   - LLM Pre-Check가 잡아낸 fund vehicle 비율 측정

**의존성**: Q-004 즉시 적용 (Phase 2 sprint 진입 전 또는 sprint 내)

**완료 기준**:
- us_sync_symbol_master.py 다중 소스 + 휴리스틱 작동
- override 테이블 PROD 적용 + 검증
- 회고 측정 결과 보고 (`phase2_progress.md`)
- 자연 운영에서 fund vehicle 신규 STOCK 등록 0건 (1~2주 검증)

**예상 소요**: 2~4일

**참고**:
- ADR-013 §3 LLM Pre-Check 안전망 그대로 유지 — 본 sprint는 upstream 보강
- ADR-010 §1 패턴(Alembic + raw SQL + 운영 큐) 준수

---

### Sprint D (Phase 2B): 분류 안정성 정량 모니터링

**목표**: Phase 1.3에서 관찰된 multi-evaluated 종목 분류 toggle (ALTO 4시점 등)을 정량 측정.

**산출물**:
- 분석 스크립트 — `apps/llm-analysis/analysis/classification_stability.py`
- 측정 metric:
  - multi-evaluated 종목 분류 일관성 (같은 종목 N회 평가에서 분류 변경 빈도)
  - 분류 변경 시 confidence 변화 추적
  - watch ↔ ignore toggle 빈도 통계
  - 시장 변화 vs LLM 노이즈 분리 (예: 같은 chart에 2회 평가 시 일관성)
- 보고 — `phase2_progress.md` 또는 `_meta/eval/phase2_stability.md`

**의존성**: Phase 1.3 167행 + Phase 2 추가 누적

**완료 기준**:
- multi-evaluated 종목 30개 이상 표본 (분류 변경 vs 일관 사례)
- 시장 변화 vs LLM 노이즈 식별
- 결과에 따라 Sprint E (prompt v3) 입력 (LLM 노이즈 큰 경우)

**예상 소요**: 1~2일 (분석 스크립트) + 자연 누적 대기

**참고**:
- `phase1_classification_logic_review.md` §1.2 watch vs ignore 경계 모호 케이스 입력 활용
- Phase 1.3 ALTO 4시점, NVST 2시점 사례를 baseline으로

---

### Sprint E (Phase 2B): (5) prompt v3 + (6) prompt v1.2 검토 통합 sprint

**목표**: Phase 1.1.15 외부 평가 후속 5종 + Phase 1.3 Evaluator 약점 4종 + Sprint B/D 결과 + KnownWarning analytical quality 10종 backlog를 통합하여 prompt v3/v1.2 작업 여부 결정.

**입력 (통합 5+4+10종 + Sprint B/D)**:

Phase 1.1.15 외부 평가 후속:
1. AAOI reverse_split 누락 → price_data_notes의 split 정보를 deterministic 소비
2. completion 토큰 폭증 (v1 1,800 → v2 3,000) → ignore 케이스 "tight reasoning" 지시
3. entry 후보 5~10종 별도 검증 배치 (Sprint A에 통합)
4. reasoning 사실 정확성 sanity check — 구체 수치 vs source data 자동 비교
5. taxonomy 후보: late_stage_base, distribution_days, reversal_off_high

Phase 1.3 Evaluator 약점:
6. entry-side 검증 부재 (Sprint A 처리)
7. watch reasoning 모호성 (Sprint B 처리)
8. boundary 결정성 부족 (Sprint B 처리)
9. VCP 정량화 미비 (Sprint B 처리)

KnownWarning analytical quality 10종 (Sprint B 6번 입력):
10. low_rs_rating / late_in_advance_sequence / narrow_base_for_size / no_clear_handle / prior_uptrend_borderline / risk_reward_below_2x / lone_signal_no_leadership_group / catalyst_age_exceeds_4w / weekly_chart_choppy / extended_above_pivot — Sprint B 6번 결정 후 prompt v3 발행 조건 통합

Sprint B/D 결과:
- boundary 결정성 + severity 매핑 + revisit_condition + earnings warning + VCP 정량화 + KnownWarning 카테고리 확장 (B)
- 분류 안정성 측정 결과 (D)

**산출물**:

- (5) prompt v3 작업 여부 결정 — 작업 시 `apps/llm-analysis/prompts/analyze_chart_v3.md`
- (6) prompt v1.2 작업 여부 결정 — 작업 시 `apps/llm-analysis/prompts/calculate_entry_params_v1_2.md`
- 작업 미진행 결정 시 — 사유 명시 + Phase 3 또는 후속으로 이관

**의존성**: Sprint A·B·D 결과

**완료 기준**:
- v3/v1.2 작업 여부 결정 보고
- 작업 시 production lock 검증 (단위 테스트 + B.5.5 양식 sample 검증 + Evaluator)
- 작업 미진행 결정 시 사유 명시 + backlog 등록

**예상 소요**: 결정 1~2일 + (작업 시) 5~10일

**참고**:
- daily_analysis 테이블 prompt_version 컬럼 추가 검토 (06_CURRENT_STATE 미해결 이슈 §I) — v3/v1.2 진입 직전 결정. 운영 부담 작으면 현행 유지
- v3 작업 시 v2 결과 보존 — 06_CURRENT_STATE §I 정합

---

### Sprint F (Phase 2B): 운영 부수 정리

**목표**: Phase 1 운영 중 발견된 부수 항목 일괄 정리.

**산출물**:

1. **database_schema.md 갱신 의무 명문화**
   - Phase별 종료 시 `apps/ingest-databatcher/docs/database_schema.md` 동기화 의무 명시
   - 본 brief의 §10 또는 ADR로 격상 (Architect 판단)
   - Phase 2A/B 종료 시 첫 적용

2. **alembic.ini 자격증명 env 참조 변경** (ADR-010 §6)
   - 현재 alembic.ini에 자격증명 평문 → env 변수 참조로 변경
   - DEV·PROD 모두 동일 변수명 사용 (예: `DATABASE_URL`)
   - 마이그레이션 실행 절차 갱신

3. **DEV·PROD `alembic_version` 동기화** (ADR-010 §5, 06_CURRENT_STATE §G)
   - PROD에 `alembic_version` 테이블 도입
   - 현재 PROD 상태에 stamp (예: `20260428_000001 (head)` 또는 그 이후)

4. **ADR-011/012 재검토 시점 점검**
   - 2026-10-24 (ADR-011 채택 6개월 후) 도달 또는 사용자 판단 시점
   - 점검 항목: 약관 위반 징후 / 비용 메트릭 / Anthropic 정책 / Phase 5 백테스트 결과 (해당 시)
   - 점검 결과는 새 ADR로 기록 (재검토 결과 ADR)

5. **Q-004 PROD 적용 점검** ✅ 완료 (2026-05-10)
   - PROD 사전 확인 결과 12건 모두 자연 정정 — UPDATE 실행 불필요
   - operational_queue.md "완료된 작업" 섹션 이동 완료
   - ADR-015 Sprint C (us_sync_symbol_master.py 보강 + override 테이블) 본 항목과 무관하게 Phase 2B에서 진행

6. **PROD git 관리 원칙 — "PROD = main 유지" 명문화**

   배경: Phase 1 운영 중 Q-002·Q-003·Q-004 등 운영 큐 항목별 부분 PROD 적용이 발생했고, 사용자가 운영 단순성 차원 통찰 제기 — "PROD는 main만 유지하면 되지 왜 중간중간 동기화하나?" (2026-05-10).

   채택 원칙:
   | 원칙 | 내용 |
   |---|---|
   | PROD git 상태 | 항상 main 브랜치 유지 |
   | 중간 작업 브랜치 사용 | OK (`phase1/...`, `phase2/sprint-...` 등). 단 PROD 전환은 main 머지 시점에만 |
   | 운영 큐 PROD 적용 | main 머지 시점에 일괄 적용 (긴급 아닌 경우) |
   | 긴급 적용 예외 | 운영 진입 자체가 필요한 경우 (Q-002·Q-003 패턴) — phase1_brief §10.4-bis 1번 예외 절차에 따라 사유·범위 기록 후 적용 |

   산출물:
   - 본 항목 자체로 명문화 완료. 추가 ADR 또는 별도 문서 작성 불필요
   - phase1_brief §10.4-bis 1번 예외 절차와 정합 (긴급 예외 처리 방식 동일)

   적용 시점: 본 항목 명문화 시점부터 즉시 적용. Phase 2 이후 모든 운영 큐는 본 원칙 따름.

   예상 소요: 0일 (명문화만)

7. **거버넌스 문서 사실 정정 — 코드 SSoT 정합화** ✅ 완료 (2026-05-11)

   ADR-014 §1 (a)·(d) 카테고리 통합 처리 sprint. 코드 본질 불변, 거버넌스 문서 카운트·관찰 사후 정정.
   본 항목은 Phase 2 Sprint 1 진입 시 Builder SSoT 점검·시각 검증에서 발견된 두 건의 사실 오류를 통합 정정한다.

   **7-a: EntryParams 16→17 필드 카운트 정정** ✅ 완료 (commit `c07b37a`)

   - 발견 경위: Phase 2 Sprint 1 1.A 진입 시 Builder SSoT 점검 (L1·L2·L3) + Sprint 1 머지 후 Architect 사후 점검 (L4) + Sprint F #7 commit 1 진행 중 Builder 잔존 grep (L6).
   - 코드 SSoT: `apps/llm-analysis/models/entry_params.py` EntryParams Pydantic 모델 17필드 (v1 13필드 + v1.1 신규 4필드 `trigger_price`, `current_price`, `stop_loss_pct_from_current_price`, `observed_breakout_volume_ratio`).
   - 정정 위치 5건 일괄 처리: L1 `entry_params.py` docstring (module + class) / L2·L3 `_meta/05_GLOSSARY.md` / L4 `_meta/06_CURRENT_STATE.md` / L6 `_meta/phases/phase2_brief.md` Sprint 1 명세.
   - **L5 backlog 이관**: `_meta/phases/phase1_brief.md` line 621·1650 "13 → 16필드" 표기. phase1_brief Phase 1 종료 시점 SSoT 봉인 보존 우선. 차후 phase1_brief 갱신 필요 사항 발생 시 함께 처리 또는 Phase 2 종료 시 재검토.
   - **정정 불가** (Auditor 봉인): `_meta/phases/phase1_audit.md` line 74 "16필드" — Auditor 산출물 시간적 봉인 원칙 (§6.3 + addendum 정신). 사실 자체만 `phase2_progress.md`에 기록.
   - 카테고리: ADR-014 §1 (a) Implementation Detail 정밀화.

   **7-b: 5/6 US 26→122 사실 정정** ✅ 완료 (commit `83fcf76`)

   - 발견 경위: Phase 2 Sprint 1 1.C.2 sample 시각 검증.
   - 사실 확인: `SELECT COUNT(*) FROM daily_analysis_us WHERE date='2026-05-06';` → 122행.
   - 처리: `phase1_progress.md` §1.3.10 line 1547 본문에 인라인 괄호 footnote 추가 (봉인 본문 보존 + 사후 관찰 보강). 핵심 위치 1곳만 처리, 기타 표·헤더 위치(line 1231·1239·1412)는 본 commit 범위 밖.
   - 카테고리: ADR-014 §1 (d) 결과/영향 사후 관찰 추가 — 본 항목이 (d) 카테고리 첫 명시 사례.

   **완료 기준**:
   - ✅ 7-a 5 위치 정정 + phase2_progress.md SSoT 발견 위치 카운트 정합 (3→5)
   - ✅ 7-b phase1_progress §1.3.10 line 1547 footnote
   - ✅ 단위 테스트 회귀 0건 (149/149 passed)
   - ✅ ADR-014 §5 형식 A 인라인 이력 표기 패턴 준수

   **실제 소요**: 0.5일.

**의존성**: 항목별 독립

**완료 기준**:
- 7종 모두 처리 (완료 또는 명시적 backlog 이관)
- 각 결정 ADR 또는 brief 갱신

**예상 소요**: 항목별 0.5~1일 (총 2~4일)

---

## §4. Sprint 실행 순서 권고

```
┌─────────────────────────────────────────────────────────┐
│ Phase 2A (메일+엑셀)                                     │
│  Sprint 1 (엑셀) → Sprint 2 (SMTP) → Sprint 3 (자동)   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Phase 2B (인계 sprint, Sprint 1·2 완료 후 병렬)         │
│  Sprint C (ADR-015) — 독립, 우선 진행 가능              │
│  Sprint F (운영 부수) — 독립, 우선 진행 가능            │
│  Sprint A (entry 누적) — 시간 의존, 백그라운드          │
│  Sprint D (분류 안정성) — Sprint A와 병행               │
│  Sprint B (Evaluator 6종) — Sprint A 일부 도움          │
│  Sprint E (prompt v3) — Sprint A·B·D 결과 후 결정      │
└─────────────────────────────────────────────────────────┘
```

**권고 진입 순서**:
1. Auditor 세션 PASS → Phase 1 코드 머지 → Q-004 PROD 적용
2. Sprint 1 (엑셀) — 1~2일
3. Sprint 2 (SMTP) — 1일
4. Sprint 3 (자동 발송) + Sprint C (ADR-015) + Sprint F (운영 부수) — 병렬, 4~7일
5. Sprint A·D (자연 누적, 백그라운드) — 2~4주
6. Sprint B (Evaluator 6종) — Sprint A 진행 중 1주 시점 검토 5~9일
7. Sprint E (prompt v3) — Sprint A·B·D 결과 후 결정 + (작업 시) 5~10일

**총 예상 기간**: 4~7주 (Phase 2A 핵심은 1주, Phase 2B는 자연 누적 대기 포함하여 3~6주)

---

## §5. 작업 환경 가정

(Phase 1과 동일, 변경 없음)

- **DEV**: Mac (macOS, bash/zsh)
- **PROD**: 집 PC 24시간 (Windows + PowerShell + Task Scheduler)
- **DB**: MySQL 8.4.8 (Docker)
- **LLM**: Phase 1과 동일 (Claude Code CLI Max 플랜, ADR-011/012)
- **자격증명**: 메일 SMTP 자격증명은 Phase 2 Sprint 2에서 결정

---

## §6. 비용·상한 정책

Phase 1과 동일. Phase 2A는 LLM 추가 호출 없음 (분석 결과 후처리만). Phase 2B Sprint A·D·E는 추가 LLM 호출 가능 — Phase 1 settings.yaml의 daily_call_limits 그대로 적용.

Sprint 별 추가 비용 추정:

| Sprint | 추가 LLM 호출 | 비용 |
|---|---|---|
| Sprint 1·2·3 | 없음 | $0 |
| Sprint A | entry 자연 누적 (기존 운영 범위) | $0 (기존) |
| Sprint B | Evaluator 추가 호출 가능 (Web Claude Evaluator 프로젝트 활용 → Max 플랜) | $0~$5 |
| Sprint C | 없음 (코드 + 외부 소스 lookup만) | $0 |
| Sprint D | 분석 스크립트 (LLM 호출 없음) | $0 |
| Sprint E | (작업 시) prompt v3 검증 sample 호출 | $5~$20 (B.5.5 양식 n=400) |
| Sprint F | 없음 | $0 |

---

## §7. 헌법 준수 자동 점검

Phase 1 §9.3 5종 양식 계승. Auditor 세션에서 Phase 2 종료 시 점검:

| 헌법 항목 | 점검 방법 |
|---|---|
| **§2.1** LLM 직접 주문 실행 금지 | Phase 2A 메일 발송은 사용자 수동 매매를 위한 정보 전달 — 주문 실행 아님 ✅ |
| **§2.2** 결정론 코어와 LLM의 물리적 분리 | Phase 2A 엑셀·메일은 계층 3, Phase 2B Sprint C는 계층 1 (코드 분리 유지) ✅ |
| **§2.5** LLM 출력 영구 보존 | 메일 발송 기록 + Sprint A·B·D·E LLM 추가 호출 모두 llm_calls에 영구 보존 ✅ |
| **§3.1** 4계층 단방향 흐름 | Phase 2A는 (5)/(6) → 엑셀 → 메일 단방향. Phase 2B Sprint C는 계층 1 내부 ✅ |
| **§4** 통제권·이해 | 메일 형식·발송 시각 사용자 결정. 모든 변경 ADR 또는 brief 갱신 명시 ✅ |

---

## §8. 의식적으로 두루뭉술하게 둔 부분

다음 항목은 본 brief에서 의도적으로 결정하지 않음:

1. **메일 발송 시각** — Sprint 3 진입 시 사용자 결정 (KR 09:00 / US 17:00 KST 후보)
2. **엑셀 시트 디자인 세부** — Sprint 1 진입 시 첫 시안 후 사용자 피드백 반영
3. **prompt v3 작업 여부** — Sprint E 결정 시 sprint A·B·D 결과 종합
4. **Sprint A 자연 누적 시한** — 4주 기본, 부족 시 운용적 완화 재검토
5. **revisit_condition 필드 신설 여부** — Sprint B 검토 후 ADR 또는 prompt 본문 결정
6. **alembic.ini 자격증명 변경 시점** — Sprint F 안에서 Phase 2A 종료 후 또는 함께
7. **외부 SMTP 옵션** — Sprint 2 진입 시 gmail / 자체 메일 / 사용자 선택
8. **메일 본문 한글 vs 영문** — Sprint 2 진입 시 사용자 결정 (KR/US 분리 가능)
9. **KnownWarning analytical quality 10종 채택 범위** — Sprint B 6번 검토 후 결정 (전체 채택 / 일부만 / 전체 거부)

---

## §9. 종료 게이트 (Phase 2 종료 조건)

Phase 1 §9.1 양식 계승. 다음 모두 충족 시 Phase 2 종료:

### 9.1 자동 점검 (Builder)

1. ✅ Sprint 1·2·3 (Phase 2A 메일+엑셀) 모두 production 가동 + 7거래일 자동 발송 검증
2. ✅ Sprint C (ADR-015 구현) 완료 + 회고 측정 결과 보고
3. ✅ Sprint F (운영 부수 7종) 모두 처리 (완료 또는 명시적 backlog 이관)
4. ✅ Sprint A (entry-side 평가) 처리 — 정식 충족 또는 운용적 완화 사유 명시
5. ✅ Sprint B (Evaluator 6종) 처리 결과 보고
6. ✅ Sprint D (분류 안정성 모니터링) 결과 보고
7. ✅ Sprint E (prompt v3 검토) 결정 보고
8. ✅ database_schema.md 갱신 (Sprint F 의무 명문화 후 첫 적용)
9. ✅ 헌법 §2.1·§2.2·§2.5 위배 없음
10. ✅ 운영 큐 항목 모두 "완료된 작업" 섹션 이동 (Q-004 처리 + Phase 2 새 항목 처리)
11. ✅ `_meta/phases/phase2_progress.md` Phase 2 종료 보고 작성

### 9.2 정성 평가 (사용자)

1. 사용자가 매일 아침 메일을 보고 "쓸만하다" 판단
2. 메일 정보가 그날의 매매 결정에 충분 (정성 평가)

### 9.3 Auditor 세션 (헌법 5종 점검)

phase1_brief §9.3 양식 계승 — Auditor 세션 prompt 별도 작성 (본 brief §10 참조).

---

## §10. Auditor 세션 의뢰 프롬프트 (Phase 1 종료 점검용)

본 §10은 Phase 2 진입 직전 Auditor 세션 의뢰용 프롬프트를 제공한다. **Phase 1 종료 후 Phase 2 sprint 진입 직전 별도 Auditor 세션에서 본 프롬프트로 점검을 요청한다.**

### 10.1 Auditor 세션 의뢰 프롬프트

```
Phase 1 헌법 5종 점검을 의뢰합니다.

본 세션은 ADR-005 정의 Auditor 역할로 진행되며, _meta/ 거버넌스 문서에 직접 변경하지 않고 헌법 준수 여부를 점검 보고합니다.

【점검 대상】
- 작업 브랜치: phase1/1.3-daily-analysis (코드 미머지)
- _meta/만 main 사전 머지 commit eb09b80 (Web Claude 동기화 정합성 확보)
- _meta/ 추가 거버넌스 갱신 commit (phase2/governance-update 브랜치 — 작업 1·2·3·4·5·6 누적)
- Phase 1 종료 시점 (2026-05-08) 산출물 전체

【점검 항목 — phase1_brief.md §9.3 5종】

1. 헌법 §2.1 (LLM 직접 주문 실행 금지)
   - run_daily_analysis.py가 결과를 DB 저장만 하고 매매·발주를 트리거하지 않는지
   - llm_calls에 저장된 raw_response에 actionable order 형식 출력 사례가 있는지

2. 헌법 §2.2 (결정론 코어와 LLM의 물리적 분리)
   - 계층 1 (apps/ingest-databatcher) 코드에 LLM 호출이 없는지
   - 계층 2 (apps/llm-analysis) 코드가 계층 1 결과를 read-only로 소비하는지
   - 계층 1 → 계층 2 단방향 흐름 유지 (계층 2가 계층 1 데이터를 변경하지 않는지)

3. 헌법 §2.5 (LLM 출력 영구 보존)
   - llm_calls 테이블에 모든 (5)/(6) 호출이 저장됐는지 (Phase 1.3 167행 + Q-004 발견 12건의 etf_methodology_mismatch 안전망 호출 포함)
   - 호출 실패 케이스도 보존됐는지 (timeout/error 메타)
   - daily_analysis_kr/us의 raw_response 압축·삭제·요약 없이 저장됐는지

4. 헌법 §3.1 (4계층 단방향 흐름)
   - 1 → 2 → 3 → 4 흐름 유지 (역방향 없음)
   - LLM 분석 결과(계층 2)가 계층 1을 수정하지 않는지
   - 계층 3 (대시보드 등)이 계층 2를 직접 트리거하지 않는지 (Phase 1 시점 미구현 부분 포함 검토)

5. 헌법 §4 (사용자 통제권·이해)
   - 모든 자동 트리거 (LLMAnalysis_KR/US Task Scheduler)가 사용자 승인된 ADR-012 범위 내인지
   - ADR 본문 수정 사례 (ADR-010·011 4건)가 ADR-014 §1 카테고리에 부합하는지
   - operational_queue.md Q-001~004가 §10.4 절차를 준수했는지 (Q-004는 1번 예외 적용 인지)

【산출물】

- _meta/phases/phase1_audit.md 작성 (Auditor 세션 산출물)
- 5종 항목별 PASS / FINDING / FAIL 판정
- FAIL 발견 시 시정 권고 + Phase 2 진입 전 처리 의무 명시
- FINDING (위배 아니나 주의 필요)은 Phase 2 brief 또는 backlog로 이관

【제약】

- _meta/ 거버넌스 문서 직접 변경 금지 (Architect 권한, 본 세션 권한 밖)
- 코드 직접 변경 금지 (Builder 권한, 본 세션 권한 밖)
- 점검 결과는 phase1_audit.md로만 산출
- 본 세션은 Auditor 권한 한정으로 진행 (ADR-005 §3 정의)

【참고 문서】

- _meta/00_CONSTITUTION.md (헌법)
- _meta/04_DECISIONS.md (ADR-001~015 전체)
- _meta/06_CURRENT_STATE.md (Phase 1 종료 + Phase 2 진입 준비 상태)
- _meta/phases/phase1_brief.md §9.3 (자동 점검 5종)
- _meta/phases/phase1_progress.md (1.1~1.3.11 진행 기록 + 종료 보고)
- _meta/phases/phase1_classification_logic_review.md (Builder 자체 분류 로직 조사)
- _meta/operational_queue.md (Q-001~004 절차 준수 점검)

PASS 판정 시 Phase 2 sprint 진입.
```

### 10.2 Auditor 세션 결과 처리

- **PASS**: Phase 2 sprint 진입 → §3 sprint 1부터 시작
- **FINDING**: Phase 2 brief §3에 sprint 추가 또는 §3 sprint 본문에 보강 — Architect 세션
- **FAIL**: Phase 2 진입 보류 → 시정 후 재점검

---

## §11. 본 brief 작성 메모

### 11.1 작성 배경

본 brief는 Phase 1 종료 직후 (2026-05-09) Architect 세션 + Builder 세션 (phase2/governance-update 브랜치, 6건 작업 분리 진행)에서 작성. Phase 1 종료 보고(`phase1_progress.md` 1.3.11) + Phase 2 ROADMAP 본질(메일+엑셀) + Phase 1 인계 sprint 통합으로 구성.

### 11.2 작성 시 고려한 변수

- ROADMAP 정의의 Phase 2는 3~5일 추정이나, Phase 1 인계 sprint 통합으로 4~7주로 확장
- Phase 1 §9.2 정식 충족(entry 10개 70%+)을 Sprint A에서 처리 — 자연 누적 시점 의존성 명시
- ADR-015 채택으로 us_symbol_master 보강 sprint(C) 추가
- Evaluator 1차 평가 5종 약점을 Sprint B/E로 분리 처리 (즉시 가능 vs prompt 작업 의존성)
- prompt v3 작업 여부를 Sprint E에서 결정 (Sprint A·B·D 결과 후) — 자연 누적 데이터 부족 시 v3 작업 보류 가능
- **작업 3 (GLOSSARY 갱신, 2026-05-09) 시 Architect의 KnownWarning enum 추론 실수 발생 — 코드 SSoT(operational decision 10종)와 추론 본문(analytical quality 10종) 카테고리 불일치. 코드 SSoT 채택. 추론 10종은 Sprint B 6번 + Sprint E 입력으로 보존 (의미상 가치). 본 사건은 Architect 세션이 코드를 직접 안 보고 추론으로 작성하는 패턴의 위험을 보여줌 — 향후 코드 SSoT 의존 항목은 Builder의 head 점검에서 정정 필요.**
- **작업 4 (phase1_brief 갱신, 2026-05-09) 시 Architect 인용 commit hash 5개 오류 — Builder의 git log 점검에서 정정. 같은 패턴 (Architect가 git을 직접 안 보고 추론). 향후 commit hash·sprint 의존성 등 사실 정보 인용 시 Builder 점검 필수.**

### 11.3 미해결 이슈 매핑

`06_CURRENT_STATE.md` 미해결 이슈와 Phase 2 sprint 매핑:

| 06_CURRENT_STATE 이슈 | 처리 sprint |
|---|---|
| §B 테스트 DB currency 컬럼 | 우선순위 낮음, Sprint F backlog |
| §G alembic_version 동기화 | Sprint F |
| §H 1.1.15 외부 평가 후속 5종 | Sprint E |
| §I prompt_version 컬럼 추가 | Sprint E 진입 시 결정 |
| §J ETF 잘못 통과 | ✅ ADR-015로 해소, Sprint C 구현 |
| §K (5) v2 분류 보수성 | Sprint A + Sprint E |
| §L v1.1 fix | ✅ Phase 1.3.0 해소 |
| §M 분류 불안정 | Sprint D |
| §N database_schema 드리프트 | ✅ Phase 1.3 해소, Sprint F 갱신 의무 명문화 |

### 11.4 SSoT 정책

- 본 brief는 Phase 2 한정 SSoT
- Phase 2 진행 중 발견·결정 사항은 `phase2_progress.md`에 기록
- Phase 2 종료 후 본 brief는 영구 보존, `phase2_progress.md`는 sprint별 상세 기록 유지
- Phase 3 brief는 Phase 2 종료 후 별도 작성 (현재 미작성)

### 11.5 참고 문서

- `_meta/phases/phase1_brief.md` (양식 계승)
- `_meta/phases/phase1_progress.md` 1.3.11 종료 보고 (Phase 2 sprint 입력)
- `_meta/phases/phase1_classification_logic_review.md` (분류 체계 개편 입력)
- `_meta/04_DECISIONS.md` ADR-014/015 (본 brief 입력)
- `_meta/06_CURRENT_STATE.md` 미해결 이슈 §B/§G/§H/§I/§K/§M/§N (Phase 2 sprint 매핑)
- `_meta/operational_queue.md` Q-004 (Sprint C 입력)

---

*Phase 2 진입 직후 본 brief를 사용자가 검토. Auditor 세션 PASS 후 Builder 세션 진입.*

*마지막 업데이트: 2026-05-09 (Architect 세션, Phase 2 brief 신규 작성).*
