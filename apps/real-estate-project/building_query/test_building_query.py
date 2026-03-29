#!/usr/bin/env python3
"""
BuildingTransactionQuery 테스트 스크립트

다양한 조건으로 건물 거래 내역 조회 기능을 테스트합니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from building_transaction_query import BuildingTransactionQuery
import pandas as pd
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from project_config import get_db_config

# 데이터베이스 연결 정보
DB_CONFIG = get_db_config()

def test_basic_query():
    """기본 쿼리 테스트"""
    print("="*60)
    print("테스트 1: 기본 건물 거래 내역 조회 (전체 기간)")
    print("="*60)
    
    query = BuildingTransactionQuery(DB_CONFIG)
    
    # 서초구 반포동의 특정 건물 조회
    result = query.get_building_transactions(
        sgg_cd='11650',
        umd_nm='반포동', 
        jibun='728-33',
        build_year=1992
    )
    
    if not result.empty:
        print(f"✅ 조회 성공: 총 {len(result)}건")
        print("\n[첫 번째 거래 내역]")
        first_row = result.iloc[0]
        print(f"  - 거래일: {first_row['dealYear']}-{first_row['dealMonth']:02d}-{first_row['dealDay']:02d}")
        print(f"  - 거래금액: {first_row['dealAmount']:,}만원")
        print(f"  - 층: {first_row['floor']}층")
        print(f"  - 평당가: {first_row['price_per_pyeong']:,.2f}만원")
        
        print(f"\n[마지막 거래 내역]")
        last_row = result.iloc[-1]
        print(f"  - 거래일: {last_row['dealYear']}-{last_row['dealMonth']:02d}-{last_row['dealDay']:02d}")
        print(f"  - 거래금액: {last_row['dealAmount']:,}만원") 
        print(f"  - 층: {last_row['floor']}층")
        print(f"  - 평당가: {last_row['price_per_pyeong']:,.2f}만원")
    else:
        print("❌ 조회 결과 없음")
    
    return result

def test_date_filtering():
    """날짜 필터링 테스트"""
    print("\n" + "="*60)
    print("테스트 2: 날짜 필터링 테스트")
    print("="*60)
    
    query = BuildingTransactionQuery(DB_CONFIG)
    
    # 2019년 거래만 조회
    print("\n[2019년 거래 내역만 조회]")
    result_2019 = query.get_building_transactions(
        sgg_cd='11650',
        umd_nm='반포동',
        jibun='728-33', 
        build_year=1992,
        start_date='2019-01-01',
        end_date='2019-12-31'
    )
    
    if not result_2019.empty:
        print(f"✅ 2019년 거래: {len(result_2019)}건")
        for _, row in result_2019.iterrows():
            print(f"  - {row['dealYear']}-{row['dealMonth']:02d}-{row['dealDay']:02d}: {row['dealAmount']:,}만원 ({row['floor']}층)")
    else:
        print("❌ 2019년 거래 내역 없음")
    
    # 2020년 이후 거래만 조회  
    print("\n[2020년 이후 거래 내역 조회]")
    result_2020_after = query.get_building_transactions(
        sgg_cd='11650',
        umd_nm='반포동',
        jibun='728-33',
        build_year=1992,
        start_date='2020-01-01'
    )
    
    if not result_2020_after.empty:
        print(f"✅ 2020년 이후 거래: {len(result_2020_after)}건")
        for _, row in result_2020_after.iterrows():
            print(f"  - {row['dealYear']}-{row['dealMonth']:02d}-{row['dealDay']:02d}: {row['dealAmount']:,}만원 ({row['floor']}층)")
    else:
        print("❌ 2020년 이후 거래 내역 없음")

def test_summary_function():
    """요약 정보 테스트"""
    print("\n" + "="*60)
    print("테스트 3: 건물 요약 정보 조회")
    print("="*60)
    
    query = BuildingTransactionQuery(DB_CONFIG)
    
    summary = query.get_building_summary(
        sgg_cd='11650',
        umd_nm='반포동', 
        jibun='728-33',
        build_year=1992
    )
    
    if summary['total_transactions'] > 0:
        print("✅ 요약 정보 조회 성공")
        print(f"\n[건물 정보]")
        info = summary['building_info']
        print(f"  - 법정동코드: {info['sgg_cd']}")
        print(f"  - 동이름: {info['umd_nm']}")
        print(f"  - 지번: {info['jibun']}")
        print(f"  - 건축년도: {info['build_year']}")
        print(f"  - 건물명: {info['mhouse_nm']}")
        
        print(f"\n[거래 통계]")
        print(f"  - 총 거래 건수: {summary['total_transactions']}건")
        print(f"  - 거래 기간: {summary['date_range']['first_transaction']} ~ {summary['date_range']['last_transaction']}")
        
        amount_stats = summary['deal_amount_stats']
        print(f"\n[거래금액 통계 (만원)]")
        print(f"  - 최소: {amount_stats['min']:,}")
        print(f"  - 최대: {amount_stats['max']:,}")
        print(f"  - 평균: {amount_stats['avg']:,}")
        print(f"  - 중간값: {amount_stats['median']:,}")
        
        print(f"\n[층별 정보]")
        print(f"  - 거래된 층: {summary['floor_info']['floors']}")
        print(f"  - 층 종류: {summary['floor_info']['floor_count']}개")
        
        price_stats = summary['price_per_pyeong_stats']
        print(f"\n[평당가 통계 (만원)]")
        print(f"  - 최소: {price_stats['min']:,.2f}")
        print(f"  - 최대: {price_stats['max']:,.2f}")
        print(f"  - 평균: {price_stats['avg']:,.2f}")
    else:
        print("❌ 요약 정보 없음")

def test_different_buildings():
    """다른 건물들 테스트"""
    print("\n" + "="*60)
    print("테스트 4: 다양한 건물 조회 테스트")
    print("="*60)
    
    query = BuildingTransactionQuery(DB_CONFIG)
    
    # 테스트할 건물들 (CLAUDE.md의 샘플 데이터 기준)
    test_buildings = [
        {'sgg_cd': '11650', 'umd_nm': '방배동', 'jibun': '539-16', 'build_year': 1989, 'description': '서초구 방배동 금강하이츠빌라'},
        {'sgg_cd': '11650', 'umd_nm': '방배동', 'jibun': '593-50', 'build_year': 2015, 'description': '서초구 방배동 지안'},
        {'sgg_cd': '11170', 'umd_nm': '청파동2가', 'jibun': '1-1', 'build_year': 1991, 'description': '용산구 청파동2가'},
    ]
    
    for building in test_buildings:
        print(f"\n[{building['description']} 조회]")
        result = query.get_building_transactions(
            sgg_cd=building['sgg_cd'],
            umd_nm=building['umd_nm'],
            jibun=building['jibun'],
            build_year=building['build_year']
        )
        
        if not result.empty:
            print(f"✅ 조회 성공: {len(result)}건")
            
            # 최근 거래 1건 출력
            latest = result.iloc[-1]
            print(f"  - 최근 거래: {latest['dealYear']}-{latest['dealMonth']:02d}-{latest['dealDay']:02d}")
            print(f"  - 거래금액: {latest['dealAmount']:,}만원")
            print(f"  - 층: {latest['floor']}층")
        else:
            print("❌ 거래 내역 없음")

def test_error_cases():
    """에러 케이스 테스트"""
    print("\n" + "="*60)
    print("테스트 5: 에러 케이스 테스트")
    print("="*60)
    
    query = BuildingTransactionQuery(DB_CONFIG)
    
    # 존재하지 않는 건물
    print("\n[존재하지 않는 건물 조회]")
    result = query.get_building_transactions(
        sgg_cd='99999',
        umd_nm='존재하지않는동',
        jibun='999-999', 
        build_year=2099
    )
    print(f"결과: {len(result)}건 (예상: 0건)")
    
    # 잘못된 날짜 형식
    print("\n[잘못된 날짜 형식 테스트]")
    try:
        result = query.get_building_transactions(
            sgg_cd='11650',
            umd_nm='반포동',
            jibun='728-33',
            build_year=1992,
            start_date='2019/01/01'  # 잘못된 형식
        )
        print(f"❌ 예외가 발생해야 하는데 성공함")
    except Exception as e:
        print(f"✅ 예상된 예외 발생: 날짜 형식 오류")

def run_all_tests():
    """모든 테스트 실행"""
    print("🏠 BuildingTransactionQuery 테스트 시작")
    print("Current Time:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    try:
        # 각 테스트 실행
        result1 = test_basic_query()
        test_date_filtering()
        test_summary_function() 
        test_different_buildings()
        test_error_cases()
        
        print("\n" + "="*60)
        print("🎉 모든 테스트 완료!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()