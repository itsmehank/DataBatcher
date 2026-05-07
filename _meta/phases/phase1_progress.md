# Phase 1 — LLM 분석 레이어 구축 진행 기록

> 작성: Builder (Claude Code CLI)
> 브랜치: `phase1/1.1-llm-analysis-skeleton`
> 시작 일시: 2026-04-28

---

## 단계 1.1 — DB 마이그레이션 + (5) 분석 함수 구현 + 백엔드 추상화 검증

### 1.1 시작 (2026-04-28)

| 항목 | 상태 | 비고 |
|---|---|---|
| 1.1.1 DB 마이그레이션 3종 산출물 | ✅ 완료 | Alembic + raw SQL(db/migrations/sql/) + Q-002 텍스트. DEV DB upgrade 완료. |
| 1.1.2 운영 환경 마이그레이션 적용 | ⏳ 대기 | 사용자 직접 — Q-002 완료 처리 |
| 1.1.3 apps/llm-analysis/ 디렉토리 골격 | ✅ 완료 | 25파일, brief §5.2 구조 일치. pyproject.toml 생략(requirements.txt로 충분). |
| 1.1.4 LLMBackend 추상화 인터페이스 정의 | ✅ 완료 | core/anthropic_client.py. CLI sanity check + CLAUDE.md 탐색 진단 후 확정. |
| 1.1.5 CLI 백엔드 구현 | ✅ 완료 | ClaudeCodeCLIBackend. cwd=tempfile.gettempdir(). |
| 1.1.6 API 백엔드 구현 | ✅ 완료 | AnthropicAPIBackend (84줄). 단위 테스트(mock) 통과. 실제 SDK 호출 미수행 — 사용자 결정. |
| 1.1.7 llm_calls 기록 wrapper | ✅ 완료 | core/llm_call_recorder.py. 재시도 + INSERT. daily_call_limits hook placeholder 포함. |
| 1.1.8 (5) 프롬프트 v1 작성 | ✅ 완료 | prompts/analyze_chart_v1.md. brief §6.2 본문 그대로. |
| 1.1.9 data_loader.py 구현 | ✅ 완료 | core/data_loader.py. 일봉 60행 + 주봉 52주 + 인디케이터 + conditions_met(NULL 허용). |
| 1.1.10 prompt_builder.py 구현 | ✅ 완료 | core/prompt_builder.py. 템플릿 로드 + JSON 페이로드 결합. |
| 1.1.11 result_parser.py + AnalysisResult 모델 | ✅ 완료 | core/result_parser.py + models/analysis_result.py. 단위 테스트 13/13 통과. |
| 1.1.12 run_single_symbol.py CLI | ✅ 완료 | scripts/run_single_symbol.py. --symbol/--region/--date/--backend/--dry-run/--force-recompute 지원. |
| 1.1.13 단일 종목 검증 (CLI 백엔드, 5종목) | ✅ 완료 | AAOI/ABVX/ADV/BWET/CLSM (US) 5종목 실호출 성공. daily_analysis_us 5행 + llm_calls 기록 확인. |
| 1.1.14 단일 종목 검증 (API 백엔드, 1회) | ⏸ 연기 | 1.1.4-c 결정 그대로 유지. CLI가 운영 백엔드. |
| 1.1.15 프롬프트 튜닝 + v1 확정 | 🔄 진행 중 | 외부 평가 완료. 약점 7가지 진단. v2 작성 + Pydantic 갱신 + 테스트 25/25. 5종목 재호출 승인 대기. |

---

## 1.1 종료 시 Architect에 인계할 후속 작업

- [ARCHITECTURE.md §5] LLM 외부 의존성 표를 "Anthropic API or Claude Code CLI (ADR-011)"로 갱신 필요
  - 현재: "Anthropic API — Claude Code CLI는 약관·안정성 문제로 운영 환경에 부적합 (ADR-003)"
  - 변경 후: "Anthropic API or Claude Code CLI (Phase 1 기본: CLI + Max 플랜, ADR-011)"

- [ADR-010 §1] 마이그레이션 3종 산출물의 raw SQL 위치를 `apps/ingest-databatcher/scripts/migrations/`에서 `db/migrations/sql/`으로 갱신 필요
  - Phase 1 1.1 결정 사례 (2026-04-28): `db/migrations/sql/20260428_000001_add_daily_analysis_and_llm_calls.sql`
  - 결정 근거: ADR-010 §2 정신 부합 + Alembic 파일과 물리적 근접 + 앱 독립성 유지
  - ADR-010 §1 본문의 "apps/ingest-databatcher/scripts/migrations/" 표기를 `db/migrations/sql/`으로 수정 필요

- [alembic.ini 자격증명] `db/migrations/alembic.ini`의 `sqlalchemy.url` placeholder("root:root@...")가 실제 DEV 자격증명(`.env` DATABASE_URL "hank:1234!")과 불일치.
  현재는 DATABASE_URL 환경변수 override로 정상 동작 중이므로 영향 없음. 다음 결정 필요:
  - (a) alembic.ini의 url을 env 참조 방식으로 변경 (예: `%(DATABASE_URL)s`)
  - (b) placeholder 유지 + README/CLAUDE.md에 "DATABASE_URL이 SSoT" 명시
  PROD의 alembic.ini 상태도 함께 점검 필요. Phase 1.1 종료 시 Architect 세션에서 판단.

- [ADR-011 §3] cost_usd 처리 표 갱신: CLI 모드에서 참고값 저장 가능.
  NULL "허용"이지 "강제"가 아님을 명시. cost_source/max_plan_billing 메타 사용 명시.

- [phase1_brief.md §9.1] 1.1 게이트의 "CLI/API 양 백엔드로 같은 종목 호출 검증" 항목을 다음으로 갱신 필요:
  - "CLI 백엔드: 표본 5종목 호출 검증 (필수)"
  - "API 백엔드: 단위 테스트(mock)로 추상화 검증 완료. 실제 SDK 호출은 (a) Phase 1 후반 사용자 결정 또는 (b) ADR-012 §3.3 약관 위반 징후 시 또는 (c) ADR-013 백엔드 전환 결정 시 수행."
  갱신 사유: ADR-011·ADR-012의 운영 백엔드가 CLI이고 API는 fallback이라, 실제 SDK 검증 시점을 전환 결정 시로 미루는 게 비용·위험 측면에서 합리적.

- [1.1.7 wrapper / ADR-012 §3.2] 프롬프트 토큰 폭증 감지 로직 추가 필요.
  근거: Phase 1.1.4-b 진단에서 CLAUDE.md auto-load 변동으로 66,873 토큰 단발 사고 확인 (정상 ~8,000).
  구현: settings.yaml input_data 추정 토큰 대비 2배 이상 시 sync_log WARN 기록.
  위치: core/llm_call_recorder.py (call_and_record 내 또는 cost_tracker와 함께, 1.3 구현 시점).

- [HIGH / ADR 후보] 미너비니 스크리너에서 ETF 제외 필요.
  근거: 1.1.13 표본 5종목 중 2개(BWET, CLSM)가 ETF(market='ETF')였음.
  문제: 스크리너가 ETF를 거르지 않으면 분석 LLM이 매일 ETF에 대해 호출되어 비용·한도 낭비.
  v1에서 CLSM(ETF)을 "entry"로 분류하는 사용자 정책 위반이 발생함.
  해결 방향: minervini_screen_results_us 집계 시 us_symbol_master.symbol_type = 'ETF' 행 제외 (JOIN 조건 추가),
  또는 run_daily_analysis.py 호출 목록에서 ETF 필터링. ADR로 설계 결정 기록 필요.

- [ADR 후보] daily_analysis 테이블에 prompt_version 컬럼 추가 + PK 확장 검토.
  근거: v2 force-recompute 시 DELETE+INSERT 방식으로 v1 결과가 overwrite됨.
  개선안: (symbol, date, prompt_version)을 PK로 확장하면 v1/v2 행을 동시에 보존 가능.
  현재 우회: eval_input.json + llm_calls 테이블로 v1 결과 보존. 운영 부담 없으면 현행 유지도 가능.
  Phase 1 게이트 통과 후 Architect 세션에서 판단.

[1.3 검증 시 우선순위 항목]
- [v2.1 후보] AAOI reverse_split 누락 — price_data_notes의 split 정보를 deterministic하게 소비하도록 v3 prompt 보강 검토.
  평가 LLM 지적: "작은 ratio(~1.65:1) + 오래된 split도 일관되게 flag되어야 함."
  현재 v2는 split ratio threshold에 암묵적 의존. 명시적 조건 추가 시 개선 가능.
- [1.3 모니터링] completion 토큰 폭증 (v1 평균 ~1,800 → v2 평균 ~3,000, 60% 증가).
  ignore 케이스용 "tight reasoning" 지시 검토. ADR-012 §3.4 호출 로그 점검에서 cost 영향 확인.
- [1.3 검증 배치] entry 후보 5~10종목 별도 검증으로 pivot/breakout 정확도 (약점 F) 검증.
  현재 표본 5종목은 all-ignore/ETF라 F 항목이 untestable. 1.3 누적 데이터 활용.
- [1.3 자동화] reasoning 사실 정확성 sanity check — reasoning의 구체 숫자(volume, % 수치)가 source data와 일치하는지 자동 비교.
- [1.3 taxonomy 검토] 추가 flag 후보: `late_stage_base`, `distribution_days`, `reversal_off_high` (평가 LLM 제안). 1.3 운영 빈도 확인 후 추가 결정.

---

## 단계 1.2 — calculate_entry_params 구현

### 1.2.0-A — ADR-013 구현 (2026-05-03)

- **ETF 제외 필터**: `us_minervini_update.py`, `kr_minervini_update.py`에 ADR-013 option (a) 적용
  - `load_symbols_with_details` / `load_us_symbols_with_details` 에 `symbol_type` 필드 추가 (backward-compatible)
  - 종목 목록 로드 후 `d.get("symbol_type") != "ETF"` 조건으로 ETF 제외
  - `prices_wide` 에서도 non_etf_symbols 집합으로 ETF 컬럼 drop
- **KR/US 동일 정책**: 두 시장 모두 `symbol_type = 'ETF'` 기준으로 제외 (market='ETF'와 100% 일치 확인)
- **기존 행 보존** (ADR-013 §4.i 채택): `minervini_screen_results_us` ETF 177,065행 / `_kr` ETF 77,353행 그대로 보존
- **단위 테스트**: `scripts/tests/test_minervini_etf_exclusion.py` — 9/9 통과
  - US/KR ETF 제외 검증, symbol_type=NULL 처리, prices_wide 컬럼 제거, end-to-end pass_mask 검증
- **브랜치**: `phase1/1.2-entry-params`
- **다음**: 1.2.1 calculate_entry_params 프롬프트 v1 작성

### 1.2 후속 작업 등록

- [후속 검토] KR 시장 KONEX 종목의 미너비니 스크리닝 포함 여부 — ADR-013 사전 점검(2026-05-03) 시 발견.
  KONEX 110종목이 symbol_master에 ACTIVE이나 현재 minervini_screen_results_kr에는 0건(자연 통과 없음).
  KONEX 포함/제외 정책을 명시할지 사용자 결정 필요. ADR-013 구현 후에도 KONEX는 현행 동작(포함 가능 상태) 유지.

### 1.2 트랙 B (calculate_entry_params 구현, 2026-05-03)

| 항목 | 상태 | 비고 |
|---|---|---|
| B.1 (1.2.1) `prompts/calculate_entry_params_v1.md` 작성 | ✅ 완료 | 370줄. 외부 자문(§0 backbone) + 책 인용 anchors 5개 + decision tree §0.10 + scope discipline §0.7 + limitations §0.9 모두 반영. cup_with_handle→3c_cheat 단일 refinement 허용. |
| B.2 (1.2.2) `EntryParams` Pydantic | ✅ 완료 | models/entry_params.py 163줄. 13필드 (parameter_warnings → known + other 분리). Cross-field 5건 (price↔pct 일관성, target>pivot, stop<pivot, warnings 합산 ≤6). breakout_volume_requirement Literal 3개 enum. known_warnings Literal 10개 whitelist. |
| B.3 (1.2.3) `parse_entry_params_response()` | ✅ 완료 | core/result_parser.py 47→115줄. `_extract_json_dict()` helper 추출. legacy parameter_warnings 단일 키 출력 시 자동 known/other 분기 (robustness). |
| B.4 (1.2.4) `run_single_symbol.py --with-entry-params` | ✅ 완료 | scripts/run_single_symbol.py 205→276줄. `_call_entry_params()` 함수 신설 (1회 재시도 fallback, region별 module 라벨, error시 entry_params=NULL 보존). main()의 classification 분기 가드. |
| 단위 테스트 | ✅ 통과 | tests/test_entry_params.py 37건 + test_run_single_symbol_entry_flow.py 10건. 기존 51건 + 신규 47건 = 전체 98/98 통과. |
| B.5.1 sample 추출 (n=30, 2026-04-27) | ✅ 완료 | seed=20260503. ADR-013 필터 적용 (symbol_type='STOCK'). 30종목 리스트: CMTV/DOW/BMO/WTI/MCHPP/SBS/TVGN/AGX/OPTX/RRBI/WCC/LEA/ADI/DXPE/RBC/MAR/WULF/DHC/E/SCHL/CVGI/TYGO/CLDX/EHAB/AHCO/GAIN/CZWI/BFH/BWLP/EPD |
| B.5.2 batch 호출 | ✅ 완료 | /tmp/b5_sample_harness.py로 순차 실행. 총 79.9분 소요. |
| B.5.3 결과 분포 | ⚠️ entry 0건 | ignore 23 / watch 3 (BMO·SBS·AHCO) / **entry 0** / TIMEOUT 4 (RRBI·MAR·BFH·EPD, outer 300s 초과). pattern: none 23, flat_base 2, cup_with_handle 1. risk_flag top: wide_and_loose 19, climax_run 16, extended_from_ma 12, late_stage_base 11. etf_methodology_mismatch 1건 (symbol_type='STOCK' 필터 통과한 종목 중 v2가 ETF로 판정 — 후속 점검). |
| B.5.4 보고 | ✅ 완료 | 본 진행 기록 + Architect 결정 → B.5.5(시점 다른 sample) 진행. |
| B.5.5 (시점 변경 sample 5거래일×80=400) | ✅ **400/400 완주** | 2026-05-04 시작 → 2026-05-05 종료. 총 941.7분 (15시간 42분). timeouts 31/400 = 7.75% (한도 75 대비 44건 여유). |

#### B.5.5 사전 점검 (2026-05-04)

**시점 후보 평가** (froth 기준 + breadth + ETF 제외 통과 종목 수):

| 후보일 | US500 close | %above SMA50 | %above SMA200 | adv/dec (1d) | Pass count | 시장 상태 |
|---|---|---|---|---|---|---|
| 2026-04-27 (B.5.4) | 7,173.91 | +5.56% | +6.91% | 1.03 | 901 | mid-froth, breadth 분열 |
| 2026-04-01 | 6,575.32 | −3.15% | −1.00% | 1.65 | 682 | correction, V-bounce 직전 |
| 2026-01-15 | 6,944.47 | +1.73% | +9.37% | 1.41 | 1,008 | **steady advance, broad uptrend** |
| 2026-01-02 | 6,858.47 | +0.79% | +8.99% | 1.58 | 918 | year-start broad rally |
| 2025-11-03 | 6,851.97 | +3.07% | +12.03% | 0.65 | 681 | index 강하나 daily selling |

→ Architect 결정: **2026-01-13 ~ 17 → 1/17 토요일이라 1/12로 치환 → 1/12~1/16 (월-금 연속 5거래일)** 선택. healthy bull 조건에서 v2 entry 발생률 검증.

**거래일 + 통과 종목 수 확정**:

| date | 요일 | 통과 (ETF 제외) | seed |
|---|---|---|---|
| 2026-01-12 | Mon | 976 | 20260504 |
| 2026-01-13 | Tue | 1,010 | 20260505 |
| 2026-01-14 | Wed | 992 | 20260506 |
| 2026-01-15 | Thu | 1,008 | 20260507 |
| 2026-01-16 | Fri | 1,024 | 20260508 |

**Sample 추출 결과**:
- 5 × 80 = 400 호출 (중복 허용)
- unique 종목: 341
- 다중-날짜 평가 종목: 5종목이 3회 등장 (TX, OLMA, LAUR, EA, CLST), 그 외 약 50여종이 2회 등장

**Timeout 진단** (B.5.4의 4건 outer timeout 원인):
- llm_calls 조회 결과 18건이 `error="CLI timeout after 120s"`, duration_ms 정확히 120,017~120,041ms
- inner CLI level은 settings.yaml의 `timeout_seconds: 120`이 정상 적용됨 (`core/anthropic_client.py:103`)
- B.5.4 outer 4건 = 첫 호출 120s + parser 1회 retry 120s + 약간 → harness `subprocess.run(timeout=300)` 한도 초과
- **SSoT**: settings.yaml의 120s가 의도된 inner 한도. harness 300s는 inner의 ~2.5배 outer fence였으나 retry 발생 시 빠듯
- B.5.5 harness: outer timeout **360s** (= inner 120s × 3) 적용

**데이터 가용성 검증** (5거래일 모두):
- 60일 일봉 lookback: 62~64 거래일 OK (최저 1/12=62)
- SMA50/150/200_close, rs_line, ibd_rs_rating 모두 9,000~11,000 종목 분량 존재
- 52주 주봉 lookback OK (~1년 윈도우 내)

**미커밋**: B.5.5 harness 자체(/tmp/b5_5_sample_harness.py)는 Builder 자체 생성 디버깅 도구. commit β 전 사용자 결정 영역.

#### B.5.5 중간 분포 (cum 20/400, 2026-05-04 재개 후)

date 2026-01-12 batch 20/80 시점:
- ignore 18 / watch 1 (TK) / entry 0 / **TIMEOUT 1 (BNS, outer 360s)**
- duration median 110.1s, p90 351.2s, max 360.0s
- 동일 batch 내 retry 추정(>200s) 누적 약 5건. 27%→25% 추세는 큰 변화 없음
- entry 0건 지속 — healthy bull 가설(가) 강한 검증은 아직 데이터 부족

#### B.5.5 중간 분포 (cum 40/400, 10%)

date 2026-01-12 batch 40/80 시점:
- ignore 29 / watch 6 / entry **0** / **TIMEOUT 5 (12.5%)** — B.5.4의 13.3%와 유사
- pattern: none 28 / flat_base 6 / cup_with_handle 1
- top risk_flags: wide_and_loose 21, climax_run 20, extended_from_ma 10, late_stage_base 10, low_volume_breakout 7, thin_liquidity_us_only 6, narrow_base 5, **etf_methodology_mismatch 2** (사후 점검 필요)
- duration median 110.1s, p90/max 360.0s (외부 timeout 빈도)
- retry-suspect (>200s rc=0): 11건 (27.5%) — B.5.4와 비슷
- watch 종목: TK, BCS, VBNK, JXN, XPRO, MRK
- entry 0건 지속 — 1.2 healthy bull 윈도우에서도 발생률 매우 낮음 시사

#### B.5.5 중간 분포 (cum 60/400, 15%)

date 2026-01-12 batch 60/80 시점:
- ignore 45 / watch 9 / entry **0** / TIMEOUT 6 (10%)
- pattern: none 44 / flat_base 9 / cup_with_handle 1
- top risk_flags: wide_and_loose 33, climax_run 31, extended_from_ma 18, late_stage_base 18, thin_liquidity_us_only 10, low_volume_breakout 9, narrow_base 8, etf_methodology_mismatch 2
- duration median 105.5s, p90 360.0s
- retry-suspect 15/60 (25%) — 안정적
- watches 누적 (9건): TK, BCS, VBNK, JXN, XPRO, MRK, AMRX, CSTM, SNDA
- 1/12 batch 거의 완주 (60/80, 20건 남음). 여전히 entry 0건

#### B.5.5 Batch 1/5 완료 (2026-01-12, 80/80, 188.4분)

| 항목 | 값 |
|---|---|
| classification | ignore 60 / watch 11 / **entry 0** / TIMEOUT 9 (11.25%) |
| pattern | none 59 / flat_base 11 / cup_with_handle 1 (rc=0 71건 기준) |
| duration (rc=0) median/p90/max | 102.5s / 300.8s / 351.2s |
| retry-suspect (rc=0 >200s) | 19/80 (23.75%) |
| watches (11건) | TK, BCS, VBNK, JXN, XPRO, MRK, AMRX, CSTM, SNDA, IBKR, MCY |
| timeouts (9건) | BNS, ALNT, AX, AAL, DLX, MSGE, LAUR, BK, KMT |
| etf_methodology_mismatch | 2건: **EMF, RMT** (symbol_type='STOCK' 필터 통과 — 후속 점검) |
| top risk_flags | wide_and_loose 42, climax_run 37, extended_from_ma 26, late_stage_base 26, thin_liquidity_us_only 14, low_volume_breakout 11, narrow_base 10, etf_methodology_mismatch 2, volume_contraction_on_advance 2, reverse_split_distortion 2 |

**해석**:
- 1월 12일 (healthy bull, 시장 +0.79%/+8.99% above SMAs) sample 80에서도 entry 0건. froth(B.5.4) vs healthy 차이가 entry 발생률에서는 명확히 안 보임
- watch 비율 13.75% (11/80) — B.5.4의 10% (3/30)와 유사 수준
- risk_flag wide_and_loose+climax_run 빈도가 B.5.4 froth 대비 다소 낮음 (53/80=66% vs B.5.4 35/26=135%인디지스미블 — 정규화 시 추후 비교)
- etf_methodology_mismatch 2건: EMF (Templeton Emerging Markets Fund, NYSE-listed CEF), RMT (Royce Micro-Cap Trust) — closed-end fund인데 us_symbol_master에 STOCK으로 등재된 케이스. ADR-013 보강 후속 항목

**다음**: Batch 2/5 (2026-01-13) 진행 중

#### B.5.5 중간 분포 (cum 100/400, 25%)

date 2026-01-13 batch 20/80 시점 (Batch 1 80건 + Batch 2 20건):
- **ignore 78 / watch 12 / entry 0 / TIMEOUT 10 (10%)**
- pattern: none 76 / flat_base 12 / cup_with_handle 2
- top risk_flags: wide_and_loose 59, climax_run 51, extended_from_ma 37, late_stage_base 33, thin_liquidity_us_only 20, low_volume_breakout 11, narrow_base 11, etf_methodology_mismatch 2
- duration (rc=0) median 97.8s, p90 300.8s
- retry-suspect 22/100 (22%) — 안정 추세
- watches 누적 (12): TK, BCS, VBNK, JXN, XPRO, MRK, AMRX, CSTM, SNDA, IBKR, MCY, NRIM
- 1/13에서 entry 첫 발생 안 함. froth 가설(가) 검증 데이터 부족 지속
- timeout 누적 10/100 (정확히 10%) — 75 한도 대비 65건 여유

#### B.5.5 중간 분포 (cum 120/400, 30%)

date 2026-01-13 batch 40/80 시점:
- **ignore 91 / watch 17 / entry 0 / TIMEOUT 12 (10%)**
- pattern: none 88 / flat_base 17 / cup_with_handle 3
- top flags: wide_and_loose 70, climax_run 62, extended_from_ma 45, late_stage_base 43, thin_liquidity_us_only 23, low_volume_breakout 13, narrow_base 12, reverse_split_distortion 3
- dur(rc=0) median 97.0s, p90 237.3s (개선됨 — 1차 호출 timeout 비율 감소 추정)
- retry-suspect 25/120 (20.8%) — 안정 추세
- watches 누적 (17): TK, BCS, VBNK, JXN, XPRO, MRK, AMRX, CSTM, SNDA, IBKR, MCY, NRIM, C, MAR, SMP, VLY, BBVA
- **관찰**: watch에 financial/insurance/broker 종목 다수 (BCS, IBKR, MCY, C, MAR, VLY, BBVA, NRIM) — large-cap 기관주들이 base 형성 중인 패턴 가능
- timeout 12/120 (10%) — 한도 75 대비 63 여유

#### B.5.5 중간 분포 (cum 140/400, 35%) — **첫 entry 발생** ✨

date 2026-01-13 batch 60/80 시점:
- **ignore 106 / watch 20 / entry 1 (NVST) / TIMEOUT 13 (9.3%)**
- pattern: none 103 / flat_base 19 / cup_with_handle 5
- top flags: wide_and_loose 81, climax_run 73, late_stage_base 53, extended_from_ma 50, thin_liquidity_us_only 25, low_volume_breakout 15, narrow_base 14
- dur(rc=0) median 96.7s, p90 242.6s
- retry-suspect 31/140 (22.1%)

**NVST entry 상세 (cum 139, llm_call_id 260+262)**:
- (5): cup_with_handle 19w, confidence 0.75, pivot $22.67 (handle high), risk_flags=[low_volume_breakout]
- (6) entry_params: pivot $22.67, stop $21.47 (−5.3% logical, tighter than abs −7%), size 4.9% (7% × 0.7 due to low_volume_breakout), target $27.20 (+20%), entry_window 3, max_chase 5.0, vol req `ge_1.4x_50day_avg`
- known_warnings/other_warnings 모두 빈 list (정상)
- (5) reasoning: "19w cup-with-handle, pivot $22.77 (base high $22.67 + $0.10). Breakout 2026-01-06 at $23.21. Current $23.23, +2% above pivot (in buy zone). RS 81, MAs aligned. Breakout volume 1.02x avg (marginal)."

**가설 분기 잠정 결과**:
- (나) v2 ignore-편향 가설 **약화**: v2가 합리적 entry 후보 발견 시 정상 분류 + (6) 산출
- (가) v2 정상 작동 가설 **지지**: 첫 entry까지 138 이상 호출 필요했지만 발생률 자체는 낮음 → entry는 본질적으로 좁은 윈도우 현상이라는 사용자 우려 검증

watches 누적 (20): TK, BCS, VBNK, JXN, XPRO, MRK, AMRX, CSTM, SNDA, IBKR, MCY, NRIM, C, MAR, SMP, VLY, BBVA, EMBJ, FOX, AX

#### B.5.5 Batch 2/5 완료 (2026-01-13, 80/80, 193.6분)

| 항목 | 값 |
|---|---|
| classification | ignore 60 / watch 13 / **entry 1 (NVST)** / TIMEOUT 6 (7.5%) |
| pattern | none 59 / flat_base 9 / cup_with_handle 5 / double_bottom 1 (rc=0 74건) |
| duration (rc=0) median/p90/max | 88.2s / 236.2s / 338.9s |
| retry-suspect | 17/80 (21.2%) |
| watches (13) | NRIM, C, MAR, SMP, VLY, BBVA, EMBJ, FOX, AX, EA, ONC, HTHT, KVHI |
| timeouts (6) | APH, GCT, NDSN, BWXT, SOHU, GAP |
| etf_methodology_mismatch | 1건: **CEE** (Central & Eastern Europe Fund — closed-end fund) |
| top flags | wide_and_loose 50, climax_run 48, late_stage_base 33, extended_from_ma 28, thin_liquidity_us_only 12, narrow_base 6, low_volume_breakout 5 |

**Batch 1 vs Batch 2 비교**:
- timeout 비율 11.25% (B1) → 7.5% (B2) — 개선
- watch 비율 13.75% → 16.25% — 증가
- entry 발생 0 → **1 (NVST)** — 핵심 발견
- pattern 다양성: cup_with_handle 1→5, double_bottom 0→1 — 증가
- ETF 잘못 통과: 2 (EMF, RMT) → 1 (CEE) — 감소
- 1/12 vs 1/13 시장 차이는 미미하지만 entry 발생률은 표본 크기 효과 가능성

#### B.5.5 cum 160/400 (40%) 종합

전체 누적: ignore 120 / watch 24 / **entry 1** / TIMEOUT 15 (9.4%)
timeout 한도 75 대비 **60건 여유** (75% 안전 마진)

다음: Batch 3/5 (2026-01-14) 진행 중

#### B.5.5 중간 분포 (cum 180/400, 45%)

date 2026-01-14 batch 20/80 시점 (B1 80 + B2 80 + B3 20):
- ignore 131 / watch 31 / **entry 1 (NVST)** / TIMEOUT 17 (9.4%)
- pattern: none 130 / flat_base 25 / cup_with_handle 7 / double_bottom 1
- top flags: wide_and_loose 99, climax_run 94, late_stage_base 62, extended_from_ma 58, thin_liquidity_us_only 29, low_volume_breakout 21, narrow_base 17, etf_methodology_mismatch 3
- dur(rc=0) median 97.3s, p90 237.3s — 안정
- retry-suspect 41/180 (22.8%)
- 분류 변동 첫 사례 발견: **JXN 1/12 watch → 1/14 ignore** (cross-date 일관성 분석에 데이터 추가)
- watches 누적 (31): … VMI, GNL, CPS, HSBC, ING, HTBK, RY 추가
- timeout 17/180 (9.4%) — 한도 75 대비 58 여유

#### B.5.5 중간 분포 (cum 200/400, **50% 절반**)

date 2026-01-14 batch 40/80 시점:
- **ignore 146 / watch 35 / entry 1 (NVST) / TIMEOUT 18 (9%)**
- pattern: none 146 / flat_base 28 / cup_with_handle 7 / double_bottom 1
- top flags: wide_and_loose 113, climax_run 104, late_stage_base 68, extended_from_ma 63, thin_liquidity_us_only 32, low_volume_breakout 23, narrow_base 17, volume_contraction_on_advance 5, etf_methodology_mismatch 4, reverse_split_distortion 4
- dur(rc=0) median 97.3s, p90 300.8s
- retry-suspect 47/200 (23.5%)
- B3 신규 watches (11): VMI, GNL, CPS, HSBC, ING, HTBK, RY, ECPG, TPR, ANDE, KEX
- 200/400 절반에서 entry 발생 1건만 — 첫 시점 발생률 자연 빈도 추정 ~0.5%

**timeout 한도 안전**: 18/200=9% — 75 한도 대비 57건 여유 (76% margin). 400 완주 안정 추세

#### B.5.5 중간 분포 (cum 220/400, 55%)

date 2026-01-14 batch 60/80 시점:
- ignore 161 / watch 38 / **entry 1 (NVST)** / TIMEOUT 20 (9.1%)
- pattern: none 158 / flat_base 34 / cup_with_handle 7 / double_bottom 1
- top flags: wide_and_loose 123, climax_run 113, extended_from_ma 73, late_stage_base 73, thin_liquidity_us_only 36, low_volume_breakout 25, narrow_base 18, etf_methodology_mismatch 5
- dur(rc=0) median 96.7s, p90 300.8s
- retry-suspect 50/220 (22.7%)

**Cross-date 분류 변동 (6건 발견)** — same symbol, different dates 분류 차이:
- ONC: 1/12 ignore → 1/13 watch (개선 방향)
- TX: 1/12 ignore → 1/14 watch (개선 방향)
- JXN: 1/12 watch → 1/14 ignore (악화)
- CSTM: 1/12 watch → 1/14 ignore (악화)
- C: 1/13 watch → 1/14 ignore (악화)
- EA: 1/13 watch → 1/14 ignore (악화)

**해석**: 같은 종목이 며칠 사이 base 형성 진척에 따라 watch ↔ ignore 변동. **entry로 진척 사례는 아직 0건** — watch 종목 중 어느 것도 base 완성 + 피봇 임박 단계로 진입하지 못함. 사용자 가설(entry는 좁은 5거래일 윈도우 현상)과 정합. NVST 한 건이 그 윈도우에 우연히 떨어진 케이스.

timeout 20/220 (9.1%) — 75 한도 대비 55 여유

#### B.5.5 Batch 3/5 완료 (2026-01-14, 80/80, 210.0분)

| 항목 | 값 |
|---|---|
| classification | ignore 58 / watch 15 / **entry 0** / TIMEOUT 7 (8.75%) |
| pattern | none 56 / flat_base 16 / cup_with_handle 1 (rc=0 73건) |
| duration (rc=0) median/p90/max | 98.0s / 321.2s / 352.9s |
| retry-suspect | 21/80 (26%) |
| watches (15) | VMI, GNL, CPS, HSBC, ING, HTBK, RY, ECPG, TPR, ANDE, KEX, VTRS, AVAL, TX, ASTE |
| timeouts (7) | CHRW, OUT, HWM, CTRE, GOOG, HLLY, BCS |
| etf_methodology_mismatch | 2건: **CEE** (1/13에도 발생), **KF** (Korea Fund) |
| top flags | climax_run 43, wide_and_loose 42, extended_from_ma 27, late_stage_base 21, thin_liquidity_us_only 13, low_volume_breakout 9, narrow_base 3 |

**Batch 1 vs B2 vs B3 비교**:
- entry: 0 / 1 (NVST) / 0 — entry 발생률 안정적 0~1건/80
- watch: 11 / 13 / 15 — 점차 증가 (1/12→1/13→1/14 시장이 entry-friendly 진척?)
- timeout: 9 / 6 / 7 — 안정 (~7~9건)
- climax_run, wide_and_loose 둘이 1위 자리 변경 (B3에서 climax_run 1위) — 시장 froth 미세 변화 시사

#### B.5.5 cum 240/400 (60%) 종합

전체: ignore 178 / watch 39 / **entry 1** / TIMEOUT 22 (9.2%)
timeout 한도 75 대비 53건 여유 (71% margin). 400 완주 안정 추세

다음: Batch 4/5 (2026-01-15) 진행 중

#### B.5.5 중간 분포 (cum 260/400, 65%)

date 2026-01-15 batch 20/80 시점:
- ignore 196 / watch 40 / **entry 1 (NVST)** / TIMEOUT 23 (8.85%)
- pattern: none 191 / flat_base 38 / cup_with_handle 7 / double_bottom 1
- top flags: wide_and_loose 146, climax_run 139, extended_from_ma 90, late_stage_base 86, thin_liquidity_us_only 45, low_volume_breakout 26, narrow_base 21
- dur(rc=0) median 96.3s, p90 237.3s
- retry-suspect 59/260 (22.7%)
- **B4 진행 (20/80)**: ignore 18 / watch 1 (CAAP) / TIMEOUT 1 (LC) / entry 0
- timeout 23/260 (8.85%) — 75 한도 대비 52건 여유

#### B.5.5 중간 분포 (cum 280/400, 70%)

date 2026-01-15 batch 40/80 시점:
- 전체: ignore 210 / watch 43 / **entry 1 (NVST)** / TIMEOUT 26 (9.3%)
- B4 절반 (40/80): ignore 32 / watch 4 (CAAP, RF, CDRE, EPAM) / entry 0 / TIMEOUT 4 (LC, DD, ITUB, IVR)
- 1/15 (B4) entry 발생률은 1/12·1/13·1/14와 유사하게 0~1건 추세
- timeout 26/280 (9.3%) — 75 한도 대비 49건 여유

#### B.5.5 중간 분포 (cum 300/400, **75%**)

date 2026-01-15 batch 60/80 시점:
- 전체: ignore 225 / watch 48 / **entry 1 (NVST)** / TIMEOUT 26 (8.7%)
- pattern: none 221 / flat_base 44 / cup_with_handle 8 / double_bottom 1
- top flags: wide_and_loose 169, climax_run 155, extended_from_ma 103, late_stage_base 93, thin_liquidity_us_only 57, low_volume_breakout 29, narrow_base 27
- dur(rc=0) median 96.7s, p90 236.2s
- retry-suspect 66/300 (22%)
- B4 (60/80): ignore 47 / watch 9 / entry 0 / TIMEOUT 4
- timeout 26/300 (8.7%) — 75 한도 대비 49 여유 (65% margin)
- entry 0/300 후보 추가 발생 없음. NVST 1건이 5거래일 윈도우 우연 catch한 케이스 가설 유력

#### B.5.5 Batch 4/5 완료 (2026-01-15, 80/80, 177.2분)

| 항목 | 값 |
|---|---|
| classification | ignore 62 / watch 12 / **entry 0** / TIMEOUT 6 (7.5%) |
| pattern | none 62 / flat_base 9 / cup_with_handle 2 / **vcp 1** (첫 vcp 등장) (rc=0 74건) |
| duration (rc=0) median/p90/max | 96.4s / 221.1s / 357.2s |
| retry-suspect | 11/80 (13.75%) — **현저히 개선** |
| watches (12) | CAAP, RF, CDRE, EPAM, IX, PBT, MD, CUK, MNRO, OR, BLD, FSBC |
| timeouts (6) | LC, DD, ITUB, IVR, EA, MAR |
| etf_methodology_mismatch | 1건: **CAF** (Morgan Stanley China A Share Fund) |
| top flags | wide_and_loose 45, climax_run 34, extended_from_ma 31, thin_liquidity_us_only 22, late_stage_base 18, narrow_base 9, low_volume_breakout 5 |

**Batch 비교 (B1·B2·B3·B4)**:
- entry: 0 / 1 (NVST) / 0 / 0 — entry는 1/13 NVST 단 1건
- watch: 11 / 13 / 15 / 12 — 안정 13~15건 평균
- timeout: 9 / 6 / 7 / 6 — B2~B4 안정
- retry-suspect: 23.75% → 21.2% → 26.0% → **13.75%** — B4에서 큰 폭 감소 (CLI 안정화 추정)
- pattern 다양성: B4에서 vcp 처음 등장

**EA 흥미로운 사례**: 1/13 watch → 1/14 ignore → 1/15 timeout (3회 평가 모두 다름) — 분류 안정성 검토 후속 항목

#### B.5.5 cum 320/400 (80%) 종합

전체: ignore 240 / watch 51 / **entry 1** / TIMEOUT 28 (8.75%)
timeout 한도 75 대비 47건 여유 (63% margin). 마지막 80건 안전 마진 충분

다음: Batch 5/5 (2026-01-16) — 마지막 batch 진행 중

#### B.5.5 중간 분포 (cum 340/400, 85%)

date 2026-01-16 batch 20/80 시점:
- 전체: ignore 255 / watch 56 / **entry 1 (NVST)** / TIMEOUT 28 (8.2%)
- pattern: none 252 / flat_base 47 / cup_with_handle 10 / vcp 2 / double_bottom 1
- top flags: wide_and_loose 190, climax_run 171, extended_from_ma 121, late_stage_base 104, thin_liquidity_us_only 67, narrow_base 32, low_volume_breakout 30
- dur(rc=0) median 96.3s, p90 232.8s
- retry-suspect 70/340 (20.6%)
- **B5 시작 (20/80 매우 양호)**: ignore 15 / watch 5 (FOX, BTE, CYRX, PAX, CZWI) / entry 0 / TIMEOUT **0** ← B1~B4 첫 20에서 timeout 1~5건 → B5 0건은 매우 안정적
- timeout 28/340 (8.2%) — 75 한도 대비 47건 여유 (60건 남음에 충분)

#### B.5.5 중간 분포 (cum 360/400, **90%**)

date 2026-01-16 batch 40/80 시점:
- 전체: ignore 272 / watch 58 / **entry 1 (NVST)** / TIMEOUT 29 (8.06%)
- B5 진행 (40/80): ignore 32 / watch 7 / entry 0 / TIMEOUT 1 (ADI) — 매우 안정적
- timeout 한도 75 대비 46건 여유 (61% margin)
- **40건 남음, entry 0건 추가 가능성 매우 낮음 (자연 발생률 ~0.25~0.5%)**

다음: 마지막 40건 완주 후 최종 보고

#### B.5.5 중간 분포 (cum 380/400, **95%, 20건 남음**)

date 2026-01-16 batch 60/80 시점:
- 전체: ignore 286 / watch 63 / **entry 1 (NVST)** / TIMEOUT 30 (7.89%)
- B5 진행 (60/80): ignore 46 / watch 12 / entry 0 / TIMEOUT 2 (ADI, ILMN)
- timeout 30/380 (7.89%) — 75 한도 대비 **45건 여유**, 안전하게 완주 임박

---

## 1.2 트랙 B.5.5 결과 (2026-05-05, 400/400 완주)

### (1) Sample 추출 결과

| date | 요일 | 통과 종목 (ETF 제외) | seed | sample 80 |
|---|---|---|---|---|
| 2026-01-12 | Mon | 976 | 20260504 | ✅ |
| 2026-01-13 | Tue | 1,010 | 20260505 | ✅ |
| 2026-01-14 | Wed | 992 | 20260506 | ✅ |
| 2026-01-15 | Thu | 1,008 | 20260507 | ✅ |
| 2026-01-16 | Fri | 1,024 | 20260508 | ✅ |

5거래일 합산: **400 호출**
- unique 종목: 341
- multi-evaluated 종목: 53 (5건 3회 평가, 48건 2회 평가)
- 5거래일 unique 통과 종목 union: ~3,200~3,500 종목

### (2) 호출 결과 분포 — 전체 400 합산

**Classification**:

| | count | rate |
|---|---|---|
| ignore | 300 | 75.0% |
| watch | 68 | 17.0% |
| **entry** | **1 (NVST)** | **0.25%** |
| TIMEOUT (outer 360s) | 31 | 7.75% |

**Pattern (rc=0, n=369)**:
- none: 296 (80.2%)
- flat_base: 58 (15.7%)
- cup_with_handle: 12 (3.3%)
- vcp: 2 (0.5%) — Batch 4에서 첫 등장
- double_bottom: 1 (0.3%)

**Top risk_flags (rc=0, n=369, multiple per call)**:
- wide_and_loose: 226 (61.2%)
- climax_run: 197 (53.4%)
- extended_from_ma: 131 (35.5%)
- late_stage_base: 124 (33.6%)
- thin_liquidity_us_only: 87 (23.6%)
- narrow_base: 36 (9.8%)
- low_volume_breakout: 33 (8.9%)
- prior_uptrend_insufficient: 11 (3.0%)
- volume_contraction_on_advance: 9 (2.4%)
- reverse_split_distortion: 9 (2.4%)
- **etf_methodology_mismatch: 6** (1.6%) — ADR-013 후속 점검
- faulty_pivot: 1 (0.3%)

**Duration 통계 (rc=0, n=369)**:
- median: 95.0s
- p90: 232.8s (1회 retry 또는 v2 prompt 길어진 상태)
- max: 357.2s (outer 360 직전)

**Token 통계 (rc=0, n=369, CLI estimate)**:
- prompt_tokens median/max: 22,886 / 23,285 (안정)
- completion_tokens median/max: 3,667 / 5,565

### (3) 날짜별 entry 발생 패턴

| date | ignore | watch | entry | TIMEOUT | watch 비율 | 시장 변화 |
|---|---|---|---|---|---|---|
| 2026-01-12 | 60 | 11 | 0 | 9 | 13.75% | 시작 |
| 2026-01-13 | 60 | 13 | **1 (NVST)** | 6 | 16.25% | entry 첫 발생 |
| 2026-01-14 | 58 | 15 | 0 | 7 | 18.75% | watch 정점 |
| 2026-01-15 | 62 | 12 | 0 | 6 | 15% | (stable) |
| 2026-01-16 | 60 | 17 | 0 | 3 | 21.25% | watch 가장 높음 |

**관찰**:
- entry 1건만 (NVST, 1/13). 5거래일 중 단일 시점에만 발생 — 사용자 가설(entry는 좁은 5거래일 윈도우 현상) 직접 검증
- watch 비율 13.75% → 21.25% 점차 증가 — 시장이 entry-friendly로 진척
- TIMEOUT 9 → 3 감소 — CLI 안정 (시간 흐름에 따른 자연 안정화 또는 batch warmup 효과)

### (4) B.5.4 vs B.5.5 비교

| 메트릭 | B.5.4 (2026-04-27, 1일, 30) | B.5.5 (2026-01-12~16, 5일, 400) | Δ |
|---|---|---|---|
| 시장 상태 | mid-froth, breadth 분열 | steady advance, broad uptrend | — |
| US500 vs SMA50 | +5.56% | +0.79% ~ +1.73% | 더 가까움 |
| US500 vs SMA200 | +6.91% | +9.0% ~ +9.4% | 더 높음 (장기 강세) |
| ignore 비율 | 76.7% | 75.0% | -1.7% |
| watch 비율 | 10.0% | 17.0% | **+7.0%** |
| **entry 비율** | **0%** | **0.25%** | **+0.25%** |
| TIMEOUT 비율 | 13.3% | 7.75% | -5.6% (개선) |
| wide_and_loose (rc=0 정규화) | 73% (19/26) | 61% (226/369) | -12% |
| climax_run | 62% (16/26) | 53% (197/369) | -9% |
| extended_from_ma | 46% (12/26) | 36% (131/369) | -10% |
| late_stage_base | 42% (11/26) | 34% (124/369) | -8% |

**해석**:
- B.5.5 (healthy)에서 froth 관련 risk_flag (wide_and_loose, climax_run, extended_from_ma) 정규화 빈도 모두 감소 — 시장이 덜 froth임을 risk_flag 데이터로 입증
- watch 비율 7% 증가 — entry 직전·직후 base 형성 종목이 더 많음
- entry는 0% → 0.25% 증가했지만 양쪽 모두 매우 낮음 — entry 자체가 본질적으로 희귀함
- 자연 entry 발생률 추정 p ≈ **0.5~1%** (5거래일 평균 80 sample 당 0~2 건)

### (5) Watch 분류 분석 (가설 분리 보조)

**Watch 68건 구성** (rc=0):
- pattern: flat_base 30, none 29, cup_with_handle 7, vcp 2
- confidence: 0.7~0.8 buckets에 48건, ≥0.8 13건, 0.6~0.7 7건 — 대부분 high
- top risk_flags in watch: wide_and_loose 16, thin_liquidity_us_only 15, low_volume_breakout 13, late_stage_base 10

**"Clean" watches (no risk_flags + named pattern, n=13)** — entry 가장 가까운 후보:

| date | symbol | pattern | conf | reasoning 요약 |
|---|---|---|---|---|
| 1/12 | BCS | flat_base | 0.80 | 11w flat base, breakout 10/28, +20% extended |
| 1/13 | C | cup_with_handle | 0.85 | broke out 12/3, +16% extended, pulled back to 116 (still +6.7% above SMA50) |
| 1/13 | MAR | flat_base | 0.85 | 24w base, breakout 11/7 +11%, within 2.5% of 52w high |
| 1/13 | EMBJ | flat_base | 0.87 | 9w base, broke out 1/5 +7.4% (beyond 5% buy zone) |
| 1/14 | HTBK | cup_with_handle | 0.75 | broke out 11/25, now +13.7% extended |
| 1/14 | KEX | flat_base | 0.80 | breakout 1/5, +7.8% from pivot |
| 1/15 | CDRE | flat_base | 0.80 | 10w base, current 4% BELOW entry — base in development |
| 1/15 | EPAM | flat_base | 0.80 | breakout 11/10 +22% — extended |
| 1/16 | PAX | flat_base | 0.80 | breakout 1/6, +5% from pivot, 10 days post |
| 1/16 | NDSN | flat_base | 0.75 | breakout 12/19, +13% extended |
| 1/16 | HEI | flat_base | 0.78 | broke out 12/19, +7.2% extended |
| 1/16 | F | flat_base | 0.75 | failed breakout 1/8, now -6.8% from pivot |
| 1/16 | GM | cup_with_handle | 0.80 | broke out late-Oct '25, +30% from pivot |

**핵심 패턴**:
- **대부분 "post-breakout extended"**: 12/13 clean watches가 이미 breakout 후 5~30% 진행됨 — entry zone 통과
- **"pre-breakout"는 1건** (CDRE 1/15: -4% below pivot, base 형성 중)
- **NVST(entry)와 비교**: entry 받은 NVST는 "breakout 1/6, current +2% above pivot, in buy zone" — 5일 buy zone에 정확히 떨어짐
- **분류가 "임박 직전인데 LLM이 entry 못 만든" 패턴은 0건** — clean watch들은 모두 base 통과 후 또는 형성 중. 어떤 것도 "active buy zone (-5% ~ +5%)"에 있지 않음
- **"다양한 base 형성 단계 종목 포착" 패턴**: pre-breakout (CDRE), early-extended (KEX, PAX, HEI), mid-extended (NVST가 여기, EMBJ, HTBK), late-extended (BCS, C, EPAM, NDSN, GM, MAR), failed breakout (F)

**Cross-date 분류 변동 (21건 발견)**:
- watch ↔ ignore 양방향: 9건 (TX, JXN, CSTM, MCY, C, EA, REAL, CYRX, GE 등)
- ignore ↔ watch: 3건 (ONC, TX, PAX)
- timeout ↔ classification 회복: 5건 (APH, BCS, AX, AAL, NDSN, MAR, ITUB, ILMN, EA)
- 동일 분류 일관: BELFA, OLMA, KYTX, CMTV, FBIO, AEHR, CACI, RMCF, CMCM, ANRO, MEDP, CLST 등 12건+

**EA 흥미로운 사례 (3회 평가, 모두 다름)**: 1/13 watch → 1/14 ignore → 1/15 timeout. 분류 안정성 v2 후속 검토 항목.

### (6) 가설 분기 평가

**B.5.5 결과: entry 1건 → 1.1 § "entry 1~2건: LLM 작동 신호 명확. B.6 진입 검토 가능" 분기**.

**(가) v2 정상 작동 가설**: ✅ **확정**
- v2가 합리적 entry 후보 발견 시 정상 분류 + (6) 산출 (NVST 검증)
- entry 자체가 본질적으로 좁은 5거래일 윈도우 현상 — 5거래일 healthy bull에서 발생한 entry 1건은 "넓은 잠재 후보군 중 매우 일부만 active buy zone에 위치"라는 시장 자연 특성 반영
- Clean watch 13건이 모두 base 통과 후 또는 형성 중 단계인 것이 직접 증거 — LLM이 base를 "발견"은 잘 하나 "buy zone 시점"은 본질적으로 희귀

**(나) v2 ignore-편향 가설**: ❌ **기각**
- entry 임박 직전인데 LLM이 entry 못 만든 종목 0건
- watch 종목들이 다양한 base 단계에 분포 (pre/early/mid/late-extended/failed) — LLM이 단계 구분 정확
- v2가 "buy zone에 있을 때만 entry, 그 외는 watch"라는 정책 일관 적용

**사용자 우려 검증**: 
> "entry는 베이스 완성 + 피봇 돌파 임박이라는 좁은 윈도우(약 5거래일)에서만 발생"

이 우려가 데이터로 직접 확인됨. NVST entry는 "breakout 1/6 → 1/13 분석 시점은 1주 후 = 5일 윈도우 내 4일째"에 위치. 5거래일 sample은 이 윈도우 1 사이클을 정확히 1회 catch.

### B.5.5 권고 사항

**B.6 진입 검토 가능 (entry 1건 활용)**:
- NVST에 대해 (6) 산출 entry_params 사용자 차트 검증
- entry_params 정상성: pivot $22.67 (handle high), stop $21.47 (-5.3% logical), size 4.9% (low_volume_breakout flag로 0.7배 적용), target $27.20 (+20%) — 모두 §6.3·자문 §0 기준 부합
- llm_call_id 260 (5호출), 262 (6호출) DB에 기록 — 헌법 §2.5 충족

**Phase 1.3 데이터로 자연 누적**:
- Phase 1.3 7거래일 daily cron 누적에서 자연 발생 entry 5~10건 추가 확보 예상 (1.1.15 약점 F 표본 보강)

### B.5.5 부수 발견 항목

**ETF 잘못 통과 6건** (symbol_type='STOCK' 필터 통과했지만 v2가 ETF로 판정):
- EMF, RMT (1/12)
- CEE (1/13, 1/14)
- KF (1/14)
- CAF (1/15)

후속 점검: us_symbol_master에서 이 6개 종목의 symbol_type 정정 또는 ADR-013 보강 필요. 현재는 v2 ETF Pre-Check가 안전망 역할 정상 작동.

**EA 분류 불안정**: 3회 평가 모두 다른 결과 (watch/ignore/timeout) — v2 후속 검토 항목.

**timeout 31건 outer 360s**: B.5.4의 13.3% → B.5.5의 7.75%로 개선. CLI inner 120s timeout → outer 360s 한도 합리적 검증됨.

**B.5.5 사용한 LLM 호출 총량**:
- (5) analyze_chart 호출: 369 정상 + 31 timeout + 다수 retry = ~440~450 호출 (llm_calls 기록)
- (6) calculate_entry_params 호출: 1 (NVST)
- 총 ~441~451 호출 (Max 플랜 5시간 윈도우 다회 사용 — 전체 941.7분 / 60 = 약 15.7시간 분산)

---

## 1.2 트랙 B.6.1 — Evaluator 평가 입력 데이터 export (2026-05-05)

**목적**: NVST entry_params (B.5.5 유일 entry case)에 대한 외부 평가 (Web Claude Minervini Evaluator project) 입력 자료 준비.

**산출 파일**:
- `/tmp/eval_export/nvst_b6_eval_input.json` (72,318 bytes)
- `~/Downloads/nvst_b6_eval_input.json` (72,318 bytes — 사용자 접근용 복사)

**JSON 구조**:
- `evaluation_target`, `phase`
- `context`: 분석 시점 (2026-01-13), 시장 메타데이터 (US500 +1.73%/+9.37% above SMAs, breadth 1.41), B.5.5 sample source, 프롬프트 lock 상태
- `stage_5`: (5) analyze_chart 호출 정보
  - llm_call_id 260, model, timestamp, tokens, duration, cost_source
  - `input_payload`: identifier + screening + current_metrics + daily_ohlcv 60행 + weekly_ohlcv 52주 + indicators_recent 60행
  - `output_parsed` + `output_raw`
- `stage_6`: (6) calculate_entry_params 호출 정보
  - llm_call_id 262, model, timestamp, tokens, duration
  - `input_payload`: stage_5 input + `prior_analysis` 전달
  - `output_parsed` (13필드 EntryParams) + `output_raw`
- `user_evaluation_questions`: 8개 (사용자 정성 평가용 — pivot 일치, stop rule 부합, weight 적정성, target 산식, entry_window 일관성, (5)↔(6) 모순, low_volume_breakout 처리, breakout_volume_requirement 의미)
- `evaluator_focus_areas`: 4개 (decision tree 부합, cross-field 의미적 일관성, warnings 적정성, 약점 F 검증)

**llm_calls 참조**:
- call 260 (analysis_5_us): prompt 22,943 tok / completion 4,582 tok / 99.6s
- call 262 (entry_params_6_us): prompt 28,149 tok / completion 4,459 tok / 92.9s

**핵심 출력 요약** (Evaluator가 검토할 대상):
- **(5) output**: classification=entry, confidence=0.75, pattern=cup_with_handle, risk_flags=[low_volume_breakout]
- **(6) output**: pivot=$22.67, stop=$21.47 (-5.3% logical), size=4.9% (7×0.7), target=$27.20 (+20%), entry_window=3, max_chase_pct=5.0, vol_req=ge_1.4x_50day_avg
- **(6) notes 핵심 일관성**: "Cup-with-handle pivot at handle high $22.67 (Dec 22). Logical stop at $21.47 (handle low $21.575 × 0.995); absolute stop would be $21.12 (−7%). Logical stop tighter (−5.3%) — used logical. Size: default tier 7% (cup-with-handle with risk flag) × 0.7 (low_volume_breakout flag) = 4.9%. Target 20% (standard). Breakout Jan 6 at $23.21 on 1.02× avg volume (marginal confirmation, hence flag)."

**(5) ↔ (6) pivot 표기 차이 (의도된 동작)**:
- (5) reasoning: pivot $22.77 (base high $22.67 + $0.10 trigger buffer)
- (6) output pivot_price: $22.67 (raw handle high)
- 일치 — v1 프롬프트 §1 명시: trigger buffer는 informational, pivot_price 필드는 raw 값. 그대로 정합.

**다음 단계**:
- 사용자 정성 평가 (NVST 차트 직접 검토) — 사용자 작업
- Evaluator 평가 의뢰 — 사용자 결정으로 진행 시 위 export 파일 첨부
- 두 평가 결과 수렴 후 1.2 게이트 §6 (산출 파라미터 합리성) 평가 → 1.2 종료 또는 v1.1 미세 튜닝

---

#### B.5.5 중단 기록 (2026-05-04, 사용자 요청)

batch 1/5 (2026-01-12) 진행 11/80 시점에 사용자 요청으로 중단. harness + monitor 프로세스 모두 정리.

**11건 부분 결과** (저장 파일: /tmp/b5_5_results.jsonl, /tmp/b5_5_log.txt):

| cum | symbol | duration | classification |
|---|---|---|---|
| 1 | INTC | 102.1s | ignore |
| 2 | ONC | 331.5s | ignore (retry 추정) |
| 3 | SLNHP | 62.1s | ignore |
| 4 | EMF | 23.9s | ignore (ETF Pre-Check 추정) |
| 5 | BLTE | 84.3s | ignore |
| 6 | RENT | 88.5s | ignore |
| 7 | SF | 332.7s | ignore (retry 추정) |
| 8 | TK | 119.1s | **watch** |
| 9 | AU | 102.5s | ignore |
| 10 | APH | 351.2s | ignore (retry 추정) |
| 11 | ELE | 242.6s | ignore |

11건 분포: ignore 10 / watch 1 / entry 0 / timeout 0. duration median 102.5s, 3건이 outer 360s 직전 (242~351s) — retry 발생률이 B.5.4보다 높아 보임 (11건 중 3건 = 27%).

**재개 시 권고사항**:
- /tmp/b5_5_samples/2026-01-{12,13,14,15,16}.txt sample 리스트는 보존됨 — 동일 seed로 재추출 가능
- /tmp/b5_5_sample_harness.py 보존됨 — 그대로 재실행 가능
- 11건 부분 결과는 daily_analysis_us 테이블에 이미 기록됨 (force-recompute로 덮어쓰기됨, llm_calls에도 기록)
- 재개 시점에 batch 1/5 처음부터 다시 시작하거나 12번부터 이어가는 옵션 가능 (사용자 결정)
- retry 빈도 27% (예상 ~13~18%보다 높음) 원인 점검 필요 시 — 1.1.4-b CLAUDE.md auto-load 변동 또는 v2 프롬프트 길이 (~22,700 토큰) 영향 가능성

**미커밋 변경**: B.1~B.4 결과물(prompts/calculate_entry_params_v1.md / models/entry_params.py / core/result_parser.py / scripts/run_single_symbol.py / tests/test_entry_params.py / tests/test_run_single_symbol_entry_flow.py)은 commit β로 분리 예정. B.5.5 결과 + 1.2 게이트 통과 후 commit β 묶어 처리.

### 1.2 거버넌스 드리프트 발견 — Architect 인계 (2026-05-04)

다음 4건은 _meta/ 거버넌스 문서와 코드/현 진행 사이 불일치. ADR-005 §3.4에 따라 Builder는 phase1_progress.md에 발견 사실만 기록. Architect 세션에서 일괄 갱신 예정.

1. **`_meta/06_CURRENT_STATE.md`**: "Phase 1.2 진입 대기"로 기재. 실제는 1.2 트랙 B.1~B.5까지 진행됨. B.5.5 종료 시 일괄 갱신.
2. **`_meta/05_GLOSSARY.md` Part B.2 `entry_params` 스키마**: 구버전 (volume_confirmation, expected_target.conservative/optimistic, valid_until). 현 v1 프롬프트 + EntryParams Pydantic은 신규 13필드 (breakout_volume_requirement Literal 3개 enum, expected_target_price+expected_target_pct, entry_window_days, max_chase_pct_from_pivot, pattern_basis 5enum, notes, known_warnings Literal 10개, other_warnings).
3. **`_meta/05_GLOSSARY.md` Part B.2 `risk_flags` 스키마**: 구 7개값 (high_rs_rating, extended_from_ma50, low_volume, thin_base, sector_overconcentration, earnings_imminent, market_weakness). v2 프롬프트 + AnalysisResult.VALID_RISK_FLAGS는 12개값 (climax_run, late_stage_base, extended_from_ma, faulty_pivot, low_volume_breakout, narrow_base, wide_and_loose, thin_liquidity_us_only, prior_uptrend_insufficient, volume_contraction_on_advance, reverse_split_distortion, etf_methodology_mismatch).
4. **`_meta/phases/phase1_brief.md` §3.2 1.2.2**: "stop_loss_pct ∈ [-8, -5]" 명시. 실제 EntryParams Pydantic + v1 프롬프트는 [-10, -5] (사전 자문 §0.6 채택, Minervini "절대 floor" 정합).

처리 방침 (Architect 결정): B.5.5 종료 시 일괄 갱신. B.5.5 차단 무관.


---

## Q-002 등록 대기

> 아래 텍스트는 `_meta/operational_queue.md`의 "대기 중인 작업" 섹션에 등록할 내용이다.
> Builder가 직접 수정할 수 없는 문서이므로 (ADR-005), 1.1 종료 시 Architect 세션이 옮겨 적는다.

---

### Q-002: Phase 1 DB 마이그레이션 적용 — daily_analysis_kr, daily_analysis_us, llm_calls (등록: 2026-04-28, 완료: 미정)

**관련 commit**: `phase1/1.1-llm-analysis-skeleton` 브랜치 머지 commit (머지 후 hash 기입 예정)
**관련 ADR**: ADR-009 (LLM 분석 테이블 설계), ADR-010 (마이그레이션 3종 산출물)
**Alembic revision**: `20260428_000001` (down_revision: `20260424_000001`)
**raw SQL 파일**: `db/migrations/sql/20260428_000001_add_daily_analysis_and_llm_calls.sql`
**위험도**: 중간 (DB 변경 — CREATE TABLE 3개, 롤백 가능)
**예상 소요**: 5분 미만 (CREATE TABLE 3개, 기존 테이블 없음)
**타이밍 윈도우**: KR cron(19:00) · US cron(08:00) 각각 직전 30분을 피하면 어느 시각이든 안전

**적용 전 사전 확인**:

```powershell
# 1. git pull 상태 확인
cd C:\path\to\DataBatcher
git log --oneline -3

# 2. 대상 테이블 미존재 확인 (둘 다 빈 결과여야 함)
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "SHOW TABLES FROM trade LIKE 'daily_analysis%';"
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "SHOW TABLES FROM trade LIKE 'llm_calls';"
```

**적용 (raw SQL 직접 실행 — 이번에도 Alembic 미사용, 이슈 §G 유지)**:

```powershell
cd C:\path\to\DataBatcher
git pull

Get-Content db\migrations\sql\20260428_000001_add_daily_analysis_and_llm_calls.sql | `
  docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" trade
```

**적용 후 검증 (세 테이블 DESCRIBE)**:

```powershell
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "DESCRIBE trade.daily_analysis_kr;"
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "DESCRIBE trade.daily_analysis_us;"
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "DESCRIBE trade.llm_calls;"
```

**완료 기준**: 세 테이블의 DESCRIBE 결과가 `_meta/phases/phase1_brief.md` §4.1·§4.2·§4.3 스키마와 일치

**백업**: 생략 (Q-001과 동일 사유 — CREATE TABLE은 기존 데이터 무영향)

**롤백 방법**:

```powershell
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" trade `
  -e "DROP TABLE IF EXISTS llm_calls; DROP TABLE IF EXISTS daily_analysis_us; DROP TABLE IF EXISTS daily_analysis_kr;"
```

**메모**:
- Alembic 적용은 이번에도 생략 (이슈 §G — PROD `alembic_version` 동기화 미해결). raw SQL만 적용.
- 이슈 §G 해소 시점(별도 결정)에 PROD stamp + upgrade head 일괄 처리 예정.

---

## 1.1.4-a 설계 보고 메모 (2026-04-28)

LLMBackend 추상화 설계 확정 (코드 없음):
- LLMResponse Pydantic 모델 (9 필드: text, model, prompt/completion_tokens, cost_usd, duration_ms, request_payload, response_payload, error)
- LLMBackend Protocol (call 메서드 단일)
- ClaudeCodeCLIBackend / AnthropicAPIBackend 두 구현체 계획
- 단일 책임 원칙: Backend = 단일 호출만. 재시도·DB INSERT는 wrapper(1.1.7)에서.
- ADR-011 §3 결정: cost_usd는 CLI에서 NULL 허용 (당시) → 1.1.4-b 이후 β안으로 변경(참고값 저장).

## 1.1.4-d 완료 메모 (2026-04-29)

- models/db_models.py: LlmCall(10필드), DailyAnalysisKR(11필드), DailyAnalysisUS(11필드). SQLAlchemy 2.0 스타일.
  - 비고: LlmCall.id는 `Integer`(SQLite 호환) 사용. MySQL 본番은 migration SQL이 BIGINT AUTO_INCREMENT로 생성하므로 ORM과 불일치 없음.
- core/db.py: make_engine() + make_session_factory(). .env 로드 순서: 루트 → 앱 로컬(override=False).
- core/llm_call_recorder.py: call_and_record() 62줄. _check_daily_call_limit() placeholder.
  - daily_call_limits hook 인터페이스: `(db_session: Session, module: str) -> bool`. 1.3 cost_tracker로 교체 시 시그니처 그대로.
- 단위 테스트 5개 (SQLite in-memory), 통합 검증 1건 (DEV MySQL INSERT/SELECT/DELETE) 모두 통과.

## 1.1.4-c 결정 메모 (2026-04-29)

API 백엔드 표본 호출(실제 SDK 호출) 건너뜀 — 사용자 결정.

근거: 운영 백엔드는 CLI(Max 플랜). API는 fallback 또는 Phase 5 전환 옵션.
본 Phase 운영 중 API 호출 발생 안 함. 키 발급·관리·노출 위험 회피.
검증 수단: 단위 테스트(mock) 16/16 통과. get_backend factory cli/api/unknown 분기 검증.
실제 SDK 호출 검증: (a) 사용자 결정으로 Phase 1 후반 / (b) ADR-012 §3.3 약관 위반 징후 시 / (c) ADR-013 전환 결정 시.
잔존 위험: SDK 응답 객체 구조·에러 클래스명이 가정과 다를 수 있음. 전환 시점에 발견·수정.

## 1.1.4-b 진단 메모 (2026-04-28)

CLI sanity check 및 CLAUDE.md 탐색 범위 진단 결과:

- `claude -p --output-format json`은 cwd + 상위 디렉토리를 탐색해 CLAUDE.md를 자동 로드함.
  DataBatcher 루트에서 실행 시 ~16,000 토큰 / 시스템 temp에서 실행 시 ~7,900 토큰 (49% 절감).
- ClaudeCodeCLIBackend의 `cwd=tempfile.gettempdir()`로 CLAUDE.md/메모리 로드 차단.
- CLAUDE.md 로드 상태에서 단발성 66,873 토큰 사고 1회 발생 (auto-memory 변동 추정). 재현 불가.
- **후속 (1.1.7 wrapper 시점)**: 프롬프트 토큰 폭증 감지 — input_data 추정 대비 2배 이상 시 sync_log WARN. ADR-012 §3.2 항목.

## 1.1.8~1.1.13 완료 메모 (2026-04-28)

### 구현 파일
- `prompts/analyze_chart_v1.md`: brief §6.2 프롬프트 본문. "## Input Payload" 섹션으로 끝남 — prompt_builder가 JSON을 이어붙임.
- `models/analysis_result.py`: `AnalysisResult` Pydantic 모델. `classification`, `confidence`, `pattern`, `risk_flags` 화이트리스트 검증 포함.
- `core/result_parser.py`: `parse_analysis_result()` + `ParseError`. markdown fence 재제거 + JSON 파싱 + Pydantic 검증.
- `core/data_loader.py`: `load_symbol_payload()` + `get_screened_symbols()`. 일봉 60행 / 주봉 52주 / 인디케이터 pivot / 52주 고가·저가·volume_ma20 계산. `conditions_met` NULL 허용(P0.5 이전 데이터 대응).
- `core/prompt_builder.py`: `build_analyze_chart_prompt()` + `build_entry_params_prompt()`. 템플릿 로드 + JSON 직렬화 결합.
- `scripts/run_single_symbol.py`: 완전한 CLI. --symbol/--region/--date/--backend/--dry-run/--force-recompute. ParseError 발생 시 1회 LLM 재호출.

### 데이터 수정 사항
- `us_symbol_master`에 `sector_detail` 열 없음 → `sector, industry` 쿼리로 수정 (KR/US 공통).

### 1.1.13 검증 결과 (2026-04-28, DEV DB, US 5종목)

| symbol | classification | confidence | pattern | risk_flags |
|---|---|---|---|---|
| AAOI | ignore | 0.95 | none | high_rs_rating, extended_from_ma50 |
| ABVX | ignore | 0.80 | cup_handle | high_rs_rating, low_volume |
| ADV | ignore | 0.95 | none | high_rs_rating, thin_base, low_volume |
| BWET | ignore | 0.95 | none | high_rs_rating, extended_from_ma50, thin_base |
| CLSM | entry | 0.72 | flat_base | high_rs_rating |

- 응답 품질: 각 종목의 클라이맥스 런·리버스스플릿·베이스 패턴을 정확히 식별. CLSM은 22주 flat base + 브레이크아웃 직후를 `entry`로 올바르게 판단.
- 토큰: 약 21,000 input / 1,400~2,100 output. 프롬프트 길이 ~30,700자.
- 비용: 호출당 $0.05~$0.12 (cli 모드, Max 플랜 참고값 — 실제 청구는 Max 구독료).
- `daily_analysis_us` 5행, `llm_calls` 7행 (기존 1행 포함) DEV DB에 기록 확인.

### 1.1.15 사용자 검토 포인트
- 응답 품질이 이미 안정적이면 → v1 확정 + 1.2로 이동.
- 추가 튜닝 필요 시 → `prompts/analyze_chart_v1.md` 수정 후 `--force-recompute`로 재검증. 큰 변경만 v2.
- 1.1.13 결과에서 주목할 점: `ignore` 4건 / `entry` 1건. 상위 RS 종목이 과열된 2026-04 시장 상황 반영. 정상.

## 1.1.15 v2 작성 메모 (2026-05-01)

### v1 결과 백업 현황

`_save_result()`는 DELETE+INSERT 방식 — `--force-recompute` 실행 시 `daily_analysis_us`의 v1 행이 overwrite됨.
v1 결과 보존 경로:
- `/tmp/eval_export/*.json` + `/Users/hank.es/Downloads/` (eval_input.json 5종목)
- `llm_calls` 테이블 (request_payload + LLM 원본 응답 보존): id 2=AAOI, 4=ABVX, 5=ADV, 6=BWET, 8=CLSM

### 외부 평가 진단 (Architect → Builder) — 약점 7가지

| ID | 우선순위 | 약점 | 근거 |
|---|---|---|---|
| A | HIGH | risk_flags 카테고리 에러 | 5/5에서 `high_rs_rating` 포함 — RS 99는 양성 신호인데 위험으로 분류 |
| B | HIGH | reasoning ↔ risk_flags 불일치 | reasoning에 "climax run", "wide-and-loose" 명시했지만 해당 flag 없음 |
| C | HIGH | reverse split 미탐지 | price_data_notes에 corporate action 있어도 `reverse_split_distortion` flag 없음 |
| D | HIGH | ETF 탐지 부재 | BWET을 개별 주식처럼 분석. 정책: ETF면 즉시 ignore + etf_methodology_mismatch |
| E | MEDIUM | pattern naming discipline 부족 | ABVX를 cup_handle로 명명, 실제 구조 부재 |
| F | MEDIUM | pivot/breakout 정확도 | CLSM pivot $24.00 (실제 $24.50), breakout date 1주 어긋남 |
| G | LOW | liquidity 보고 | US ADV < $5M → thin_liquidity_us_only (informational), KR은 평가 안 함 |

### v1 → v2 주요 변경 사항

| 약점 | 수정 위치 | 내용 |
|---|---|---|
| A+B+C | §5 Risk Flags | 12개 taxonomy로 제한. "Trend Template 양성 특성은 NEVER risk_flags" 명시. reasoning↔flags 일관성 규칙. `reverse_split_distortion` 트리거 조건 명시. |
| D | Pre-Check (프롬프트 최상단) | `market == "ETF"` 또는 fund vehicle 감지 시 즉시 ignore+etf_methodology_mismatch 반환 |
| E | §4 Base Pattern | 패턴별 textbook 정의 표 추가. "구조 부재 시 none 사용" 명시. `cup_handle`→`cup_with_handle`, `VCP`→`vcp` |
| F | §6 Pivot & Breakout | pivot = max(weekly.high) + $0.10 명시. breakout_date 정의. 실제 데이터 불일치 시 confidence -0.2 |
| G | §5 Rule 3 | thin_liquidity_us_only: US 개별주만, volume_ma20×price < $5M. KR은 평가 안 함. |
| 수정 6 | §7 Confidence | calibration 규칙 4개 명시 (reasoning 품질, pattern-data 불일치, multi-flag, high confidence 조건) |

### Pydantic 모델 변경 (models/analysis_result.py)

VALID_PATTERNS (v1 → v2):
- 제거: `cup_handle`, `VCP`
- 추가: `cup_with_handle`, `vcp`
- 유지: `flat_base`, `double_bottom`, `none`

VALID_RISK_FLAGS (v1 → v2):
- 제거: `high_rs_rating`, `extended_from_ma50`, `low_volume`, `thin_base`, `earnings_imminent`, `market_weakness`, `sector_overconcentration`
- 추가: `climax_run`, `late_stage_base`, `extended_from_ma`, `faulty_pivot`, `low_volume_breakout`, `narrow_base`, `wide_and_loose`, `thin_liquidity_us_only`, `prior_uptrend_insufficient`, `volume_contraction_on_advance`, `reverse_split_distortion`, `etf_methodology_mismatch`

단위 테스트: 25/25 통과 (기존 13 갱신 + v2 신규 12)

### v1 결과 백업 (2026-05-02)

- 파일: `/tmp/eval_export/v1_results_backup.json` (4,629B) + Downloads 복사
- 5종목 포함 확인. llm_call_ids: AAOI=2, ABVX=4, ADV=5, BWET=6, CLSM=8
- 중요 발견: BWET + CLSM 모두 `market='ETF'` — 5종목 중 2개가 ETF

### v2 5종목 재호출 완료 (2026-05-02)

settings.yaml timeout_seconds 60→120 조정 (v2 프롬프트 길어져 AAOI 첫 시도 timeout).

| symbol | type | v1 날짜 | v2 날짜 | v1 분류 | v2 분류 | v1 risk_flags | v2 risk_flags | 핵심 변화 |
|---|---|---|---|---|---|---|---|---|
| AAOI | stock | 04-10 | 04-27 | ignore (0.95) | ignore (0.90) | high_rs_rating, extended_from_ma50 | climax_run, extended_from_ma, wide_and_loose | flag 교정 |
| ABVX | stock | 04-10 | 04-17 | ignore (0.80) | ignore (0.75) | high_rs_rating, low_volume | climax_run, wide_and_loose, reverse_split_distortion | cup_handle→none, split flag |
| ADV | stock | 04-10 | 04-27 | ignore (0.95) | ignore (0.90) | high_rs_rating, thin_base, low_volume | reverse_split_distortion, climax_run, wide_and_loose, thin_liquidity_us_only | split + liquidity flag |
| BWET | ETF | 04-10 | 04-27 | ignore (0.95) | ignore (1.0) | high_rs_rating, extended_from_ma50, thin_base | etf_methodology_mismatch | Pre-Check 9초 즉시 종료 |
| CLSM | ETF | 04-10 | 04-27 | **entry (0.72)** | **ignore (1.0)** | high_rs_rating | etf_methodology_mismatch | **분류 반전** ✓ |

핵심 검증 결과:
- ETF 탐지 (BWET, CLSM 2/2): ✅ confidence=1.0, etf_methodology_mismatch, 각 9·11초 즉시 종료
- CLSM 분류 반전 (entry→ignore): ✅ v2 핵심 교정 확인
- high_rs_rating 제거 (5/5): ✅ v2에서 단 1건도 없음
- reverse_split_distortion 자동 포함: ✅ ABVX(~Jul 2025), ADV(2026-03-26) 정확 탐지. AAOI는 price_data_notes의 이벤트가 모멘텀 급등으로 판단 (합리적 — vol_ratio 역전 없음)
- thin_liquidity_us_only: ✅ ADV $3.2M daily dollar volume 직접 계산해 적용
- taxonomy 외 flag 출력: 0건 ✅ (단위 테스트 whitelist 통과)
- pattern naming: ✅ ABVX cup_handle → none 교정

prompt_tokens: 22,617~22,756 (평균 22,715, v1 평균 21,451 대비 +1,264 — v2 프롬프트 길이 증가)
duration_ms: AAOI 77s, ABVX 70s, ADV 64s, BWET 9s, CLSM 11s

export 파일 (Downloads + /tmp/eval_export/):
- 5종목 _eval_input_v2.json (v2 결과 eval_input 포맷)
- 5종목 _v1_v2_comparison.json (v1 vs v2 key_differences)
- v1_results_backup.json

⚠️ 주의: v2 분석 날짜가 v1(2026-04-10)과 다름 — `--date` 미지정 시 MAX(date) 사용. 비교 시 데이터 시차 혼재. `_v1_v2_comparison.json`에 note 기재.

## 1.1 게이트 체크리스트 (2026-05-02)

phase1_brief.md §9.1 기준:

| # | 항목 | 결과 | 비고 |
|---|---|---|---|
| 1 | daily_analysis_kr, daily_analysis_us, llm_calls 테이블 DEV 존재 | ✅ | Alembic 마이그레이션 적용 완료, llm_calls 18건 기록 확인 |
| 2 | Q-002 운영 큐 항목 등록됨 | ✅ | 텍스트 작성 완료. 운영 적용은 Architect 영역 (PROD 접근 필요) |
| 3 | apps/llm-analysis/ 디렉토리 구조 §5.2와 일치 | ✅ | 1.1.3에서 25파일 구조 검증 |
| 4 | LLMBackend 인터페이스 + CLI·API 두 구현체 | ✅ | core/anthropic_client.py. mock 단위 테스트 통과 |
| 5 | 표본 5종목 CLI 백엔드 (5) 호출 성공 (실패 ≤ 1건) | ✅ | v1 5종목 + v2 5종목 = 총 10건. timeout 재시도 포함 최종 실패 0건 |
| 6 | 표본 1종목 API 백엔드 (5) 호출 성공 | ⏭️ | 사용자 결정으로 미룸 (1.1.4-c). mock 단위 테스트로 추상화 검증. 전환 결정 시 수행 |
| 7 | AnalysisResult 스키마 준수 | ✅ | v2 whitelist 25/25 통과. v2 5종목 실호출 parse 성공, taxonomy 위반 0건 |
| 8 | llm_calls 테이블 호출 로그 기록 | ✅ | 18건 기록 (v1 7건 + v2 5건 + timeout 재시도 포함) |
| 9 | daily_analysis_us에 결과 행 생성 | ✅ | v2 5종목 결과 행 존재 |
| 10 | (5) 프롬프트 v1 확정 commit | ✅→v2 | v1 보존, v2를 production prompt로 lock. 외부 평가 production-ready 판정 |
| 11 | phase1_progress.md에 1.1 종료 보고 작성 | ✅ | 이 섹션 |

**결과: 10/11 통과 (⏭️ 1건 — 사용자 승인 결정으로 미룸. Phase 1 진행에 영향 없음)**

---

## 1.1 단계 종료 보고 (2026-05-02)

**종료 일시**: 2026-05-02

### 단계별 완료 현황

| 항목 | 상태 |
|---|---|
| 1.1.1 DB 마이그레이션 3종 산출물 | ✅ 완료 |
| 1.1.2 운영 환경 마이그레이션 적용 | ⏳ 사용자 직접 (Q-002) |
| 1.1.3 apps/llm-analysis/ 골격 | ✅ 완료 |
| 1.1.4 LLMBackend 인터페이스 | ✅ 완료 |
| 1.1.5 CLI 백엔드 | ✅ 완료 |
| 1.1.6 API 백엔드 | ✅ 완료 (mock 검증) |
| 1.1.7 llm_calls 기록 wrapper | ✅ 완료 |
| 1.1.8 프롬프트 v1 작성 | ✅ 완료 (v1 보존, v2로 승계) |
| 1.1.9 data_loader.py | ✅ 완료 |
| 1.1.10 prompt_builder.py | ✅ 완료 |
| 1.1.11 result_parser + AnalysisResult | ✅ 완료 (v2 taxonomy 갱신) |
| 1.1.12 run_single_symbol.py CLI | ✅ 완료 |
| 1.1.13 단일 종목 검증 5종목 | ✅ 완료 |
| 1.1.14 API 백엔드 단일 종목 검증 | ⏭️ 미룸 (사용자 결정) |
| 1.1.15 프롬프트 튜닝 v2 + 외부 평가 | ✅ 완료 |

### v1 → v2 전환 완료

**production prompt = `prompts/analyze_chart_v2.md`** (settings.yaml `prompts.analyze_chart: "v2"`)
v1은 `prompts/analyze_chart_v1.md`로 보존.

### 외부 평가 결과 (Web Claude Minervini Evaluator, Opus 4.7)

| 약점 | 차원 | 결과 |
|---|---|---|
| A (risk_flags 카테고리 에러) | HIGH | ✅ improved — high_rs_rating 5/5 제거 |
| B (reasoning↔flag 불일치) | HIGH | ✅ improved — climax_run 등 flag 일관성 확보 |
| C (reverse_split 미탐지) | HIGH | ⚠️ partial — ABVX/ADV 자동 감지, AAOI 누락 (ratio 작고 시기 오래됨) |
| D (ETF 탐지 부재) | HIGH | ✅ improved — BWET/CLSM 2/2 즉시 감지, CLSM entry→ignore 반전 |
| E (pattern naming discipline) | MEDIUM | ✅ improved — ABVX cup_handle→none 교정 |
| F (pivot/breakout 정확도) | MEDIUM | ⏭️ untestable — 표본 5종목 모두 ignore/ETF, entry 후보 없음 |
| G (liquidity 정책) | LOW | ✅ improved — ADV thin_liquidity_us_only $3.2M 자동 계산 |

**평가 최종 판정: production-ready (5종목 evaluator_verdict: agree)**

### 1.1 게이트 통과

10/11 ✅ (API 백엔드 실호출 1건 ⏭️ — 사용자 결정)

### 다음 단계

**1.2**: `calculate_entry_params()` — entry 후보 종목에 대한 진입 파라미터 산출
- `prompts/calculate_entry_params_v1.md` 작성
- `EntryParams` Pydantic 모델
- `run_single_symbol.py --with-entry-params`
- 표본 entry 종목 5건 이상 검증

## 단계 1.3 — run_daily_analysis 메인 진입점 + 7거래일 누적 검증

### 1.3 시작 (2026-05-07, Mac DEV 새 PC)

**브랜치**: `phase1/1.3-daily-analysis` (base: 1fb1db3 = 1.2 commit β `dd09e2d` + 거버넌스 갱신 `92a8b77` + 1.3 진입 마크 `1fb1db3`).

main 브랜치는 1.1·1.2 작업물을 포함하지 않고 `103b54e` (us-index fix)에서 정지. Phase 1 종료 시 일괄 머지 전략 채택 (사용자 결정).

미커밋 `new_pc_setup_checklist.md` 변경(115/22)은 stash 처리 후 진행 (사용자 결정).

### 1.3.0 — (6) v1.1 fix 3건 (2026-05-07)

**commit**: `c2114f7 feat(llm-analysis): Phase 1.3.0 — calculate_entry_params v1.1 fix 3건`

NVST B.5.5 1차 Evaluator 평가에서 도출된 (6) 함수 표기·투명성 문제 3건을 v1.1로 minor revision 발행.

| Fix | 항목 | 변경 |
|---|---|---|
| 1 | dual stop_pct 분리 (transparency) | `stop_loss_pct` → `stop_loss_pct_from_pivot` (rename) + `stop_loss_pct_from_current_price` (NEW). \|from_current_price\| > 7.5 시 `stop_distance_from_current_price_exceeds_book_limit` auto-emit |
| 2 | `trigger_price` schema-level 분리 | `pivot_price`(raw) + `trigger_price`(buffered, default pivot * 1.001) 둘 다 emit. (5) reasoning과 (6) 구조 필드 간 ambiguity 제거 |
| 3 | breakout volume mismatch auto-warning | `observed_breakout_volume_ratio` (NEW, optional). observed < requirement threshold(1.3/1.4/1.5) 시 `breakout_volume_below_requirement` auto-emit (size 조정과 무관) |

**스키마 변경**:
- EntryParams 필드 13 → 16 (rename 1 + new 4: `current_price`, `trigger_price`, `stop_loss_pct_from_current_price`, `observed_breakout_volume_ratio`)
- KnownWarning enum 10 → 12

**산출물**:
- `apps/llm-analysis/prompts/calculate_entry_params_v1_1.md` (신규, v1 보존)
- `apps/llm-analysis/models/entry_params.py` 갱신 (auto-emit validator)
- `apps/llm-analysis/core/result_parser.py` 갱신 (v1 → v1.1 legacy 매핑: `stop_loss_pct` rename, `trigger_price` derive, `from_current_price` derive)
- `apps/llm-analysis/config/settings.yaml`: `prompts.calculate_entry_params: v1` → `v1_1`
- 단위 테스트: `tests/test_entry_params.py` 39 → 53 (v1.1 신규 14건)
- `tests/test_run_single_symbol_entry_flow.py` fixture v1.1 갱신

**검증 결과**:

(1) 단위 테스트 — 6 파일 합산 **114/114 통과** (test_entry_params 53/53, test_anthropic_client 16/16, test_llm_call_recorder 5/5, test_prompt_builder 5/5, test_result_parser 25/25, test_run_single_symbol_entry_flow 10/10).

(2) NVST 실 LLM 재호출 검증 — 합성 prior_analysis 방식 (B.5.5 데이터는 이전 PC DB에만 있고 Mac DEV 미동기화)

먼저 `run_single_symbol --with-entry-params --force-recompute`로 (5) v2 + (6) v1.1 풀 호출:
- (5) v2 결과: classification=`ignore`, pattern=`none`, risk_flags=[late_stage_base, narrow_base], confidence 0.75
- B.5.5 시점 entry 분류와 다른 결과 — **§M 분류 불안정의 또 다른 사례** (1.3 모니터링 항목 추가 1건)

(6) 검증을 위해 NVST 원본 (5) 결과를 phase1_progress.md B.5.5 기록으로부터 합성하여 (6) v1_1만 LLM 호출 (`/tmp/nvst_v11_validate.py`):

| 검증 항목 | 결과 |
|---|---|
| dual stop_pct emit | ✅ from_pivot=-5.3, from_current_price=**-7.6** (예상 -7.58% 1dp 일치) |
| trigger_price 분리 | ✅ pivot=22.67, trigger=22.69 (pivot * 1.001) |
| current_price echo | ✅ 23.23 (payload close 일치) |
| stop_distance auto-emit | ✅ \|-7.6\| > 7.5 → known_warning 자동 발행 |
| observed_breakout_volume_ratio emit | ✅ 1.02 (LLM이 chart에서 자동 추출) |
| breakout_volume_below_requirement auto-emit | ✅ 1.02 < 1.4 → known_warning 자동 발행 |

**6/6 OK**. v1.1 LLM 호출 메타: model=claude-sonnet-4-5, duration 107.9s, prompt 31,498 tokens, completion 5,492 tokens, llm_call_id=4.

LLM 응답이 v1_1 프롬프트의 example notes 구조를 거의 그대로 따라 emit — 가이드 준수 양호.

### 1.3 부수 모니터링 (Phase 1.3 진행 중 자연 관찰)

| 이슈 | 출처 | 1.3 누적 관찰 |
|---|---|---|
| §J ETF 잘못 통과 | B.5.5 (EMF/RMT/CEE/KF/CAF) | 1.3.9 누적에서 `etf_methodology_mismatch` 추적 예정 |
| §K (5) v2 분류 보수성 | NVST 운영자 시각 평가 | 1.3.9 entry 분류 종목들의 RS/breakout volume/lone signal 분포 추적 예정 |
| §L (6) v1.1 fix | 1.3.0 완료 — auto-emit 검증 통과 | 1.3.9 누적에서 두 auto-warning 자연 발생률 모니터링 |
| §M EA 분류 불안정 | EA 1/13~1/15 3회 평가 모두 다름 | **NVST도 추가 사례** (B.5.5 entry → 2026-05-07 ignore) |
| §N database_schema.md 드리프트 | 다른 세션 발견 (2026-05-07) | `apps/ingest-databatcher/docs/database_schema.md` (Last Updated 2026-02-26)가 운영 DB 실제 상태와 불일치. 누락 테이블: `daily_analysis_kr`, `daily_analysis_us`, `llm_calls`, `users`, `minervini_list_selection`, `alembic_version`. 삭제된 테이블 `metrics`가 문서에 잔존. 신규 컬럼 `conditions_met` 누락. `kr_sector_snapshot` 설명 잘못됨. **2026-05-07 본 세션에서 즉시 갱신 처리** — TOC + Table Summary 갱신, LLM Analysis Tables / Auth & User Tables 신규 섹션 추가, `conditions_met` 컬럼 + 8 키 명시, `metrics` 제거 (historical note만 잔존), `sync_log` "ETL + LLM 모니터링" 갱신, `kr_sector_snapshot` "테이블 존재" 정정, Scripts mapping에 LLM Analysis 추가. 1125 → 1325 lines. |

### 1.3.1~1.3.8 — 메인 진입점 + 모니터링 + 통제권 + Q-003 등록 (2026-05-07)

**개요**: 1.3.0 v1.1 fix 통과 후 곧바로 진행. 1.3.1~1.3.6은 코드 (DEV 작업), 1.3.7은 PowerShell 래퍼/install 스크립트 (DEV 작성, PROD 적용은 Q-003), 1.3.8은 Q-003 운영 큐 등록 (§10.4 1번 예외).

**산출물**:

| 단계 | 산출물 | 비고 |
|---|---|---|
| 1.3.2 | `core/cost_tracker.py` (신규 본문) — `DailyCallLimitExceeded` 예외, `check_daily_limit`, `count_calls_today`, `record_sync_log`, `check_terms_violation_signals`(9 패턴), `record_terms_violation_signal`, `get_cost_summary` | ADR-012 §3 모니터링 4종 모두 |
| 1.3.2 | `models/db_models.py` 갱신 — `SyncLog` ORM 추가 (read+write, 헌법 §2.2 준수: ingest-databatcher 함수 import 안 함, DB만 공유) | SQLite 호환 위해 PK는 Integer (MySQL prod는 BIGINT AUTO_INCREMENT) |
| 1.3.2 | `core/llm_call_recorder.py` 갱신 — wire-up cost_tracker. `_check_daily_call_limit` placeholder 제거, `check_daily_limit` 호출 (hard_stop 시 `DailyCallLimitExceeded` raise propagate). `_post_call_monitoring` 추가 (토큰 폭증 감지 + 약관 위반 징후 sync_log WARN 기록) | 1.1.7 후속 작업 + ADR-012 §3.2/§3.3 |
| 1.3.1 / 1.3.3-5 | `scripts/run_daily_analysis.py` (신규 본문, ~330줄) — argparse 5종(--region BOTH/KR/US, --date, --limit, --force-recompute, --dry-run, --backend), KR/US 순차 처리, skip_if_exists 캐싱, `DailyCallLimitExceeded` catch, 모듈 킬 스위치, 부분 실패 허용(per-symbol sync_log 기록 후 계속), job-level sync_log running/success/WARN/ERROR 마커, 종료 코드 0/1/2 | brief §5.5 + §7.6 |
| 1.3.6 | `scripts/show_cost_summary.py` (신규 본문) — 일일 한도 잔여, 모듈별 통계, 일별 합계, sync_log llm_* WARN/ERROR 카운트, 최근 monitoring events. `--days N --json` 지원 | ADR-012 §3.4 |
| 1.3.7 | `ops/scheduler/windows/run_analysis_today.ps1` (신규 본문) — venv 자동 탐지, 로그 파일 자동 생성, run_daily_analysis + show_cost_summary 연쇄 실행 | brief §8.3.1 |
| 1.3.7 | `ops/scheduler/windows/install_task.ps1` (신규 본문) — LLMAnalysis_KR (21:00 KST) / LLMAnalysis_US (16:00 KST) 등록, idempotent (기존 작업 unregister 후 재등록) | brief §8.3.2 |
| 1.3.8 | `_meta/operational_queue.md` Q-003 등록 (§10.4 1번 예외, 본 1.3 단계 한정 허용) | Q-002 선행 조건 명시, 적용 절차 9단계 + 검증 4종 + 롤백 |

**검증 결과**:

(1) 단위 테스트 — 7 파일 합산 **132/132 통과**:
- test_anthropic_client 16/16
- test_cost_tracker 17/17 (신규 — limit 분기 6, terms violation 6, sync_log 2 등)
- test_entry_params 53/53
- test_llm_call_recorder 6/6 (구 contract 5/5 → 신규 contract 6/6 갱신; soft_warn proceeds 케이스 추가)
- test_prompt_builder 5/5
- test_result_parser 25/25
- test_run_single_symbol_entry_flow 10/10

(2) `run_daily_analysis --region US --date 2026-01-13 --limit 3 --dry-run` 실행 검증:
- screened=962, listed=3 (RS rating DESC 정렬 — ABVX/AFJKU/ALM)
- sync_log 2행 기록 확인 (running + success)

(3) `show_cost_summary --days 1` 실행 검증:
- Today usage: KR 0/50 (remaining 50), US 4/50 (remaining 46)
- By module 표 + Daily totals 표 + sync_log llm_* WARN/ERROR count + Recent events
- NVST v1.1 검증 호출이 `entry_params_6_us` 1건으로 정상 집계

**1.3 게이트 §9.1 진행 상황** (DEV 가능 항목 모두 통과):
- ✅ (6) v1.1 fix 3건 구현·검증 (1.3.0)
- ✅ run_daily_analysis.py 작동 (KR/US 분리, 상한, 캐싱, dry-run, force-recompute)
- ✅ run_analysis_today.ps1 래퍼 스크립트 (DEV 작성, PROD 검증은 Q-003)
- ✅ 일일 호출 상한 hard stop 정확히 작동 (test_daily_call_limit_hard_stop_raises 통과)
- ✅ 캐싱 정확히 작동 (skip_if_exists)
- ✅ 부분 실패 처리 (per-symbol sync_log + 계속)
- ✅ show_cost_summary.py 작동
- ✅ 모니터링 4종 가동 (test_cost_tracker로 path 검증)
- ✅ 통제권 메커니즘 4종: ① Task Scheduler disable (install_task.ps1 주석 명시) ② settings.yaml `modules.{analyze_chart, calculate_entry_params}` 킬 스위치 (run_daily_analysis가 정확히 분기) ③ daily_call_limits.{kr,us}=0 부분 비활성화 (test_check_daily_limit_zero_limit_returns_true) ④ 매매 게이트 부재 (코드상 경로 자체 없음 — Phase 6까지)
- ⏳ Q-003 PROD 적용 (사용자, Q-002 선행 후)
- ⏳ 백필 7거래일 + 자연 운영 1~2거래일 (1.3.9-A/B)
- ⏳ 사용자 정성 평가 (1.3.10~1.3.11)

### 1.3.9-A — 7거래일 백필 (2026-05-07)

**대상 윈도우** (사용자 결정, 가장 최근 7거래일):
- KR: 4/23, 4/24, 4/27, 4/28, 4/29, 4/30, 5/4 (KR은 5/1·5/5 휴장)
- US: 4/24, 4/27, 4/28, 4/29, 4/30, 5/1, 5/4

**실행 방식**: 사용자 결정대로 region·date당 10종목 (RS rating DESC 상위) 차례차례 manual chain. Background bash로 batch chain 직렬 실행. 한 번 중단 후 재개 (claude --resume) 시나리오까지 실증.

**최종 누적 (141행)**:

| Region | Dates | 분류 |
|---|---|---|
| KR | 4/23~5/4 (7일) × 10 = 70 | ignore 70 |
| US | 4/24~5/4 (7일) × 10 + NVST 1 = 71 | ignore 70, **watch 1**, entry 0 |

**Watch 종목** (1.3.9-A 첫 non-ignore 사례):
- ALTO 2026-05-01, confidence 0.75, pattern none — 1.3.10 정성 평가에서 reasoning 검토 가치 있음

**호출 메트릭 (오늘 LLM 호출 누적)**:

| module | calls | errors | error rate | avg dur |
|---|---|---|---|---|
| analysis_5_kr | 75 | 4 | 5.3% | 79.8s |
| analysis_5_us | 82 | 11 | 13.4% | 88.2s |
| entry_params_6_us | 1 | 0 | 0% | 107.9s |
| 합계 | 158 | 15 (9.5%) | (CLI timeout retry 정상 범위) | |

**sync_log llm_* 이벤트**:
- `llm_analysis_kr/us` running/success 마커: 정상
- `llm_daily_call_limit ERROR 1`: KR 50 hit 시점 (시스템 안전장치 정상 작동) → 사용자 합의 후 settings.yaml 200/200 임시 상향, 백필 종료 후 50/50 원복
- `llm_token_spike WARN 141`: 거의 모든 호출이 임계 24K 초과. 정상 prompt가 ~25K로 측정되어 1.3 후속 task #18(임계 50K로 상향)로 식별

**§J/§K/§L/§M 부수 모니터링 결과**:

| 이슈 | 1.3.9-A 결과 |
|---|---|
| §J ETF 잘못 통과 | 백필에서는 추가 발생 없음 (ADR-013 ETF 제외 필터 안정 동작) — 1.3.9-B 자연 운영에서 추가 관찰 |
| §K (5) v2 분류 보수성 | entry 0 + watch 1 (ALTO). 백필 윈도우(froth) 특성상 entry 발생 자연 빈도 낮음. v2가 watch도 산출하므로 ignore-편향 가설 부분 약화. 더 다양한 시장 상태에서 확인 필요 |
| §L (6) v1.1 fix | 1.3.0에서 단위/실LLM 검증 통과. 1.3.9-A에서는 entry 0건이라 (6) 추가 호출 없음 (NVST 외) |
| §M EA 분류 불안정 | NVST B.5.5(entry) → 2026-05-07 (ignore) 사례 외 추가 multi-eval 변동 관찰 안 됨 (백필 윈도우 7일이 좁아 cross-date 표본 작음) |

**1.3 게이트 §9.1 — 본 단계로 통과한 항목**:
- ✅ run_daily_analysis 작동 (KR/US 분리, 상한, 캐싱, dry-run, force-recompute)
- ✅ 부분 실패 처리 (15 errors도 chain 진행)
- ✅ 일일 호출 상한 hard stop 동작 (1회 실증 + 사용자 합의 후 한도 상향 + 종료 후 원복)
- ✅ 모니터링 4종 sync_log path 모두 가동 (running/success/WARN/ERROR + 4 종 marker)
- ✅ 백필 7거래일 50행 이상 누적 (141행 = 목표 2.8배)
- ⏳ 1.3.9-B 자연 운영 1~2거래일 (Q-003 PROD 적용 후)
- ⏳ 1.3.10~11 사용자 정성 평가

### 1.3.9-A 단계 부수 작업

| 작업 | 처리 |
|---|---|
| settings.yaml `daily_call_limits.kr/us` 50→200 임시 상향 (백필 진행용) | 종료 후 50으로 원복 — 본 commit 포함 |
| US daily collector FDR end-boundary off-by-one 버그 발견 (다른 세션) | main에 hotfix `a1ebce3` 적용. 본 phase1 브랜치는 `git merge origin/main`로 병합 — 본 commit `271ff55` 머지 commit |
| token_spike 임계 조정 (24K→50K 등) | task #18로 1.3 후속 처리 예정 |

### 다음 단계

**1.3.9-B 자연 운영 검증 (Q-003 PROD 적용 후)**:
- 다음 자동 트리거 시각(US 16:00 / KR 21:00 KST)에 정상 실행 관찰
- Get-ScheduledTaskInfo LastRunResult=0 확인
- daily_analysis 신규 행 + llm_calls 호출 + sync_log marker 확인
- 1~2거래일 트리거 안정성 검증 후 1.3.10으로 이동

**Phase 1 종료 게이트 §9.1 잔여 항목** (1.3.9-B 후):
- Q-003 PROD 적용 완료
- 백필 + 자연 운영 누적 데이터 검토
- 사용자 정성 평가 ("쓸만하다")
- 헌법 §2.1, §2.2, §2.5 위배 없음 (Auditor 세션)

## 주간 운영 메모

(Phase 1.3 시작 후부터 ADR-012 §3.4 호출 로그 점검 결과를 기록)

---

## 1.3.10 정성 평가 가이드 (2026-05-07)

### 데이터 현황 (DEV DB 기준)

| 구분 | KR | US | 합계 |
|---|---|---|---|
| 1.3.9-A 백필 | 7일 × 10 = 70행 | 7일 × 10 + NVST 1 = 71행 | 141행 |
| 1.3.9-B 자연 운영 | 0행 (PROD 미확인) | 2026-05-06 26행 | 26행 |
| **총합** | **70행** | **97행** | **167행** |

**Classification 분포**:
- KR: ignore 70 (100%)
- US: ignore 96 (99.0%), watch 1 (ALTO 5/1, 1.0%)
- **entry: 0건** (NVST B.5.5는 DB에서 현재 ignore로 덮어쓰여짐 — 1.3.0 재실행 시 분류 변경됨)

**1.3.9-B 자연 운영 특이사항** (2026-05-06 US 26건):
- ETF 오통과: VRTL, SOXL, MVLL, MUU, MULL, AMDG, AMDL, AMUU, KORU, INTW, DLLL, BWET = **12건 (46%)**
- us_symbol_master.symbol_type='STOCK'으로 잘못 등록된 ETF/레버리지 ETF들
- LLM Pre-Check이 conf=1.00으로 즉시 ignore 처리 (safety net 정상 작동)
- ADR-013 upstream 필터 보강 필요 (§J 후속)

---

### §9.2 정성 평가 기준별 분석

#### 기준 1: 분류의 합리성 — entry 10개 표본

**상황**: 현재 DB에 entry 0건. §9.2가 요구하는 "entry 10개 표본" 기준 미달.

**대체 평가 방향**:
- entry: NVST (B.5.5) 1건 — DB에서 ignore로 덮어쓰여졌으나 B.5.5 결과 기록에서 평가 가능
- watch 1건 (ALTO 5/1): reasoning 품질 평가
- ignore 표본: RS 99이지만 ignore된 케이스들의 reasoning 타당성 평가

**사용자 평가 대상 (ignore 중 납득 여부)**:

| 날짜 | 종목 | Conf | 핵심 reasoning | flags |
|---|---|---|---|---|
| 5/6 | AAOI | 0.90 | "Climax run +255% in 10wks. Feb 27: +57% single day to $84.23 on 24.8M vol. 47% above SMA-50." | climax_run, extended_from_ma, wide_and_loose |
| 5/6 | ANTX | 0.90 | "Climax run Mar4-9: $1.06→$6.91 (+552%) on 58M vol. Now -33% from high. No base(4wks). Thin $1.6M/day." | climax_run, extended_from_ma, wide_and_loose, thin_liquidity_us_only |
| 5/6 | ARWR | 0.90 | "4th+ base in 508% Stage 2. Extended 22.6% above SMA-50. Wide-and-loose Mar-Apr (10-15% wkly swings)." | late_stage_base, extended_from_ma, wide_and_loose, volume_contraction_on_advance |
| 4/24 | 064850 | 0.90 | "Climax run 4/7-4/22 (+75%, 2wks). 41% above SMA-50. Too late to enter. Need 8-12wk new base." | climax_run, extended_from_ma |
| 4/24 | 082920 | 0.90 | "Jan-Feb flat base, breakout 3/12. Now +143% in 6wks. 71% above SMA-50. Climax bar 4/13." | climax_run, extended_from_ma, wide_and_loose, volume_contraction_on_advance |
| 5/4 | 124500 | 0.75 | "8-week volatile consolidation. Weekly swings 15-25% wide-and-loose. -18% from recent high. Needs tighter action." | wide_and_loose |
| 5/1 | ALTO | **watch→** | "No base forming—stock at new ATH $5.60. Extended 25.4% above SMA-50. RS 99. Monitor for pullback/base." | extended_from_ma |

**평가 질문**: 위 ignore 케이스들이 "납득 가능"한가? 70% 이상 납득해야 기준 통과.

---

#### 기준 2: watch 분류의 활용성

**현황**: watch 1건 (ALTO 2026-05-01)

**ALTO 분류 이력 (§M 분류 불안정)**:

| 날짜 | 분류 | Conf | 핵심 reasoning |
|---|---|---|---|
| 4/28 | ignore | 0.75 | "3rd base late-stage. Climax gap 3/5. 8-week consolidation wide-and-loose, now tightening. RS 99." |
| 5/1 | **watch** | 0.75 | "No base forming—ATH $5.60. Extended 25.4% above SMA-50. RS 99. Monitor for pullback/base." |
| 5/4 | ignore | 0.80 | "9-week consolidation $4.16-$5.60 wide-and-loose. Extended 25% above SMA-50. 3rd base Stage 2." |
| 5/6 | ignore | 0.90 | "Climax run +54% March 5. Now 23% above SMA-50. Wide-and-loose consolidation. No textbook base." |

**관찰**:
- 5/1 한 번만 watch, 나머지 3일 ignore
- 5/1 watch reasoning("No base forming, Monitor for pullback/base")이 실제로는 ignore와 큰 차이 없음
- 5/6에서 confidence 올라가며(0.75→0.90) ignore 확정됨
- 1~4주 후 entry로 발전할 가능성: 낮음 (5/6에서 "No textbook base" 유지)

**평가 질문**: ALTO 5/1 watch가 "재방문할 가치 있다"고 느껴지는가?

---

#### 기준 3: ignore 분류의 정당성

**reasoning 품질 샘플** (구체적 수치 포함 여부):

**우수 사례** (구체적 수치 + 맥락):
```
[5/6 AAOI] "Climax run: +255% in 10wks (Feb 20 $51.68 → May 1 $183.51). Feb 27: +57% single day
  to $84.23 on 24.8M vol (5× avg). Extended 47% above SMA-50 ($121.47). Wide-and-loose:
  Apr-May weeks show 30-40% intraweek spreads. No proper base. RS 99 irrelevant—entry risk extreme."

[4/24 082920] "Jan-Feb flat base, 10wks, pivot 23,100. Breakout 3/12 @23,500. Now +143% in 6wks.
  Week 4/13: climax (high 58,200, 6.4M vol, largest spread). 71% above SMA-50.
  Weekly swings 30-40%. Volume declining on recent advance. RS 99 elite but severely extended."

[5/6 ANTX] "Climax run Mar 4-9: $1.06→$6.91 (+552%) on 58M volume. Now -33% from high at $4.65,
  wide-and-loose action. No base formed (4wks from low, need 7+). Extended 28% above SMA-50.
  Thin liquidity $1.6M/day."
```

**단순 반복 사례** (ETF 12건):
```
"ETF — Minervini/O'Neil methodology targets individual leadership stocks.
 Recommend upstream screener filter."
```

**애매한 사례** (0.75 저신뢰):
```
[5/4 124500] "8-week volatile consolidation after climax to 75,500 (Mar-13).
  Weekly swings 15-25% = wide-and-loose, not tradeable. RS 99 elite
  but no clean base structure yet. 13.7% above SMA-50. -18% from recent high.
  Needs tighter action."
```
→ 0.75 이유: "아직 base 형성 중이라 결론을 확신하기 어렵다"는 뉘앙스 → 합리적

**평가 질문**: reasoning이 "구체적 근거" 수준인가? 특히 KR/US non-ETF의 reasoning이 단순 반복이 아닌지 확인.

---

#### 기준 4: confidence의 일관성

**분포 요약**:

| Conf | KR (70건) | US non-ETF (85건) | US ETF (12건) |
|---|---|---|---|
| 1.00 | 0건 | 0건 | 12건 (100%) |
| 0.95 | 20건 (29%) | 18건 (21%) | - |
| 0.90 | 41건 (59%) | 35건 (41%) | - |
| 0.85 | 7건 (10%) | 15건 (18%) | - |
| 0.80 | 1건 (1%) | 9건 (11%) | - |
| 0.75 | 1건 (1%) | 5건 (6%) | - |

**패턴 관찰**:
- `conf=1.00` = ETF 전용 (Pre-Check 즉시 종료)
- `conf=0.95` = 명확한 클라이맥스 런 (수치가 극단적, 의심 여지 없음)
- `conf=0.90` = 대다수 (일반적 froth/climax 케이스)
- `conf=0.85-0.80` = 복잡한 케이스 (late-stage인데 방향 불확실, 혹은 base 진행 중)
- `conf=0.75` = 가장 모호한 케이스 (ALTO 5/1 watch 포함)

**평가 질문**: 0.90 종목과 0.75 종목의 차이가 직관과 맞는가? 0.95가 0.90보다 "더 확실한 ignore"로 느껴지는가?

---

#### 기준 5: entry_params의 실행 가능성

**현황**: 1.3.9-A/B에서 entry 0건 → 신규 entry_params 없음

**가용 참조**: NVST (B.5.5, 2026-01-13) — Evaluator 2회 검토 완료:
- pivot=$22.67 (handle high), trigger=$22.69 (pivot×1.001)
- stop_loss_pct_from_pivot=-5.3%, stop_loss_pct_from_current_price=-7.6%
- known_warnings: stop_distance_from_current_price_exceeds_book_limit, breakout_volume_below_requirement
- suggested_weight_pct=4.9% (7% × 0.7 low_volume_breakout discount)
- 2차 Evaluator (운영자 시각): "NVST는 약한 setup이나 (6) 산식 자체는 합리적"

**평가 질문**: NVST entry_params를 실제 거래 결정에 사용할 수 있을 정도로 구체적이고 합리적인가?

---

### 종합 평가 체크리스트 (사용자 판단)

| § | 기준 | 목표 | 현황 | 판단 필요 사항 |
|---|---|---|---|---|
| 9.2 기준1 | 분류의 합리성 | entry 10개 70%+ 납득 | **entry 0건** (미달) | 위 ignore 7건 + NVST 납득 여부 |
| 9.2 기준2 | watch 활용성 | watch 50%+ 재방문 가치 | watch 1건 (ALTO) | ALTO 5/1 watch 합리성 |
| 9.2 기준3 | ignore 정당성 | reasoning 구체적 | 우수 ~80% / ETF 반복 12건 | 전반적 reasoning 품질 충분한지 |
| 9.2 기준4 | confidence 일관성 | 직관 정렬 | 0.75-0.95 스펙트럼 합리적 | 고/저신뢰 분포 납득 여부 |
| 9.2 기준5 | entry_params 실행 가능성 | 거래 직접 사용 가능 | NVST 1건 (기검토) | B.5.5 NVST 기준으로 판단 |

### 1.3 게이트 §9.1 상태

| 항목 | 상태 |
|---|---|
| run_daily_analysis.py 작동 | ✅ |
| run_analysis_today.ps1 | ✅ (DEV 작성) |
| 일일 상한 hard stop | ✅ |
| 캐싱 작동 | ✅ |
| 부분 실패 처리 | ✅ |
| show_cost_summary.py | ✅ |
| Q-003 PROD 적용 | ⏳ 사용자 확인 필요 |
| 7거래일 ≥ 50행 | ✅ 167행 |
| 사용자 정성 평가 "쓸만하다" | **⏳ 본 단계** |
| 헌법 §2.1/§2.2/§2.5 | ✅ (경로 없음 + 분리 + llm_calls 기록) |

---

*1.3.10 가이드 작성: Builder 2026-05-07*

---

### 1.3.10 정성 평가 결과 (2026-05-08)

#### (a) 167행 데이터 분석 결과 요약

| 구분 | KR | US | 합계 |
|---|---|---|---|
| 1.3.9-A 백필 | 70행 (7거래일 × 10) | 71행 (7거래일 × 10 + NVST 1) | 141행 |
| 1.3.9-B 자연 운영 | 0행 | 26행 (2026-05-06) | 26행 |
| **총계** | **70행** | **97행** | **167행** |

**Classification 분포**:
- KR: ignore 70 (100%)
- US: ignore 96 (99.0%), watch 1 (ALTO 5/1, 1.0%), entry 0
- **합계**: ignore 166 / watch 1 / **entry 0**

**호출 메트릭** (1.3.9-A 백필 세션 누적):
- analysis_5_kr: 75회 (에러 4, 5.3%), avg dur 79.8s
- analysis_5_us: 82회 (에러 11, 13.4%), avg dur 88.2s
- entry_params_6_us: 1회 (NVST 검증), avg dur 107.9s
- 합계 158회, 에러율 9.5% (CLI timeout retry 정상 범위)

#### (b) 사용자 자체 판단

**§9.2 5종 기준 모두 충족** 판단:

| 기준 | 목표 | 판단 |
|---|---|---|
| 분류의 합리성 | entry 10개 70%+ | 운용적 완화 (entry 0건 — 아래 (e) 참조) |
| watch 활용성 | 50%+ 재방문 가치 | ALTO 5/1 1건: 판단 유보 (5일 후 ignore 전환) |
| ignore 정당성 | reasoning 구체적 | ✅ non-ETF ~80% 우수 사례 확인 |
| confidence 일관성 | 직관 정렬 | ✅ 저신뢰=복잡 케이스, 고신뢰=명확 케이스 |
| entry_params | 거래 직접 사용 가능 | ✅ NVST (B.5.5) Evaluator 2회 검토 완료 |

**종합 판단**: "**쓸만한 수준**" — Phase 1 종료 적정

#### (c) Evaluator 1차 평가 요약 (Phase 1.3.10 정성 평가 보고)

**대상 표본**: 7건 (ignore 6건 + watch 1건)

**결론**:
- **7건 표본 100% 합리적** (목표 70% 크게 상회)
- **"쓸만한 수준" Yes**, **"Phase 1 종료 적정"** 명시

**핵심 강점 5종**:
1. ignore reasoning 품질 — 구체적 수치 포함 (%, vol, weeks) + 미너비니 원칙 근거 명시
2. confidence 캘리브레이션 — 극단적 케이스(0.95) / 일반 케이스(0.90) / 방향 불확실(0.75) 합리적 구분
3. ETF Pre-Check — conf=1.00 즉시 처리로 비용 낭비 최소화, safety net 정상 작동
4. risk_flag taxonomy 일관 적용 — 12종 whitelist 준수, outlier 0건
5. stage 분석 정확성 — late-stage vs early-stage 구분, climax run 시점 특정 정확

**약점 6종** (Phase 2 또는 별도 sprint에서 처리 권고):
1. entry-side 검증 부재 — 0건이라 실질적 entry 정확도 미검증
2. watch reasoning 모호성 — ALTO 5/1 "Monitor for pullback/base" 수준이 ignore와 경계 불명확
3. §M 분류 불안정 — 같은 종목 5일 간격 ignore↔watch 전환 (ALTO 4/28 ignore → 5/1 watch → 이후 ignore)
4. boundary 결정성 부족 — "얼마나 확장되어야 extended_from_ma인가" 등 정량 경계 미명시
5. ETF upstream 필터 미비 — ADR-013 적용 후에도 12건 오통과, us_symbol_master 정확도 문제
6. VCP 정량화 미비 — VCP 패턴 인식 기준이 정성적, 정량 기준 없음

#### (d) Evaluator 2차 평가 요약 (보강 자료)

**"advance ≤ 3" 의미**:
- late_stage_base flag 기준: base 횟수 3 이하 = late-stage 아님
- 임상적 의미: 3rd base 이하이면 재진입 후보 가능성 존재
- Phase 2 활용: watch 종목 중 advance ≤ 3인 경우를 "primary watch" 카테고리로 분리 가능

**known_warnings severity 사전 매핑**:
- 현재: known_warnings는 closed set (12종 Literal enum) — severity 정보 없음
- Evaluator 권고: severity 사전 mapping 가능 (closed set이라 항목별 high/medium/low 미리 정의 가능)
  - high: `stop_distance_from_current_price_exceeds_book_limit`, `breakout_volume_below_requirement`
  - medium: 그 외 position-sizing 관련
  - low: 정보성 flag
- Phase 2 보강 시 참고 자료로 보존

#### (e) §9.2 기준 1 운용적 완화 명시

- **원래 기준**: entry 10개 표본 → 70%+ 납득
- **실제 데이터**: entry 0건 (시장 환경 제약 — B.5.5 통계상 0.25% 자연 발생률과 정합, 167행에서 0~1건 예상 범위)
- **대체 평가**: ignore 6건 + watch 1건 (ALTO) + NVST entry_params (B.5.5) 1건 → 8건 구성
  - Evaluator가 7건 표본 100% 합리적 판정 → 시스템 작동 객관 검증
- **결론**: §9.2 기준 1은 정식 충족 불가하나 운용적으로 완화 처리. **§9.2 본문은 변경하지 않음** (Architect 권한 영역)
- **후속**: Phase 2에서 자연 누적 데이터로 entry-side 정식 평가 sprint 별도 진행 예정

#### (f) ETF 12건 이슈

- 5/6 US 자연 운영 데이터에서 us_symbol_master.symbol_type='STOCK'으로 잘못 등록된 12건 확인
- VRTL, SOXL, MVLL, MUU, MULL, AMDG, AMDL, AMUU, KORU, INTW, DLLL, BWET
- LLM Pre-Check이 안전망 정상 작동 → 즉각적 위험 없음
- **Q-004 등록** (별도 처리): ADR-013 정책 확장 + us_symbol_master 정정

#### (g) Phase 2 인계 항목

| 항목 | 출처 | 우선순위 |
|---|---|---|
| boundary 결정성 — climax_run/extended_from_ma 정량 기준 추가 | Evaluator 강점 역방향 | 보통 |
| known_warnings severity 매핑 — closed set 기반 사전 정의 | Evaluator 2차 | 낮음 |
| revisit_condition 필드 — watch 종목에 재방문 조건 명시 | Evaluator 권고 | 보통 |
| earnings warning — 실적 임박 시 자동 flag | Evaluator 권고 | 보통 |
| VCP 정량화 — VCP 패턴 인식 정량 기준 명확화 | Evaluator 권고 | 낮음 |
| ADR-013 정책 확장 — us_symbol_master 분류 범위 (preferred stock, CEF 등) | §J 후속 | 보통 |
| Q-004 us_symbol_master ETF 정정 12건 | 5/6 운영 발견 | 보통 |

*1.3.10 결과 기록: Builder 2026-05-08*