#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Binance Spot exchangeInfo를 호출해서 USDT 페어 목록을 가져오는 라이브 테스트.

주의
- 이 스크립트는 네트워크 호출을 수행합니다.
- Copilot은 실행하지 않습니다. 사용자가 실행 후 출력 결과를 첨부해주세요.

실행 예:
  python scripts/tests/test_crypto_binance_exchangeinfo_live.py --limit 20

기대 출력:
- USDT 페어 총 개수
- 샘플 N개 (symbol/base/quote/status)
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class Pair:
    symbol: str
    base: str
    quote: str
    status: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--quote", default="USDT")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--timeout", type=float, default=20.0)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    url = "https://api.binance.com/api/v3/exchangeInfo"
    r = requests.get(url, timeout=args.timeout)
    r.raise_for_status()
    data: dict[str, Any] = r.json()

    symbols = data.get("symbols") or []

    pairs: list[Pair] = []
    for s in symbols:
        if s.get("isSpotTradingAllowed") is not True:
            continue
        if s.get("status") != "TRADING":
            continue
        if s.get("quoteAsset") != args.quote:
            continue
        pairs.append(Pair(symbol=s.get("symbol"), base=s.get("baseAsset"), quote=s.get("quoteAsset"), status=s.get("status")))

    print(f"[binance exchangeInfo] spot+TRADING+quote={args.quote}")
    print(f"  pairs={len(pairs)}")

    print("\n[sample]")
    for p in pairs[: max(args.limit, 0)]:
        print(f"  {p.symbol} base={p.base} quote={p.quote} status={p.status}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
