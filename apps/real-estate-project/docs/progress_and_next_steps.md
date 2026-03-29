# 작업 진행 현황 및 남은 작업 계획

작성일: 2026-03-13

## 0) OpenCode 재시작용 핸드오프 요약

이 문서만 보고 새 세션에서 이어서 진행할 수 있도록 핵심 맥락을 정리합니다.

- 표준 실행 경로는 `python -m src.real_estate.cli ...` 입니다.
- 이 프로젝트는 외부 DB 전용입니다. 테스트 시에는 임시 Docker MySQL(3308)을 사용했습니다.
- 현재 상태 기준으로 DB 비의존 테스트는 통과 상태입니다.
  - `pytest -q tests -m "not db"` -> `11 passed, 3 deselected`
- API 키가 없으면 `ingest`는 401이 정상입니다.
- 실제 API 키 기반 축소 E2E 재검증은 완료되었습니다.

### 빠른 재현 명령 (새 세션 시작 시)

```bash
# 1) baseline
"/Users/hank.es/LocalBigqueryTask/RealEstateProject/.venv/bin/python" -m pytest -q tests -m "not db"

# 2) 테스트 DB 컨테이너
docker rm -f re-mysql-test >/dev/null 2>&1 || true
docker run -d --name re-mysql-test -e MYSQL_ROOT_PASSWORD=1234 -e MYSQL_DATABASE=real_estate -p 3308:3306 mysql:8.0
for i in $(seq 1 40); do docker exec re-mysql-test mysqladmin ping -h 127.0.0.1 -uroot -p1234 --silent && break; sleep 2; done

# 3) 환경변수
export RE_DB_HOST=127.0.0.1
export RE_DB_PORT=3308
export RE_DB_USER=root
export RE_DB_PASSWORD=1234
export RE_DB_NAME=real_estate
# export RE_API_SERVICE_KEY=실제키

# 4) 파이프라인
python -m src.real_estate.cli validate-config
python -m src.real_estate.cli init-db
python -m src.real_estate.cli ingest --lawd-cds 11650 --start-ymd 202401 --end-ymd 202402
python -m src.real_estate.cli clean-anomalies
python -m src.real_estate.cli recalculate-derived
python -m src.real_estate.cli analyze

# 5) 웹 실행(미사용 포트)
PORT=$(python3 -c "import socket;s=socket.socket();s.bind(('127.0.0.1',0));print(s.getsockname()[1]);s.close()")
python -m src.real_estate.cli serve-web --port $PORT
```

### 종료/정리 명령

```bash
docker rm -f re-mysql-test
```

## 1) 현재까지 완료한 작업

### A. 실행 구조/운영 경로 정리
- 표준 실행 엔트리포인트를 `src/real_estate/cli.py`로 정리했습니다.
- 주요 명령을 확정했습니다.
  - `validate-config`
  - `init-db`
  - `ingest`
  - `analyze`
  - `serve-web`
- 레거시 실행 호환(루트 스크립트 wrapper)도 유지했습니다.

### B. 설정/보안/환경 개선
- `project_config.py`에 DB 환경변수 strict 검증 로직을 추가했습니다.
- `.env.example`를 추가해 외부 DB 전용 실행 모델을 명확히 했습니다.
- README를 외부 DB 기준으로 재작성했습니다.

### C. 코드 구조 개선
- Detector 구현을 `src/real_estate/detectors/`로 승격했습니다.
  - `combined.py`
  - `district.py`
- Analyzer 공통화 베이스를 `src/real_estate/analyzers/base.py`로 정리했습니다.
- 기존 루트 파일은 thin-wrapper 성격으로 유지했습니다.

### D. 테스트 체계 강화
- `pytest.ini` 및 `tests/` 기반 테스트 체계를 구축했습니다.
- DB 비의존 테스트를 기본 게이트로 확정했습니다.
  - `pytest -q tests -m "not db"`
- CLI/설정 관련 단위 테스트를 추가했습니다.

### E. 실제 동작 검증(테스트 DB)
- Docker MySQL(3308) 임시 컨테이너로 파이프라인 검증을 수행했습니다.
  - 컨테이너: `re-mysql-test`
  - 포트: `3308:3306`
- 단계별 게이트 결과:
  - Baseline 테스트: 통과 (`11 passed, 3 deselected`)
  - `init-db`: 성공 (필수 테이블 생성)
  - `ingest`: 초기에는 API 키 미설정으로 401 확인
  - 이후 실제 키 기반 축소 범위(`11650`, `202401~202402`) 적재 성공 (139건)
  - `analyze`: 성공
  - 웹 실행(미사용 포트 자동 탐색): `/` 200, 핵심 API 응답 정상

### G. 현재 핵심 파일(운영 경로)
- `src/real_estate/cli.py`
- `src/real_estate/detectors/combined.py`
- `src/real_estate/detectors/district.py`
- `src/real_estate/analyzers/base.py`
- `src/real_estate/analyzers/above_ground.py`
- `src/real_estate/analyzers/below_ground.py`
- `src/real_estate/ingestion/data_manager.py`
- `src/real_estate/analysis/monthly_dong.py`
- `web_ui/app.py`
- `map_drawing/map_utils.py`

### F. 문서화
- 4분류 + 레거시 분류 및 파이프라인 게이트 문서를 추가했습니다.
  - `docs/structure_and_pipeline_plan.md`
- 운영 Runbook 문서를 추가했습니다.
  - `docs/operations_runbook.md`

### H. 레거시 분리 1차 완료
- 아래 파일을 `legacy/`로 이동해 운영 경로 혼선을 줄였습니다.
  - `legacy/analyzers/RealEstateAnalyzerOld.py`
  - `legacy/detectors/DistrictSurgeDetector_Back.py`
  - `legacy/detectors/SurgeDetector_Original.py`
  - `legacy/maps/map_utils_back.py`
  - `legacy/maps/test.py`, `legacy/maps/test2.py`, `legacy/maps/test3.py`, `legacy/maps/test4.py`
  - `legacy/misc/api_test.py`
  - `legacy/misc/check_land_size.py`

### M. 레거시 분리 2차 완료
- optional/experimental detector를 `legacy/detectors/`로 이동했습니다.
  - `legacy/detectors/SurgeDetector.py`
  - `legacy/detectors/FlexibleSurgeDetector.py`
  - `legacy/detectors/ClusterSurgeDetector.py`

### N. 지도 산출물 디렉토리 통합 완료
- 기존 `maps/`, `maps_kakao/`를 `map_images/`로 통합했습니다.
- 기존 산출물은 아래로 이동했습니다.
  - `map_images/legacy_maps/seoul_map.html`
  - `map_images/legacy_maps_kakao/seoul_map_kakao.html`

### O. pandas 경고 제거 리팩토링 완료
- detector/analyzer의 `pd.read_sql` 경로를 cursor 기반 DataFrame 생성으로 교체했습니다.
- detector의 `groupby.apply` 경고를 줄이기 위해 `include_groups=False`(지원 버전) + fallback을 적용했습니다.
- 검증 결과:
  - `pytest -q tests -m "not db"` 통과
  - `pytest -q tests -m db` 통과
  - DB 테스트 출력 기준 경고 미발생

### P. 4분류 최종 구조 수렴(1차) 완료
- `src/real_estate` 하위에 도메인 패키지를 추가했습니다.
  - `src/real_estate/ingestion/`
  - `src/real_estate/analysis/`
  - `src/real_estate/processing/`
  - `src/real_estate/maps/`
  - `src/real_estate/frontend/`
- `src/real_estate/cli.py`는 수집/분석 모듈을 새 도메인 패키지 경로에서 import 하도록 변경했습니다.
- 검증 결과:
  - `pytest -q tests -m "not db"` 통과
  - `pytest -q tests -m db` 통과
- 웹 스모크(`/`, `/combined_analysis`) 통과

### Q. 4분류 최종 구조 수렴(2차) 완료
- 핵심 원본 구현을 `src` 내부로 이동했습니다.
  - `src/real_estate/ingestion/data_manager.py` (원본 수집 구현)
  - `src/real_estate/analysis/monthly_dong.py` (원본 월/동 분석 구현)
- 루트 파일은 이후 `legacy/wrappers/`로 이동했습니다.
- 검증 결과:
  - `pytest -q tests -m "not db"` 통과
  - `pytest -q tests -m db` 통과
  - CLI 웹 스모크(`/`) 통과

### R. data_processing CLI 통합 완료
- 아래 명령을 `src.real_estate.cli`에 추가했습니다.
  - `clean-anomalies`
  - `recalculate-derived`
- `README.md`, `docs/operations_runbook.md`에 표준 실행 순서를 반영했습니다.

### S. 불필요 디렉토리 정리 완료
- 사용처 점검 후 아래 디렉토리를 제거했습니다.
  - `disco/`
  - `map_drawing/maps/`
  - `map_drawing/maps_kakao/`
- 정리 전/후 게이트 검증을 모두 통과했습니다.
  - `pytest -q tests -m "not db"`
  - `pytest -q tests -m db`
  - 웹 스모크(`/`, `/combined_analysis`)
  - `clean-anomalies`, `recalculate-derived` CLI 실행

### T. processing 원본 구현 src 승격 완료
- `src/real_estate/processing`에 원본 구현을 배치했습니다.
  - `src/real_estate/processing/anomaly_corrector.py`
  - `src/real_estate/processing/recalculator.py`
- 검증 결과:
  - `pytest -q tests -m "not db"` 통과
  - `pytest -q tests -m db` 통과
  - `clean-anomalies`, `recalculate-derived` CLI 실행 통과

### U. data_processing 디렉토리 정리 완료
- `data_processing/` 디렉토리를 제거했습니다.
- 기존 wrapper 파일은 legacy 보관을 위해 이동했습니다.
  - `legacy/processing/DataAnomalyCorrector.py`
  - `legacy/processing/DataRecalculator.py`
- 표준 실행 경로는 CLI만 유지합니다.

### W. 루트 wrapper 정리 완료
- 아래 wrapper 파일을 `legacy/wrappers/`로 이동했습니다.
  - `legacy/wrappers/RealEstateDataManager.py`
  - `legacy/wrappers/RealEstateAnalyzer.py`
  - `legacy/wrappers/CombinedSurgeDetector.py`
  - `legacy/wrappers/DistrictSurgeDetector.py`
  - `legacy/wrappers/AboveGroundBuildingAnalyzer.py`
  - `legacy/wrappers/BelowGroundBuildingAnalyzer.py`
  - `legacy/wrappers/BuildingLevelAnalyzer.py`
  - `legacy/wrappers/BuildingLevelAnalyzerTwo.py`
- 루트 실행은 더 이상 권장하지 않으며, 표준 경로는 CLI입니다.

### X. 루트 슬림화 검증 완료
- wrapper 이동 후 루트 디렉토리에서 실행 스크립트 혼재가 제거되었습니다.
- 검증 결과:
  - `pytest -q tests -m "not db"` 통과
  - `pytest -q tests -m db` 통과
  - `clean-anomalies`, `recalculate-derived` CLI 실행 통과
  - `serve-web` + `/combined_analysis` 스모크 통과

### V. 최종 상태 요약
- 운영 핵심 경로는 `src/real_estate/*` + `python -m src.real_estate.cli ...`로 수렴되었습니다.
- 루트의 기존 실행 파일은 thin-wrapper로 호환을 유지합니다.
- 불필요 디렉토리(`disco/`, `map_drawing/maps/`, `map_drawing/maps_kakao/`, `data_processing/`) 정리 완료.
- 현재 테스트 게이트는 모두 통과 상태입니다.
  - `pytest -q tests -m "not db"` -> `11 passed, 3 deselected`
  - `pytest -q tests -m db` -> `3 passed, 11 deselected`

### I. 실제 API 키 기반 축소 E2E 재검증 완료
- Docker MySQL(3308) 기준으로 아래 순서를 모두 통과했습니다.
  - `validate-config --require-api-key`
  - `init-db`
  - `ingest --lawd-cds 11650 --start-ymd 202401 --end-ymd 202402`
  - `analyze`
  - `serve-web` + API 호출 검증
- 데이터 확인:
  - `rh_trade_analysis`: 139건
  - `monthly_dong_analysis`: 10건
  - `building_transaction_analysis_above_ground`: 125건
  - `building_transaction_analysis_below_ground`: 6건

### J. 실행 가이드 일원화 완료
- `README.md`에서 레거시 직접 실행 안내를 축소하고, CLI 중심 경로를 명확히 고정했습니다.
- 레거시 목록은 `legacy/README.md`로 분리했습니다.

### K. 백엔드/프론트 경계 정리 2차(부분) 완료
- `src/real_estate/backend/runtime.py` 추가
- `src/real_estate/backend/web_app.py` 추가 (기존 `web_ui/app.py` 라우트/런타임 로직 이관)
- `src/real_estate/cli.py`의 `serve-web`가 `src.real_estate.backend.get_web_app()`을 사용하도록 변경
- `web_ui/app.py`는 thin-wrapper로 전환하여 호환 유지

### L. DB 통합 테스트 강화 완료
- `tests/integration/test_db_runtime_contract.py` 추가 (`@pytest.mark.db`)
- 검증 범위:
  - 파이프라인 핵심 테이블 row count 점검
  - 실DB 기반 `/combined_analysis` API 계약 확인
- 실행 결과: `pytest -q tests -m db` -> `3 passed`

---

## 2) 확인된 이슈/주의사항

1. `ingest`는 실제 `RE_API_SERVICE_KEY`가 없으면 401로 실패합니다.
2. Docker SQL 직접 삽입 시 한글 인코딩 깨짐 가능성이 있어, 지역명 직접 매칭 테스트에 영향이 있습니다.
3. 현재도 레거시/실험 파일이 루트에 남아 있어 신규 사용자 입장에서 혼선 가능성이 있습니다.
4. `district_analysis`는 테스트 데이터 인코딩이 깨진 경우 `district_name` 직접 필터보다 `gu_name` 경로가 먼저 안정적으로 검증됩니다.
5. 구조는 수렴되었으나 문서/코드 참조 경로에서 구 표현(legacy, old path)이 남아 있을 수 있어 주기적 정리가 필요합니다.

---

## 3) 남은 작업 계획 (우선순위)

## P0 (최우선)

### 3-1. 실제 API 키 기반 축소 E2E 재검증
- 상태: 완료
- 목표: 수동 seed 없이 `ingest -> analyze -> serve-web` 전 구간 확인
- 범위:
  - 지역코드 1개(`11650`)
  - 기간 2~3개월
- 완료 기준:
  - `rh_trade_analysis` row count > 0
  - 분석 테이블 row count > 0
  - `/combined_analysis`, `/district_analysis` 정상 응답
  - 기준월은 ingest 범위의 max `deal_ymd`와 일치시켜 검증

### 3-1-1. 단계별 중단 조건(필수)
- `validate-config --require-api-key` 실패 시 즉시 중단
- `init-db` 실패 시 즉시 중단
- `ingest` 후 `rh_trade_analysis` row count = 0 이면 중단
- `analyze` 후 위/아래층 분석 테이블 row count = 0 이면 중단
- 웹 API 응답에 `success != true`면 중단

### 3-2. 레거시 파일 라벨링/격리 1차
- 상태: 완료
- 목표: 운영 파일 vs 레거시 파일 구분 명확화
- 작업:
  - `legacy/` 디렉토리 생성
  - `*_Old`, `*_Back`, `*_Original`, `map_drawing/test*.py` 이동 또는 실행금지 표기
- 완료 기준:
  - README에서 “운영 표준 경로”만 따라도 실행 가능

### 3-3. 실행 가이드 일원화
- 상태: 완료
- 목표: 사용자 혼란 제거
- 작업:
  - README의 레거시 실행 예시는 하단으로 이동
  - CLI 중심 Quickstart를 최상단 유지
- 완료 기준:
  - 신규 사용자가 `src.real_estate.cli`만으로 전체 실행 가능

## P1 (중요)

### 3-4. 백엔드/프론트 경로 정리 2차
- 상태: 완료 (호환 유지 방식)
- 목표: `web_ui`와 `src` 경계 명확화
- 작업:
  - `web_ui/app.py`의 핵심 로직을 `src/real_estate/backend/web_app.py`로 이관
  - `web_ui/app.py`는 thin-wrapper 유지

### 3-5. DB 통합 테스트 강화
- 상태: 완료
- 목표: 실DB 연결 시 자동 검증 확대
- 작업:
  - `@pytest.mark.db` 시나리오 확장
  - 최소 1개 지역/기간에 대한 검증 케이스 고정

## P2 (개선)

### 3-6. 운영 Runbook 작성
- 상태: 완료
- 목표: 장애 대응/재처리 기준 문서화
- 작업:
  - 실패 유형별 원인/조치 정리
  - 재실행 순서 및 데이터 검증 쿼리 템플릿 추가

### 3-7. 구조 리팩토링 최종 단계
- 상태: 대부분 완료
- 목표: 4분류 디렉토리로 완전 수렴
- 작업:
  - ingestion/analysis/backend/frontend/maps 경로 최종 정리 (완료)
  - thin-wrapper 유지 여부 최종 결정 (정책 확정 필요)

---

## 4) 다음 실행 권장 순서

1. 문서/코드 내 구 경로 표현(legacy 이전 표기, old path) 정리
2. legacy 정리 정책(유지 기간/삭제 시점) 확정

---

## 5) 검증 SQL 템플릿

```sql
SELECT COUNT(*) AS raw_cnt FROM rh_trade_analysis;
SELECT COUNT(*) AS monthly_cnt FROM monthly_dong_analysis;
SELECT COUNT(*) AS above_cnt FROM building_transaction_analysis_above_ground;
SELECT COUNT(*) AS below_cnt FROM building_transaction_analysis_below_ground;
SELECT MIN(CONCAT(dealYear, LPAD(dealMonth,2,'0'))) AS min_ymd,
       MAX(CONCAT(dealYear, LPAD(dealMonth,2,'0'))) AS max_ymd
FROM rh_trade_analysis;
```

## 6) 문서 간 참조

- 구조/분류 및 게이트 상세: `docs/structure_and_pipeline_plan.md`
- 전체 실행 가이드: `README.md`
