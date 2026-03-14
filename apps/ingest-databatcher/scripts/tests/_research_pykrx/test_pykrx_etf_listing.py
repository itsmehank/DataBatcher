#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/tests/test_pykrx_etf_listing.py

목적
- pykrx로 ETF 티커(종목코드) 목록을 가져올 수 있는지 확인
- 반환되는 데이터가 symbol_master에 넣기 위한 최소 컬럼 요구사항(symbol, Name, Market)을 충족하는지 점검

주의
- 이 파일은 "제품 코드" 변경 없이, pykrx API 가능 여부/데이터 형태를 확인하기 위한 테스트 스크립트입니다.
- 네트워크/pykrx 서버 상태에 따라 결과가 달라질 수 있습니다.

실행 예시:
  python scripts/tests/test_pykrx_etf_listing.py
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

import pandas as pd


@dataclass
class EtfListingRow:
    symbol: str
    Name: str
    Market: str


def fetch_etf_listing(asof: str) -> pd.DataFrame:
    """pykrx에서 ETF 티커 목록을 조회하고, symbol_master 호환 컬럼으로 변환."""
    from pykrx import stock

    tickers = stock.get_etf_ticker_list(asof)
    rows: List[EtfListingRow] = []

    for ticker in tickers:
        name = stock.get_etf_ticker_name(ticker)
        # 프로젝트의 symbol_master.market은 KOSPI/KOSDAQ/KONEX만 허용하는 전제가 있음.
        # ETF는 별도 유형이므로 우선 "ETF"로 명시해둔다(실제 설계 시 확정 필요).
        rows.append(EtfListingRow(symbol=str(ticker), Name=str(name), Market="ETF"))

    df = pd.DataFrame([r.__dict__ for r in rows])
    return df


def main() -> int:
    asof = datetime.now().strftime("%Y%m%d")
    df = fetch_etf_listing(asof)

    print(f"asof={asof}")
    print(f"ETF tickers={len(df)}")
    print("columns:", list(df.columns))
    print("sample:")
    print(df.head(10).to_string(index=False))

    # 최소 요구 컬럼 체크(symbol_master upsert 로직과 맞추기)
    required = ["symbol", "Name", "Market"]
    missing = [c for c in required if c not in df.columns]
    assert not missing, f"Missing columns: {missing}"

    # 타입/결측 체크
    assert df["symbol"].map(lambda x: isinstance(x, str)).all(), "symbol must be str"
    assert df["Name"].map(lambda x: isinstance(x, str)).all(), "Name must be str"
    assert df["Market"].eq("ETF").all(), "Market must be 'ETF' in this test"

    # 예시로 6자리 아닌 코드(예: 채권 ETF 등)도 존재(샘플에서 0120J0 같은 값) → 문자열 처리 필수
    non_numeric = df[~df["symbol"].str.match(r"^\d+$")].head(5)
    if not non_numeric.empty:
        print("\nNOTE: Non-numeric ETF tickers detected (must be handled as string):")
        print(non_numeric.to_string(index=False))

    print("\n✅ ETF listing fetch test PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
