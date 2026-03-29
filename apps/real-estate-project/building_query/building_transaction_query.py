#!/usr/bin/env python3
"""
BuildingTransactionQuery - 특정 건물의 거래 내역 조회 모듈

법정동 코드, 동이름, 지번, 건축년도를 이용해 특정 건물의 거래 내역을 조회하고,
선택적으로 시작/끝 시점을 지정하여 기간별 필터링을 수행하는 기능을 제공합니다.
"""

import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime, date
from typing import Optional, Dict, List, Any


class BuildingTransactionQuery:
    """특정 건물의 거래 내역 조회 클래스"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        BuildingTransactionQuery 초기화
        
        Args:
            db_config (Dict[str, Any]): 데이터베이스 연결 정보
        """
        self.db_config = db_config
        
    def _get_db_connection(self):
        """데이터베이스 연결 생성"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Error as e:
            print(f"데이터베이스 연결 실패: {e}")
            return None
    
    def _parse_date_string(self, date_str: str) -> tuple:
        """
        날짜 문자열을 파싱하여 (year, month, day) 튜플 반환
        
        Args:
            date_str (str): 'YYYY-MM-DD' 형식의 날짜 문자열
            
        Returns:
            tuple: (year, month, day)
        """
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
            return parsed_date.year, parsed_date.month, parsed_date.day
        except ValueError:
            raise ValueError(f"날짜 형식이 올바르지 않습니다. 'YYYY-MM-DD' 형식을 사용하세요: {date_str}")
    
    def _build_date_condition(self, start_date: Optional[str], end_date: Optional[str]) -> tuple:
        """
        날짜 조건 SQL과 파라미터를 생성
        
        Args:
            start_date (Optional[str]): 시작 날짜 ('YYYY-MM-DD')
            end_date (Optional[str]): 끝 날짜 ('YYYY-MM-DD')
            
        Returns:
            tuple: (date_condition_sql, date_params)
        """
        date_conditions = []
        date_params = []
        
        # 시작 시점과 끝 시점이 모두 None인 경우 날짜 조건 없음
        if start_date is None and end_date is None:
            return "", []
        
        # 시작 시점 처리 (기본값: 1990-01-01)
        if start_date is None:
            start_year, start_month, start_day = 1990, 1, 1
        else:
            start_year, start_month, start_day = self._parse_date_string(start_date)
        
        # 끝 시점 처리 (기본값: 현재 날짜)
        if end_date is None:
            today = date.today()
            end_year, end_month, end_day = today.year, today.month, today.day
        else:
            end_year, end_month, end_day = self._parse_date_string(end_date)
        
        # SQL 날짜 조건 생성
        date_conditions.append("""
            (dealYear > %s OR 
             (dealYear = %s AND dealMonth > %s) OR 
             (dealYear = %s AND dealMonth = %s AND dealDay >= %s))
        """)
        date_params.extend([start_year, start_year, start_month, start_year, start_month, start_day])
        
        date_conditions.append("""
            (dealYear < %s OR 
             (dealYear = %s AND dealMonth < %s) OR 
             (dealYear = %s AND dealMonth = %s AND dealDay <= %s))
        """)
        date_params.extend([end_year, end_year, end_month, end_year, end_month, end_day])
        
        date_condition_sql = " AND " + " AND ".join(date_conditions)
        return date_condition_sql, date_params
    
    def get_building_transactions(self, 
                                  sgg_cd: str, 
                                  umd_nm: str, 
                                  jibun: str, 
                                  build_year: int,
                                  start_date: Optional[str] = None,
                                  end_date: Optional[str] = None) -> pd.DataFrame:
        """
        특정 건물의 거래 내역 조회
        
        Args:
            sgg_cd (str): 법정동 코드 (예: '11650')
            umd_nm (str): 동 이름 (예: '반포동')
            jibun (str): 지번 (예: '728-33')
            build_year (int): 건축년도 (예: 1992)
            start_date (Optional[str]): 시작 날짜 'YYYY-MM-DD' (기본값: 1990-01-01)
            end_date (Optional[str]): 끝 날짜 'YYYY-MM-DD' (기본값: 현재 날짜)
            
        Returns:
            pd.DataFrame: 거래 내역 데이터프레임
        """
        
        connection = self._get_db_connection()
        if not connection:
            return pd.DataFrame()
        
        try:
            # 기본 쿼리
            base_query = """
                SELECT 
                    id, sggCd, umdNm, mhouseNm, jibun, buildYear,
                    excluUseAr, landAr, dealYear, dealMonth, dealDay,
                    dealAmount, floor, price_per_pyeong, land_price_per_pyeong,
                    land_share_ratio, dealingGbn, estateAgentSggNm, rgstDate,
                    slerGbn, buyerGbn
                FROM rh_trade_analysis
                WHERE sggCd = %s AND umdNm = %s AND jibun = %s AND buildYear = %s
            """
            
            # 기본 파라미터
            params = [sgg_cd, umd_nm, jibun, build_year]
            
            # 날짜 조건 추가
            date_condition, date_params = self._build_date_condition(start_date, end_date)
            full_query = base_query + date_condition + " ORDER BY dealYear, dealMonth, dealDay"
            params.extend(date_params)
            
            # 쿼리 실행
            cursor = connection.cursor()
            cursor.execute(full_query, params)
            
            # 컬럼명 가져오기
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            
            # DataFrame 생성
            df = pd.DataFrame(data, columns=columns)
            
            if df.empty:
                print(f"조건에 맞는 거래 내역이 없습니다:")
                print(f"  - 법정동코드: {sgg_cd}")
                print(f"  - 동이름: {umd_nm}")
                print(f"  - 지번: {jibun}")
                print(f"  - 건축년도: {build_year}")
                if start_date or end_date:
                    start_display = start_date if start_date else "1990-01-01"
                    end_display = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
                    print(f"  - 기간: {start_display} ~ {end_display}")
            else:
                print(f"총 {len(df)}건의 거래 내역을 조회했습니다.")
                
            return df
            
        except Error as e:
            print(f"쿼리 실행 중 오류 발생: {e}")
            return pd.DataFrame()
        except ValueError as e:
            print(f"날짜 형식 오류: {e}")
            return pd.DataFrame()
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_building_summary(self, 
                           sgg_cd: str, 
                           umd_nm: str, 
                           jibun: str, 
                           build_year: int,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        특정 건물의 거래 요약 정보 조회
        
        Args:
            sgg_cd (str): 법정동 코드
            umd_nm (str): 동 이름  
            jibun (str): 지번
            build_year (int): 건축년도
            start_date (Optional[str]): 시작 날짜
            end_date (Optional[str]): 끝 날짜
            
        Returns:
            Dict[str, Any]: 거래 요약 정보
        """
        
        df = self.get_building_transactions(sgg_cd, umd_nm, jibun, build_year, start_date, end_date)
        
        if df.empty:
            return {
                'total_transactions': 0,
                'message': '거래 내역이 없습니다.'
            }
        
        # 요약 통계 계산
        summary = {
            'building_info': {
                'sgg_cd': sgg_cd,
                'umd_nm': umd_nm,
                'jibun': jibun,
                'build_year': build_year,
                'mhouse_nm': df['mhouseNm'].iloc[0] if not df.empty else None
            },
            'total_transactions': len(df),
            'date_range': {
                'first_transaction': f"{df['dealYear'].min()}-{df['dealMonth'].min():02d}-{df['dealDay'].min():02d}",
                'last_transaction': f"{df['dealYear'].max()}-{df['dealMonth'].max():02d}-{df['dealDay'].max():02d}"
            },
            'deal_amount_stats': {
                'min': int(df['dealAmount'].min()),
                'max': int(df['dealAmount'].max()),
                'avg': int(df['dealAmount'].mean()),
                'median': int(df['dealAmount'].median())
            },
            'floor_info': {
                'floors': sorted(df['floor'].unique().tolist()),
                'floor_count': len(df['floor'].unique())
            },
            'price_per_pyeong_stats': {
                'min': float(df['price_per_pyeong'].min()),
                'max': float(df['price_per_pyeong'].max()),
                'avg': float(df['price_per_pyeong'].mean())
            }
        }
        
        return summary


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from project_config import get_db_config
    # 테스트용 DB 연결 정보
    DB_CONFIG = get_db_config()
    
    # 간단한 테스트
    query = BuildingTransactionQuery(DB_CONFIG)
    
    # 테스트 케이스 1: 전체 거래 내역 조회
    print("=== 테스트 1: 전체 거래 내역 조회 ===")
    result1 = query.get_building_transactions('11650', '반포동', '728-33', 1992)
    print(f"조회 건수: {len(result1)}")
    
    # 테스트 케이스 2: 기간 필터링
    print("\n=== 테스트 2: 2019년 거래 내역만 조회 ===")
    result2 = query.get_building_transactions('11650', '반포동', '728-33', 1992, 
                                            start_date='2019-01-01', 
                                            end_date='2019-12-31')
    print(f"조회 건수: {len(result2)}")
    
    # 테스트 케이스 3: 요약 정보
    print("\n=== 테스트 3: 건물 요약 정보 ===")
    summary = query.get_building_summary('11650', '반포동', '728-33', 1992)
    print(f"총 거래 건수: {summary['total_transactions']}")
    if summary['total_transactions'] > 0:
        print(f"거래 기간: {summary['date_range']['first_transaction']} ~ {summary['date_range']['last_transaction']}")
        print(f"거래금액 범위: {summary['deal_amount_stats']['min']:,} ~ {summary['deal_amount_stats']['max']:,} 만원")