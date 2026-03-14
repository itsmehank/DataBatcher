#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pykrx 고급 기능 테스트: 거래대금, 수정주가

목적:
    1. 거래대금 조회 API 사용법 확인
    2. adjusted 옵션으로 수정주가 동작 검증
    3. FDR과 비교하여 차이 분석
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    import pandas as pd
except ImportError:
    print("❌ Error: pandas not installed")
    sys.exit(1)

try:
    import FinanceDataReader as fdr
except ImportError:
    print("❌ Error: FinanceDataReader not installed")
    sys.exit(1)

try:
    from pykrx import stock
except ImportError:
    print("❌ Error: pykrx not installed")
    sys.exit(1)


# 테스트 설정
TEST_SYMBOL = "005930"  # 삼성전자
TEST_NAME = "삼성전자"
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=60)  # 약 2개월
START_STR = START_DATE.strftime('%Y%m%d')
END_STR = END_DATE.strftime('%Y%m%d')
START_FDR = START_DATE.strftime('%Y-%m-%d')
END_FDR = END_DATE.strftime('%Y-%m-%d')


def print_header(title: str):
    """출력 헤더"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def test_trading_value():
    """
    테스트 1: 거래대금 조회

    pykrx에는 여러 거래대금 관련 API가 있음:
    - get_market_trading_value_by_date: 날짜별 거래대금
    - get_market_trading_value_by_ticker: 종목별 거래대금
    - get_market_trading_value_and_volume_by_ticker: 거래대금+거래량
    """
    print_header("테스트 1: 거래대금 조회")

    print(f"\n종목: {TEST_SYMBOL} ({TEST_NAME})")
    print(f"기간: {START_STR} ~ {END_STR}\n")

    # -------------------------------------------------------------------------
    # 방법 1: get_market_ohlcv와 별도로 조회하는 방식
    # -------------------------------------------------------------------------
    print("=" * 80)
    print("방법 1: OHLCV + 거래대금 별도 조회")
    print("=" * 80)

    try:
        # OHLCV 조회
        ohlcv_df = stock.get_market_ohlcv(START_STR, END_STR, TEST_SYMBOL)
        print(f"\n✅ OHLCV 조회 성공: {len(ohlcv_df)}행")
        print(f"   컬럼: {list(ohlcv_df.columns)}")
        print(f"\n   샘플 데이터 (최근 3일):")
        print(ohlcv_df.tail(3))

        # 거래대금 조회 시도 1: get_market_trading_value_by_date
        print("\n" + "-" * 80)
        print("시도 1: get_market_trading_value_by_date()")
        print("-" * 80)
        try:
            # 이 함수는 특정 날짜의 전체 종목 거래대금을 반환
            # 특정 종목만 필터링 필요
            value_df = stock.get_market_trading_value_by_date(START_STR, END_STR, TEST_SYMBOL)
            print(f"✅ 성공: {len(value_df)}행")
            print(f"   컬럼: {list(value_df.columns)}")
            print(f"\n   샘플 데이터 (최근 3일):")
            print(value_df.tail(3))
        except Exception as e:
            print(f"❌ 실패: {e}")

        # 거래대금 조회 시도 2: get_market_cap (시가총액과 함께 제공)
        print("\n" + "-" * 80)
        print("시도 2: get_market_cap() - 시가총액과 함께 거래대금 제공")
        print("-" * 80)
        try:
            cap_df = stock.get_market_cap(END_STR, market="KOSPI")
            # 삼성전자 필터링
            if TEST_SYMBOL in cap_df.index:
                samsung = cap_df.loc[TEST_SYMBOL]
                print(f"✅ 성공")
                print(f"   컬럼: {list(cap_df.columns)}")
                print(f"\n   삼성전자 데이터:")
                print(samsung)
            else:
                print(f"❌ {TEST_SYMBOL} 종목 미발견")
        except Exception as e:
            print(f"❌ 실패: {e}")

    except Exception as e:
        print(f"❌ OHLCV 조회 실패: {e}")

    # -------------------------------------------------------------------------
    # 방법 2: OHLCV에 거래대금이 포함되는지 재확인
    # -------------------------------------------------------------------------
    print("\n\n" + "=" * 80)
    print("방법 2: OHLCV에 거래대금이 포함되는지 확인")
    print("=" * 80)

    try:
        # 다양한 파라미터로 시도
        print("\n시도 1: 기본 OHLCV")
        df1 = stock.get_market_ohlcv(START_STR, END_STR, TEST_SYMBOL)
        print(f"   컬럼: {list(df1.columns)}")

        print("\nシ도 2: freq='d' 명시")
        df2 = stock.get_market_ohlcv(START_STR, END_STR, TEST_SYMBOL, freq='d')
        print(f"   컬럼: {list(df2.columns)}")

        print("\n시도 3: adjusted=True")
        df3 = stock.get_market_ohlcv(START_STR, END_STR, TEST_SYMBOL, adjusted=True)
        print(f"   컬럼: {list(df3.columns)}")

        # 거래대금 포함 여부
        has_value = '거래대금' in df1.columns
        print(f"\n결론: OHLCV에 거래대금 포함? {'✅ YES' if has_value else '❌ NO'}")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


def test_adjusted_price():
    """
    테스트 2: 수정주가 (adjusted 옵션)

    pykrx의 adjusted 파라미터:
    - True: 수정주가 (액면분할, 배당 등 반영)
    - False: 비수정주가 (원본 가격)
    """
    print_header("테스트 2: 수정주가 (adjusted 옵션)")

    print(f"\n종목: {TEST_SYMBOL} ({TEST_NAME})")
    print(f"기간: {START_STR} ~ {END_STR}\n")

    # -------------------------------------------------------------------------
    # pykrx: adjusted=True vs adjusted=False
    # -------------------------------------------------------------------------
    print("=" * 80)
    print("pykrx: adjusted=True vs adjusted=False")
    print("=" * 80)

    try:
        # adjusted=False (비수정주가)
        print("\n1. adjusted=False (비수정주가)")
        df_unadj = stock.get_market_ohlcv(START_STR, END_STR, TEST_SYMBOL, adjusted=False)
        print(f"   ✅ 조회 성공: {len(df_unadj)}행")
        print(f"\n   최근 5일 종가:")
        print(df_unadj['종가'].tail(5))

        # adjusted=True (수정주가)
        print("\n2. adjusted=True (수정주가)")
        df_adj = stock.get_market_ohlcv(START_STR, END_STR, TEST_SYMBOL, adjusted=True)
        print(f"   ✅ 조회 성공: {len(df_adj)}행")
        print(f"\n   최근 5일 종가:")
        print(df_adj['종가'].tail(5))

        # 차이 계산
        print("\n" + "-" * 80)
        print("비수정주가 vs 수정주가 차이")
        print("-" * 80)

        # 공통 날짜로 정렬
        common_dates = df_unadj.index.intersection(df_adj.index)
        if len(common_dates) > 0:
            diff = df_adj.loc[common_dates, '종가'] - df_unadj.loc[common_dates, '종가']
            diff_pct = (diff / df_unadj.loc[common_dates, '종가'] * 100).abs()

            print(f"\n   공통 날짜 수: {len(common_dates)}")
            print(f"   평균 차이: {diff.mean():.2f}원")
            print(f"   최대 차이: {diff.max():.2f}원")
            print(f"   평균 차이율: {diff_pct.mean():.4f}%")
            print(f"   최대 차이율: {diff_pct.max():.4f}%")

            if diff.abs().max() < 1:
                print("\n   💡 결론: 수정주가와 비수정주가가 거의 동일")
                print("           → 최근 기간에 액면분할/배당 등 이벤트 없음")
            else:
                print("\n   💡 결론: 수정주가와 비수정주가에 차이 있음")
                print("           → 액면분할/배당 등 이벤트 반영됨")

            # 차이가 있는 날짜 샘플
            if diff.abs().max() >= 1:
                print("\n   차이가 큰 날짜 샘플 (상위 5개):")
                top_diff = diff.abs().nlargest(5)
                for date, val in top_diff.items():
                    unadj_price = df_unadj.loc[date, '종가']
                    adj_price = df_adj.loc[date, '종가']
                    print(f"      {date.date()}: 비수정={unadj_price:,}원, 수정={adj_price:,}원, 차이={val:.2f}원")
        else:
            print("   ❌ 공통 날짜 없음")

    except Exception as e:
        print(f"❌ pykrx 조회 실패: {e}")
        import traceback
        traceback.print_exc()

    # -------------------------------------------------------------------------
    # FDR과 비교
    # -------------------------------------------------------------------------
    print("\n\n" + "=" * 80)
    print("FDR vs pykrx 수정주가 비교")
    print("=" * 80)

    try:
        # FDR 조회
        print("\n1. FDR 조회")
        fdr_df = fdr.DataReader(TEST_SYMBOL, start=START_FDR, end=END_FDR)
        print(f"   ✅ 조회 성공: {len(fdr_df)}행")
        print(f"   컬럼: {list(fdr_df.columns)}")

        # Adj Close 존재 여부 확인
        has_adj_close = 'Adj Close' in fdr_df.columns
        print(f"   Adj Close 존재? {'✅ YES' if has_adj_close else '❌ NO'}")

        if has_adj_close:
            print(f"\n   Close vs Adj Close 비교:")
            print(f"   Close 최근 5일:")
            print(fdr_df['Close'].tail(5))
            print(f"\n   Adj Close 최근 5일:")
            print(fdr_df['Adj Close'].tail(5))

            # 차이 계산
            diff_fdr = (fdr_df['Adj Close'] - fdr_df['Close']).abs()
            print(f"\n   평균 차이: {diff_fdr.mean():.2f}원")
            print(f"   최대 차이: {diff_fdr.max():.2f}원")

        # pykrx adjusted=True와 비교
        print("\n2. FDR Close vs pykrx adjusted=True")
        pykrx_adj_df = stock.get_market_ohlcv(START_STR, END_STR, TEST_SYMBOL, adjusted=True)

        # 인덱스를 날짜로 변환하여 비교
        fdr_df.index = pd.to_datetime(fdr_df.index)
        common_dates = fdr_df.index.intersection(pykrx_adj_df.index)

        if len(common_dates) > 5:
            fdr_close = fdr_df.loc[common_dates, 'Close']
            pykrx_close = pykrx_adj_df.loc[common_dates, '종가']

            diff = (fdr_close - pykrx_close).abs()
            diff_pct = (diff / fdr_close * 100)

            print(f"   공통 날짜 수: {len(common_dates)}")
            print(f"   평균 차이: {diff.mean():.2f}원")
            print(f"   최대 차이: {diff.max():.2f}원")
            print(f"   평균 차이율: {diff_pct.mean():.4f}%")
            print(f"   최대 차이율: {diff_pct.max():.4f}%")

            if diff_pct.max() < 0.1:
                print("\n   ✅ 결론: FDR과 pykrx의 종가가 거의 일치 (0.1% 미만 차이)")
            elif diff_pct.max() < 1.0:
                print("\n   ⚠️  결론: FDR과 pykrx의 종가에 소폭 차이 (0.1~1% 차이)")
            else:
                print("\n   ❌ 결론: FDR과 pykrx의 종가에 유의미한 차이 (1% 이상)")

            # 샘플 출력
            print("\n   최근 5일 비교:")
            comparison = pd.DataFrame({
                'FDR_Close': fdr_close,
                'pykrx_종가': pykrx_close,
                '차이': diff,
                '차이율(%)': diff_pct
            })
            print(comparison.tail(5).to_string())
        else:
            print(f"   ❌ 공통 날짜 부족: {len(common_dates)}개")

    except Exception as e:
        print(f"❌ 비교 실패: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("=" * 80)
    print("pykrx 고급 기능 테스트")
    print("=" * 80)
    print(f"대상 종목: {TEST_SYMBOL} ({TEST_NAME})")
    print(f"테스트 기간: {START_FDR} ~ {END_FDR}")
    print("=" * 80)

    # 테스트 1: 거래대금
    test_trading_value()

    # 테스트 2: 수정주가
    test_adjusted_price()

    print("\n\n" + "=" * 80)
    print("✅ 모든 테스트 완료")
    print("=" * 80)
    print("\n결과 요약:")
    print("1. 거래대금: 별도 API 사용법 확인 완료")
    print("2. 수정주가: adjusted 옵션 동작 확인 완료")
    print("3. FDR 비교: 데이터 일치도 검증 완료")


if __name__ == "__main__":
    main()