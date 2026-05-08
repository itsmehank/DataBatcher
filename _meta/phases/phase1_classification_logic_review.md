# Phase 1 분류 로직 리뷰 — analyze_chart (5) entry/watch/ignore

> 작성: Builder (Claude Code CLI), 2026-05-08  
> 목적: Architect가 Phase 2 brief 작성 시 분류 체계 개편 여부를 판단할 수 있도록,  
> 현재 v2 프롬프트의 분류 로직을 있는 그대로 정리한다.  
> 코드·거버넌스 변경 없음. 조사 + 정리 보고서.

---

## 목차

- §1. 현재 분류 3종의 정의와 경계
- §2. 분류 결정 절차 (LLM 사고 흐름)
- §3. risk_flags 12종 영향도
- §4. confidence 의미
- §5. 실제 분류 사례
- §6. 부록: 프롬프트 v2 핵심 발췌

---

## §1. 현재 분류 3종의 정의와 경계

### 1.1 세 분류의 정의

프롬프트 v2 "## Definitions" 섹션에서 명시적으로 정의:

| 분류 | 프롬프트 영문 정의 | 한국어 의역 |
|---|---|---|
| **entry** | "Stock is at or near a proper buy point with a clean base. A swing trade entry is appropriate now or imminently (within ~5 trading days)." | 깨끗한 베이스(base) 구조를 갖추고, 현재 또는 약 5거래일 이내에 적절한 매수 포인트(pivot)에 위치한 종목. 즉시 스윙 트레이드 진입이 적합하다. |
| **watch** | "Stock passes the trend template but is not at a buy point. Either the base is forming, or it has extended too far from a recent breakout. Re-evaluation in 1–4 weeks is appropriate." | 트렌드 템플릿 통과 종목이지만 아직 매수 포인트가 아닌 상태. 베이스 형성 중이거나 최근 돌파 후 과도하게 상승한 경우. 1~4주 후 재평가가 적절하다. |
| **ignore** | "Despite passing the trend template, this stock is not a Minervini-quality setup. Examples: thin or wide-and-loose base, climax run, late-stage advance, no clean base, post-reverse-split speculation." | 트렌드 템플릿을 통과했음에도 불구하고 미너비니 기준의 셋업 품질을 갖추지 못한 종목. 대표 사유: 너무 좁거나 넓고 거친 베이스, 클라이맥스 런, 레이트 스테이지, 베이스 없음, 역분할 후 투기적 상태. |

### 1.2 경계 조건과 모호한 케이스

**entry vs watch 경계**:
- "at or near a proper buy point" vs "not at a buy point"
- 핵심 구분자: 현재 또는 5거래일 이내에 pivot 돌파가 임박했는가
- **모호 케이스**: pivot까지 3~8% 남은 경우, 베이스가 거의 완성됐지만 아직 handle이 형성 중인 경우
- 프롬프트에 "~5 trading days" 외에 정량 경계선 없음 → **LLM 판단에 위임**

**watch vs ignore 경계**:
- watch: "base is forming" (베이스 진행 중이므로 '재방문 가치' 있음)
- ignore: "no clean base" (재방문해도 의미 없는 구조적 문제)
- **모호 케이스**: wide-and-loose하지만 최근 수주 사이 점차 타이트해지는 종목 → v2는 대부분 watch보다 ignore로 처리하는 경향 (ALTO 4/28→5/1→5/4 이력 참조)

**entry vs ignore 경계**:
- 직접 전환은 드물지만 가능 (예: pivot 직전인데 climax_run 기준 충족 시)
- 프롬프트 §7에서 명시: "multiple high-impact flags (climax_run + late_stage_base + extended_from_ma) → classification must be ignore"

### 1.3 프롬프트에 명시된 기준 vs LLM 판단 위임 부분

**명시적 기준 (정량)**:
- `climax_run`: 1~3주 내 ≥25% 급등 + 해당 기간 최대 주간 스프레드 + 최대 거래량
- `extended_from_ma`: SMA-50 대비 >15% 이격
- `low_volume_breakout`: 돌파 거래량 < 20일 평균의 1.5배
- `flat_base`: 5주 이상 + 고점 대비 <15% 조정 + prior uptrend ≥20%
- `cup_with_handle`: 7~65주, 깊이 <33%, 핸들은 컵 상단 절반에서 형성
- `vcp`: 수축 ≥3회, 각 수축마다 거래량 감소
- `double_bottom`: 두 저점, 두 번째가 첫 번째 약간 하회, 7주 이상

**LLM 판단에 위임된 부분**:
- Stage 2 vs Stage 3 경계 판정 (어느 시점이 distribution인지)
- "late-stage base" 카운팅 (몇 번째 베이스인지 세는 방식)
- watch와 ignore 사이의 최종 결정 (베이스 형성 중인지 vs 구조적으로 불가인지)
- entry 시 "5거래일 이내" 매수 가능 여부 판단
- confidence 값 설정 (프롬프트는 규칙 제시, 최종 값은 LLM)

---

## §2. 분류 결정 절차 (LLM 사고 흐름)

프롬프트 v2 "## Analysis Procedure"에 6단계로 명시. 아래는 각 단계와 분류 결정에의 영향을 정리.

### Step 0: Pre-Check — ETF / Fund Vehicle (즉시 종료)

**위치**: Analysis Procedure 진입 전 별도 섹션.

```
market == "ETF" 또는 fund vehicle 판단
  → 즉시 {"classification": "ignore", "confidence": 1.0, "risk_flags": ["etf_methodology_mismatch"]}
  → 이하 6단계 모두 생략
```

**영향**: ETF는 어떤 분석 없이 confidence 1.00 ignore. B.5.5에서 symbol_type='STOCK'으로 잘못 등록된 레버리지 ETF들도 LLM의 ticker/sector 인식으로 여기서 걸러진다.

---

### Step 1: Corporate Action Check (역분할 확인)

**데이터 소스**: `price_data_notes.known_corporate_actions`

**분류 영향**:
- 최근 ~12주 내 역분할 확인 → `reverse_split_distortion` 플래그 의무 부여
- 역분할 후 다중주 베이스가 없으면 → ignore 강하게 지시
- 실질적으로: "일단 ignore" 추정값을 설정하고 예외 조건 충족 시 완화

**한계**: AAOI 케이스에서 오래된/낮은 ratio 역분할이 누락되는 경우 있음 (이슈 §H.1).

---

### Step 2: Trend Confirmation (트렌드 확인)

**데이터**: `conditions_met` (미너비니 8조건 불리언)

**분류 영향**:
- 이 단계의 모든 종목은 이미 8조건 통과 → 걸러지는 종목 없음
- 프롬프트 지시: "Check whether each condition passed **comfortably or marginally**"
  → 마지막 분류 최종 synthesis (Step 7)에서 marginal 통과 여부를 입력으로 사용
  → 특히 `rs_rating_above_70` 마진 체크 → 70~75 범위면 entry 결정에 부정적

**중요**: `high_rs_rating`, `price_above_MA` 같은 양성 신호를 risk_flags에 넣는 것은 명시적으로 금지 (프롬프트 §5 Three inviolable rules #1).

---

### Step 3: Stage Analysis (스테이지 분석)

**목적**: 현재 종목이 Stage 1(저점 베이스), Stage 2(상승), Stage 3(고점 분배), Stage 4(하락) 중 어디인지

**분류 영향 — 핵심 gate**:
- **Stage 2 + 적절한 베이스만 entry 가능**
- Stage 1, 3, 4는 즉시 ignore 방향
- Stage 2이더라도 진행이 얼마나 됐는지 → late_stage_base 판단 (몇 번째 베이스?)

**LLM 판단 위임**: Stage 경계는 명시적 기준 없음 → LLM이 이동평균 slope, 거래량 패턴, 가격 패턴으로 추론.

---

### Step 4: Base Pattern (베이스 패턴 식별)

**허용된 5개 패턴**: `flat_base`, `cup_with_handle`, `vcp`, `double_bottom`, `none`

| 패턴 | 핵심 조건 | 분류 영향 |
|---|---|---|
| `flat_base` | 5주+, 조정 <15%, prior uptrend ≥20% | entry 또는 watch (pivot 위치에 따라) |
| `cup_with_handle` | U자형(V자 불가), 7~65주, 깊이 <33%, 핸들은 컵 상단 절반 | entry 또는 watch |
| `vcp` | ≥3회 변동성 수축, 거래량 각 수축마다 감소 | entry 또는 watch |
| `double_bottom` | W자형, 두 번째 저점이 첫 번째보다 약간 낮음, 7주+ | entry 또는 watch |
| `none` | 위 패턴 없음; climax run, 초기 스테이지, wide-and-loose | **ignore 강하게 지시** |

**Discipline rule**: "구조적 요소가 불분명하거나 모호하면 억지로 패턴 명칭을 붙이지 말고 `none`을 사용하라." → 현재 데이터에서 `none`이 압도적 다수 (US 97건 중 95건, KR 70건 전체).

**Step 6과의 연계**: 패턴을 식별했으면 pivot_price를 `max(weekly.high of base period) + $0.10`으로 계산하고, 데이터에서 실제 돌파일 확인 의무.

---

### Step 5: Risk Flags 부여

**12종 taxonomy** (§3에서 상세 설명). 이 단계가 최종 분류 결정의 핵심 input.

**Consistency rule** (프롬프트 §5 #2):
> reasoning에 "climax run", "wide-and-loose", "extended from MA"라는 표현이 나오면 해당 flag가 반드시 risk_flags에 포함돼야 한다.

즉, reasoning과 risk_flags는 일관성 강제 — 검증 가능한 체크.

---

### Step 6: Pivot & Breakout Accuracy (피봇·돌파 정확도)

**조건**: Step 4에서 패턴을 식별한 경우에만 실행.

- `pivot_price` = 식별된 베이스 기간의 `max(weekly.high) + $0.10` (Minervini standard add-on)
- `breakout_date` = 일봉 데이터에서 `close > pivot_price`인 **첫 번째 거래일**
- **만약 데이터 내에 돌파일이 없으면**: 돌파 주장 금지. confidence를 0.2 낮추고 이유를 reasoning에 명기.

이 단계는 entry/watch 경계 결정에 직접 영향:
- 돌파 완료 + 아직 buy zone(pivot에서 +5% 이내): entry
- 돌파 전 (pivot 미도달): watch 가능
- 돌파했지만 크게 이탈: ignore (`extended_from_ma` 등)

---

### Step 7: Classification & Confidence (최종 분류 + confidence 설정)

**합성 규칙** (프롬프트 §7):

```
entry  ← 깨끗한 베이스 + pivot에 위치 + Stage 2 + 거래량 확인
watch  ← 트렌드 템플릿 OK + 베이스 형성 중 또는 약간 이격 + 즉시 진입 포인트 없음
ignore ← 클라이맥스 런, wide-and-loose, 베이스 없음, 레이트 스테이지, 역분할, ETF
```

**Confidence 보정 규칙** (프롬프트에 명시):
- 내부 분석 100단어 미만 또는 책 기준 누락: max 0.60
- 패턴 명칭은 있지만 데이터에 구조 없음: max 0.50
- `climax_run` + `late_stage_base` + `extended_from_ma` 동시: confidence 심각성 반영 + 반드시 ignore
- 고신뢰(≥0.85): 명확한 베이스 구조 + 거래량 근거 + 명시적 pivot 참조 + stage 명확

**if confidence < 0.50**: 분류는 강제로 watch + 낮은 confidence + reasoning에 이유 기술.

---

## §3. risk_flags 12종 영향도

아래는 `apps/llm-analysis/models/analysis_result.py`의 `VALID_RISK_FLAGS` + 프롬프트 v2 §5 기준으로 정리.

| Flag | 발동 조건 | 정량 기준? | 분류 영향 | 관찰된 빈도 |
|---|---|---|---|---|
| `climax_run` | 1~3주 내 ≥25% 급등 + 해당 기간 최대 주간 스프레드 + 최대 거래량 | 부분 정량(25%, 1~3주) | **ignore 강력 유도** — 단독으로도 충분히 ignore | 매우 높음 |
| `late_stage_base` | Stage 2 진행 중 3번째 이상 베이스 | 정성 (몇 번째인지 카운팅) | ignore 유도. climax_run과 공존 시 확정 | 높음 |
| `extended_from_ma` | SMA-50 대비 >15% 이격 | **정량** (15%) | ignore 강력 유도 (단독도 가능) | 매우 높음 |
| `faulty_pivot` | 베이스 pivot이 과거 저항선에서 2회 이상 실패한 지점 | 정성 | entry → watch 또는 ignore 강등 | 낮음 (미관찰) |
| `low_volume_breakout` | 돌파 거래량 < 20일 평균의 1.5배 | **정량** (1.5배) | entry는 허용하되 confidence 하락 + (6)에서 비중 감소 | NVST 1건 관찰 |
| `narrow_base` | 베이스 기간 7주 미만 | **정량** (7주) | watch 또는 ignore | 간헐 |
| `wide_and_loose` | 베이스 내 주간 가격 스윙 >10~15% — 거칠고 예측 어려운 구조 | 부분 정량(10~15%) | ignore 유도. 단독으로도 충분히 ignore | **압도적으로 많음** |
| `thin_liquidity_us_only` | US 개별주 한정: 일평균 달러 거래량 (volume_ma20 × 현재가) < $5M | **정량** ($5M). KR 미적용 | ignore 유도 (단독도 충분) | US에서 간헐 |
| `prior_uptrend_insufficient` | 이전 베이스 이후 현 consolidation까지 상승폭 20% 미만 | **정량** (20%) | watch 또는 ignore | 낮음 |
| `volume_contraction_on_advance` | 상승 구간에서 거래량 감소 | 정성 | entry → watch 강등, 또는 confidence 하락 | 간헐 |
| `reverse_split_distortion` | 최근 ~12주 내 역분할 확인 | 부분 정량(12주) | ignore 강력 유도 — 데이터 신뢰성 자체가 훼손 | 낮음 |
| `etf_methodology_mismatch` | ETF 또는 fund vehicle — Pre-Check에서 즉시 트리거 | 정성 | **ignore 즉시 확정** (confidence=1.00, 분석 중단) | 1.3.9-B에서 다수 |

### 플래그 조합과 분류 영향

| 조합 | 전형적 결과 |
|---|---|
| `climax_run` 단독 | ignore (confidence 0.90~0.95) |
| `climax_run` + `late_stage_base` + `extended_from_ma` | ignore 확정 (프롬프트 명시) |
| `wide_and_loose` 단독 | ignore (confidence 0.85~0.90) |
| `extended_from_ma` 단독 | ignore 또는 watch (degree에 따라) — ALTO 5/1이 extended_from_ma 단독 → watch |
| `low_volume_breakout` 단독 | entry 허용 + confidence 0.70~0.80 + (6) 비중 감소 |
| `late_stage_base` + `wide_and_loose` | ignore (confidence 0.80~0.90) |
| 빈 배열 `[]` | entry 또는 고신뢰 watch |
| `etf_methodology_mismatch` | ignore (confidence 1.00, 즉시 종료) |
| `reverse_split_distortion` + `wide_and_loose` | ignore (confidence 0.75~0.85) |

**주목**: `extended_from_ma` 단독은 ignore가 아닌 watch도 가능 — ALTO 5/1 사례에서 "Extended 25.4% above SMA-50"임에도 watch 분류됨. 이는 "베이스 형성 중이므로 재방문 가치"로 해석된 결과.

---

## §4. confidence 의미

### 4.1 프롬프트 기반 보정 규칙 (명시적)

```
< 0.50 → 강제 watch + 이유 명기
≥ 0.85 → 반드시: 명확한 베이스 + 거래량 근거 + 명시적 pivot + stage 명확
패턴 명시 but 데이터에 구조 없음 → max 0.50
100단어 미만 내부 분석 → max 0.60
climax_run + late_stage_base + extended_from_ma → severity 반영
```

### 4.2 실제 분포 패턴 (1.3.9-A/B 167건 기준)

| Confidence | KR (70건) | US non-ETF (85건) | US ETF (12건) | 의미 |
|---|---|---|---|---|
| **1.00** | 0건 | 0건 | 12건 (100%) | ETF Pre-Check 즉시 종료 전용 |
| **0.95** | 20건 (29%) | 18건 (21%) | — | 명확한 클라이맥스 런 (수치 극단적, 의심 여지 없음) |
| **0.90** | 41건 (59%) | 35건 (41%) | — | 대다수 — 일반적 froth/climax, wide-and-loose |
| **0.85** | 7건 (10%) | 15건 (18%) | — | 복잡한 케이스 (late-stage이지만 방향 불확실, base 진행 중) |
| **0.80** | 1건 (1%) | 9건 (11%) | — | 구조 복잡 + 일부 불확실성 |
| **0.75** | 1건 (1%) | 5건 (6%) | — | 가장 모호한 케이스 — watch 포함, 경계성 ignore |
| < 0.75 | 0건 | 0건 | — | 미관찰 (entry 없어서 0.50~0.70 데이터 없음) |

### 4.3 confidence와 분류의 관계

**현재 데이터에서**:
- ignore가 대다수이므로 confidence는 사실상 "ignore 확신도" 측정값
- 0.90~0.95: "명확히 ignore — 수치 하나만 봐도 알 수 있는 케이스"
- 0.85: "ignore인 건 맞는데 방향성 판단이 약간 복잡함"
- 0.75: "ignore가 맞을 것 같지만 base 형성 가능성 있어 불확실"

**entry 케이스(NVST)**에서:
- confidence 0.75 — low_volume_breakout 플래그 + 여러 약점 때문에 낮음
- 프롬프트 기준으로 entry confidence ≥ 0.85는 매우 깨끗한 셋업에만 가능

### 4.4 주의사항

B.5.5 분포에서 0.90이 압도적으로 많은 이유: v2가 froth 시장에서 "명확히 ignore"인 케이스를 처리할 때 0.90을 기본값처럼 사용하는 경향. 이 값이 실제로 0.90인지 0.85여야 하는지는 reasoning의 구체성으로 구분해야 하며, 자동화된 검증은 어렵다.

---

## §5. 실제 분류 사례

### 5.1 entry 사례

**NVST — 2026-01-13 (US, B.5.5 표본)**

현재 DB에서는 1.3.0 재실행으로 ignore로 덮여 있음. B.5.5 진행 기록 기준.

| 항목 | 값 |
|---|---|
| classification | **entry** |
| confidence | 0.75 |
| pattern | cup_with_handle |
| risk_flags | ["low_volume_breakout"] |
| reasoning | "19w cup-with-handle, pivot $22.77 (base high $22.67 + $0.10). Breakout 2026-01-06 at $23.21. Current $23.23, +2% above pivot (in buy zone). RS 81, MAs aligned. Breakout volume 1.02x avg (marginal)." |

**entry_params 요약 (v1.1, 1.3.0 적용 기준)**:
- pivot_price: $22.67, trigger: $22.69
- stop_loss_pct_from_pivot: -5.3%, stop_loss_pct_from_current_price: -7.6%
- suggested_weight_pct: 4.9% (7% × 0.7, low_volume_breakout 페널티)
- known_warnings: [stop_distance_from_current_price_exceeds_book_limit, breakout_volume_below_requirement]

**왜 entry로 분류됐는가**:
- 19주 cup_with_handle 패턴 → textbook 기준 충족
- 돌파 확인 (1월 6일 close $23.21 > pivot $22.67)
- 분석 시점에 buy zone (+2%) 내
- risk_flags가 low_volume_breakout 1개뿐 → 진입 차단 아님

**왜 confidence 0.75인가**:
- 거래량 1.02× (1.5× 기준 크게 미달) → 낮은 확신
- RS 81 (90+ preferred 아님)
- Evaluator 2차 평가: "약한 setup — 4가지 약점" (volume, RS, lone signal, catalyst)

---

### 5.2 watch 사례

**ALTO — 2026-05-01 (US, 실제 DB)**

| 항목 | 값 |
|---|---|
| classification | **watch** |
| confidence | 0.75 |
| pattern | none |
| risk_flags | ["extended_from_ma"] |
| reasoning | "No base forming—stock at new ATH $5.60, currently $5.43. Extended 25.4% above 50-day MA. RS 99, trend template pristine. 2nd advance from March $2.28 low. Monitor for pullback/base." |

**왜 watch로 분류됐는가**:
- 트렌드 템플릿 완벽 통과 (RS 99, MA stack pristine)
- 베이스가 없지만 "forming 가능성" 인정 → 재방문 가치
- extended_from_ma 단독 → 진입 불가, 但 ignore까지는 아님

**왜 confidence 0.75인가**:
- 베이스 없는 상태라 구조 판단이 불확실
- 4일에 걸친 ALTO 이력에서 분류 불안정 (ignore → watch → ignore → ignore)
  → v2의 watch 판단이 flaky한 케이스 대표 사례

**ALTO 이력 (분류 불안정 §M)**:

| 날짜 | 분류 | Conf | 핵심 요인 |
|---|---|---|---|
| 4/28 | ignore | 0.75 | "3rd base late-stage, climax gap 3/5, wide-and-loose" |
| 5/1 | **watch** | 0.75 | "ATH, extended, monitor for pullback" |
| 5/4 | ignore | 0.80 | "9wk consolidation wide-and-loose, 3rd base" |
| 5/6 | ignore | 0.90 | "Climax run +54% Mar5, 23% above SMA-50, no textbook base" |

**CAPR — 2026-05-06 (US, 실제 DB)**

| 항목 | 값 |
|---|---|
| classification | **watch** |
| confidence | 0.70 |
| pattern | none |
| risk_flags | ["wide_and_loose"] |
| reasoning | "RS 99. Post-December spike, 20-week consolidation $29-$36. Wide-and-loose: weekly swings >10-15% (Mar 9: $28.98-$36.49). No clean base structure. Current $34.38 below potential pivot $35.37. Monitor for tightening pattern." |

---

### 5.3 ignore 사례

**클라이맥스 런 + 레이트 스테이지 복합 (KR 010170)**

| 항목 | 값 (5/4 기준) |
|---|---|
| classification | ignore |
| confidence | 0.95 |
| pattern | none |
| risk_flags | ["climax_run", "late_stage_base", "extended_from_ma", "wide_and_loose"] |
| reasoning | "Parabolic climax: +435% in 8wks to 22K peak (Apr 14), then -32% drop. Late-stage (3rd+ base). 70% above SMA-50. Wide-and-loose: weekly swings >20%, one 100%+ intraweek range. No proper base. Speculative blow-off." |

**ETF Pre-Check (US AMDG 등)**

| 항목 | 값 |
|---|---|
| classification | ignore |
| confidence | 1.00 |
| pattern | none |
| risk_flags | ["etf_methodology_mismatch"] |
| reasoning | "ETF — Minervini/O'Neil methodology targets individual leadership stocks. Recommend upstream screener filter." |

**역분할 + wide-and-loose (US PRAX)**

| 항목 | 값 |
|---|---|
| classification | ignore |
| confidence | 0.75 |
| pattern | none |
| risk_flags | ["reverse_split_distortion", "wide_and_loose"] |
| reasoning | "Oct'25 reverse split distorts metrics. Current 10-wk consolidation (23.6% depth) is wide-and-loose: weekly ranges 10-24%. RS 99 confirms trend strength but base structure untradeable per Minervini. 5% from 356 high." |

**레이트 스테이지 (US XWIN — 유일한 flat_base ignore)**

| 항목 | 값 |
|---|---|
| classification | ignore |
| confidence | 0.78 |
| pattern | flat_base |
| risk_flags | ["late_stage_base", "extended_from_ma"] |
| reasoning | "5th base in Stage 2 advance. Dec-Mar flat base (13w, 10.7% depth), pivot $6.43, breakout Mar 19 on 1.78× vol. Now $8.10 (+26% from pivot), 15.8% above SMA-50, at new highs. RS 99 strong but late-stage risk dominates." |

**왜 이렇게 분류됐는가**: pattern=flat_base임에도 ignore — 패턴 구조는 있지만 5번째 베이스(late-stage)라 실패 확률이 지배적.

---

### 5.4 사례 요약 표

| 종목/날짜 | 분류 | Conf | Pattern | 주요 Flags | 핵심 거부/승인 이유 |
|---|---|---|---|---|---|
| NVST 1/13 | entry | 0.75 | cup_with_handle | low_volume_breakout | 돌파 확인 + buy zone 내 + 플래그 1개 |
| ALTO 5/1 | watch | 0.75 | none | extended_from_ma | RS99 완벽하지만 베이스 없음 + 재방문 가치 |
| CAPR 5/6 | watch | 0.70 | none | wide_and_loose | 수렴 추세 + pivot 근접 → 재방문 |
| 010170 5/4 | ignore | 0.95 | none | climax_run + 3개 | 8주 +435% 이후 -32% 급락 |
| AAOI 5/6 | ignore | 0.90 | none | climax_run + extended_from_ma + wide_and_loose | 10주 +255% 극단적 클라이맥스 |
| PRAX 5/6 | ignore | 0.75 | none | reverse_split_distortion + wide_and_loose | 역분할로 데이터 신뢰 불가 |
| XWIN 5/6 | ignore | 0.78 | flat_base | late_stage_base + extended_from_ma | 5번째 베이스 — 레이트 스테이지 우선 |
| AMDG 5/6 | ignore | 1.00 | none | etf_methodology_mismatch | ETF Pre-Check 즉시 종료 |

---

## §6. 부록: 프롬프트 v2 핵심 발췌

### 6.1 분류 정의 원문

```
- entry: Stock is at or near a proper buy point with a clean base.
         A swing trade entry is appropriate now or imminently (within ~5 trading days).
- watch: Stock passes the trend template but is not at a buy point.
         Either the base is forming, or it has extended too far from a recent breakout.
         Re-evaluation in 1–4 weeks is appropriate.
- ignore: Despite passing the trend template, this stock is not a Minervini-quality setup.
          Examples: thin or wide-and-loose base, climax run, late-stage advance,
          no clean base, post-reverse-split speculation.
```

### 6.2 Step 7 Classification & Confidence 원문

```
- entry: clean base, at or near pivot, Stage 2, volume confirmation available.
- watch: trend template OK, base forming or stock slightly extended, no imminent entry point.
- ignore: climax run, wide-and-loose, no base, late-stage, post-reverse-split distortion, or ETF.

Confidence calibration:
- Thin reasoning (under 100 words) or missing book-defined criteria: max confidence 0.6.
- Pattern named but structure is absent in the data: max confidence 0.5.
- Multiple high-impact flags (climax_run + late_stage_base + extended_from_ma):
  confidence reflects severity and classification must be ignore.
- High confidence (≥ 0.85) requires: clear base structure, volume evidence,
  explicit pivot reference, and no stage ambiguity.
```

### 6.3 risk_flags 12종 원문 (프롬프트 §5)

```
| climax_run         | Price up ≥25% in 1–3 weeks; largest weekly price spread and heaviest volume of the current move |
| late_stage_base    | 3rd or later base in the current Stage 2 advance |
| extended_from_ma   | Price > SMA-50 by more than 15% |
| faulty_pivot       | Pivot is at a prior resistance level that has failed 2+ times |
| low_volume_breakout| Breakout volume < 1.5× the 20-day average |
| narrow_base        | Base duration < 7 weeks |
| wide_and_loose     | Weekly price swings > 10–15% during the base; erratic, difficult to trade |
| thin_liquidity_us_only | US individual stock only: avg daily dollar volume < $5M |
| prior_uptrend_insufficient | Less than 20% run from prior base before current consolidation |
| volume_contraction_on_advance | Price advancing consistently on declining volume |
| reverse_split_distortion | Reverse split within past ~12 weeks confirmed |
| etf_methodology_mismatch | Instrument is an ETF/fund (handled in Pre-Check) |

Three inviolable rules:
1. Trend Template positive traits NEVER go in risk_flags.
2. Reasoning ↔ flags consistency (naming = must appear in flags).
3. thin_liquidity_us_only applies ONLY to US individual stocks.
```

### 6.4 분류 세분화 시 참고 가능한 관찰

현재 사용자가 "entry를 entry_strict / entry_mild / entry_naive로 세분화하면 어떨까"를 고려 중이라면:

**v2가 현재 묵시적으로 구분하는 entry 품질 지표들**:
- confidence 0.90+ → 매우 깨끗한 셋업 (플래그 0개, pivot 명확, 거래량 충분)
- confidence 0.80~0.89 → 복잡하지만 허용 가능 (플래그 1~2개 경미)
- confidence 0.70~0.79 → 약한 셋업 (NVST 케이스 — low_volume, RS 낮음 등)

**세분화 시 조작화 가능한 기준 후보**:
1. `risk_flags = []` + confidence ≥ 0.85 → entry_strict
2. `risk_flags` 중 low_volume_breakout만 있거나 + confidence 0.75~0.84 → entry_mild
3. `risk_flags` 2개+ 있지만 entry → entry_naive (지금의 NVST 위치)

**주의**: 세분화는 프롬프트 변경을 요구하거나, 현재 출력 결과를 규칙 기반 후처리로 재분류하는 두 가지 방법이 가능. 후처리 방식이 더 결정론적이고 안전하다 (헌법 §2.2 정신에도 부합).

---

*작성: Builder (Claude Code CLI), 2026-05-08*  
*다음 소비자: Architect (Web Claude) — Phase 2 brief 작성 시 분류 체계 개편 여부 판단에 사용*
