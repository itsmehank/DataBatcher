# 부동산 급등 분석 웹 UI

이 웹 애플리케이션은 `src/real_estate/backend/web_app.py`를 중심으로,
`src/real_estate/detectors/district.py`와 `src/real_estate/detectors/combined.py` 기능을 웹 인터페이스로 제공합니다.
`web_ui/app.py`는 호환 목적의 thin wrapper입니다.

## 기능

### 1. 전체 지역 급등 분석 (CombinedSurgeDetector)
- 서울 전체 지역의 급등 건물을 분석
- 상위 N% 건물 선별
- 지상층/지하층 통합 분석

### 2. 특정 지역 급등 분석 (DistrictSurgeDetector)
- 특정 동(district) 단위 분석
- 상위 N개 건물 선별
- 구/동 선택 인터페이스

## 설치 및 실행

실행 절차의 단일 기준 문서는 루트 `README.md`입니다.
이 문서는 웹 UI 기능/화면 관점 설명에 집중합니다.

### 표준 실행 명령 (요약)

```bash
cd apps/real-estate-project
python -m src.real_estate.cli serve-web --port 5001
```

환경변수 설정/검증, DB 초기화, 수집/분석 선행 절차는 루트 `README.md`를 따르세요.

### 브라우저에서 접속
포트는 기본 5001이며, 사용 중이면 자동으로 다음 사용 가능한 포트로 실행됩니다.

## 사용법

### 전체 지역 분석
1. 분석 기준 년월 설정
2. 상위 비율(%) 설정 (예: 1.0%)
3. 분석 기간 설정 (3, 6, 12개월)
4. "전체 지역 분석 시작" 버튼 클릭

### 특정 지역 분석
1. 분석 기준 년월 설정
2. 구 선택 (서울 10개 구)
3. 동 선택 (선택한 구의 동 목록)
4. 상위 개수 설정 (1-10개)
5. 분석 기간 설정 (3, 6, 12개월)
6. "특정 지역 분석 시작" 버튼 클릭

## 결과 해석

### 컬럼 설명
- **순위**: 급등 점수 기준 순위
- **법정동코드**: 행정구역 코드
- **동이름**: 해당 동 이름
- **지번**: 건물 지번
- **건축년도**: 건물 건축 연도
- **건물명**: 연립다세대 명칭
- **급등점수**: 상승률 기반 점수(%)
- **신뢰도**: 분석 기간 내 총 거래 건수
- **최근거래월**: 가장 최근 거래 년월
- **평균거래금액**: 평균 거래 대금 (만원)
- **층유형**: 지상/지하 구분

## 주의사항

1. 분석에 필요한 테이블이 사전에 구축되어 있어야 합니다:
   - `building_transaction_analysis_above_ground`
   - `building_transaction_analysis_below_ground`

2. 데이터베이스 연결이 정상적으로 설정되어야 합니다.

3. 분석 시간이 오래 걸릴 수 있으므로 로딩 인디케이터를 확인하세요.

## 파일 구조

```
web_ui/
├── app.py                  # 호환용 wrapper
├── requirements.txt        # Python 패키지 의존성
├── README.md               # 사용 설명서
├── templates/
│   ├── index_console.html       # 메인 분석 페이지 (기본 라우트 /, 별칭 /v2)
│   ├── building_detail.html     # 건물 상세 페이지
│   ├── partials/
│   │   ├── combined_form.html   # 서울 전체 분석 폼
│   │   ├── district_form.html   # 특정 지역 분석 폼
│   │   └── shared_script.html   # 공통 JS (지도, API, 자동 분석 등)
│   └── deprecated/
│       ├── index_v2.html        # 이전 메인 화면 (deprecated, 라우트 미연결)
│       └── README.md
└── static/                 # CSS, JS 파일 (현재 CDN 사용)
```
