# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Policy

- Default response language is Korean.
- Use another language only when the user explicitly requests it.

## Project Overview

This is a Korean real estate analysis project that collects and analyzes apartment transaction data using the Korean Ministry of Land, Infrastructure and Transport API. The project focuses on detecting price surges and generating visual maps of real estate trends in Seoul districts.

## Core Architecture

### Data Pipeline
1. **Data Collection**: `src/real_estate/ingestion/data_manager.py` - Fetches transaction data from government API and stores in MySQL
2. **Data Processing**: `src/real_estate/analysis/monthly_dong.py` - Creates secondary analysis tables with time-series indicators
3. **Anomaly Detection**: `python -m src.real_estate.cli clean-anomalies`, `python -m src.real_estate.cli recalculate-derived` - Handles data quality issues
4. **Analysis & Detection**: Multiple surge detector classes for different analysis types

### Key Analysis Components

**Surge Detection Classes** (all follow similar patterns):
- `src/real_estate/detectors/combined.py` - Main detector for both above-ground and below-ground buildings
- `src/real_estate/detectors/district.py` - District-specific analysis with map generation  
- `src/real_estate/analyzers/above_ground.py` / `src/real_estate/analyzers/below_ground.py` - Floor-specific analyzers
- `legacy/detectors/FlexibleSurgeDetector.py` / `legacy/detectors/ClusterSurgeDetector.py` - Legacy alternative algorithms (not standard runtime path)

**Map Visualization**:
- `map_drawing/map_utils.py` - Core map generation utilities
- Maps generated in `map_images/` directory as HTML files
- Legacy map experiments are under `legacy/maps/`

### Database Structure
- Uses MySQL with `rh_trade_analysis` as the main transaction table
- Secondary analysis tables created by `RealEstateAnalyzer`
- Seoul district codes defined in `gu_codes.json`
- **Schema SSOT**: `sql/init_schema.sql` — 전체 10개 테이블 정의가 이 파일 하나에 통합
- `project_config.ensure_schema(db_config)` 함수가 SQL 파일을 실행 (프로세스 내 1회)
- `init-db`, `ingest`, `analyze` 등 어떤 명령이든 최초 실행 시 자동으로 스키마 초기화

### Database Connection
환경변수 기반 (`RE_DB_HOST`, `RE_DB_PORT`, `RE_DB_USER`, `RE_DB_PASSWORD`, `RE_DB_NAME`).
`project_config.get_db_config()`로 로드하며, 필수 환경변수가 없으면 즉시 예외를 발생시킵니다.

### Security Notes
- `RE_FLASK_SECRET`는 필수이며, 하드코딩 fallback이 없습니다.
- `web_ui/app.py`와 CLI 기본 바인딩은 `127.0.0.1` 기준입니다.
- 운영 배포는 Nginx 리버스 프록시 뒤에서 수행하는 것을 전제로 합니다.
- CI 보안 점검: `.github/workflows/security.yml` (`pip-audit`), `.github/dependabot.yml`
- 배포 예시 설정: `ops/nginx/real-estate.conf`
- 공개 전 최종 점검: `docs/public_release_checklist.md`

## Usage Instructions

### Main Analysis Tools

**For general surge detection across all areas:**
```python
# Use src.real_estate.detectors.combined
# Extracts top surge candidates for specified time periods
# Includes both above-ground (1F+) and below-ground (-1F and below) analysis
# Results use "_" delimiter to separate building types
```

**For district-specific analysis:**
```python  
# Use src.real_estate.detectors.district
# Analyzes specific districts for specified time periods
# Generates map visualizations saved to map_images/
# Displays top surge candidates with geographic context
```

### Data Flow
1. Configure API key and MySQL connection in respective classes
2. Run `python -m src.real_estate.cli ingest` to collect raw transaction data
3. Process with `python -m src.real_estate.cli analyze` to create analysis tables
4. Use surge detectors to identify investment opportunities
5. Generate maps for spatial analysis

### Key Files
- `utils.py` - Common utilities including JSON loading functions
- `legacy/misc/api_test.py` - API testing utilities (legacy)
- Configuration files use Korean district names and government administrative codes

## 데이터베이스 테이블 구조

### rh_trade_analysis
**설명**: 연립다세대 매매 실거래 원본 데이터 테이블  
**총 레코드 수**: 253,536건

**주요 컬럼:**
- `sggCd` (varchar(10)): 시군구 코드 (예: 11650=서초구)
- `umdNm` (varchar(100)): 읍면동명 (예: 반포동)
- `jibun` (varchar(50)): 지번 (예: 728-33)
- `mhouseNm` (varchar(100)): 연립다세대 명칭
- `buildYear` (int): 건축년도
- `excluUseAr` (decimal(10,4)): 전용면적(㎡)
- `landAr` (decimal(10,4)): 대지권면적(㎡)
- `dealAmount` (bigint): 거래금액(만원)
- `floor` (int): 층 (양수=지상, 음수=지하)
- `price_per_pyeong` (decimal(20,2)): 전용면적 평당가
- `land_price_per_pyeong` (decimal(20,2)): 대지권 평당가

**인덱스:**
- `unique_trade`: 거래 중복 방지 (sggCd, jibun, dealYear, dealMonth, dealDay, dealAmount, mhouseNm, excluUseAr)
- `idx_sgg_umd`: 지역별 조회 최적화 (sggCd, umdNm)

### building_transaction_analysis_above_ground
**설명**: 지상층(1층 이상) 건물별 시계열 분석 테이블  
**총 레코드 수**: 187,127건

**주요 컬럼:**
- `sggCd`, `jibun`, `buildYear`: 건물 식별자
- `deal_ymd` (varchar(6)): 거래년월 (예: 202408)
- `trade_count` (int): 해당 월 거래건수
- `avg_exclu_price_per_pyeong` (decimal(20,2)): 평균 전용면적 평당가
- `prev_avg_exclu_price_per_pyeong` (decimal(20,2)): 이전 거래시점 평당가
- `exclu_price_change_rate_vs_prev` (decimal(10,4)): 이전 대비 변동률(%)
- `avg_land_price_per_pyeong` (decimal(20,2)): 평균 대지권 평당가
- `land_price_change_rate_vs_prev` (decimal(10,4)): 대지권 변동률(%)
- `months_since_prev_trade` (int): 이전 거래 이후 경과 개월
- `avg_dealAmount` (bigint): 평균 거래금액

**인덱스:**
- `uk_sgg_jibun_buildyear_ymd`: 건물별 월단위 UNIQUE (sggCd, jibun, buildYear, deal_ymd)
- `idx_sgg_jibun_buildyear`: 건물별 조회 (sggCd, jibun, buildYear)

### building_transaction_analysis_below_ground
**설명**: 지하층(-1층 이하) 건물별 시계열 분석 테이블  
**총 레코드 수**: 18,702건

**스키마**: above_ground 테이블과 동일한 구조

### 테이블 관계도
```
rh_trade_analysis (원본 거래 데이터)
    ↓ (층별 분리 및 건물별 집계)
building_transaction_analysis_above_ground (지상층 분석)
building_transaction_analysis_below_ground (지하층 분석)
    ↓ (급등 분석)
CombinedSurgeDetector / DistrictSurgeDetector (급등 탐지)
```

### 주요 쿼리 패턴
**건물별 시계열 데이터 조회:**
```sql
SELECT * FROM building_transaction_analysis_above_ground 
WHERE sggCd = '11650' AND jibun = '728-33' AND buildYear = 1992
ORDER BY deal_ymd;
```

**특정 지역 급등 후보 조회:**
```sql
SELECT sggCd, umdNm, jibun, buildYear, exclu_price_change_rate_vs_prev
FROM building_transaction_analysis_above_ground
WHERE umdNm = '반포동' AND exclu_price_change_rate_vs_prev > 50
ORDER BY exclu_price_change_rate_vs_prev DESC;
```

## Development Notes

- Korean language comments and variable names throughout
- Focus on MySQL database operations and API integration
- Map outputs are self-contained HTML files with embedded JavaScript

## Web UI

웹 기반 분석 도구는 `src/real_estate/backend/web_app.py`를 중심으로 동작하며,
`web_ui/app.py`는 호환용 thin wrapper입니다.

### 파일 구조
```
web_ui/
├── app.py              # 호환용 wrapper (실제 앱은 src/real_estate/backend/web_app.py)
├── requirements.txt    # Python 의존성 패키지 목록
├── templates/
│   ├── index_console.html       # 메인 분석 페이지 (기본 라우트 /, 별칭 /v2)
│   ├── building_detail.html     # 건물 상세 정보 페이지
│   ├── partials/
│   │   ├── combined_form.html   # 서울 전체 분석 폼
│   │   ├── district_form.html   # 특정 지역 분석 폼
│   │   └── shared_script.html   # 공통 JS (지도, 분석 API 호출 등)
│   └── deprecated/
│       ├── index_v2.html        # 이전 메인 화면 (deprecated, 라우트 미연결)
│       └── README.md
└── static/            # CSS, JS 파일 (현재 CDN 사용)

scripts/
├── collect_initial.sh  # 최초 1회 bulk 데이터 수집
└── collect_daily.sh    # 일일 정기 데이터 수집 (cron용)

.github/workflows/
└── deploy.yml          # VM 배포 + cron 자동 등록
```

### 실행 방법
```bash
pip install -r web_ui/requirements.txt
python -m src.real_estate.cli serve-web --port 5001
```
웹 브라우저에서 http://localhost:5001 접속

### 웹 UI 주요 기능

**1. 메인 분석 페이지 (`/`, `/v2`)**
- **전체 지역 급등 분석**: CombinedSurgeDetector를 사용하여 서울 전체 지역에서 급등 후보 건물 탐지
- **특정 지역 급등 분석**: 구/동 선택을 통한 특정 지역 집중 분석
- **실시간 지도 시각화**: 급등 건물들을 지도상에 마커로 표시 (최대 10개)
- **인터랙티브 결과 테이블**: 순위, 급등점수, 신뢰도, 거래금액 등 상세 정보 표시

**2. 건물 상세 페이지 (`/building_detail`)**
- **건물 기본 정보**: 위치, 건축년도, 법정동코드 등
- **분석 기간 정보**: 사용자가 선택한 분석 조건 표시
- **거래 통계**: 총 거래건수, 평균 거래금액, 평균 평당가, 거래된 층 수
- **분석 기간 내 거래 내역**: 급등 분석에 사용된 거래 데이터만 별도 표시
- **전체 거래 내역**: 해당 건물의 모든 거래 기록 (스크롤 가능한 테이블)

### API 엔드포인트

**분석 API:**
- `POST /combined_analysis`: 전체 지역 급등 분석 실행
- `POST /district_analysis`: 특정 지역 급등 분석 실행

**유틸리티 API:**
- `GET /get_districts?gu={구이름}`: 특정 구의 동 목록 조회
- `GET /map/{filename}`: 생성된 지도 파일 서빙

### 기술 스택
- **백엔드**: Flask 2.3.3
- **데이터베이스**: MySQL (mysql-connector-python 8.1.0)
- **데이터 처리**: Pandas 2.1.1, NumPy 1.24.3
- **날짜 처리**: python-dateutil 2.8.2
- **프론트엔드**: Bootstrap 5.1.3, Font Awesome 6.0.0
- **지도 시각화**: 기존 `map_utils.py` 모듈 활용

### 사용자 워크플로우
1. **분석 조건 설정**: 기준 년월, 분석 기간, 지역 선택
2. **분석 실행**: 전체 지역 또는 특정 지역 분석 선택
3. **결과 확인**: 급등 후보 건물 목록과 급등점수 확인
4. **지도 시각화**: 생성된 지도에서 건물 위치와 급등점수 시각적 확인
5. **상세 조회**: 관심 건물 클릭하여 거래 내역 상세 분석

### 데이터 연동
- `CombinedSurgeDetector`, `DistrictSurgeDetector` 클래스 직접 활용
- `map_utils.create_map_with_multiple_addresses()` 함수로 지도 생성
- `BuildingTransactionQuery` 클래스로 건물별 거래 내역 조회
- 생성된 지도 파일들은 `map_images/` 디렉터리에 저장되며 웹에서 직접 접근 가능
