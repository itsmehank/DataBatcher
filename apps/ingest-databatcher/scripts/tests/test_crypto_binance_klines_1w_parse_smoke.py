#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live+parse smoke: Binance 1w klines → normalized weekly price DataFrame.

목적
- Binance interval=1w 응답을 '우리 DB 스키마(crypto_prices_weekly)'에 맞는 형태로
  정규화할 때 필요한 변환 규칙을 미리 검증한다.

검증 포인트
- week_start가 UTC Monday 00:00에서 나온 날짜인지 (이전 테스트에서 경계는 OK였음)
- week_end = week_start + 6일
- OHLC, volume_quote가 숫자로 변환되는지
- exchange/source 필드 값

주의
- Copilot은 실행하지 않습니다. 사용자가 실행 후 출력 결과를 첨부해주세요.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from collectors.crypto_binance import BinanceCryptoCollector  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--start", required=True, help="YYYY-MM-DD (UTC date)")
    p.add_argument("--end", required=True, help="YYYY-MM-DD (UTC date)")
    p.add_argument("--limit", type=int, default=200, help="max klines to request")
    return p.parse_args()


def _parse_date(s: str) -> date:
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def main() -> int:
    args = parse_args()
    symbol = args.symbol.upper().strip()
    start_d: date = _parse_date(args.start)
    end_d: date = _parse_date(args.end)

    collector = BinanceCryptoCollector()

    import requests

    start_ms = int(datetime(start_d.year, start_d.month, start_d.day, tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime(end_d.year, end_d.month, end_d.day, 23, 59, 59, tzinfo=timezone.utc).timestamp() * 1000)

    url = f"{collector.cfg.base_url}/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": "1w",
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": int(args.limit),
    }
    r = requests.get(url, params=params, timeout=collector.cfg.timeout_sec)
    r.raise_for_status()
    data = r.json() or []

    print(f"[binance 1w parse smoke] symbol={symbol} candles={len(data)} range={start_d}..{end_d}")
    if not data:
        print("(no rows)")
        return 0

    df = pd.DataFrame(
        data,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume_base",
            "close_time",
            "quote_asset_volume",
            "num_trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )

    dt_open = pd.to_datetime(df["open_time"], unit="ms", utc=True).astype("datetime64[ns, UTC]")
    # pandas 타입 스텁/IDE 경고를 피하기 위해 파이썬 datetime 기반으로 계산
    dt_list = [x.to_pydatetime().astimezone(timezone.utc) for x in dt_open]
    df["week_start"] = [d.date() for d in dt_list]
    df["week_dow"] = [d.strftime("%A") for d in dt_list]
    df["week_end"] = df["week_start"].apply(lambda d: d + timedelta(days=6))

    for c in ["open", "high", "low", "close", "quote_asset_volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    out = pd.DataFrame(
        {
            "symbol": symbol,
            "week_start": df["week_start"],
            "week_end": df["week_end"],
            "open": df["open"],
            "high": df["high"],
            "low": df["low"],
            "close": df["close"],
            "volume_quote": df["quote_asset_volume"],
            "exchange": "BINANCE",
            "source": "binance",
        }
    )

    # 간단한 검증 출력
    ws_min, ws_max = out["week_start"].min(), out["week_start"].max()
    print(f"[week_start] min={ws_min} max={ws_max}")

    print("\n[sample rows]")
    print(out.head(5).to_string(index=False))

    # week boundary quick check
    bad_boundary = df[(df["week_dow"] != "Monday")]
    print(f"\n[week boundary] non-Monday week_start rows={len(bad_boundary)}")
    if not bad_boundary.empty:
        print(bad_boundary[["open_time", "week_start", "week_dow"]].head(5).to_string(index=False))

    # week_end 검증: week_start + 6
    bad = out[out.apply(lambda r: r["week_end"] != (r["week_start"] + timedelta(days=6)), axis=1)]
    print(f"\n[week_end check] mismatches={len(bad)}")

    # 결측/비정상
    na_counts = out[["open", "high", "low", "close", "volume_quote"]].isna().sum()
    print("\n[na counts]")
    for k, v in na_counts.items():
        print(f"  {k}: {int(v)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
