# 의사결정 로그 (Architecture Decision Records)

> 이 문서는 프로젝트 진행 중 내린 주요 결정과 그 사유를 기록한다.  
> 모든 결정은 시간 순서로 추가되며, 한 번 기록된 결정은 삭제하지 않는다.  
> 결정의 핵심 의미를 변경할 때는 새 ADR을 작성하고, 기존 ADR의 상태를 "Superseded"로 표시한다.  
> 단 implementation detail 정밀화·부수 항목 추가·관계 명시·사후 관찰 추가에 한해 본문 수정을 허용하며, 변경 이력 표기 의무를 진다 (ADR-014 §1·§3).

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

## ADR-010: 마이그레이션 관리 일원화 + 운영 작업 큐 도입

- **날짜**: 2026-04-24
- **상태**: Accepted
- **결정자**: 사용자 + Architect 협의 (P0.5 진행 중 발견된 이슈에 따른 결정)

### 컨텍스트

P0.5 스크리너 개편 작업 중 Builder가 다음 세 가지 구조적 문제를 발견했다 (`_meta/phases/phase0_5_progress.md` §4 참조):

1. **마이그레이션 이원화**: `apps/ingest-databatcher/scripts/migrations/*.sql`에 8개의 raw SQL 마이그레이션 파일이 존재하지만, `db/migrations/versions/`의 Alembic 체인과 분리되어 있다. `alembic upgrade head`만으로는 프로덕션과 동일 스키마에 도달할 수 없다.

2. **운영 환경 추적 누락**: 프로덕션 DB에 `alembic_version` 테이블이 없어 마이그레이션 이력이 추적되지 않았다. P0.5 작업 중 노트북(개발 환경)에는 stamp 처리했으나, 운영 환경(집 PC)에는 적용 안 됨.

3. **개발/운영 비대칭**: 개발 환경은 Mac, 운영 환경은 Windows. 같은 명령어가 두 환경에서 다르게 동작. 또한 사용자가 매일 운영 환경에 접속하지 않으므로, 개발 환경에서의 변경을 운영 환경에 적용하는 시점이 비동기적이다.

이 상태로 Phase 1을 진행하면 `daily_analysis_kr/us`, `llm_calls` 테이블 생성 등의 추가 마이그레이션이 발생할 때마다 같은 혼란이 반복된다.

### 결정

#### 1. 마이그레이션 작성 일원화 (Q1, Q2)

**향후 모든 새 스키마 변경은 다음 세 가지 산출물을 함께 만든다**:

```
새 스키마 변경 1건
  ├── ① Alembic 버전 파일 (필수, 실 적용 수단)
  │     db/migrations/versions/YYYYMMDD_NNNNNN_<설명>.py
  ├── ② Raw SQL 파일 (필수, 사람이 검토할 명세)
  │     db/migrations/sql/YYYYMMDD_NNNNNN_<설명>.sql
  └── ③ 운영 작업 큐 항목 (필수, 운영 환경 적용 절차)
       _meta/operational_queue.md 의 "대기 중인 작업"에 Q-NNN 추가
```

세 가지 모두를 작성하는 이유:
- ①은 "어떻게 자동 적용할까"
- ②는 "사람이 무엇이 바뀌는지 한눈에 본다"
- ③은 "운영 환경에서는 언제·어떻게 직접 적용할까"

**Raw SQL 위치 결정 (Phase 1 1.1, 2026-04-28)**: 신규 raw SQL은 `db/migrations/sql/`에 둔다. 본 ADR 채택 시점(2026-04-24)에는 `apps/ingest-databatcher/scripts/migrations/` 표기였으나, Phase 1.1 진행 중 다음 사유로 위치 변경:
- 본 ADR §2의 정신("기존 디렉토리에 새 raw SQL 추가하지 않는다")과 부합
- Alembic 버전 파일(`db/migrations/versions/`)과 물리적 근접 — 함께 검토·관리 용이
- 앱 독립성 — `db/`는 특정 앱(ingest-databatcher)에 종속되지 않음 (LLM 분석 테이블 등은 ingest-databatcher 작업 결과 아님)
- 첫 적용 사례: `db/migrations/sql/20260428_000001_add_daily_analysis_and_llm_calls.sql` (Phase 1 1.1.1)

#### 2. 기존 `scripts/migrations/*.sql`의 운명 (Q1)

- **그대로 보존하되, 새 raw SQL 파일을 이 디렉토리에 추가하지 않는다** ← 이번 결정 시점부터의 규칙
- 보존 이유: 과거 변경 이력의 사람-가독 기록. 신규 환경 셋업 시 참고 가능.
- P0.5의 `add_conditions_met_column.sql`은 본 ADR보다 먼저 작성되었으므로 예외로 인정. 차기 변경부터 위 §1의 ① ② ③ 패턴 강제.

#### 3. 운영 환경 적용 방식 (Q3)

**자동 적용하지 않는다. 사용자가 운영 작업 큐를 보고 의식적으로 적용한다.**

- 운영 환경 cron 안에 `git pull && alembic upgrade head`를 자동으로 끼워넣지 않음
- 사용자가 운영 환경에 접속할 때마다 `_meta/operational_queue.md`의 "대기 중인 작업"을 확인하고 순차적으로 처리
- 적용 후 항목을 "완료된 작업"으로 이동

이유:
- 자동 적용은 "DB 망가질 때 망가진 줄 모름"의 위험.
- 사용자가 운영 환경에 가는 일이 잦지 않으므로, 의식적 검토가 비용 대비 충분히 합리적.
- ADR-002·헌법 §4.1(통제권)의 정신과 부합 — 자동화의 편의보다 통제권 보존.

#### 4. 환경 인벤토리

본 프로젝트의 모든 환경:

| ID | 명칭 | 디바이스 | OS | 역할 |
|---|---|---|---|---|
| DEV | 개발 환경 | Mac 노트북 | macOS | 코드 작성, 테스트 DB 검증 |
| PROD | 운영 환경 | 집 PC | Windows | Daily/weekly cron, 실데이터 누적, MySQL 호스트 |

새 환경(예: 클라우드 백업 인스턴스, 백테스트용 별도 DB 등)이 추가되면 본 ADR을 갱신하거나 후속 ADR 작성.

#### 5. 첫 동기화 처리 방식 (Q5) — P0.5 마이그레이션 한정

**운영 환경(PROD)에 P0.5의 `add_conditions_met_column.sql`을 raw SQL로만 적용하고, `alembic_version` 테이블은 만들지 않는다.**

이후 ADR-010이 확정되어 Alembic 일원화가 본격 가동되는 시점에:
- DEV의 `alembic_version` (현재 `20260424_000001 (head)`)을 어떻게 처리할지 결정
- PROD에 `alembic_version`을 새로 만들고 적절한 revision으로 stamp
- 가능하면 **DEV·PROD가 같은 alembic 상태**가 되도록 정리

이 정리 작업은 Q-NNN 번호를 부여한 새 큐 항목으로 등록한다 (현재 시점에는 Q-001 뒤에 큐로 추가될 예정).

#### 6. alembic.ini 자격증명 처리 (Phase 1 1.1, 2026-05-02)

**`db/migrations/alembic.ini`의 `sqlalchemy.url`은 placeholder를 두지 않고, `.env`의 `DATABASE_URL`을 단일 SSoT로 참조한다.**

배경:
- Phase 1 1.1 진행 중 alembic.ini의 `sqlalchemy.url = root:root@...` placeholder가 실제 DEV 자격증명(`.env`의 `DATABASE_URL = hank:1234!`)과 불일치.
- 현재는 alembic이 DATABASE_URL 환경변수를 우선 읽는 동작으로 정상 동작 중. 그러나 두 곳에 자격증명 정보가 있어 신규 셋업 시 혼란 가능.

결정:
- **(a) alembic.ini의 url을 env 참조 방식으로 변경한다** (예: alembic env.py에서 `DATABASE_URL` 읽어 sqlalchemy.url을 동적 설정).
- placeholder는 제거 또는 주석 처리.
- **자격증명의 단일 SSoT는 `.env`의 `DATABASE_URL`**로 명문화.

근거:
- ADR-005 SSoT 원칙 부합 (자격증명 출처 1개)
- "환경변수 안 셋팅 시 alembic 명령 실패"는 정상 동작 (실패가 더 안전)
- Builder·Architect 모두 `.env`만 보면 됨

후속 작업:
- 실제 코드 변경(alembic.ini·env.py)은 Phase 1.2 또는 별도 Builder 세션에서 처리. 본 결정 자체는 ADR로 명문화 완료.
- PROD 환경의 alembic.ini 상태도 같은 시점에 점검·일치.

### 사유

**왜 raw SQL을 별도로 유지하는가**:
- Alembic Python 파일은 ORM 추상화 레벨이라 사람이 읽을 때 SQL이 즉각 보이지 않음
- DBA·데이터 분석가·미래의 자기 자신이 "이때 무슨 변경이 있었지?"를 확인할 때 raw SQL이 가장 빠름
- 작성 비용은 거의 없음 (Alembic 파일 작성 시 SQL을 어차피 머릿속에 그리고 있음)

**왜 자동 적용 안 하는가**:
- 운영 환경 1대 + 개인 프로젝트 규모에서 자동화의 ROI가 낮음
- 의식적 적용은 안전망 역할 (백업 먼저, 타이밍 확인, 검증)
- 헌법 §4.1 통제권 원칙

**왜 운영 큐를 별도 문서로 두는가**:
- ADR-005에서 정한 SSoT(로컬 Git) 원칙 안에서 동작
- 단순한 메모가 아니라 운영 절차의 일부 → 버전 관리 대상
- Builder/Architect/Auditor 모두가 참조 가능
- "지난번에 운영 환경에서 뭐 했더라?"를 영구히 추적

### 결과 / 영향

**변경 사항**:
- `_meta/operational_queue.md` 신설 (DEV/PROD 환경 정보 + Q-001 P0.5 마이그레이션 등록)
- 향후 모든 Phase brief는 "운영 환경 적용 항목" 섹션을 포함해야 함 (스키마 변경이 있는 Phase 한정)
- Builder가 새 마이그레이션 작성 시 ① Alembic ② raw SQL ③ 큐 항목 세 가지를 모두 만들도록 가이드 (Phase brief에 명시)

**Builder의 새 책임**:
- 마이그레이션 PR에 위 세 가지 산출물이 모두 포함되었는지 self-check
- 운영 환경 적용 절차(PowerShell 명령어)를 큐 항목에 정확히 작성
- 큐 항목의 위험도·타이밍 윈도우 평가

**Architect의 새 책임**:
- Phase brief 작성 시 마이그레이션 산출물 요건 명시
- ADR-010 절차 위반 시 PR 머지 거부 (Builder가 raw SQL만 만들고 큐 항목 생략 등)

**Auditor의 새 책임**:
- Phase 종료 감사 시 해당 Phase가 운영 환경에 정상 적용되었는지 (큐 항목이 "완료" 섹션에 있는지) 확인

**Phase 1 영향**:
- `daily_analysis_kr`, `daily_analysis_us`, `llm_calls` 테이블 생성 시 ① Alembic 파일 ② raw SQL 파일 ③ 큐 항목 Q-NNN 모두 작성 필요
- Phase 1 brief 작성 시 본 ADR 절차 명시 필요

**파생 결정 (후속 ADR 후보)**:
- DEV·PROD `alembic_version` 동기화 방식 — Q-001 완료 후 Q-002로 큐 등록 예정
- 새 환경 추가 시 표준 셋업 절차 ADR — 필요 시점에 ADR-011 또는 후속

---


## ADR-011: Phase 1 LLM 호출 — Max 플랜 + Claude Code CLI를 기본 백엔드로 (ADR-003의 조건부 예외)

- **날짜**: 2026-04-24
- **상태**: Accepted (조건부, §1은 ADR-012로 부분 개정됨 — 2026-04-26)
- **결정자**: 사용자 + Architect 협의
- **관련 ADR**: ADR-003 (Supersede 아닌 **조건부 예외**로 보완), ADR-009, ADR-012 (§1 부분 개정)

### 컨텍스트

ADR-003은 "프로덕션 LLM 호출은 모두 Anthropic API를 사용한다. Claude Code CLI는 개발·실험·프롬프트 튜닝 용도로만 사용한다"고 결정했다. 이 결정 시점에는 비용 추정치를 월 $20~40로 잡았다.

Phase 1 brief 작성 중 입력 페이로드의 실제 크기를 산정한 결과, 비용 추정치가 **월 $120~150** 수준으로 상향되었다 (Sonnet + 60일 일봉 + 52주 주봉 기준). 옵션 D(Haiku + 입력 다이어트)로 낮춰도 월 $20~30이지만 분석 품질 검증이 필요하다.

한편 사용자는 다음 사정에 있다:
- 개인 비상업 사용
- Claude Max 플랜을 개발 도구로 이미 가입 예정
- Phase 1은 헌법 §3.3에 따라 점진적·실험적 단계
- 비용 부담 최소화 선호

이 상황에서 ADR-003을 그대로 따르면 사용자가 결제할 의사가 있던 Max 플랜의 자원이 활용되지 않고, 별도로 API 비용이 발생한다. 합리적 대안 검토가 필요하다.

### 결정

**Phase 1 LLM 호출(모듈 (5)와 (6))의 기본 백엔드를 Claude Code CLI + Max 플랜으로 한다. 단 다음 조건을 모두 충족한다.**

#### 1. 사용 시점의 명시적 트리거

운영 환경의 daily cron 스케줄러가 무인으로 LLM 호출을 시작하지 않는다. 호출은 다음 중 하나의 방식으로 트리거된다:

- (a) 사용자가 대시보드 UI 또는 CLI에서 명시적으로 실행
- (b) 사용자가 매일 PC에 직접 접속해 수동 실행
- (c) 또는 사용자가 격일·평일 등 자기 스케줄에 맞춰 운영

요컨대 "사용자 의도가 매 호출 세트마다 개입"되어야 한다. 24/7 무인 자동화는 본 ADR의 적용 범위 밖이다.

#### 2. 백엔드 추상화 의무

`apps/llm-analysis/core/anthropic_client.py`는 다음 인터페이스를 갖는다:

```python
class LLMBackend(Protocol):
    def call(self, prompt: str, model: str, max_tokens: int) -> LLMResponse: ...

class ClaudeCodeCLIBackend: ...   # CLI 호출
class AnthropicAPIBackend: ...    # 공식 API 호출
```

호출자는 백엔드 구현을 알지 못한다. `settings.yaml`의 `llm_analysis.backend` 값에 따라 런타임에 선택:

```yaml
llm_analysis:
  backend: "cli"   # "cli" | "api"
```

이 추상화는 미래의 백엔드 전환 시 호출자 코드를 건드리지 않게 한다. 추상화 작성을 게을리하고 CLI에 직접 의존하는 코드는 ADR 위반.

#### 3. 헌법 §2.5 — LLM 호출 영구 보존

CLI 백엔드도 모든 호출을 `llm_calls` 테이블에 기록한다. 단, 다음 필드는 CLI 모드에서 NULL 또는 추정값 허용:

| 필드 | API 모드 | CLI 모드 |
|---|---|---|
| `model` | API 응답에서 정확 | CLI 호출 시 설정값 그대로 |
| `prompt_tokens` | API 응답에서 정확 | tiktoken 또는 추정 |
| `completion_tokens` | API 응답에서 정확 | tiktoken 또는 추정 |
| `cost_usd` | 정확 계산 | NULL 허용. 또한 CLI가 stdout으로 회신하는 참고값(Max 플랜 토큰 환산 추정치) 저장 가능 (Phase 1 1.1.4-b 결정, 선택지 β) |
| `request_payload` | 정확 | 정확 (CLI에 전달한 프롬프트) |
| `response_payload` | 정확 (구조화 JSON) | CLI stdout 캡처 (마크다운 펜스 등 후처리) |
| `duration_ms` | 정확 | 정확 (subprocess wall time) |
| `error` | 정확 | stderr 캡처 또는 파싱 실패 메시지 |

추정 토큰 수를 사용한 경우 별도 컬럼이 아니라 `request_payload` JSON 안에 메타로 기록 (`{"prompt_tokens_estimated": true}`).

**`cost_usd`의 의미 (Phase 1.1.4-b, 2026-04-29 명시)**:
- API 모드: 실제 API 청구액 (정확)
- CLI 모드 NULL: Max 플랜은 정액제 — 호출당 한계비용이 0에 수렴
- CLI 모드 참고값: CLI가 stdout으로 회신하는 토큰 환산 추정치를 그대로 저장. 회계상 청구액 아님. **운영 모니터링·트렌드 관측용**.
- 두 모드 식별 메타: `request_payload` JSON 안에 `cost_source` 키로 명시 (`"api_billing"` / `"cli_estimate"` / `"max_plan_billing"`)
- ADR-012 §3.4의 cost 임계 모니터링은 이 참고값으로도 동작 가능

#### 4. 약관 위험 인식

본 ADR은 Claude Pro/Max 플랜의 약관에 대한 회색 지대 운영임을 명시한다. 사용자는 다음을 인지한다:

- Anthropic이 자동화·프로그래매틱 사용을 제한해왔으며, 정책은 시간에 따라 변할 수 있다
- "사용자 명시적 트리거"는 자동화로 해석되지 않을 가능성이 높지만 보장은 아니다
- 만에 하나 정책 위반으로 판정되면 Max 플랜 정지 위험이 있다 (법적 문제는 아닐 가능성 높음)

이 위험을 받아들이는 대신 비용을 절감한다는 것이 본 결정의 본질이다.

#### 5. 재검토 시점 (강제)

본 결정은 **항구적이지 않다**. 다음 시점에 강제로 재검토하고, 재검토 결과를 새 ADR로 기록한다:

- (a) Phase 5 백테스트 결과 — 시스템이 가치를 입증하면 API 전환 검토
- (b) 본 ADR 채택 후 6개월 시점 (2026-10-24) — 도달 시 Architect 세션에서 재평가
- (c) Anthropic 약관 또는 사용량 한도 정책의 의미 있는 변경 시 — 즉시 재검토
- (d) 사용자가 "API로 전환할 시점이다"라고 판단 — 즉시 재검토

위 (d) 항목이 사용자가 요청한 "내가 원하는 시점까지 CLI 기본"의 명문화다. 사용자 결정에 따라 언제든 백엔드 전환 가능.

#### 6. 전환 시 절차

CLI → API 전환 시:

1. 새 ADR 작성 (예: ADR-NNN "Phase X LLM 백엔드 API 전환")
2. `settings.yaml`의 `llm_analysis.backend`를 `"api"`로 변경
3. ANTHROPIC_API_KEY 환경 변수 셋업
4. 첫 호출 검증 (1~3종목)
5. 운영 큐 항목으로 등록 → 운영 환경 적용
6. `06_CURRENT_STATE.md` 갱신

코드 변경은 거의 없어야 한다 (백엔드 추상화 덕분).

### 사유

**ADR-003을 supersede하지 않고 "조건부 예외"로 두는 이유**:
- ADR-003의 원칙(API 우선)은 여전히 유효하다. 24/7 무인 자동화 단계(Phase 6 자동 주문 등)에서는 API가 맞다.
- 본 ADR은 Phase 1의 실험적 단계에 한정된 예외다. 모든 시기에 적용되지 않는다.
- ADR-003을 supersede하면 미래의 자동화 Phase에서도 CLI를 쓰는 듯한 인상을 준다. "조건부 예외"가 더 정확.

**추상화 의무가 핵심인 이유**:
- 백엔드 의존을 분리하지 않으면 미래 전환 시 곳곳을 고쳐야 한다.
- Phase 1에서 `LLMBackend` 인터페이스를 잘 짜두면, 단 한 줄(`backend: "api"`)로 전환 가능.
- 추가 작업 1~2일이지만, Phase 5 또는 그 이후의 전환을 단순화한다.

**약관 위험을 명시하는 이유**:
- 거버넌스의 정직성. 헌법 §4.2 "이해" 원칙 — 사용자가 위험을 인지하고 결정한 것임을 기록.
- 만약 정책 변경으로 문제가 생기면, 본 ADR을 보고 즉시 옵션 ①로 전환할 근거가 됨.

### 결과 / 영향

**Phase 1 brief 변경**:
- §5 디렉토리 구조: `core/anthropic_client.py`를 백엔드 추상화로 설계
- §7 비용 정책: CLI 모드의 `cost_usd` NULL 허용. CLI 참고값(stdout 토큰 환산) 저장도 허용 (1.1.4-b β안). `cost_source` 메타로 두 모드 식별.
- §8 배치 통합: 자동 cron 진입점이 아닌 사용자 트리거 진입점 우선 설계
- 1.1 단계: Haiku vs Sonnet 비교는 **API 비용 시뮬레이션**이 주 목적이었으므로 우선순위 하향. CLI 모드에서는 Max 플랜 한 모델 안에서 운영.

**ANTHROPIC_API_KEY**:
- 본 결정 시점에는 필수 아님 (CLI 모드).
- 단, 백엔드 추상화의 API 구현체는 Phase 1 안에 작성·테스트 (전환 대비). 이때는 API 키 필요.

**Builder의 추가 책임**:
- `LLMBackend` 인터페이스가 깔끔히 분리되었는지 self-check
- CLI 호출 시 약관 회색 지대 인식 (예: 5시간 윈도우 한도 초과 시 합리적 백오프)
- `llm_calls` 테이블 채움 정책을 백엔드별로 정확히 구현

**Auditor의 새 책임**:
- Phase 1 종료 감사 시 `LLMBackend` 추상화의 적절성 평가
- CLI 모드 운영 중 약관 위반 징후(계정 경고, 한도 초과 빈발) 검토

**환경 변수 변경**:
- `apps/llm-analysis/.env.example`에 `ANTHROPIC_API_KEY=optional` 명시
- Builder가 README에 "본 Phase는 CLI 백엔드 기본, API는 옵션"임을 명시

**연관 문서 갱신 필요**:
- `_meta/05_GLOSSARY.md` Part C "외부 API 인터페이스 / Anthropic API"에 백엔드 선택지 명시
- `_meta/06_CURRENT_STATE.md`에 본 ADR 추가 + 재검토 일정(2026-10-24) 기록
- `_meta/01_ARCHITECTURE.md` 외부 의존성 표에 "Anthropic API or Claude Code CLI (선택)" 표기

---

## ADR-012: Phase 1 LLM 분석 자동 트리거 허용 (ADR-011 §1 부분 개정)

- **날짜**: 2026-04-26
- **상태**: Accepted (조건부, ADR-011과 함께 운영)
- **결정자**: 사용자 + Architect 협의
- **관련 ADR**: ADR-003, ADR-004, ADR-011 (§1 부분 supersede)

### 컨텍스트

ADR-011 §1은 "운영 환경의 daily cron 스케줄러가 무인으로 LLM 호출을 시작하지 않는다"고 결정했고, 사용자 명시적 트리거(대시보드 클릭, 수동 PowerShell 실행 등)만 허용했다. 이 결정의 의도는:
- Anthropic Pro/Max 플랜의 자동화 사용 제한 정책에 대한 회색 지대 회피
- 헌법 §4.1(통제권) 정신 — 자동화의 편의보다 의식적 검토

Phase 1 brief 마무리 단계에서 사용자가 다음을 검토했다:

1. **운영 현실**: 사용자가 매일 운영 환경(집 PC) 앞에 앉아 PowerShell을 직접 실행하는 시나리오는 비현실적. 출장·여행·바쁜 일정에서 분석이 자주 누락되면 7거래일 누적 검증(Phase 1 종료 조건)이 어렵다.

2. **Task Scheduler 자동화의 본질**: Windows Task Scheduler 등록은 사용자가 의식적으로 한 번 결정한 후 매일 같은 시각에 같은 작업을 반복시키는 행위다. 이는 cron 자동화이지만, "사용자가 한 번도 의도를 가진 적 없는 무인 자동화"와는 성격이 다르다.

3. **약관 위험 트레이드오프**: ADR-011 §4에서 이미 "약관 회색 지대" 위험을 인지하고 받아들였다. Task Scheduler 자동화가 이 위험을 의미 있게 증가시키는지가 핵심 질문. 결론은 "증가시키지만, 모니터링 강화로 보완 가능한 수준"이라고 판단.

4. **운영 큐 절차의 적용**: ADR-010이 정한 운영 작업 큐 절차에 따라 Task Scheduler 등록 자체가 사용자의 의식적 승인 행위(Q-NNN 항목 처리)로 기록된다. "한 번도 결정한 적 없는 자동화"가 아니다.

### 결정

**ADR-011 §1을 다음과 같이 부분 개정한다.**

#### 1. ADR-011 §1 개정 (자동 트리거 허용)

ADR-011 §1의 "운영 환경의 daily cron 스케줄러가 무인으로 LLM 호출을 시작하지 않는다" 조항을 다음으로 대체:

> 운영 환경에서 Windows Task Scheduler를 통한 LLM 분석 자동 트리거를 허용한다. 단 다음 조건을 모두 충족한다:
> - (a) Task Scheduler 등록 자체가 사용자의 의식적 승인 행위로 운영 작업 큐(Q-NNN)에 기록된다
> - (b) 본 ADR §3의 모니터링·안전장치가 모두 가동된다
> - (c) 사용자는 Task Scheduler 작업을 언제든 disable·삭제할 수 있다 (헌법 §4.1 통제권)
> - (d) 약관 위반 징후 발생 시 §4 절차에 따라 즉시 API 백엔드로 전환한다

ADR-011 §2(백엔드 추상화)·§3(llm_calls 영구 보존)·§4(약관 위험 인식)·§5(재검토 시점)·§6(전환 절차)는 **그대로 유효하다**. 본 ADR은 §1만 부분 개정한다.

#### 2. 자동 트리거 시각

운영 환경의 daily cron 스케줄과 +1h30m 안전 마진 원칙(시각 정시 보정 포함)에 따라 다음 시각을 권장 기본값으로 정한다.

| Region | 트리거 시각 (KST) | 산정 근거 |
|---|---|---|
| US | **16:00** | US daily 08:00 시작, 최대 14:00 종료 + 미너비니 ~14:10 + ~1h50m 안전 마진 (정시 보정) |
| KR | **21:00** | KR daily 19:00 시작, 최대 19:30 종료 + 미너비니 ~19:40 + ~1h20m 안전 마진 (정시 보정) |

**권장값과 SSoT의 관계**:
- 본 ADR과 `apps/llm-analysis/config/settings.yaml`에 위 권장값을 명시한다 (운영 의도 문서화 목적).
- 그러나 **실제 트리거 시각의 SSoT는 Windows Task Scheduler에 등록된 값**이다. Python 프로세스는 시작 시 settings.yaml을 읽지 않으며(시각 트리거가 아니라 즉시 분석 실행이 목적), settings.yaml의 시각 필드는 사람이 운영 의도를 추적하기 위한 문서다.
- 운영 중 시각 변경 시 ① Task Scheduler 등록 갱신 ② settings.yaml 갱신 ③ 큰 변경이면 ADR 후속 수정 — 세 가지를 함께 수행한다. 절차는 운영 큐 항목으로 등록.

`settings.yaml` 표기 형식:

```yaml
analysis_trigger:
  kr:
    recommended_time_kst: "21:00"
    rationale: "KR daily(19:00 시작, 최대 19:30 종료) + 미너비니(~19:40) + ~1h20m 안전 마진 (정시 보정)"
  us:
    recommended_time_kst: "16:00"
    rationale: "US daily(08:00 시작, 최대 14:00 종료) + 미너비니(~14:10) + ~1h50m 안전 마진 (정시 보정)"
```

#### 3. 모니터링·안전장치 (필수)

자동 트리거를 허용하는 대가로, 다음 모니터링·안전장치를 모두 가동한다.

##### 3.1 일일 호출 상한 (강제)

- `settings.yaml`의 `daily_call_limits` (KR 50건, US 50건)을 **반드시 enabled: true 로 운영**.
- `hard_stop_on_exceed: true`로 설정 — 한도 초과 시 즉시 중단, 나머지 종목 스킵.
- 자동 트리거 환경에서 한도 초과는 약관 위반 징후일 가능성이 높으므로 hard stop이 안전.

##### 3.2 실패·이상 알림 (sync_log 기록)

다음 이벤트는 모두 `sync_log`에 `WARN` 또는 `ERROR` 상태로 기록:
- 일일 호출 상한 초과
- 비용 알림 임계값 초과 (CLI 모드는 추정값)
- LLM 호출 실패율이 한 region 안에서 30% 이상
- Max 플랜 5시간 윈도우 한도 초과 (CLI 백엔드)
- 응답 파싱 실패율이 한 region 안에서 20% 이상
- Task Scheduler 작업이 예정 시각에 시작되지 못함 (작업 자체 실패는 Task Scheduler의 last run result로 별도 추적)

Phase 2 메일 발송 도입 후 위 알림은 메일로도 전송. 본 Phase에서는 sync_log 기록까지.

##### 3.3 약관 위반 징후 즉시 중단

다음 징후 중 하나라도 관측되면 자동 트리거를 즉시 비활성화하고 ADR-011 §6 절차로 API 백엔드로 전환한다:
- Anthropic으로부터 계정 경고 또는 정지 통보
- Max 플랜 사용량 한도 초과가 한 주 안에 3회 이상 반복
- CLI 백엔드 호출 실패가 약관 관련 사유로 명시적으로 거부됨

전환은 새 ADR(예: ADR-013)로 기록. 본 ADR-012는 "Superseded by ADR-013"으로 표시.

##### 3.4 호출 로그 주간 점검

매주 일요일 등 사용자가 정한 시점에 다음 쿼리로 LLM 호출 패턴을 점검:

```sql
-- 일별 호출 수 / 실패율
SELECT DATE(timestamp) AS d,
       module,
       COUNT(*) AS calls,
       SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) AS errors
FROM trade.llm_calls
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY d, module
ORDER BY d DESC, module;
```

이 쿼리 결과를 `phase1_progress.md`의 "주간 운영 메모" 섹션(Builder 세션에서 작성)에 첨부.

#### 4. 약관 위반 징후 시 즉시 API 전환

ADR-011 §6의 전환 절차를 그대로 사용. 단 자동 트리거 환경이므로 다음을 추가:
- Task Scheduler 작업 disable (즉시)
- `settings.yaml`의 `llm_analysis.backend`를 `"api"`로 변경
- `ANTHROPIC_API_KEY` 환경 변수 셋업 (운영 환경)
- 운영 큐 Q-NNN 등록 (전환 적용 절차)
- 새 ADR로 사실 기록 (이때 ADR-012는 Superseded)

#### 5. 헌법 §4.1 통제권 충족 방식

자동 트리거를 허용해도 통제권은 보존됨을 다음으로 보장:

- **언제든 비활성화 가능**: 사용자는 Windows Task Scheduler에서 작업을 disable·삭제할 수 있음.
- **킬 스위치**: `settings.yaml`의 `modules.analyze_chart: false` 설정으로 (5)·(6) 호출 자체를 차단 가능.
- **부분 비활성화**: `analyze_chart: true, calculate_entry_params: false`로 (5)만 돌리고 (6) 차단 가능.
- **결과 검토 후 매매 실행 게이트**: LLM 분석 결과는 `daily_analysis_kr/us`에 저장될 뿐, 실제 매매로 이어지는 경로는 없음 (Phase 6까지). 헌법 §2.1 위배 없음.

#### 6. 재검토 시점

ADR-011 §5의 재검토 트리거를 그대로 상속한다:
- (a) Phase 5 백테스트 결과
- (b) 2026-10-24 시점 도달 (ADR-011 채택 후 6개월)
- (c) Anthropic 약관 또는 정책의 의미 있는 변경 시
- (d) 사용자 판단 시

추가로 본 ADR 고유 트리거:
- (e) §3.3의 약관 위반 징후 관측 시 — 즉시 재검토 + API 전환

### 사유

**왜 ADR-011을 supersede하지 않고 §1만 부분 개정하는가**:
- ADR-011의 §2~§6은 여전히 정확하다 (백엔드 추상화, llm_calls 보존, 약관 위험 인식 등). 전체 supersede는 과잉.
- §1만 정확히 갱신하는 게 이력 추적 측면에서 명확.
- ADR 거버넌스 관점에서 "ADR-N의 §X절을 ADR-M이 부분 개정함"이라는 패턴은 표준적이고 깨끗하다.

**왜 자동 트리거를 허용하기로 했는가**:
- ADR-011 §1의 원래 의도("사용자 의도 매번 개입")는 약관 회색 지대 보호였다. Task Scheduler 등록은 "한 번 결정한 사용자 의도가 매일 반복 적용되는 것"으로, 정신적으로는 같은 결정.
- 매일 수동 PowerShell 실행은 비현실적이며, 7거래일 누적 검증(Phase 1 종료 조건)을 어렵게 만든다.
- 모니터링 강화(§3)로 약관 위반 징후를 빠르게 잡을 수 있다.
- 헌법 §4.1 통제권은 "Task Scheduler를 언제든 끌 수 있다"로 충족된다.

**왜 모니터링을 ADR로 명시하는가**:
- 자동 트리거를 단순 허용만 하면 위험. 모니터링 의무를 ADR 본문에 기록해서 Builder가 누락 없이 구현하게 만든다.
- Auditor가 Phase 1 종료 감사 시 §3의 각 항목이 실제로 가동되는지 점검할 수 있다.

**왜 settings.yaml과 Task Scheduler 사이의 SSoT를 Task Scheduler로 두는가**:
- settings.yaml은 Python 프로세스가 시작된 후 분석 동작을 결정하는 설정이지, 시각 스케줄링 자체를 결정하지 않는다.
- Task Scheduler가 실제로 매일 그 시각에 Python 프로세스를 띄우는 주체.
- settings.yaml의 시각 필드는 운영 의도(왜 그 시각인가)를 사람이 추적할 수 있게 하는 문서적 역할.
- 둘이 어긋나면 Task Scheduler 등록값이 진실이며, settings.yaml은 따라가야 함.

**왜 ADR-011 §6을 그대로 상속하는가 (전환 절차)**:
- 약관 위반 징후 시 전환 절차는 그대로 유효하고, ADR-012는 거기에 "Task Scheduler disable" 한 단계를 추가할 뿐.
- ADR-011의 결과 부담을 두 ADR이 나눠 짊어지지 않고 ADR-011에 일관되게 둠.

### 결과 / 영향

#### Phase 1 brief 변경 (필수)

본 ADR 채택과 동시에 `_meta/phases/phase1_brief.md`를 갱신:

- **헤더의 "관련 ADR"**에 ADR-011, ADR-012 추가
- **§7.2 일일 호출 상한**: "자동 트리거 환경에서 약관 위험 보완용으로 hard stop 강제" 한 문단 추가
- **§8 배치 통합 방식 전면 재작성**:
  - §8.1 트리거 옵션 비교 — Task Scheduler 자동 트리거를 채택으로 변경
  - §8.2 자동 트리거 시각 — US 16:00 / KR 21:00
  - §8.3 운영 환경 자동 트리거 등록 절차 (Task Scheduler 등록 + 일시 중단·재개·삭제 명령)
  - §8.4 모니터링·안전장치 (본 ADR §3 내용 요약 + 구체 구현 가이드)
  - §8.5 통제권 메커니즘 (본 ADR §5 표 정리)
  - §8.6 사용자 경험 흐름 갱신
  - §8.7 운영 큐 항목 — Q-002(DB 마이그레이션) + Q-003(Task Scheduler 등록 + 첫 실행 검증)

#### Builder의 새 책임

- Task Scheduler 등록 절차를 PowerShell 스크립트로 작성 (`apps/llm-analysis/ops/scheduler/windows/install_task.ps1` 등)
- §3.1 일일 상한 hard stop 정확 구현
- §3.2 sync_log 기록 정책 누락 없이 구현
- §3.3 약관 위반 징후 감지 로직 구현 (Max 플랜 한도 초과 카운터, 주간 임계값)
- §3.4 호출 로그 점검 쿼리를 `apps/llm-analysis/scripts/show_cost_summary.py`에 통합

#### Auditor의 새 책임

- Phase 1 종료 감사 시 §3의 각 항목이 실제로 가동되는지 표본 검증
- 자동 트리거가 실제로 작동했는지(7거래일 누적 데이터 분포로) 확인
- 약관 위반 징후가 관측되지 않았는지 sync_log·llm_calls 점검

#### 운영 큐 영향

- 본 ADR 채택과 동시에 Q-001(P0.5)는 이미 완료(2026-04-26).
- Q-002(daily_analysis + llm_calls 마이그레이션)는 Phase 1 1.1 단계에서 등록.
- Q-003(Task Scheduler 등록 + 첫 실행 검증)은 Phase 1 1.3 단계에서 등록.

#### 환경 인벤토리 영향

ADR-010의 환경 인벤토리(DEV·PROD)는 변경 없음. PROD 환경에 Task Scheduler 사용이 명시적으로 추가되는 것은 본 ADR과 Q-003에서 다룬다.

#### 연관 문서 갱신 필요

- `_meta/01_ARCHITECTURE.md` 외부 의존성 표 — Anthropic API/CLI 표기 그대로, 본 ADR은 별도 변경 없음
- `_meta/06_CURRENT_STATE.md` — ADR-012 추가, 미해결 이슈 §E(ADR-011 재검토 일정)에 ADR-012 내용 반영
- `_meta/05_GLOSSARY.md` Part C — 변경 없음

---


## ADR-013: 미너비니 스크리너에서 ETF 제외 (사용자 정책 명문화)

- **날짜**: 2026-05-02
- **상태**: Accepted (§1·§4는 ADR-015로 확장됨 — 2026-05-09)
- **결정자**: 사용자 + Architect (Phase 1 1.1.15 외부 평가 결과 반영)
- **관련 ADR**: ADR-009 (스크리너 결과 테이블 + 분석 LLM 흐름), ADR-015 (적용 범위 확장 + us_symbol_master 보강)

### 컨텍스트

Phase 1 1.1.13 단계에서 미너비니 트렌드 템플릿을 통과한 표본 5종목(US 시장)을 분석 LLM v1으로 호출했다. 외부 평가(Web Claude Minervini Evaluator 프로젝트)에서 5종목 중 2개(BWET, CLSM)가 **ETF**임이 확인됐다.

발견된 문제:

1. **방법론 불일치 (methodology mismatch)**: Mark Minervini의 SEPA·Trend Template와 William O'Neil의 CAN SLIM은 **개별 주식의 institutional accumulation·earnings catalyst·leadership** 개념 위에 구성된 방법론이다. ETF는 sector-rotation 또는 thematic 노출을 제공하는 fund vehicle이므로 위 개념들이 직접 적용되지 않는다. 평가 LLM이 책 인용으로 재확인:
   - Minervini, *Trade Like a Stock Market Wizard* (Ch. 5 Trend Template, Ch. 10 VCP) — 개별 leadership 종목 대상
   - O'Neil, *How to Make Money in Stocks* (CAN SLIM) — C(quarterly earnings), A(annual earnings), N(new product/management)는 ETF에 부재

2. **잘못된 entry 분류 발생**: v1에서 CLSM(ETF)을 `entry`로 분류한 사용자 정책 위반 발생. CLSM의 22주 flat base는 8:1 reverse split의 데이터 artifact였고, 분석 LLM이 ETF임을 인지 못 함.

3. **운영 비용 낭비**: 스크리너가 ETF를 거르지 않으면 ETF가 매일 미너비니 통과 종목으로 들어가 분석 LLM이 호출됨. 매 호출당 Max 플랜 한도 + 시간 소비. ETF 분석 결과는 사용자에게 가치 없음 (분석 대상 아님).

Phase 1 1.1.15에서 분석 LLM 프롬프트 v2에 ETF Pre-Check를 추가하여 즉시 `ignore` 처리하는 방식으로 임시 대응 했다. 그러나 이는 **분석 LLM 호출 자체를 막지 못한다** — ETF가 분석 LLM에 도달한 시점에 이미 비용 발생.

### 결정

**미너비니 스크리너 결과(`minervini_screen_results_kr`, `minervini_screen_results_us`)에서 ETF 종목을 제외한다.**

#### 1. 적용 범위

- **US 시장**: `us_symbol_master.symbol_type = 'ETF'` 행을 스크리닝 결과에서 제외
- **KR 시장**: `symbol_master`의 ETF 식별 컬럼 활용 (Phase 1.2 또는 본 ADR 구현 시점에 정확한 컬럼명·값 확인). KR 미너비니 통과 결과에서도 동일하게 ETF 제외.

#### 2. 구현 위치 (옵션)

다음 중 하나로 구현 (Builder가 결정):

**옵션 (a)**: 스크리너 자체에서 거름 (권장)
- `kr_minervini_update.py`, `us_minervini_update.py`의 SELECT 쿼리에 `JOIN <symbol_master>` + `WHERE symbol_type != 'ETF'` 추가
- 장점: ETF가 `minervini_screen_results_*` 테이블에 아예 들어가지 않음. 가장 깨끗.
- 단점: 미너비니 통과한 ETF를 별도로 보고 싶다면 별도 쿼리 필요 (현재 그런 요구 없음)

**옵션 (b)**: 분석 LLM 호출 직전에 거름
- `run_daily_analysis.py`에서 `minervini_screen_results_*`를 읽을 때 ETF 필터링
- 장점: 스크리너 자체는 그대로
- 단점: 데이터 흐름 두 단계 필요. ETF가 미너비니 통과 결과에는 남음.

**제언**: 옵션 (a) 채택. ETF 분석 안 한다는 정책이 명확하므로 데이터 자체에서 제거하는 게 일관성 측면에서 우월.

#### 3. 분석 LLM 프롬프트의 ETF Pre-Check (안전망 유지)

ADR-013 적용 후에도 v2 프롬프트의 ETF Pre-Check는 **그대로 유지**한다 (제거하지 않는다). 이유:

- 다중 안전망 — 스크리너가 거르지 못한 ETF (예: 분류 누락)가 흘러들어도 LLM이 잡음
- 사용자가 수동으로 종목을 분석에 넣을 때(`run_single_symbol.py --symbol XXXX`) ETF 보호
- 추가 비용 거의 없음 (Pre-Check는 응답 1회만 회신, 토큰 소량)

#### 4. 데이터 정리

본 ADR 구현 시점 이전에 이미 `minervini_screen_results_*`에 들어간 ETF 행은 다음 중 선택:

- **(i) 그대로 둠**: 과거 이력 보존. 신규 분석에는 ETF 안 들어감.
- **(ii) 일괄 삭제**: 과거 ETF 행을 DELETE. 깨끗하지만 이력 손실.

**제언**: (i). ADR-013 시행일 이후로만 ETF 제외. 과거 결과는 historical record로 보존. ETF 행이 daily_analysis로 흐를 일은 없으므로(분석 LLM 호출 자체를 막을 것) 무해.

### 사유

**왜 정책으로 명문화하는가**:
- "ETF는 분석 안 함"은 사용자가 일관되게 적용할 정책이고, 코드 한 군데 수정으로 보장 가능
- 명문화하지 않으면 미래 Builder가 다시 ETF를 포함시킬 수 있음 (예: 새 종목 마스터 만들 때 type 필터 누락)
- ADR-005 "거버넌스의 명문화" 정신 부합

**왜 Phase 1.2 진입 전에 처리하는가**:
- 1.2 entry 후보 검증 시 ETF가 섞이면 검증 데이터 오염
- 1.3 누적 검증에서 매일 ETF가 분석되면 약 30~50종목 중 일부가 ETF로 노이즈
- 1.1.15 외부 평가에서 이미 발견된 명확한 정책 — 미루지 말고 즉시 명문화

**KR 시장 ETF 처리를 본 ADR에 함께 포함하는 이유**:
- 정책 일관성. KR/US 비대칭 두지 않음
- KR ETF는 별도 마스터(symbol_master ETF 컬럼) 점검 필요하지만 정책 자체는 동일

### 결과 / 영향

**Phase 1 1.2 진입 전 작업**:
- 코드 변경: 옵션 (a) 채택 시 `kr_minervini_update.py`, `us_minervini_update.py` 수정
- 운영 큐 항목: 본 ADR에 따른 코드 변경은 DB 스키마 변경 없으므로 별도 큐 불필요. 머지·배포 절차로 충분.
- 검증: 코드 변경 후 다음 daily cron에서 `minervini_screen_results_us`에 ETF 행 부재 확인

**Phase 1 1.1.15 결과 영향 없음**:
- 본 ADR 시행 이전에 분석된 BWET·CLSM v2 결과는 그대로 보존
- v2의 ETF Pre-Check가 정책과 일관 동작 입증

**연관 문서 갱신 필요**:
- `_meta/01_ARCHITECTURE.md` — 계층 1 (3) 템플릿 필터 책임에 "ETF 제외" 명시 필요 시
- `_meta/05_GLOSSARY.md` Part B.1 — `minervini_screen_results_*` 설명에 "ETF 제외 (ADR-013)" 명시
- `_meta/phases/phase1_brief.md` — 1.2 entry 후보 준비 단계에 "ETF는 자동 제외됨" 안내
- `_meta/06_CURRENT_STATE.md` — ADR-013 추가, 미해결 이슈 정리

**구현 시점**:
- Phase 1.2 시작 직후 또는 1.2 진행 중 (Builder 작업)
- 가능하면 1.2의 entry 후보 종목 정의 시점과 같이 처리

### 회고 (Phase 1 종료 후 점검 항목)

- 1.3 누적 검증에서 ETF 행이 daily_analysis로 흘러들어간 사례가 있는가?
- 사용자가 수동으로 ETF를 분석한 경우 v2 ETF Pre-Check가 작동했는가?
- 본 ADR 시행 후 분석 LLM 호출 빈도가 의미 있게 줄어들었는가? (예: 매일 30~50건 → 25~45건 등)

---

## ADR-014: ADR 갱신 정책 — 본문 수정의 경계 명문화

- **날짜**: 2026-05-09
- **상태**: Accepted
- **결정자**: 사용자 + Architect 협의 (Phase 1 종료 후 부수 발견 처리)
- **관련 ADR**: ADR-005 (거버넌스 SSoT), ADR-010 §1·§6 (본문 수정 사례), ADR-011 §1·§3 (본문 수정 사례), ADR-012 (ADR-011 §1 부분 개정 사례)

### 컨텍스트

본 문서(`04_DECISIONS.md`) 헤더는 ADR 봉인 원칙을 다음과 같이 명시했다:

> "모든 결정은 시간 순서로 추가되며, 한 번 기록된 결정은 삭제하지 않는다. 결정을 번복할 때는 새 ADR을 작성하고, 기존 ADR의 상태를 'Superseded'로 표시한다."

이 원칙은 결정의 역사적 기록(history of decisions)을 왜곡하지 않기 위한 보호장치다. 그러나 Phase 1 진행 중 ADR-010·ADR-011 본문에 다음 수정이 실제로 발생했다 (`phase1_progress.md` "Phase 1 종료 보고 — Phase 2 인계 항목"에서 부수 발견으로 식별):

| ADR | 수정 유형 | 시점 | 내용 |
|---|---|---|---|
| ADR-010 §1 | 결정 보강 | Phase 1.1, 2026-04-28 | raw SQL 위치 결정 추후 정밀화 (`apps/ingest-databatcher/scripts/migrations/` → `db/migrations/sql/`) |
| ADR-010 §6 | 결정 추가 | Phase 1.1, 2026-05-02 | alembic.ini 자격증명 처리 결정 추가 |
| ADR-011 §3 | 결정 보강 | Phase 1.1.4-b, 2026-04-29 | cost_usd 필드 처리 표 — CLI 모드 NULL 허용 + 참고값 저장 가능 명시 |
| ADR-011 헤더 | 메타 갱신 | 2026-04-26 | 상태에 "§1은 ADR-012로 부분 개정됨" 표기 |

이러한 수정은 헤더 원칙의 문언과 충돌할 수 있다. 동시에, 실용적으로는 다음 같은 본문 수정이 거버넌스에 가치를 더한다:
- 결정 시점에는 추상적이었던 implementation detail이 적용 시점에 정밀화됨
- 결정이 적용된 후 사후 관찰 사실이 결과/영향 섹션에 추가됨
- 다른 ADR과의 관계가 새 ADR 작성 시 명시됨

본 ADR은 갱신 정책을 명문화하여 헤더 원칙과 실제 운영 사이의 모순을 해소한다.

### 결정

**ADR 본문 수정은 다음 조건을 모두 충족하는 경우에 한해 허용한다. 그 외에는 새 ADR + Superseded 패턴을 강제한다.**

#### 1. 허용되는 본문 수정 유형 (4 카테고리)

**(a) Implementation Detail 정밀화** (가장 흔한 케이스)
- 결정 시점에 "구현 시점에 결정"으로 두었던 사항이 후속 작업에서 정밀화될 때
- 예: ADR-010 §1의 raw SQL 위치 — 본 ADR 시점에는 `apps/ingest-databatcher/scripts/migrations/`였으나 Phase 1.1 진행 중 `db/migrations/sql/`로 정밀화
- 조건: 핵심 결정의 의미는 불변, 구현 위치/형식만 변경

**(b) 결정의 부수 항목 추가** (확장)
- 같은 결정 영역 안에서 새로 결정 필요한 항목이 발견될 때
- 예: ADR-010 §6 — alembic.ini 자격증명 처리는 ADR-010의 "마이그레이션 일원화" 결정 영역 안의 부수 결정
- 조건: 핵심 결정과 같은 영역 / 자연스러운 연속선상 / 핵심 결정을 부정하지 않음

**(c) 다른 ADR과의 관계 명시**
- 후속 ADR이 본 ADR을 참조/개정/Supersede할 때 헤더의 "관련 ADR" 또는 "상태" 갱신
- 예: ADR-011 헤더에 "§1은 ADR-012로 부분 개정됨" 추가, ADR-013 헤더에 "§1·§4는 ADR-015로 확장됨" 추가
- 조건: 사실 기록만 (해석·의도 변경 금지)

**(d) 결과/영향 섹션의 사후 관찰 추가**
- 결정이 적용된 후 관측된 실제 영향 추가
- 예: ADR-013 §"회고 (Phase 1 종료 후 점검 항목)" — 적용 후 점검 결과를 본문에 누적 가능
- 조건: 원래의 "결정"·"사유" 섹션은 불변

#### 2. 금지되는 변경 (반드시 새 ADR + Superseded)

다음 변경은 본문 수정으로 처리할 수 없다:

- **핵심 결정의 의미 변경** — 예: "ETF 제외"를 "ETF 포함"으로 변경
- **사유의 핵심 변경** — 당시 판단 근거의 사후 재서술 (역사 왜곡)
- **결정자/날짜 변경** — 역사 기록의 무결성 침해
- **부분 개정** — 한 ADR의 §N만 다른 결정으로 대체하려 할 때 → ADR-012 패턴(별도 ADR로 부분 supersede 명시)을 따른다

#### 3. 변경 이력 표기 의무

본문 수정 시 다음 둘 중 하나의 형식으로 변경 사실을 명시:

**형식 A — 인라인 표기** (작은 변경, 권장 기본)
- 변경된 절 본문에 변경 시점·사유 inline 명시
- 예: `**Raw SQL 위치 결정 (Phase 1 1.1, 2026-04-28)**: ...`

**형식 B — 변경 이력 섹션** (큰 변경 또는 다중 변경 누적)
- ADR 본문 끝에 `### 변경 이력` 섹션 추가
- 표 형식: 일자 / 변경 유형(허용 4 카테고리 중 하나) / 영향 절 / 사유

ADR 헤더의 "상태" 필드는 다음 표기를 허용:
- `Accepted` — 변경 없음
- `Accepted (Phase N N.N에서 본문 일부 갱신 — YYYY-MM-DD)` — 본문 수정 발생, 형식 B 권장
- `Accepted (§N은 ADR-XXX로 확장됨 — YYYY-MM-DD)` — 다른 ADR이 부분 개정/확장
- `Superseded by ADR-XXX` — 전체 supersede

#### 4. 04_DECISIONS.md 헤더 갱신

본 ADR 채택과 동시에 `04_DECISIONS.md` 헤더의 봉인 원칙 문언을 다음으로 갱신한다 (본 ADR 시행과 함께 일괄 처리):

> "모든 결정은 시간 순서로 추가되며, 한 번 기록된 결정은 삭제하지 않는다. 결정의 핵심 의미를 변경할 때는 새 ADR을 작성하고, 기존 ADR의 상태를 'Superseded'로 표시한다. 단 implementation detail 정밀화·부수 항목 추가·관계 명시·사후 관찰 추가에 한해 본문 수정을 허용하며, 변경 이력 표기 의무를 진다 (ADR-014 §1·§3)."

#### 5. 기존 본문 수정 사례의 소급 정합화

ADR-014 채택 시점에서, 이미 본문 수정이 발생한 ADR-010·ADR-011은 다음을 만족시킨다:

| ADR | 변경 절 | 카테고리 | 이력 표기 형식 |
|---|---|---|---|
| ADR-010 §1 | raw SQL 위치 | (a) Implementation Detail | 형식 A — "Raw SQL 위치 결정 (Phase 1 1.1, 2026-04-28)" ✅ 이미 적용 |
| ADR-010 §6 | alembic.ini 자격증명 | (b) 부수 항목 추가 | 형식 A — "(Phase 1 1.1, 2026-05-02)" ✅ 이미 적용 |
| ADR-011 §3 | cost_usd 처리 표 | (a) Implementation Detail | 형식 A — "(Phase 1.1.4-b, 2026-04-29 명시)" ✅ 이미 적용 |
| ADR-011 헤더 | 상태 표기 | (c) 관계 명시 | "§1은 ADR-012로 부분 개정됨" ✅ 이미 적용 |

위 4건은 본 ADR 기준으로 모두 허용 카테고리에 부합 + 인라인 이력 표기 충족. 별도 변경 이력 섹션 추가 없이 현 상태 유지.

### 사유

**왜 옵션 1(절대 금지)을 채택하지 않는가**:
- 절대 금지는 이상적이나 비현실적: implementation detail 갱신마다 새 ADR 작성하면 ADR 수가 폭증
- 작은 보강(예: 디렉토리 경로 정밀화)을 supersede ADR로 처리하면 ADR 그래프가 파편화되어 추적 어려움
- 거버넌스 비용 > 정확성 효익

**왜 옵션 3(현행 묵인)을 채택하지 않는가**:
- 묵인은 헤더 원칙과 실제 운영 사이의 모순 잔존
- 미래의 Builder/Architect/Auditor가 무엇이 허용·금지인지 판단 기준 없음
- ADR-005의 "거버넌스 명문화" 정신과 모순

**왜 옵션 2(허용하되 명문화)가 최선인가**:
- 실용성과 무결성의 균형
- 4 카테고리는 거버넌스 관점에서 "사실 기록·정밀화"이지 "역사 변경"이 아님
- 변경 이력 표기 의무로 추적성 확보 — Auditor가 본 ADR 기준으로 위반 여부 점검 가능
- ADR-005의 "영속 문서 기반 거버넌스" 정신 부합

**왜 헤더를 직접 갱신하는가 (§4)**:
- 헤더 원칙 문언과 본 ADR 결정이 일치하지 않으면 미래 독자가 혼란
- 헤더 갱신은 본 ADR 시행과 동시에 이뤄져야 함 (정합성 즉시 확보)

**왜 기존 사례를 소급 정합화하는가 (§5)**:
- ADR-010·ADR-011의 본문 수정은 모두 §1의 4 카테고리에 부합
- 추가 변경 이력 섹션 작성은 비용 대비 효익 낮음 (인라인 표기로 충분)
- 본 ADR이 채택된 시점부터의 향후 수정에만 새로운 형식적 요건을 적용 — 거버넌스 비용 합리화

### 결과 / 영향

**Builder의 새 책임**:
- ADR 본문 수정 시 본 ADR §1의 허용 카테고리 확인 후 진행
- 허용 외 변경은 새 ADR 작성으로 처리 (Architect 세션에서 결정)
- 변경 이력 표기 (형식 A 또는 B) 필수

**Architect의 새 책임**:
- ADR 본문 수정 시 본 ADR §1·§3 부합 확인
- 헤더 상태 필드 갱신 책임
- 옵션 2의 부수 효과 감지 (예: 한 ADR에 본문 수정이 누적되어 사실상 "다른 ADR"이 됐을 때 → 새 ADR로 분리 권고)

**Auditor의 새 책임**:
- Phase 종료 감사 시 본 ADR §1·§3 위반 사례 점검
- 핵심 결정 변경이 본문 수정으로 처리된 케이스 발견 시 시정 권고

**연관 문서 갱신 (본 ADR 시행과 동시)**:
- `_meta/04_DECISIONS.md` 헤더 — §4에 따라 봉인 원칙 문언 갱신 ✅ 본 세션 처리

**소급 적용 범위**:
- ADR-010·ADR-011의 기존 본문 수정 4건은 본 ADR 카테고리에 부합 (§5 표) — 별도 조치 없음
- 향후 모든 ADR 본문 수정은 본 ADR §1·§3 적용

---

## ADR-015: ADR-013 정책 확장 — Fund Vehicle 분류 범위 명확화 + us_symbol_master 정확성 보강

- **날짜**: 2026-05-09
- **상태**: Accepted
- **결정자**: 사용자 + Architect 협의 (Phase 1 1.3.10 발견 + Phase 2 sprint 진입 결정)
- **관련 ADR**: ADR-013 (ETF 제외 정책 — 본 ADR이 §1·§4 확장), ADR-014 (관계 명시 카테고리 적용)

### 컨텍스트

ADR-013 (2026-05-02)은 미너비니 스크리너에서 ETF를 제외하는 사용자 정책을 명문화했다. 적용 후 Phase 1 진행 중 다음 두 차례 추가 사례가 발견됐다.

#### 발견 1: B.5.5 sample 6건 (Phase 1.2 트랙 B, 2026-05-05)

B.5.5 sample 추출 시 `us_symbol_master.symbol_type='STOCK'` 필터를 적용했는데도 LLM v2가 ETF로 판정한 종목 6건:
- EMF, RMT, CEE (2회), KF, CAF

해석: 모두 closed-end fund (CEF) 또는 country fund 계열로, 명목상 STOCK으로 등록됐으나 실제로는 fund vehicle.

#### 발견 2: 1.3.10 운영 자연 발견 12건 (2026-05-08, Q-004 등록)

5/6 US 자연 운영 데이터에서 12건 추가 발견:
- VRTL, SOXL, MVLL, MUU, MULL, AMDG, AMDL, AMUU, KORU, INTW, DLLL, BWET

해석: leveraged ETF (SOXL, KORU 등 -3x bull/bear) + 신규 ETF / ETF-like vehicle. us_symbol_master.symbol_type 분류가 외부 소스(FDR/yfinance) 단계에서 부정확.

#### 공통 패턴

ADR-013은 `symbol_type='ETF'` 필터를 채택했는데, **us_symbol_master의 symbol_type 분류 자체가 불완전**하다. 다음 카테고리가 STOCK으로 잘못 등록됐을 가능성이 높음:

1. **Closed-end fund (CEF)** — EMF, RMT, CEE, KF, CAF 패턴
2. **Leveraged/Inverse ETF** — SOXL, KORU, AMDL, AMUU, MVLL, MUU, MULL, AMDG (3x bull/bear 시리즈)
3. **신규 ETF** (~6개월 내 상장) — VRTL, INTW, DLLL, BWET 후보
4. **Preferred stock·Depositary Receipt** — 본 발견 표본에는 없으나 잠재 가능성

LLM v2의 ETF Pre-Check가 conf=1.00 안전망으로 정상 작동 중 (즉각 위험 없음). 그러나 ADR-013의 적용 범위가 좁아 운영 비용·노이즈 잔존.

### 결정

**ADR-013의 적용 범위와 us_symbol_master 정확성 보강 정책을 다음으로 확장한다.**

#### 1. 적용 범위 확장 — Fund Vehicle 4 카테고리 명확화

ADR-013 §1의 "ETF 종목 제외"를 다음 4 카테고리로 명확화:

| 카테고리 | 정의 | 식별 단서 (heuristic) |
|---|---|---|
| 1. ETF (기존) | Exchange-Traded Fund | `symbol_type='ETF'` |
| 2. Leveraged/Inverse ETF | 2x/3x 또는 inverse ETF | 심볼 suffix (L/U/UU/D), name "Bull/Bear", AUM·issuer 패턴 |
| 3. Closed-end Fund (CEF) | Closed-end fund / country fund | 심볼 패턴 (XX, CEE 등), name suffix " Fund" |
| 4. ADR/Depositary Receipt (낮은 우선순위) | Depositary Receipt | 발행국이 비-US, name suffix " ADR" |

이 카테고리 모두 미너비니/O'Neil 방법론(개별 leadership stock + earnings catalyst + accumulation)의 직접 적용 대상이 아니므로 스크리너에서 제외 대상.

본 ADR 시행 후 미너비니 스크리너의 upstream 필터는 4 카테고리 모두를 제외 (정확한 SQL/JOIN 구현은 Builder가 Phase 2 sprint에서 결정 — 본 ADR은 정책 결정만).

#### 2. us_symbol_master 분류 정확성 보강

`us_sync_symbol_master.py` (계층 1 (1) 데이터 적재)에 다음 보강 로직 추가 (Phase 2 sprint):

**(a) 외부 소스 다중 검증**
- FDR/yfinance 단일 소스 의존 → 다중 소스 cross-check (예: NASDAQ trader screener, ETF.com, ICI database)
- 분류 불일치 시 ETF/CEF/LEVERAGED_ETF로 안전한 쪽 채택

**(b) 휴리스틱 재분류**
- 심볼 패턴 기반 (예: -L/-U/-UU/-D suffix → leveraged 의심)
- Name 기반 ("ETF", "Fund", "Trust", "Bull", "Bear" → fund vehicle)
- 거래량·AUM 기반 (특정 임계값 미달 시 의심)

**(c) Manual override 테이블**
- `us_symbol_master_override` 테이블 신설 (Phase 2 마이그레이션, ADR-010 §1의 3종 산출물 패턴 적용)
- (symbol, override_type, reason, set_by, set_at) 형식
- 자동 재분류로 잡히지 않는 케이스 사용자 수동 정정용

#### 3. Q-004 처리 (즉시 적용)

Phase 1.3.10에서 발견된 12건을 일괄 ETF 정정 (Q-004 운영 큐). B.5.5 발견 6건(EMF, RMT, CEE, KF, CAF)은 본 ADR 시행 시점에 별도 점검 후 Q-004 또는 후속 큐로 처리.

**Q-004 적용 절차 보강**:
- `symbol_type='ETF'` 일괄 적용 후, Phase 2 sprint에서 `LEVERAGED_ETF`/`CEF` 등으로 세분화 정정 (필요 시)
- Q-004 완료 시 점검: us_minervini_update.py 재실행 후 12건이 스크리너 결과에서 제외 확인

#### 4. 안전망 유지 (ADR-013 §3 그대로 계승)

ADR-013 §3의 "v2 프롬프트 ETF Pre-Check 유지"를 그대로 계승. 이유:
- us_symbol_master 분류가 100% 정확할 보장 없음
- 신규 상장 ETF/CEF (예: BWET처럼 최근 출시) 발견 지연 가능
- 사용자 수동 분석 (`run_single_symbol.py`) 시 다중 안전망

LLM Pre-Check 비용은 토큰 소량 (응답 1회 즉시 종료) — 안전망으로서 비용 효율 우수.

#### 5. 회고 항목 (Phase 2 종료 시 점검)

다음을 Phase 2 종료 게이트에 포함:
- us_symbol_master 분류 정확도 측정 (예: 100건 random sample 외부 소스 cross-check 일치율)
- 본 ADR §1의 4 카테고리 모두에 대한 false positive·false negative 측정
- LLM Pre-Check가 잡아낸 fund vehicle 비율 (스크리너 통과 후 LLM에서 reject되는 비율)

본 항목은 Phase 2 brief의 sprint 항목으로 등록.

### 사유

**왜 ADR-013 본문 수정이 아닌 새 ADR로 처리하는가**:
- ADR-014 §1 (a) Implementation Detail 정밀화 또는 (b) 부수 항목 추가로 본문 수정도 가능했음
- 그러나 본 ADR은 다음 영역에서 ADR-013을 의미 있게 확장:
  - 적용 범위 확장 (1 카테고리 → 4 카테고리)
  - us_symbol_master 정확성 보강 (계층 1 (1) 코드 변경 동반)
  - Manual override 테이블 신설 (스키마 변경 동반)
- 단순한 implementation detail이 아니라 새 정책 영역 확장 → 별도 ADR이 더 깨끗
- ADR-014 §1 (c) "관계 명시" 카테고리로 ADR-013 헤더에 "§1·§4는 ADR-015로 확장됨" 인라인 표기 추가 (본 세션)

**왜 4 카테고리로 명확화하는가**:
- 단일 `symbol_type='ETF'` 필터는 us_symbol_master 분류 정확도에 100% 의존 → 취약
- 4 카테고리 명문화로 us_sync_symbol_master.py 코드의 분류 책임 명확화
- LLM Pre-Check는 "ETF or fund vehicle"을 통합 판정하므로 4 카테고리 모두 같은 처리

**왜 manual override 테이블을 신설하는가**:
- 자동 분류 (소스 cross-check + 휴리스틱)에는 한계 존재
- 사용자가 발견한 오분류는 즉시 정정 가능해야 함 — 매번 ADR 작성은 과잉
- override 테이블은 ADR-005 SSoT 원칙과 부합 (DB가 SSoT)

**왜 즉시 적용이 아닌 Phase 2 sprint로 미루는가** (§2):
- Q-004 정정 (12건 일괄 ETF 변경)은 즉시 적용 가능 — 본 ADR 시점에 운영 큐 그대로 처리
- 그러나 us_sync_symbol_master.py 보강·override 테이블 신설은 코드 변경·마이그레이션 동반 → Phase 2 sprint
- ADR-013의 "긴급도 분리" 패턴 계승 (정책 즉시 명문화 + 구현 sprint 분리)

### 결과 / 영향

**Phase 2 brief 영향 (필수)**:
- Phase 2B (Phase 1 인계 sprint) 내 신규 sprint 항목으로 등록:
  - "Sprint X: ADR-015 구현 — fund vehicle 분류 보강"
  - 작업: us_sync_symbol_master.py 보강 + 휴리스틱 + override 테이블 마이그레이션 + Q-004 후속 정밀화

**ADR-013 본문 갱신 (ADR-014 §1 (c) 카테고리)**:
- ADR-013 헤더에 "§1·§4는 ADR-015로 확장됨 — 2026-05-09" 인라인 표기 ✅ 본 세션 처리
- 본문 수정은 헤더 한 줄만, 핵심 결정은 불변

**Q-004 처리 영향**:
- Q-004 적용 절차에 본 ADR §3 보강 한 줄 추가 (즉시 적용에는 영향 없음 — Q-004 그대로 처리 가능)

**연관 문서 갱신 필요**:
- `_meta/04_DECISIONS.md` — 본 ADR-015 추가 ✅ 본 세션
- `_meta/04_DECISIONS.md` ADR-013 헤더 — 인라인 표기 ✅ 본 세션
- `_meta/06_CURRENT_STATE.md` — ADR 목록 + 미해결 이슈 §J 처리 상태 갱신 (본 세션)
- `_meta/operational_queue.md` Q-004 — ADR-015 §3 보강 한 줄 추가 (본 세션)
- `_meta/phases/phase2_brief.md` — Sprint X 등록 (본 세션 신규 작성)

**Phase 2 sprint 우선순위**:
- 본 ADR 구현 sprint는 Phase 2B 안에서 보통 우선순위
- Q-004 즉시 적용으로 노이즈는 제거되므로 긴급도 낮음
- Phase 2A (메일+엑셀)와 병행 가능

**ADR-013과의 관계**:
- ADR-013은 그대로 유효 (Supersede 아님)
- 본 ADR은 ADR-013의 §1 (적용 범위)·§4 (데이터 정리)를 확장
- ADR-013의 §2 (구현 위치 옵션)·§3 (Pre-Check 유지)·§5 (회고)는 그대로 적용

---

*새로운 결정이 있을 때마다 ADR-016, ADR-017... 형태로 추가한다.*

