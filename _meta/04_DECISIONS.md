# 의사결정 로그 (Architecture Decision Records)

> 이 문서는 프로젝트 진행 중 내린 주요 결정과 그 사유를 기록한다.  
> 모든 결정은 시간 순서로 추가되며, 한 번 기록된 결정은 삭제하지 않는다.  
> 결정을 번복할 때는 새 ADR을 작성하고, 기존 ADR의 상태를 "Superseded"로 표시한다.

---

## ADR 작성 형식

각 결정은 아래 형식으로 기록한다:

```markdown
## ADR-NNN: 제목

- **날짜**: YYYY-MM-DD
- **상태**: Accepted | Superseded by ADR-XXX | Deprecated
- **결정자**: 사용자 / Architect / 협의

### 컨텍스트
어떤 상황에서 이 결정이 필요했는가?

### 결정
무엇을 결정했는가?

### 사유
왜 그렇게 결정했는가? 다른 선택지는 무엇이었는가?

### 결과 / 영향
이 결정이 시스템에 어떤 영향을 미치는가?
```

---

## ADR-001: 시스템을 4계층 아키텍처로 구성한다

- **날짜**: 2026-04-23
- **상태**: Accepted
- **결정자**: 사용자 + Architect 협의

### 컨텍스트
미너비니 트레이딩 시스템을 구축할 때 12개의 요구사항(데이터 적재부터 자동 매매, 통계까지)을 어떻게 구조화할 것인가의 문제.

### 결정
시스템을 4개 계층으로 분리한다:
1. 결정론적 코어 (LLM 호출 없음)
2. LLM 분석 레이어 (단발 호출)
3. 자동화 파이프라인
4. 에이전트 레이어 (대화형, 도구 사용)

### 사유
- 모든 작업을 "에이전트화"하는 것은 과잉 설계이며 비용·안정성·디버깅 측면에서 불리하다.
- 각 작업의 성격에 맞는 구현 방식이 다르다 (규칙 기반 / 단발 LLM / 자동화 / 에이전트).
- 계층을 분리하면 위험한 부분(주문 실행)을 가장 안쪽에 격리할 수 있다.

### 결과 / 영향
- 12개 요구사항을 각 계층에 배치한다 (ARCHITECTURE.md 참조).
- 각 계층의 의존성은 단방향(위에서 아래)으로만 흐른다.
- 헌법의 절대 원칙들이 이 구조에 종속된다.

---

## ADR-002: LLM은 절대 직접 주문을 실행하지 않는다

- **날짜**: 2026-04-23
- **상태**: Accepted
- **결정자**: 사용자 + Architect 협의

### 컨텍스트
자동 매매 시스템에서 LLM이 어디까지 권한을 가질 것인가의 문제. "AI가 매매까지 다 해주면 편하지 않을까?"라는 유혹.

### 결정
LLM과 에이전트는 분석·조언·제안만 한다. 모든 실제 주문은 결정론적 코드(if-then 규칙)가 실행한다. LLM의 출력이 주문으로 이어지는 모든 경로에 사용자 승인 게이트가 존재한다.

### 사유
- LLM은 비결정적이며, "10번 중 1번 이상 행동"이 발생할 수 있다.
- 실제 돈이 걸린 주문에서 그 1번이 치명적이다.
- 주문 실행은 명확한 규칙으로 표현 가능하므로 LLM이 필요 없다.
- 사용자의 통제권을 양도하지 않는다는 가치와 부합한다.

### 결과 / 영향
- 헌법 §2.1로 명문화됨.
- (9) 자동 주문 엔진은 순수 결정론적 코드로 구현된다.
- LLM/에이전트는 주문을 "제안"할 수 있으나 "실행"할 수 없다.

---

## ADR-003: LLM 호출은 Anthropic API를 사용한다 (Claude Code CLI 미사용)

- **날짜**: 2026-04-23
- **상태**: Accepted
- **결정자**: 사용자 + Architect 협의

### 컨텍스트
LLM 호출 방식을 결정해야 한다. 옵션은 두 가지였다:
1. Anthropic API (pay-per-token)
2. Claude Pro/Max 플랜 + Claude Code CLI

### 결정
프로덕션 LLM 호출은 모두 Anthropic API를 사용한다. Claude Code CLI는 개발·실험·프롬프트 튜닝 용도로만 사용한다.

### 사유
- **약관 측면**: Claude Pro/Max 플랜은 개인 사용자의 대화형 사용을 전제로 하며, 자동화된 백엔드가 CLI를 호출하는 형태는 약관 위반 가능성이 있다. Anthropic은 Claude Code 24/7 자동 사용을 제한하기 위해 사용량 제한을 강화한 바 있다.
- **기술 측면**: CLI는 대화형 터미널 세션용으로 설계되어, 백엔드가 subprocess로 호출하는 구조는 세션 관리·스트리밍 파싱·인증 측면에서 불안정하다.
- **비용 측면**: 일일 50종목 분석 + Q&A 비용은 API로 월 $20~40 수준 예상. Max 20x 플랜($200/월)보다 저렴하다.
- **분리 원칙**: "Max는 개발용, API는 프로덕션용"으로 분리하면 Max 플랜의 유용성도 유지된다.

### 결과 / 영향
- 모든 LLM 호출 모듈은 Anthropic API SDK를 사용한다.
- API 키 관리 정책 필요 (환경변수, .env, 로테이션 등).
- 비용 모니터링 대시보드 필요.
- Max 플랜은 사용자가 별도로 구독하여 개발 작업에 활용한다.

---

## ADR-004: LLM 분석은 일일 배치로 수행한다 (장중 분석 미포함)

- **날짜**: 2026-04-23
- **상태**: Accepted
- **결정자**: 사용자 + Architect 협의

### 컨텍스트
LLM 분석을 어느 시점에 수행할 것인가? 옵션:
1. 일일 배치 (장 마감 후 1회)
2. 장중 실시간 (가격 변동마다)
3. 사용자 요청 시

### 결정
일일 배치로만 수행한다. 장중 LLM 분석은 명시적 비목표로 둔다.

### 사유
- 미너비니 방법론은 일봉 기반 스윙 트레이딩이며, 장중 LLM 분석이 주는 추가 가치가 적다.
- 장중 분석은 비용을 폭발적으로 증가시킨다.
- 사용자 시간 부담을 30~60분/일 이내로 유지하려면 미리 분석된 결과를 검토하는 패턴이 적합하다.
- 장중 의사결정은 사전 정의된 if-then 규칙 (9)이 처리한다.

### 결과 / 영향
- 시나리오는 "아침 검토 → 장중 자동 실행" 패턴이 된다.
- 이 결정이 향후 부적절하다고 판단되면 ADR-XXX로 번복 가능.

---

## ADR-005: 프로젝트 거버넌스를 영속 문서 기반으로 운영한다

- **날짜**: 2026-04-23
- **상태**: Accepted
- **결정자**: 사용자 + Architect 협의

### 컨텍스트
사용자는 큰 프로젝트를 진행할 때 "길을 잃는" 문제를 경험해왔다. AI 세션은 휘발성이라 컨텍스트가 사라진다. 어떻게 일관성을 유지할 것인가?

### 결정
모든 거시적 결정은 `_meta/` 폴더의 영속 문서로 관리한다. AI 세션은 매번 이 문서를 읽어서 컨텍스트를 복원한다.

문서 구조:
- `00_CONSTITUTION.md` (불변)
- `01_ARCHITECTURE.md` (큰 변경 시만 수정)
- `02_SCENARIO.md` (큰 변경 시만 수정)
- `03_ROADMAP.md` (Phase 종료 시 갱신)
- `04_DECISIONS.md` (이 문서, 결정 시마다 추가)
- `05_GLOSSARY.md` (인터페이스 정의, 변경 시 갱신)
- `06_CURRENT_STATE.md` (자주 갱신)
- `phases/` (Phase별 brief / progress / audit)

역할:
- **Architect** (Web Claude): 거시 계획, Phase brief 작성, 큰 설계 결정, 감사 지시
- **Builder** (Claude Code CLI): 일상적 개발. `_meta/phases/phaseN_progress.md`에만 자유롭게 쓰기 가능. 다른 `_meta/` 문서는 Architect 세션에서만 수정.
- **Auditor** (별도 Web Claude 세션): Phase 종료 시 헌법 부합 여부 평가

SSoT(Single Source of Truth)는 **로컬 Git 저장소**이다. 웹 Claude 프로젝트에 올라간 파일은 읽기용 스냅샷이며, 사용자가 수동으로 재업로드하여 갱신한다.

### 사유
- AI는 휘발성이지만 문서는 영속적이다.
- 매 세션 시작 시 문서를 읽는 의식(ritual)이 길 잃기 방지의 핵심이다.
- 역할을 분리하되 AI 세션 수는 최소화 (3개)해서 메타 작업 비용을 통제한다.

### 결과 / 영향
- 저장소 루트의 `CLAUDE.md`에 `_meta/` 폴더 우선 읽기 지침을 명시한다.
- Phase 시작/종료 시 명확한 의식이 정의된다.
- 모든 의사결정은 추적 가능해진다.
- Builder가 `_meta/` 문서 간 불일치를 발견하면 수정하지 않고 사용자에게 보고한다.

---

## ADR-006: 인디케이터는 long-form으로 저장한다 (Phase 0에서 이미 채택, 소급 기록)

- **날짜**: 2026-04-24 (Phase 0에서 내려진 결정을 Phase 1 착수 전 정합성 검토에서 소급 기록)
- **상태**: Accepted
- **결정자**: Phase 0 사용자 결정 (소급 기록)

### 컨텍스트
Phase 0 구축 당시, 인디케이터(SMA, EMA, RS Rating, RS Line, Blue Dot 등)를 DB에 어떻게 저장할 것인가의 문제. 두 가지 주요 방식:
1. **Wide-form**: 컬럼으로 인디케이터 표현 (`sma_50, sma_100, sma_200, ...`)
2. **Long-form**: 행으로 인디케이터 표현 (`(symbol, date, indicator, params_hash, value)`)

초기 설계 문서(`05_GLOSSARY.md` 초안)는 wide-form을 상정했으나, 실제 Phase 0 구현은 long-form을 채택했다.

### 결정
모든 인디케이터 테이블을 long-form으로 유지한다.

PK: `(symbol, date, indicator, params_hash)`

대상 테이블:
- `stock_indicators`, `stock_indicators_weekly`
- `us_stock_indicators`, `us_stock_indicators_weekly`
- `kr_index_indicators`, `kr_index_indicators_weekly`
- `us_index_indicators`, `us_index_indicators_weekly`
- `crypto_indicators_daily`, `crypto_indicators_weekly`

Wide-form 조회가 필요한 경우(프론트엔드 차트 등)는 DB 뷰(`v_*_price_with_ma`)를 통해 제공한다.

### 사유
- **확장성**: 새 인디케이터 추가 시 `ALTER TABLE`이 불필요. 현재도 SMA 4종(50/100/150/200), EMA, RS Line, RS Rating, Blue Dot 등이 혼재.
- **파라미터 다변화**: 같은 인디케이터를 다른 파라미터로 돌린 결과(`params_hash`로 구분)를 자연스럽게 저장. 백테스트에서 파라미터 스윕을 할 때 필수.
- **업계 관행**: 시계열 데이터베이스에서 (entity, time, metric_name, value) 형태는 표준 패턴이다.
- **뷰로 호환성 유지**: Wide-form이 편한 쿼리는 뷰로 제공하므로 프론트·API 레이어에서 long-form을 의식할 필요 없음.

### 결과 / 영향
- `05_GLOSSARY.md`의 `daily_indicators` 스키마 설명은 long-form을 따르도록 갱신됨.
- Phase 1의 LLM 분석 모듈(`analyze_chart`)은 뷰(`v_stock_price_with_ma` 등)를 통해 wide-form으로 데이터를 받는 것을 권장.
- 새 인디케이터 추가 절차는 CLAUDE.md의 "Adding New Indicators" 섹션 참조.

---

## ADR-007: OHLCV와 스크리닝 결과를 시장별 테이블로 분리한다 (Phase 0에서 이미 채택, 소급 기록)

- **날짜**: 2026-04-24 (소급 기록)
- **상태**: Accepted
- **결정자**: Phase 0 사용자 결정 (소급 기록)

### 컨텍스트
가격 데이터(OHLCV)와 미너비니 스크리닝 결과 테이블을 시장(KR/US/Crypto) 통합으로 둘지, 시장별로 분리할지의 문제. 초기 설계 문서는 단일 `daily_ohlcv`, `template_pass` 테이블을 상정했으나, 실제 Phase 0 구현은 시장별 분리를 채택했다.

### 결정
다음 테이블들을 시장별로 분리한다:

**가격**:
- KR 주식: `stock_prices`, `stock_prices_weekly`
- US 주식: `us_stock_prices`, `us_stock_prices_weekly`
- KR 지수: `kr_index_prices`, `kr_index_prices_weekly`
- US 지수: `us_index_prices`, `us_index_prices_weekly`
- 크립토: `crypto_prices_daily`, `crypto_prices_weekly`

**스크리닝**:
- `minervini_screen_results_kr`
- `minervini_screen_results_us`

**LLM 분석 결과 (Phase 1에서 도입)**:
- `daily_analysis_kr`
- `daily_analysis_us`

### 사유
- **스키마 요구 차이**: 크립토는 소수점 정밀도 `DECIMAL(28,10)`이 필요하지만 주식은 `DECIMAL(18,4)`으로 충분. 통합 테이블이면 주식 행에서 불필요한 큰 컬럼이 낭비됨.
- **필드 차이**: `adj_close`는 주식만, `volume_quote`는 크립토만 필요. 지수는 `adj_close` 없음.
- **운영 격리**: 특정 시장 배치 실패가 다른 시장에 영향을 주지 않음. `TRUNCATE`·재적재·마이그레이션이 시장 단위로 안전하게 가능.
- **심볼 충돌 방지**: KR `005930`과 US `005930`이 겹칠 이론적 가능성 제거 (실제로 분리되어 있으므로 PK는 `(symbol, date)`만으로 충분).
- **설계 이상보다 현실 우선**: 추상적 통일성보다 운영 안정성이 낫다.

### 결과 / 영향
- `05_GLOSSARY.md`는 각 테이블 그룹을 모두 나열하는 형태로 유지됨.
- Phase 1의 `daily_analysis` 테이블도 **이 패턴을 따라 `_kr`/`_us`로 분리**됨 (ADR-009 참조).
- 모듈 함수 시그니처는 `market` 파라미터를 받아 내부에서 적절한 테이블을 라우팅한다.

---

## ADR-008: 스크리닝 결과는 `screen_config_hash`로 설정 버전을 관리한다 (Phase 0에서 이미 채택, 소급 기록)

- **날짜**: 2026-04-24 (소급 기록)
- **상태**: Accepted
- **결정자**: Phase 0 사용자 결정 (소급 기록)

### 컨텍스트
미너비니 트렌드 템플릿의 파라미터(RS Rating 임계값, 52주 고가 대비 %, Blue Dot 사용 여부 등)는 시간이 지나며 튜닝된다. 설정이 바뀌었을 때 과거 결과와 신규 결과를 어떻게 구분할 것인가?

또한, `minervini_screen_results_*`의 저장 정책: **통과 종목만 INSERT**인가, **후보 전체(탈락 종목 포함) INSERT**인가?

### 결정
1. **설정 버전 관리**: 스크리너 설정(`minervini_kr` / `minervini_us` YAML 섹션) 전체의 SHA1 해시(`screen_config_hash`)를 계산하여 모든 결과 레코드에 기록한다. PK: `(symbol, date, screen_config_hash)`. 설정이 바뀌면 자동으로 별개 레코드 세트가 생성된다.

2. **저장 정책**: 통과 종목만 INSERT한다. 탈락 종목은 저장하지 않는다. 스키마의 `failed_reason` 컬럼은 현재 사용되지 않는 dead column이다.

### 사유
- **재현성**: 백테스트나 사후 분석 시 "과거 그 시점에 이 파라미터로 돌렸을 때의 통과 종목"을 정확히 재구성할 수 있어야 한다.
- **룰 변경 시 격리**: 새 파라미터로 재스크리닝하더라도 과거 결과와 섞이지 않음.
- **저장 용량**: 후보 전체(예: KOSPI 2천 종목 × 영업일)를 저장하면 DB가 수십 GB로 비대해진다. 통과 종목(하루 수십 ~ 수백 건)만 저장하면 수 MB~수십 MB로 충분.
- **통과 여부의 세부 정보**: Phase 1 착수 전 ADR-009에서 `conditions_met` JSON 필드를 추가하여, 통과한 종목이 **어떤 조건을 어떻게 통과했는지**를 기록한다. 탈락 원인 추적이 필요하면 그때 별도 설계로 해결한다.

### 결과 / 영향
- `screen_config_hash` 계산 함수는 `core/params.py`에 위치.
- 설정 변경 후 백필 실행 시 기존 레코드와 충돌 없이 새 레코드 생성.
- `failed_reason` 컬럼은 향후 정책 변경 시 재활용 가능성을 위해 스키마에 유지하되, 현재는 항상 NULL.
- Phase 6 이후에 "탈락 이유 분석"이 필요하면 별개 테이블(`minervini_screen_candidates_*` 등)로 분리해 설계.

---

## ADR-009: Phase 1 `daily_analysis` 테이블 설계 및 스크리너 `conditions_met` 추가

- **날짜**: 2026-04-24
- **상태**: Accepted
- **결정자**: 사용자 + Architect 협의 (Phase 1 착수 전 정합성 검토)

### 컨텍스트
Phase 1(LLM 분석 레이어) 착수 직전, 다음 세 가지 설계 결정이 필요했다:
1. `daily_analysis` 테이블을 단일 테이블로 할지, 시장별(`_kr`/`_us`)로 분리할지
2. PK를 `(symbol, date, market)`으로 할지, 기존 스크리닝 패턴을 따라 `(symbol, date)`로 할지
3. 미너비니 스크리너가 현재 **통과 조건의 부울 구조**를 저장하지 않는 점(8조건 중 구현된 6조건조차 결과 저장 안 됨)을 Phase 1 전에 해결할지

또한 헌법 §2.5 (모든 LLM 출력은 구조화된 형식으로 저장)를 만족시키기 위해 `llm_calls` 테이블이 부재한 점도 해결 필요.

### 결정

**1. `daily_analysis` 분리**: `daily_analysis_kr`, `daily_analysis_us` 두 테이블로 분리. ADR-007의 패턴을 그대로 따른다.

**2. PK = `(symbol, date)`**: KR과 US가 이미 별개 테이블이므로 symbol 충돌 가능성이 없음. 기존 `minervini_screen_results_*` 패턴과 일관되게 단순 PK 유지. `market`은 별도 컬럼으로 저장 (KOSPI/KOSDAQ/ETF 구분용).

**3. 스크리너 개편을 Phase 1 시작 전에 수행**:
   - `minervini_screen_results_kr`, `minervini_screen_results_us`에 `conditions_met JSON NULL` 컬럼을 추가 (ALTER TABLE).
   - `indicators/minervini/trend_template.py`를 개편하여 미너비니 원전의 **8개 조건** 각각을 독립적으로 평가하고, 결과를 `conditions_met` JSON으로 반환·저장한다.
   - 저장 정책은 현재처럼 **통과 종목만 INSERT**로 유지 (ADR-008).
   - 8개 조건의 키명은 `05_GLOSSARY.md` Part B.2 참조.

**4. `llm_calls` 테이블 신설**: 헌법 §2.5 준수. 모든 LLM 호출의 요청/응답/토큰/비용/지연/에러를 영구 기록.

### 사유

**분리 및 PK 결정의 근거**:
- 사용자의 명시적 지침: "기존 테이블 구조를 유지하고 없는 필드의 경우는 추가하는 방향". ADR-007의 시장별 분리 패턴을 계승하는 것이 기존 시스템에 가장 영향이 적다.
- 기존 백엔드(`query_maps.py`의 `REGION_TABLES`)가 이미 `_kr`/`_us` 분리를 가정하고 있음. `daily_analysis`도 같은 패턴이면 프론트 통합 비용이 최소.
- PK `(symbol, date)`는 기존 `minervini_screen_results_*`와 일관. market 컬럼은 조회 편의용.

**스크리너 개편을 Phase 1 전에 하는 이유**:
- Phase 1 LLM 분석은 "이 종목이 왜 통과 후보가 되었는가"를 프롬프트 컨텍스트로 받는 것이 품질에 결정적. `conditions_met`가 없으면 LLM이 "MA 정렬만 가까스로 통과"와 "모든 조건을 여유있게 통과"를 구분할 수 없음.
- 헌법 §4.2 "이해" 원칙: 사용자도 "왜 통과했는가"를 조건별로 볼 수 있어야 한다.
- 옵션 비교:
  - 옵션 A (`conditions_met` 추가만, 8조건 완전 구현은 나중): 데이터가 부실함
  - 옵션 B (저장 정책까지 "후보 전체"로 변경): 용량 폭증 + 대규모 설계 변경
  - 옵션 C (컬럼 추가 + 8조건 완전 구현 + 통과만 저장): 최소 변경, 최대 효용 → **채택**

**`llm_calls` 테이블**:
- 헌법 §2.5는 선택이 아닌 절대 원칙. Phase 1 구현 첫 주에 반드시 존재해야 함.

### 결과 / 영향

**스키마 변경 (Phase 1 brief 작성 직후, 본격 구현 시작 전 실행)**:

```sql
-- 1. 스크리너 개편 준비: conditions_met 컬럼 추가
ALTER TABLE minervini_screen_results_kr
  ADD COLUMN conditions_met JSON NULL AFTER is_blue_dot;
ALTER TABLE minervini_screen_results_us
  ADD COLUMN conditions_met JSON NULL AFTER is_blue_dot;

-- 2. daily_analysis 테이블 신설
CREATE TABLE daily_analysis_kr (
  symbol             VARCHAR(32)  NOT NULL,
  date               DATE         NOT NULL,
  market             VARCHAR(16)  NOT NULL,
  classification     VARCHAR(20)  NOT NULL,
  confidence         DECIMAL(3,2) NULL,
  reasoning          TEXT         NULL,
  pattern            VARCHAR(50)  NULL,
  risk_flags         JSON         NULL,
  entry_params       JSON         NULL,
  screen_config_hash CHAR(40)     NULL,
  llm_call_id        BIGINT       NULL,
  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (symbol, date),
  KEY idx_date_class (date, classification),
  KEY idx_date_market (date, market)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- daily_analysis_us는 동일 구조

-- 3. llm_calls 테이블 신설
CREATE TABLE llm_calls (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  timestamp         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  module            VARCHAR(50),
  model             VARCHAR(50),
  prompt_tokens     INT,
  completion_tokens INT,
  cost_usd          DECIMAL(10,6),
  request_payload   JSON,
  response_payload  JSON,
  duration_ms       INT,
  error             TEXT NULL,
  KEY idx_timestamp (timestamp),
  KEY idx_module_timestamp (module, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**코드 변경**:
- `indicators/minervini/trend_template.py` 리팩토링: 현재 `screen_minervini_trend_template()`가 반환하는 `pass_mask`에 더해, 각 조건별 boolean 2D 매트릭스(dict)를 반환하도록 확장. 스크립트(`kr_minervini_update.py`, `us_minervini_update.py`)는 통과 종목 각각의 `conditions_met` dict을 JSON으로 변환해 저장.
- 8조건의 정확한 구현은 `05_GLOSSARY.md` Part B.2 `conditions_met` 스키마 키명을 기준으로 한다.

**영향 범위**:
- 기존 배치(`daily_all.sh` 등)에는 영향 없음 — 컬럼 추가만 발생하므로 기존 INSERT·SELECT 쿼리가 그대로 동작.
- 기존 프론트엔드(`trading-view-project`)에는 영향 없음 — 추가된 컬럼을 당장 사용하지 않음.
- Phase 1 LLM 분석은 `minervini_screen_results_{region}`의 `conditions_met` 필드와 `screen_config_hash`를 프롬프트 컨텍스트에 포함한다.

---

*새로운 결정이 있을 때마다 ADR-010, ADR-011... 형태로 추가한다.*