# BuildingTransactionQuery

특정 건물의 거래 내역을 조회하는 Python 모듈입니다.

## 기능

### 주요 기능
- 법정동 코드, 동이름, 지번, 건축년도로 특정 건물의 거래 내역 조회
- 선택적 날짜 범위 필터링 (시작/끝 날짜)
- 거래 내역 요약 통계 제공

### 클래스: BuildingTransactionQuery

#### 초기화
```python
from building_transaction_query import BuildingTransactionQuery

# 데이터베이스 설정
db_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '1234', 
    'database': 'real_estate'
}

query = BuildingTransactionQuery(db_config)
```

#### 주요 메서드

##### 1. get_building_transactions()
특정 건물의 거래 내역을 DataFrame으로 반환합니다.

**필수 매개변수:**
- `sgg_cd` (str): 법정동 코드 (예: '11650')
- `umd_nm` (str): 동 이름 (예: '반포동')
- `jibun` (str): 지번 (예: '728-33')
- `build_year` (int): 건축년도 (예: 1992)

**선택 매개변수:**
- `start_date` (str, optional): 시작 날짜 'YYYY-MM-DD' (기본값: '1990-01-01')
- `end_date` (str, optional): 끝 날짜 'YYYY-MM-DD' (기본값: 현재 날짜)

```python
# 전체 거래 내역 조회
result = query.get_building_transactions('11650', '반포동', '728-33', 1992)

# 2019년 거래만 조회
result_2019 = query.get_building_transactions(
    '11650', '반포동', '728-33', 1992,
    start_date='2019-01-01', 
    end_date='2019-12-31'
)

# 2020년 이후 거래만 조회
result_after_2020 = query.get_building_transactions(
    '11650', '반포동', '728-33', 1992,
    start_date='2020-01-01'
)
```

##### 2. get_building_summary()
건물의 거래 요약 정보를 딕셔너리로 반환합니다.

```python
summary = query.get_building_summary('11650', '반포동', '728-33', 1992)

# 결과 예시
{
    'building_info': {
        'sgg_cd': '11650',
        'umd_nm': '반포동',
        'jibun': '728-33',
        'build_year': 1992,
        'mhouse_nm': '(728-33)'
    },
    'total_transactions': 38,
    'date_range': {
        'first_transaction': '2007-04-18',
        'last_transaction': '2025-03-01'
    },
    'deal_amount_stats': {
        'min': 7000,
        'max': 34500,
        'avg': 15529,
        'median': 14050
    },
    'floor_info': {
        'floors': [-1, 1, 2, 3],
        'floor_count': 4
    },
    'price_per_pyeong_stats': {
        'min': 966.20,
        'max': 4429.13,
        'avg': 1806.20
    }
}
```

## 반환 데이터 구조

### DataFrame 컬럼
- `id`: 레코드 ID
- `sggCd`: 법정동 코드
- `umdNm`: 동 이름  
- `mhouseNm`: 건물명
- `jibun`: 지번
- `buildYear`: 건축년도
- `excluUseAr`: 전용면적(㎡)
- `landAr`: 대지권면적(㎡)
- `dealYear`, `dealMonth`, `dealDay`: 거래일
- `dealAmount`: 거래금액(만원)
- `floor`: 층수 (양수=지상, 음수=지하)
- `price_per_pyeong`: 전용면적 평당가(만원)
- `land_price_per_pyeong`: 대지권 평당가(만원)
- `land_share_ratio`: 대지권비율

## 사용 예시

### 기본 사용법
```python
from building_transaction_query import BuildingTransactionQuery

# 데이터베이스 연결 설정
db_config = {
    'host': 'localhost',
    'port': 3306, 
    'user': 'root',
    'password': '1234',
    'database': 'real_estate'
}

# 쿼리 객체 생성
query = BuildingTransactionQuery(db_config)

# 특정 건물의 모든 거래 내역 조회
transactions = query.get_building_transactions('11650', '반포동', '728-33', 1992)

print(f"총 {len(transactions)}건의 거래가 있습니다.")

if not transactions.empty:
    # 최근 거래 정보 출력
    latest = transactions.iloc[-1]
    print(f"최근 거래: {latest['dealYear']}-{latest['dealMonth']:02d}-{latest['dealDay']:02d}")
    print(f"거래금액: {latest['dealAmount']:,}만원")
    print(f"층: {latest['floor']}층")
```

### 날짜 필터링 사용법
```python
# 특정 연도 거래만 조회
transactions_2019 = query.get_building_transactions(
    '11650', '반포동', '728-33', 1992,
    start_date='2019-01-01',
    end_date='2019-12-31'
)

# 특정 날짜 이후 거래만 조회
recent_transactions = query.get_building_transactions(
    '11650', '반포동', '728-33', 1992,
    start_date='2020-01-01'
)

# 특정 날짜 이전 거래만 조회  
old_transactions = query.get_building_transactions(
    '11650', '반포동', '728-33', 1992,
    end_date='2018-12-31'
)
```

### 요약 정보 활용법
```python
# 건물 거래 요약 정보 조회
summary = query.get_building_summary('11650', '반포동', '728-33', 1992)

if summary['total_transactions'] > 0:
    print(f"건물명: {summary['building_info']['mhouse_nm']}")
    print(f"총 거래 건수: {summary['total_transactions']}건")
    print(f"거래 기간: {summary['date_range']['first_transaction']} ~ {summary['date_range']['last_transaction']}")
    print(f"평균 거래금액: {summary['deal_amount_stats']['avg']:,}만원")
    print(f"거래된 층: {summary['floor_info']['floors']}")
```

## 테스트

포함된 테스트 스크립트로 기능을 검증할 수 있습니다:

```bash
cd building_query
python test_building_query.py
```

### 테스트 케이스
1. 기본 건물 거래 내역 조회
2. 날짜 필터링 테스트  
3. 요약 정보 기능 테스트
4. 다양한 건물 조회 테스트
5. 에러 케이스 처리 테스트

## 에러 처리

- **날짜 형식 오류**: 'YYYY-MM-DD' 형식이 아닌 경우 ValueError 발생
- **데이터베이스 연결 실패**: 연결 정보가 잘못된 경우 빈 DataFrame 반환
- **조건에 맞는 데이터 없음**: 빈 DataFrame 반환 및 안내 메시지 출력

## 주의사항

- 날짜는 반드시 'YYYY-MM-DD' 형식으로 입력해야 합니다
- start_date와 end_date를 모두 입력하지 않으면 전체 기간 조회됩니다
- 데이터베이스 연결 정보가 정확해야 정상 작동합니다