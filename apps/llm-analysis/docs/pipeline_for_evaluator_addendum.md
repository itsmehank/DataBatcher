# pipeline_for_evaluator.md 보강 — 코드·DB 직접 확인 결과

> 작성일: 2026-05-13
> 환경: MySQL container `mysql-standalone-mysql` (Up 6 days, healthy), DB `trade`
> 원칙: 추측 없음. 본 문서의 모든 수치는 아래 명시한 SQL을 동일 시점에 실행하면 재현된다.

---

## §A. RS Rating 임계값 확인 결과

### 결론

- **임계값은 `80`이며 실제로 비교에 사용된다.** 변수명 `rs_rating_above_70`은 **레거시 잔재 (misleading literal in code)**.
- **KR / US 모두 동일하게 80**. 코드 default가 70이지만 settings.yaml에서 80으로 override.

### 근거

`apps/ingest-databatcher/indicators/minervini/trend_template.py` (해당 라인):

```python
# line 46
rs_min = filters.get("rs_rating", {}).get("min", 70)   # default 70 (settings로 override)
# line 74
conditions["rs_rating_above_70"] = rs_aligned >= rs_min   # 키 이름만 70, 비교는 rs_min
# line 76
conditions["rs_rating_above_70"] = pd.DataFrame(False, ...)   # RS 데이터 없을 때 빈 마스크
```

- 딕셔너리 키 `"rs_rating_above_70"`는 하드코딩된 string. 비교는 항상 `rs_aligned >= rs_min`이고 `rs_min`은 settings에서 불러옴 → 즉 **변수명은 디스플레이용/식별자에 불과**하며 실제 임계값을 좌우하지 않는다.
- `screen_minervini_trend_template`이 conditions dict를 `conditions_met` JSON으로 그대로 저장하므로, **DB `minervini_screen_results_*.conditions_met`의 키 또한 `rs_rating_above_70`이다.** 평가자가 conditions_met을 보고 "임계값 70이구나"로 오해할 위험이 있는 지점.

`apps/ingest-databatcher/config/settings.yaml`:

```yaml
# line 351-353 (minervini_kr)
    rs_rating:
      enabled: true
      min: 80                      # RS Rating 80 이상

# line 375-377 (minervini_us)
    rs_rating:
      enabled: true
      min: 80                      # RS Rating 80 이상
```

| 시장 | settings.yaml 경로 | 임계값 |
|---|---|---:|
| KR | `minervini_kr.filters.rs_rating.min` | **80** |
| US | `minervini_us.filters.rs_rating.min` | **80** |

→ **두 시장이 같은 임계값**. 차이는 `minervini_us.price_column: adj_close`(line 362) 하나뿐.

### 평가자에게 전달할 메시지

- `conditions_met` 필드의 `rs_rating_above_70` 키는 **"RS rating threshold passed"** 로 읽어야 한다. 임계값 자체는 KR/US 모두 **80**.
- `daily_analysis_*.pattern` / `risk_flags` 등에는 영향 없음 — 본 키는 screening 단계 내부 dict의 라벨일 뿐 LLM 페이로드에는 그대로 boolean 값으로 전달된다 (data_loader.py:225-231).

---

## §B. LLM 호출 실측 통계

### B.1 데이터 범위 (실제로 존재하는 호출)

```sql
SELECT module, COUNT(*) AS n,
       SUM(error IS NULL) AS ok, SUM(error IS NOT NULL) AS err,
       MIN(DATE(timestamp)) AS first_d, MAX(DATE(timestamp)) AS last_d
FROM llm_calls
GROUP BY module ORDER BY n DESC;
```

| module | n | ok | err | first_d | last_d |
|---|---:|---:|---:|---|---|
| `analysis_5_us` | 439 | 391 | 48 | 2026-05-07 | 2026-05-09 |
| `analysis_5_kr` | 75 | 71 | 4 | 2026-05-07 | 2026-05-07 |
| `entry_params_6_us` | 1 | 1 | 0 | 2026-05-07 | 2026-05-07 |
| `entry_params_6_kr` | — | — | — | — | — |

**중요한 한계**:
1. **30일 윈도우라고 했지만 실제 데이터는 2026-05-07~2026-05-09 3일치만 존재.** Phase 1 LLM 분석은 2026-05-07 PROD 등록 직후라 누적 데이터가 짧다 (settings.yaml 주석·sync_log에서 추정 가능).
2. **모듈 명명**: 질문에 `analyze_chart_5_*`로 표기했지만 실제 코드의 module string은 `analysis_5_*`. 근거: `apps/llm-analysis/scripts/run_daily_analysis.py:221, 241`.
3. **`entry_params_6_kr`은 0건, `entry_params_6_us`는 1건뿐**. (5) → (6) 트리거는 `classification=='entry'` 시에만 발생하는데, 실측 데이터의 분류 분포가 entry에 강하게 편향되어 있다 (§B.4 참조).

### B.2 module별 통계 (성공 호출만, n≥2인 모듈)

쿼리: 원본 행을 dump해 Python에서 percentile 계산. SQL은 다음:

```sql
SELECT module, prompt_tokens, completion_tokens, duration_ms
FROM llm_calls
WHERE error IS NULL
  AND timestamp >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);
```

| module | n | pt_avg | pt_median | pt_p95 | ct_avg | ct_median | ct_p95 | dur_avg (s) | dur_median (s) | dur_p95 (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `analysis_5_kr` | 71 | 25,202 | 25,058 | 26,262 | 3,295 | 3,176 | 4,544 | **77.5** | 74.4 | 98.0 |
| `analysis_5_us` | 391 | 25,866 | 26,012 | 26,077 | 3,350 | 3,380 | 5,084 | **77.8** | 79.6 | 112.1 |
| `entry_params_6_us` | **1** | 31,498 | 31,498 | 31,498 | 5,492 | 5,492 | 5,492 | 107.9 | 107.9 | 107.9 |
| `entry_params_6_kr` | **0** | — | — | — | — | — | — | — | — | — |

**관찰:**
- (5)의 prompt_tokens가 KR/US 모두 **약 25,000–26,000**으로 안정. settings.yaml 주석의 "추정 8,000~12,000"은 **2배 이상 과소평가**. 토큰 폭증 감지 임계 `_TOKEN_SPIKE_THRESHOLD=24,000` (`llm_call_recorder.py:41`)에 거의 항상 근접 — 실제로 24,000을 넘는 호출이 majority라 임계 의미가 사실상 무력화된 상태.
- (5)의 wall time이 KR/US 모두 평균 **약 77–78초**. settings.yaml:36 주석의 "KR 실측 평균 ~76s/건"과 일치.
- p95가 KR 98s / US 112s로 큰 분산 없음. timeout 120s에 US p95가 근접.
- (6)는 단 1건이라 통계적으로 의미 없음. 그 1건은 **prompt_tokens 31,498 (≈ (5)의 1.2배), completion_tokens 5,492 (≈ (5)의 1.6배), 107.9s** — payload에 prior_analysis가 추가되어 길어지고 응답도 16필드 JSON이라 길다.

### B.3 entry 분류 시 (5)+(6) 합산

질문은 entry 케이스의 합산 평균/중앙값 시간 요청. **실측 데이터셋에 신뢰 가능한 entry 사례가 사실상 없다.**

```sql
-- daily_analysis 분류 분포
SELECT 'KR' AS region, classification, COUNT(*) FROM daily_analysis_kr GROUP BY classification
UNION ALL
SELECT 'US', classification, COUNT(*) FROM daily_analysis_us GROUP BY classification;
```

| region | classification | n |
|---|---|---:|
| KR | ignore | 70 |
| US | ignore | 365 |
| US | watch | 4 |
| US | **entry** | **0** |
| KR | watch | 0 |
| KR | **entry** | **0** |

- **현 시점 `daily_analysis_*`에 `classification='entry'` 행이 0건.** `entry_params_6_us` 호출 1건이 존재하지만, 그 호출에 해당하는 daily_analysis 행이 entry로 살아남지 못함 (이후 force-recompute 또는 schema 검증 실패로 재분류된 것으로 추정 — 정확한 원인은 본 보고 범위 밖).
- 따라서 **"entry로 분류된 경우 (5)+(6) 합산 평균/중앙값"은 산출 불가**. 유일한 (6) 호출의 단독 시간(107.9s) + 같은 날짜 (5) 평균(77.8s)을 단순 합산하면 **약 185.7초/entry-종목 추정**이지만 n=1.

### B.4 실패율 (module별)

```sql
SELECT module, COUNT(*) total, SUM(error IS NULL) ok,
       SUM(error IS NOT NULL) err,
       ROUND(SUM(error IS NOT NULL)/COUNT(*)*100, 2) err_pct
FROM llm_calls
WHERE timestamp >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY module;
```

| module | total | ok | err | err_pct |
|---|---:|---:|---:|---:|
| `analysis_5_kr` | 75 | 71 | 4 | **5.33 %** |
| `analysis_5_us` | 439 | 391 | 48 | **10.93 %** |
| `entry_params_6_us` | 1 | 1 | 0 | 0.00 % |

**관찰:**
- US 실패율 ~11%는 production 운영 관점에서 **상당히 높다**. KR의 2배.
- 실패가 retry 정책(`max_retries=2`, `call_and_record`)으로 재시도되며 각 시도가 별행으로 기록되므로, **종목 단위 최종 실패율은 위 호출 단위 실패율보다 낮다**. 종목 단위 실패는 `sync_log` 별행 확인 필요.

---

## §C. 일별 / 주별 통과 종목 수 통계

### C.1 일별 통과 종목 수 (직전 60 거래일)

```sql
SELECT date, COUNT(*) AS n
FROM minervini_screen_results_kr   -- (KR; US는 _us 테이블 동일 패턴)
WHERE date >= DATE_SUB('2026-05-13', INTERVAL 90 DAY)
GROUP BY date;
```

데이터 범위:
- KR: 2026-02-12 ~ 2026-05-04 (53 거래일 — 60 거래일 미만)
- US: 2026-02-12 ~ 2026-05-07 (59 거래일)

| 시장 | n_days | mean | median | min | max | p95 |
|---|---:|---:|---:|---:|---:|---:|
| KR | 53 | **292** | 310 | 151 | 348 | 343 |
| US | 59 | **839** | 872 | 496 | 1,226 | 1,192 |

(요청한 "60 거래일"보다 KR이 7일, US가 1일 짧음 — 그게 DB에 존재하는 전부.)

### C.2 직전 영업주(최근 5 거래일) unique symbol 수

```sql
SELECT COUNT(DISTINCT symbol)
FROM minervini_screen_results_us
WHERE date IN (
  SELECT date FROM (
    SELECT DISTINCT date FROM minervini_screen_results_us ORDER BY date DESC LIMIT 5
  ) t);
```

| 시장 | 직전 5 거래일 unique symbol |
|---|---:|
| KR | **399** |
| US | **1,411** |

→ 평가자 안의 "주말에 한 번에 weekly 분류" 대상 종목 규모. KR 약 400, US 약 1,400.
- 종목당 (5) 평균 ~78초로 가정 시: KR 400 × 78 = **31,200초 ≈ 8.7 시간**, US 1,400 × 78 = **109,200초 ≈ 30.3 시간**.
- 병렬화 미적용 기준이며, 현 LLM 호출 시간 가정 그대로. 평가자 측에서 처리량 산정에 사용 가능.

### C.3 최근 4주 각 주별 unique symbol 수 (변동성)

```sql
SELECT YEARWEEK(date, 3) AS iso_week, MIN(date) w_from, MAX(date) w_to,
       COUNT(DISTINCT symbol) AS uniq
FROM minervini_screen_results_us
WHERE date >= DATE_SUB((SELECT MAX(date) FROM minervini_screen_results_us), INTERVAL 28 DAY)
GROUP BY iso_week ORDER BY iso_week;
```

**KR:**

| iso_week | w_from | w_to | uniq |
|---|---|---|---:|
| 202615 | 2026-04-06 | 2026-04-10 | 303 |
| 202616 | 2026-04-13 | 2026-04-17 | 357 |
| 202617 | 2026-04-20 | 2026-04-24 | 388 |
| 202618 | 2026-04-27 | 2026-04-30 | 381 |
| 202619 | 2026-05-04 | 2026-05-04 | 333 (1일치만) |

**US:**

| iso_week | w_from | w_to | uniq |
|---|---|---|---:|
| 202615 | 2026-04-09 | 2026-04-10 | 959 (2일치) |
| 202616 | 2026-04-13 | 2026-04-17 | 1,081 |
| 202617 | 2026-04-20 | 2026-04-24 | 1,059 |
| 202618 | 2026-04-27 | 2026-05-01 | 1,379 |
| 202619 | 2026-05-04 | 2026-05-07 | 1,367 |

(부분 주차는 거래일 수가 적어 작게 보임 — 5거래일 완전 주차 기준은 202616/202617/202618.)

### C.4 한 줄 요약

> KR은 일별 통과가 평균 292종목·최대 348, 5거래일 unique 399. US는 일별 평균 839·최대 1,226, 5거래일 unique 1,411. **현 일일 한도(KR 50 / US 100) 대비 KR은 약 8배, US는 약 14배의 통과 종목이 매일 발생**하고 있으며 (rs_rating DESC 컷오프로 잘려나간 종목은 carry-over 없이 그날 분석되지 못한다). 주별 unique는 일별 평균의 약 1.3–1.6배.

---

## 참조 파일 / 추가 노트

- **모듈 명명 정정**: 본 보강 작업에서 확인된 module string은 `analysis_5_*` / `entry_params_6_*`. 원 문서 §3.7에 "analysis_5_kr/us, entry_params_6_kr/us"로 이미 기재되어 있음 (정확).
- **`include_indicators` 4개 명**: settings상 `sma_50_close, sma_150_close, sma_200_close, rs_line` (settings.yaml:65-68). 페이로드에서는 `sma_50, sma_150, sma_200, rs_line`으로 키가 리네임됨 (`core/data_loader.py:23-28` `_INDICATOR_NAME_MAP`). 평가자가 페이로드 키를 검사할 때 참고.
- **본 보강의 데이터 신선도**: 최신 영업일 KR 2026-05-04, US 2026-05-07. 오늘(2026-05-13)까지 약 1주의 신규 데이터가 추가됐을 수 있으나, 본 시점 DB는 그 이전이다 (cron 미실행 또는 다른 이유 — 본 보고 범위 밖).
- **MySQL warning "Using a password on the command line"**: 모든 쿼리에서 발생했으나 결과 정확성에 영향 없음. 평가자가 재현 시 동일하게 출력될 수 있음.

---

**문서 끝.**
