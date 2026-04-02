# RealEstateProject

연립/다세대 실거래 데이터를 수집하고, 분석 테이블을 생성한 뒤, 웹 UI로 급등 후보를 시각화하는 프로젝트입니다.

중요: 이 프로젝트는 모노레포의 공용 MySQL 인프라를 사용하되, 데이터는 `real_estate` / `real_estate_test` 별도 DB에 분리해 저장합니다.

## 핵심 기능

- 데이터 수집: 국토부 API 기반 실거래 데이터 수집 및 적재
- 데이터 분석: 동단위/건물단위 분석 테이블 생성
- 급등 탐지: 지상/지하 통합 급등 점수 계산
- 시각화: Flask 웹 UI에서 분석 결과 조회 및 지도 렌더링

## 모노레포 위치 및 실행 기준

- 이 앱은 `apps/real-estate-project/` 아래에 배치됩니다.
- 아래 명령은 별도 설명이 없으면 모노레포 루트에서 `cd apps/real-estate-project` 후 실행하는 것을 기준으로 합니다.
- 스크립트는 모노레포 루트에서 `bash apps/real-estate-project/scripts/...` 형태로 직접 실행해도 됩니다.

## 문서 우선순위 (SSOT)

- 이 파일(`README.md`)이 설치/운영/테스트의 단일 기준 문서입니다.
- 빠른 실행 요약은 `사용방법.txt`를 참고하되, 상세 조건/예외/장애 대응은 반드시 이 문서를 기준으로 따릅니다.
- 웹 화면 기능 설명은 `web_ui/README.md`를 참고합니다.
- 운영 절차는 `docs/operations_runbook.md`, 공개 전 점검은 `docs/public_release_checklist.md`를 참고합니다.

## 빠른 시작

### 1) 가상환경 생성 및 패키지 설치

```bash
cd apps/real-estate-project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
```

`web_ui/requirements.txt`는 웹 런타임 전용 하위 의존성 목록이며, 일반적인 설치는 루트 `requirements.txt` 기준으로 진행합니다.

### 2) 공용 MySQL bootstrap 실행

루트 `.env`는 공용 MySQL 인스턴스와 DB bootstrap 계약을 정의합니다.

```bash
cp .env.example .env
# MYSQL_* / DATABASE_URL / REAL_ESTATE_* 값 수정
docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml --env-file .env up -d
```

첫 볼륨 초기화 시 다음이 자동으로 준비됩니다.

- 주 DB(`MYSQL_DATABASE`) + 테스트 DB(`${MYSQL_DATABASE}_test`)
- real-estate 운영 DB(`REAL_ESTATE_DB_NAME`) + 테스트 DB(`REAL_ESTATE_TEST_DB_NAME`)
- `MYSQL_USER`, `REAL_ESTATE_DB_USER` 권한 부여
- `real_estate` 계열 테이블 DDL 적용

### 3) 앱 환경 변수 설정

앱 런타임은 `apps/real-estate-project/.env.example`를 기준으로 설정합니다.

```bash
cd apps/real-estate-project
cp .env.example .env
# .env 파일에서 값 수정 후
set -a && source .env && set +a
```

루트 `.env`와 앱 `.env`의 역할은 다릅니다.

- 루트 `.env`: 공용 MySQL bootstrap용
- `apps/real-estate-project/.env`: real-estate 런타임용

권장 대응 관계:

- 루트 `.env`의 `REAL_ESTATE_DB_NAME` -> 앱 `.env`의 `RE_DB_NAME`
- 루트 `.env`의 `REAL_ESTATE_DB_USER` -> 앱 `.env`의 `RE_DB_USER`
- 루트 `.env`의 `REAL_ESTATE_DB_PASSWORD` -> 앱 `.env`의 `RE_DB_PASSWORD`

즉, 루트 `.env`는 "무엇을 생성할지"를 정하고, 앱 `.env`는 "실행 중인 앱이 어디에 붙을지"를 정합니다.

주의: `.env`에는 실제 키/비밀번호가 들어가므로 커밋하지 마세요.

필수 DB 변수:

- `RE_DB_HOST`
- `RE_DB_PORT`
- `RE_DB_USER`
- `RE_DB_PASSWORD`
- `RE_DB_NAME`

데이터 수집 시 필수:

- `RE_API_SERVICE_KEY`

선택:

- `RE_FLASK_SECRET` (웹 실행 시 필수)
- `KAKAO_REST_API_KEY` (서버 주소->좌표 변환)
- `KAKAO_JS_KEY` (브라우저 Kakao 지도 렌더링)
- `KAKAO_API_KEY` (`KAKAO_REST_API_KEY` 미설정 시 하위호환)
- `KAKAO_COORD_CACHE_FILE` (좌표 캐시 파일 경로, 미설정 시 `map_images/kakao_geocode_cache.json`)

보안 권장:

- `.env`, 인증서(`*.pem`, `*.key`)는 절대 커밋하지 마세요.
- `RE_FLASK_SECRET`는 충분히 긴 랜덤 문자열을 사용하세요.
- 공개 배포 시 Flask를 직접 외부에 노출하지 말고 Nginx 뒤에서 실행하세요.

### 4) 설정 검증

```bash
cd apps/real-estate-project
set -a && source .env && set +a
python -m src.real_estate.cli validate-config
python -m src.real_estate.cli validate-config --require-api-key
```

### 5) 데이터 수집

```bash
cd apps/real-estate-project
set -a && source .env && set +a
python -m src.real_estate.cli ingest --start-ymd 202001 --end-ymd 202412
```

특정 지역코드만 실행하려면:

```bash
cd apps/real-estate-project
set -a && source .env && set +a
python -m src.real_estate.cli ingest --lawd-cds 11650,11710 --start-ymd 202301 --end-ymd 202412
```

공용 bootstrap 또는 DBA 수동 반영으로 `real_estate` 계열 DB와 테이블이 이미 준비된 상태를 전제로 합니다.

`init-db`는 기본 적재 절차가 아니라, 기존 DB에 real-estate DDL을 다시 적용해야 할 때만 사용합니다.
실행 SQL 원본은 `db/init/03_real_estate_schema.sql`입니다.

### 6) 분석 실행

```bash
cd apps/real-estate-project
set -a && source .env && set +a
python -m src.real_estate.cli clean-anomalies
python -m src.real_estate.cli recalculate-derived
python -m src.real_estate.cli analyze
```

품질 보정이 필요 없으면 `clean-anomalies`, `recalculate-derived`는 생략 가능합니다.

### 7) 웹 실행

```bash
cd apps/real-estate-project
set -a && source .env && set +a
python -m src.real_estate.cli serve-web --port 5001
```

웹 UI 접속:

- 메인 화면(console): `http://localhost:5001/`
- 별칭 경로: `http://localhost:5001/v2`

페이지 로드 시 서울 전체 분석이 기본 조건(당월, 상위 1%, 6개월)으로 자동 실행됩니다.
포트가 사용 중이면 자동으로 다음 사용 가능한 포트를 선택합니다.

## CLI 명령 요약

- `init-db`: 기존 DB에 real-estate DDL을 다시 적용할 때 사용하는 복구/수동 명령
- `ingest`: API 데이터 수집/적재
- `analyze`: 분석 테이블 생성
- `clean-anomalies`: 원천 데이터 대지권 이상치 보정
- `recalculate-derived`: 원천 데이터 파생 컬럼 재계산
- `serve-web`: Flask 웹 UI 실행
- `validate-config`: 필수 환경 변수 검증

## 파이프라인 상세 동작

### 1) `ingest`: 수집 + 정제 + 1차 파생값 계산

`python -m src.real_estate.cli ingest ...`는 API 응답을 단순 원문으로 저장하지 않고, 분석 가능한 형태로 정제하여 `rh_trade_analysis`에 적재합니다.

주요 동작:

- API XML 응답 파싱 후 항목별 타입 정규화(문자열 -> 숫자)
- `cdealType` 값이 있는 거래 제외
  - 취소/해제/정정성 거래 가능성이 있는 건을 기본 분석 대상에서 배제하기 위한 처리
- 중복 방지(`UNIQUE KEY` + `INSERT IGNORE`)
- 최신월(당월/전월) 재수집 시 해당 월 기존 데이터 삭제 후 재삽입(갱신)
- 수집 로그(`data_ingestion_log`) 기록

수집 시 함께 계산되는 파생 컬럼:

- `price_per_pyeong`: 거래금액 / 전용면적(`excluUseAr`) 기준 평당가
- `land_price_per_pyeong`: 거래금액 / 대지권면적(`landAr`) 기준 평당가
- `land_share_ratio`: `landAr / excluUseAr`

즉, `rh_trade_analysis`는 원문 복사본이 아니라 원천 + 정제 + 기본 파생값 테이블입니다.

### 2) `clean-anomalies`: `landAr` 이상치 보정

`python -m src.real_estate.cli clean-anomalies`는 `rh_trade_analysis`에서 대지권면적(`landAr`) 이상치를 규칙 기반으로 탐지/보정합니다.

용어:

- `landAr`: 대지권면적(㎡), 즉 토지 지분 면적
- `excluUseAr`: 전용면적(㎡), 실사용 면적

이상치 후보 규칙:

- `landAr >= excluUseAr * 2`

보정 방식:

1. 이상치 후보를 조회
2. 같은 건물/층(`sggCd`, `umdNm`, `jibun`, `buildYear`, `floor`)의 다른 거래 조회
3. 그 중 정상 범위(`landAr < excluUseAr * 2`)이며 같은 `excluUseAr`를 가진 거래의 `landAr`를 참조
4. 해당 값으로 이상치 레코드의 `landAr`를 업데이트

참조 가능한 거래가 없으면 해당 건은 건너뜁니다.

### 3) `recalculate-derived`: 파생 컬럼 재계산

`python -m src.real_estate.cli recalculate-derived`는 `rh_trade_analysis`의 파생 컬럼을 일괄 재계산합니다.

재계산 대상:

- `land_price_per_pyeong`
- `land_share_ratio`

왜 필요한가:

- `clean-anomalies`로 `landAr`가 바뀌면 기존 파생 컬럼이 이전 값 기준으로 남아 데이터 정합성이 깨질 수 있음
- 파생 컬럼 재계산으로 최신 원천값과 계산값을 다시 일치시킴

주의:

- 이 명령은 `rh_trade_analysis`의 파생 컬럼 값을 직접 업데이트합니다.
- 식별/거래 기본 컬럼(예: `sggCd`, `jibun`, `dealYear`, `dealAmount`)을 변경하는 작업은 아닙니다.

### 4) `analyze`: 동단위/건물단위 집계 테이블 생성

`python -m src.real_estate.cli analyze`는 `rh_trade_analysis`를 집계해 분석 전용 테이블을 생성/갱신합니다.
기존 테이블 컬럼을 늘리는 방식이 아니라 별도 분석 테이블에 저장합니다.

#### 4-1. 동단위 월분석 (`monthly_dong_analysis`)

집계 키:

- `sggCd + umdNm + deal_ymd`

주요 지표:

- 평균 전용/대지 평당가
- 거래건수
- 저층(<1층) 비율/건수
- 직거래 건수
- 개인매도-법인매수 건수
- 월별 평당가 표준편차
- 직전 거래월 대비 가격 변동률
- 직전 거래월과의 개월 차
- 누적 월평균 대비 거래량 변화율

#### 4-2. 건물단위 지상 분석 (`building_transaction_analysis_above_ground`)

조건:

- `floor >= 1`

집계 키:

- `sggCd + jibun + buildYear + deal_ymd`

주요 지표:

- 거래건수, 평균 거래금액
- 평균 전용/대지 평당가
- 직전월 대비 전용/대지 평당가 변동률
- 직전 거래월과의 개월 차

#### 4-3. 건물단위 지하 분석 (`building_transaction_analysis_below_ground`)

조건:

- `floor <= -1`

집계 키/지표는 지상 분석과 동일하며 저장 테이블만 다릅니다.

### 5) `serve-web`: 웹(백엔드 + 프론트) 동시 제공

`python -m src.real_estate.cli serve-web --port 5001` 실행 시 Flask 앱 하나가 HTML 렌더링(프론트)과 API(백엔드)를 함께 제공합니다.

지도 동작 방식:

- 브라우저 지도: Kakao JavaScript SDK (`KAKAO_JS_KEY` 필요)
- 서버 지오코딩: Kakao Local REST API (`KAKAO_REST_API_KEY` 권장)
- 좌표 캐시: 동일 주소 재호출을 줄이기 위해 파일 캐시 사용
- 지도는 웹 화면의 Kakao 지도 패널에서 직접 렌더링하며, 별도의 정적 지도 HTML 링크(`map_url`)는 제공하지 않습니다.
- 전체/특정 지역 분석 결과는 화면과 지도 모두 최대 10건까지만 표시됩니다.
- 분석 결과의 `상세보기` 페이지에서도 단일 건물 위치 지도를 표시합니다.

Kakao JavaScript 키를 사용할 때는 Kakao 개발자 콘솔에 사이트 도메인(예: `http://localhost:5001`)을 등록해야 합니다.

주요 데이터 소스:

- 급등 분석 API(`/combined_analysis`, `/district_analysis`)
  - `building_transaction_analysis_above_ground`
  - `building_transaction_analysis_below_ground`
- 건물 상세(`/building_detail`)
  - `rh_trade_analysis` 원천 거래 내역

## DB 권한 가이드 (최소 권한 권장)

- `init-db`
  - 필요 권한: `CREATE TABLE`, `ALTER`(마이그레이션 시), `INDEX`
  - 전제: 대상 DB는 bootstrap 또는 DBA 수동 작업으로 이미 생성되어 있어야 함
- `ingest`
  - 필요 권한: `SELECT`, `INSERT`, `UPDATE`, `DELETE`
- `analyze`
  - 필요 권한: `SELECT`, `INSERT`, `UPDATE`, `DELETE`
- `serve-web`
  - 필요 권한: `SELECT`

운영 환경에서는 계정을 분리하세요.

## 테스트

DB 없는 기본 테스트:

```bash
cd apps/real-estate-project
pytest -q tests -m "not db"
```

DB 통합 테스트(선택):

```bash
cd apps/real-estate-project
pytest -q tests -m db
```

## 레거시 실행 호환

기존 파일 실행 방식은 호환 목적만으로 유지되며, 신규 운영에서는 권장하지 않습니다.

- 권장: `python -m src.real_estate.cli ...`
- 레거시/실험 파일 목록: `legacy/README.md`
- 구조/파이프라인 분류 문서: `docs/structure_and_pipeline_plan.md`

지도 산출물은 `map_images/`에 통합 관리됩니다.

## 데이터 수집 스크립트

수집 자동화를 위한 스크립트가 `scripts/` 디렉토리에 준비되어 있습니다.

### 최초 bulk 수집 (1회)

```bash
bash apps/real-estate-project/scripts/collect_initial.sh
```

2020.01부터 현재까지 전체 수집 + 후처리 파이프라인을 순차 실행합니다.
API 일일 호출량 제한에 걸릴 경우 다음 날 재실행하면 이미 수집된 데이터는 건너뛰고 나머지만 수집합니다.

### 일일 정기 수집

```bash
bash apps/real-estate-project/scripts/collect_daily.sh
```

전월+당월 데이터를 수집하고 분석 테이블을 갱신합니다. cron으로 매일 실행하도록 설정합니다.

```bash
# 매일 오전 6시 KST (= UTC 21:00)
0 21 * * * cd /app/apps/real-estate-project && bash scripts/collect_daily.sh >> logs/cron_collect.log 2>&1
```

## VM 배포

앱 내부 `.github/workflows/deploy.yml`은 원본 프로젝트에서 가져온 참고 템플릿이며, 이 모노레포에서는 자동 배포 범위에 포함하지 않습니다.

필요한 GitHub Secrets:

- `VM_HOST`: VM 퍼블릭 IP 또는 도메인
- `VM_SSH_KEY`: deploy 유저의 SSH 프라이빗 키
- `VM_SSH_KNOWN_HOSTS`: `ssh-keyscan -H <host>` 결과 전체

Nginx 예시 설정: `ops/nginx/real-estate.conf`

배포 구조 권장:

- 외부 트래픽: `Nginx -> Flask(127.0.0.1:5001)`
- Flask 기본 바인딩은 `127.0.0.1`이며, 직접 외부 노출이 필요할 때만 명시적으로 `--host 0.0.0.0` 사용

## Security

- 보안 이슈 신고 절차는 `SECURITY.md`를 참고하세요.
- 공개 리포지토리 운영 전 `pytest -q tests -m "not db"`와 `python -m src.real_estate.cli validate-config --require-api-key` 실행을 권장합니다.

## 장애 대응 체크리스트

- DB 연결 실패: `RE_DB_*` 값, DB 접근 제어(보안그룹/방화벽), 사용자 권한 확인
- API 수집 실패: `RE_API_SERVICE_KEY` 유효성 확인
- 테이블 누락 오류: 공용 bootstrap 상태를 확인한 뒤 `python -m src.real_estate.cli init-db` 재실행
- 포트 충돌: 다른 `--port` 지정 또는 자동 할당 로그 확인

운영 상세 절차/장애 대응은 `docs/operations_runbook.md`를 참고하세요.
