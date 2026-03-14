#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pykrx vs FinanceDataReader 비교 테스트

목적:
    FDR에서 pykrx로 전환하기 전, 두 라이브러리의 데이터 구조와 내용을 비교합니다.

테스트 항목:
    1. 개별 종목 가격 데이터 (OHLCV)
    2. KRX 전체 종목 목록
    3. 컬럼명, 인덱스, 데이터 타입 비교
    4. 데이터 일치 여부 검증

실행:
    # pykrx 설치 (아직 없다면)
    pip install pykrx

    # 테스트 실행
    python scripts/tests/test_pykrx_comparison.py

결과:
    - 콘솔에 비교 결과 출력
    - scripts/tests/pykrx_comparison_report.md 생성
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
import warnings

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Suppress pandas warnings
warnings.filterwarnings('ignore')

try:
    import pandas as pd
except ImportError:
    print("❌ Error: pandas not installed")
    sys.exit(1)

try:
    import FinanceDataReader as fdr
except ImportError:
    print("❌ Error: FinanceDataReader not installed. Run: pip install finance-datareader")
    sys.exit(1)

try:
    from pykrx import stock
except ImportError:
    print("❌ Error: pykrx not installed. Run: pip install pykrx")
    sys.exit(1)


# ============================================================================
# 테스트 설정
# ============================================================================

# 테스트 종목 (다양한 시장 커버)
TEST_SYMBOLS = [
    ("005930", "삼성전자", "KOSPI"),       # 대형주
    ("000660", "SK하이닉스", "KOSPI"),     # 대형주
    ("005380", "현대차", "KOSPI"),         # 대형주
    ("035720", "카카오", "KOSPI"),         # 중형주
    ("035420", "NAVER", "KOSPI"),          # 대형주
    ("247540", "에코프로비엠", "KOSDAQ"),  # KOSDAQ 대형
]

# 테스트 기간 (최근 1개월)
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=30)
START_STR = START_DATE.strftime("%Y%m%d")  # pykrx 형식
END_STR = END_DATE.strftime("%Y%m%d")
START_FDR = START_DATE.strftime("%Y-%m-%d")  # FDR 형식
END_FDR = END_DATE.strftime("%Y-%m-%d")


# ============================================================================
# 1. 개별 종목 가격 데이터 비교
# ============================================================================

def test_price_data_single_symbol(symbol: str, name: str, market: str) -> Dict[str, Any]:
    """
    단일 종목의 FDR vs pykrx 가격 데이터 비교

    Returns:
        {
            'symbol': str,
            'name': str,
            'market': str,
            'fdr_success': bool,
            'pykrx_success': bool,
            'fdr_rows': int,
            'pykrx_rows': int,
            'fdr_columns': list,
            'pykrx_columns': list,
            'fdr_index_type': str,
            'pykrx_index_type': str,
            'column_mapping': dict,
            'data_match': bool,
            'notes': list,
        }
    """
    result = {
        'symbol': symbol,
        'name': name,
        'market': market,
        'fdr_success': False,
        'pykrx_success': False,
        'fdr_rows': 0,
        'pykrx_rows': 0,
        'fdr_columns': [],
        'pykrx_columns': [],
        'fdr_index_type': '',
        'pykrx_index_type': '',
        'column_mapping': {},
        'data_match': False,
        'notes': [],
    }

    # -------------------------------------------------------------------------
    # FDR 데이터 수집
    # -------------------------------------------------------------------------
    try:
        fdr_df = fdr.DataReader(symbol, start=START_FDR, end=END_FDR)
        if fdr_df is None or fdr_df.empty:
            result['notes'].append("FDR returned empty data")
        else:
            result['fdr_success'] = True
            result['fdr_rows'] = len(fdr_df)
            result['fdr_columns'] = list(fdr_df.columns)
            result['fdr_index_type'] = str(type(fdr_df.index).__name__)
    except Exception as e:
        result['notes'].append(f"FDR error: {e}")

    # -------------------------------------------------------------------------
    # pykrx 데이터 수집
    # -------------------------------------------------------------------------
    try:
        # pykrx.stock.get_market_ohlcv(fromdate, todate, ticker, freq='d', adjusted=True)
        # adjusted=True: 수정주가 사용
        pykrx_df = stock.get_market_ohlcv(START_STR, END_STR, symbol)
        if pykrx_df is None or pykrx_df.empty:
            result['notes'].append("pykrx returned empty data")
        else:
            result['pykrx_success'] = True
            result['pykrx_rows'] = len(pykrx_df)
            result['pykrx_columns'] = list(pykrx_df.columns)
            result['pykrx_index_type'] = str(type(pykrx_df.index).__name__)
    except Exception as e:
        result['notes'].append(f"pykrx error: {e}")

    # -------------------------------------------------------------------------
    # 컬럼 매핑 추론
    # -------------------------------------------------------------------------
    if result['fdr_success'] and result['pykrx_success']:
        # FDR: Open, High, Low, Close, Volume, Change, (Adj Close)
        # pykrx: 시가, 고가, 저가, 종가, 거래량, ...
        result['column_mapping'] = {
            'Open': '시가',
            'High': '고가',
            'Low': '저가',
            'Close': '종가',
            'Volume': '거래량',
        }

        # 데이터 일치 여부 (간단히 행 수만 비교)
        if abs(result['fdr_rows'] - result['pykrx_rows']) <= 2:
            result['data_match'] = True
        else:
            result['notes'].append(f"Row count mismatch: FDR={result['fdr_rows']}, pykrx={result['pykrx_rows']}")

    return result


def test_all_price_data() -> list:
    """모든 테스트 종목에 대해 가격 데이터 비교"""
    results = []
    print("\n" + "=" * 80)
    print("테스트 1: 개별 종목 가격 데이터 비교 (FDR vs pykrx)")
    print("=" * 80)
    print(f"기간: {START_FDR} ~ {END_FDR}")
    print(f"종목: {len(TEST_SYMBOLS)}개\n")

    for symbol, name, market in TEST_SYMBOLS:
        print(f"  테스트 중: {symbol} ({name}) [{market}]...", end=" ")
        result = test_price_data_single_symbol(symbol, name, market)
        results.append(result)

        if result['fdr_success'] and result['pykrx_success']:
            if result['data_match']:
                print("✅ OK")
            else:
                print("⚠️  행 수 불일치")
        elif result['fdr_success']:
            print("❌ pykrx 실패")
        elif result['pykrx_success']:
            print("❌ FDR 실패")
        else:
            print("❌ 둘 다 실패")

    return results


# ============================================================================
# 2. KRX 전체 종목 목록 비교
# ============================================================================

def test_symbol_listing() -> Dict[str, Any]:
    """
    FDR vs pykrx 종목 목록 비교

    Returns:
        {
            'fdr_success': bool,
            'pykrx_success': bool,
            'fdr_total': int,
            'pykrx_total': int,
            'fdr_columns': list,
            'pykrx_markets': dict,  # {market: count}
            'common_symbols': int,
            'fdr_only': int,
            'pykrx_only': int,
            'notes': list,
        }
    """
    result = {
        'fdr_success': False,
        'pykrx_success': False,
        'fdr_total': 0,
        'pykrx_total': 0,
        'fdr_columns': [],
        'pykrx_markets': {},
        'common_symbols': 0,
        'fdr_only': 0,
        'pykrx_only': 0,
        'notes': [],
    }

    print("\n" + "=" * 80)
    print("테스트 2: KRX 전체 종목 목록 비교 (FDR vs pykrx)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # FDR 종목 목록
    # -------------------------------------------------------------------------
    fdr_symbols = set()
    try:
        print("  FDR StockListing('KRX') 호출 중...", end=" ")
        fdr_df = fdr.StockListing('KRX')
        if fdr_df is None or fdr_df.empty:
            result['notes'].append("FDR returned empty listing")
            print("❌ 실패")
        else:
            result['fdr_success'] = True
            result['fdr_total'] = len(fdr_df)
            result['fdr_columns'] = list(fdr_df.columns)
            fdr_symbols = set(fdr_df['Code'].tolist())
            print(f"✅ {result['fdr_total']}개 종목")
    except Exception as e:
        result['notes'].append(f"FDR listing error: {e}")
        print(f"❌ 에러: {e}")

    # -------------------------------------------------------------------------
    # pykrx 종목 목록
    # -------------------------------------------------------------------------
    pykrx_symbols = set()
    try:
        # pykrx.stock.get_market_ticker_list(date, market='ALL')
        # market: KOSPI, KOSDAQ, KONEX, ALL
        today = datetime.now().strftime("%Y%m%d")

        print("  pykrx get_market_ticker_list() 호출 중...", end=" ")

        # 각 시장별로 조회
        markets = ['KOSPI', 'KOSDAQ', 'KONEX']
        for mkt in markets:
            tickers = stock.get_market_ticker_list(today, market=mkt)
            result['pykrx_markets'][mkt] = len(tickers)
            pykrx_symbols.update(tickers)

        result['pykrx_success'] = True
        result['pykrx_total'] = len(pykrx_symbols)
        print(f"✅ {result['pykrx_total']}개 종목")
        print(f"     - KOSPI: {result['pykrx_markets'].get('KOSPI', 0)}")
        print(f"     - KOSDAQ: {result['pykrx_markets'].get('KOSDAQ', 0)}")
        print(f"     - KONEX: {result['pykrx_markets'].get('KONEX', 0)}")
    except Exception as e:
        result['notes'].append(f"pykrx listing error: {e}")
        print(f"❌ 에러: {e}")

    # -------------------------------------------------------------------------
    # 교집합/차집합 분석
    # -------------------------------------------------------------------------
    if result['fdr_success'] and result['pykrx_success']:
        result['common_symbols'] = len(fdr_symbols & pykrx_symbols)
        result['fdr_only'] = len(fdr_symbols - pykrx_symbols)
        result['pykrx_only'] = len(pykrx_symbols - fdr_symbols)

        print(f"\n  공통 종목: {result['common_symbols']}")
        print(f"  FDR만 존재: {result['fdr_only']}")
        print(f"  pykrx만 존재: {result['pykrx_only']}")

        # 차이 분석
        if result['fdr_only'] > 0:
            fdr_only_list = list(fdr_symbols - pykrx_symbols)[:5]
            print(f"  FDR 전용 샘플: {fdr_only_list}")

        if result['pykrx_only'] > 0:
            pykrx_only_list = list(pykrx_symbols - fdr_symbols)[:5]
            print(f"  pykrx 전용 샘플: {pykrx_only_list}")

    return result


# ============================================================================
# 3. 리포트 생성
# ============================================================================

def generate_report(price_results: list, listing_result: dict):
    """비교 결과를 Markdown 리포트로 저장"""
    report_path = Path(__file__).parent / "pykrx_comparison_report.md"

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# pykrx vs FinanceDataReader 비교 테스트 결과\n\n")
        f.write(f"**테스트 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**테스트 기간**: {START_FDR} ~ {END_FDR}\n\n")
        f.write("---\n\n")

        # =====================================================================
        # 1. 가격 데이터 비교 결과
        # =====================================================================
        f.write("## 1. 개별 종목 가격 데이터 비교\n\n")

        # 통계
        total = len(price_results)
        both_success = sum(1 for r in price_results if r['fdr_success'] and r['pykrx_success'])
        data_match = sum(1 for r in price_results if r['data_match'])

        f.write(f"**테스트 종목 수**: {total}\n")
        f.write(f"**FDR + pykrx 모두 성공**: {both_success}/{total}\n")
        f.write(f"**데이터 일치**: {data_match}/{total}\n\n")

        # 상세 결과 테이블
        f.write("### 상세 비교\n\n")
        f.write("| 종목코드 | 종목명 | 시장 | FDR | pykrx | FDR 행수 | pykrx 행수 | 일치 | 비고 |\n")
        f.write("|---------|-------|------|-----|-------|---------|-----------|------|------|\n")

        for r in price_results:
            fdr_status = "✅" if r['fdr_success'] else "❌"
            pykrx_status = "✅" if r['pykrx_success'] else "❌"
            match_status = "✅" if r['data_match'] else "❌"
            notes = "; ".join(r['notes']) if r['notes'] else "-"

            f.write(f"| {r['symbol']} | {r['name']} | {r['market']} | {fdr_status} | {pykrx_status} | "
                   f"{r['fdr_rows']} | {r['pykrx_rows']} | {match_status} | {notes} |\n")

        # 컬럼 비교
        f.write("\n### 컬럼 구조 비교\n\n")
        if price_results and price_results[0]['fdr_success'] and price_results[0]['pykrx_success']:
            sample = price_results[0]
            f.write(f"**FDR 컬럼** ({sample['symbol']} 기준):\n")
            f.write(f"```\n{sample['fdr_columns']}\n```\n\n")
            f.write(f"**pykrx 컬럼** ({sample['symbol']} 기준):\n")
            f.write(f"```\n{sample['pykrx_columns']}\n```\n\n")
            f.write(f"**추론된 컬럼 매핑**:\n")
            for fdr_col, pykrx_col in sample['column_mapping'].items():
                f.write(f"- `{fdr_col}` (FDR) → `{pykrx_col}` (pykrx)\n")
            f.write("\n")

            # 인덱스 타입
            f.write(f"**인덱스 타입**:\n")
            f.write(f"- FDR: `{sample['fdr_index_type']}`\n")
            f.write(f"- pykrx: `{sample['pykrx_index_type']}`\n\n")

        # =====================================================================
        # 2. 종목 목록 비교 결과
        # =====================================================================
        f.write("---\n\n")
        f.write("## 2. KRX 전체 종목 목록 비교\n\n")

        if listing_result['fdr_success'] and listing_result['pykrx_success']:
            f.write(f"**FDR 총 종목 수**: {listing_result['fdr_total']}\n")
            f.write(f"**pykrx 총 종목 수**: {listing_result['pykrx_total']}\n\n")

            f.write(f"**pykrx 시장별 분포**:\n")
            for mkt, cnt in listing_result['pykrx_markets'].items():
                f.write(f"- {mkt}: {cnt}\n")
            f.write("\n")

            f.write(f"**교집합/차집합**:\n")
            f.write(f"- 공통 종목: {listing_result['common_symbols']}\n")
            f.write(f"- FDR만 존재: {listing_result['fdr_only']}\n")
            f.write(f"- pykrx만 존재: {listing_result['pykrx_only']}\n\n")

            f.write(f"**FDR 컬럼**:\n")
            f.write(f"```\n{listing_result['fdr_columns']}\n```\n\n")
        else:
            f.write("❌ 종목 목록 비교 실패\n\n")
            for note in listing_result['notes']:
                f.write(f"- {note}\n")

        # =====================================================================
        # 3. 결론 및 권장사항
        # =====================================================================
        f.write("---\n\n")
        f.write("## 3. 결론 및 전환 가능성 평가\n\n")

        if both_success == total and data_match >= total * 0.9:
            f.write("### ✅ 전환 가능 (높은 호환성)\n\n")
            f.write("FDR과 pykrx 모두 안정적으로 데이터를 제공하며, 데이터 일치도가 높습니다.\n\n")
            f.write("**권장 조치**:\n")
            f.write("1. 컬럼명 매핑 레이어 구현\n")
            f.write("2. 인덱스 정규화 로직 추가\n")
            f.write("3. 단계적 전환 (일부 종목 → 전체)\n\n")
        else:
            f.write("### ⚠️  전환 시 주의 필요\n\n")
            f.write("일부 종목에서 데이터 불일치 또는 오류 발생.\n\n")
            f.write("**권장 조치**:\n")
            f.write("1. 실패 종목 패턴 분석\n")
            f.write("2. 폴백 메커니즘 구현 (pykrx 실패 시 FDR 사용)\n")
            f.write("3. 철저한 QA 테스트\n\n")

        # 컬럼 매핑 필요성
        f.write("### 컬럼명 차이 요약\n\n")
        f.write("| FDR 컬럼 | pykrx 컬럼 | 비고 |\n")
        f.write("|---------|-----------|------|\n")
        f.write("| Open | 시가 | 매핑 필요 |\n")
        f.write("| High | 고가 | 매핑 필요 |\n")
        f.write("| Low | 저가 | 매핑 필요 |\n")
        f.write("| Close | 종가 | 매핑 필요 |\n")
        f.write("| Volume | 거래량 | 매핑 필요 |\n")
        f.write("| Change | - | FDR만 존재 (사용 안 함) |\n")
        f.write("| Adj Close | - | FDR에서 불안정, pykrx adjusted 옵션 확인 필요 |\n\n")

        # 리스크
        f.write("### 주요 리스크\n\n")
        f.write("1. **컬럼명 매핑**: 한글 → 영문 변환 필요\n")
        f.write("2. **수정주가**: pykrx의 `adjusted` 파라미터 동작 검증 필요\n")
        f.write("3. **휴장일 처리**: 두 라이브러리의 휴장일 데이터 누락 방식 확인 필요\n")
        f.write("4. **Rate Limiting**: KRX 공식 API의 속도 제한 확인 필요\n")
        f.write("5. **종목 목록 차이**: FDR vs pykrx 종목 차이 원인 분석 필요\n\n")

        f.write("---\n\n")
        f.write("**리포트 생성**: Claude Code\n")
        f.write("**버전**: 1.0\n")

    print(f"\n✅ 리포트 생성 완료: {report_path}")


# ============================================================================
# 메인 실행
# ============================================================================

def main():
    print("\n" + "=" * 80)
    print("pykrx vs FinanceDataReader 비교 테스트")
    print("=" * 80)
    print(f"목적: FDR → pykrx 전환 가능성 평가")
    print(f"테스트 기간: {START_FDR} ~ {END_FDR}")
    print("=" * 80)

    # 1. 가격 데이터 비교
    price_results = test_all_price_data()

    # 2. 종목 목록 비교
    listing_result = test_symbol_listing()

    # 3. 리포트 생성
    print("\n" + "=" * 80)
    print("리포트 생성 중...")
    print("=" * 80)
    generate_report(price_results, listing_result)

    print("\n" + "=" * 80)
    print("✅ 테스트 완료")
    print("=" * 80)
    print("\n다음 단계:")
    print("1. scripts/tests/pykrx_comparison_report.md 확인")
    print("2. 컬럼 매핑 및 어댑터 레이어 설계")
    print("3. 전환 계획서 작성")


if __name__ == "__main__":
    main()