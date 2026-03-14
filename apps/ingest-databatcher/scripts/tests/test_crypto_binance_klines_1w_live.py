#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live probe: Binance Klines interval=1w week boundary validation.

목적
- Binance `GET /api/v3/klines?interval=1w`가 반환하는 캔들의 open_time이
  우리가 원하는 코인 주봉 경계(UTC 월요일 00:00:00)와 일치하는지 확인한다.

출력(핵심)
- 각 주봉 캔들의 open_time(UTC), open_date, open_dow, open_hms
- open_time이 UTC 월요일 00:00:00이 아닌 경우 WARNING

주의
- Copilot은 실행하지 않습니다. 사용자가 실행 후 출력 결과를 첨부해주세요.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from collectors.crypto_binance import BinanceCryptoCollector  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--limit", type=int, default=12, help="number of 1w candles to fetch (max 1000)")
    p.add_argument(
        "--start",
        default=None,
        help="UTC datetime ISO (e.g. 2025-01-01T00:00:00Z). Optional.",
    )
    p.add_argument(
        "--end",
        default=None,
        help="UTC datetime ISO (e.g. 2026-02-01T00:00:00Z). Optional.",
    )
    return p.parse_args()


def _parse_iso_utc(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def main() -> int:
    args = parse_args()
    symbol = args.symbol.upper().strip()

    collector = BinanceCryptoCollector()

    # 우리는 아직 collector에 fetch_klines_1w를 구현하지 않았을 수도 있으므로,
    # 현 시점에서는 requests를 직접 치지 않고 collector의 low-level 메서드를 쓰지 않습니다.
    # 대신: 현 프로젝트의 collector가 "1d"만 지원하는 경우를 대비해,
    # BinanceCryptoCollector에 의존하지 않고 requests로 직접 호출하는 방식을 별도 구현할 수도 있습니다.
    # 다만 현재 repo에는 requests가 이미 사용 중이므로, 여기서는 requests로 직접 호출합니다.
    import requests  # local import

    base_url = collector.cfg.base_url

    params: dict[str, object] = {
        "symbol": symbol,
        "interval": "1w",
        "limit": int(args.limit),
    }
    if args.start:
        start_dt = _parse_iso_utc(args.start)
        params["startTime"] = int(start_dt.timestamp() * 1000)
    if args.end:
        end_dt = _parse_iso_utc(args.end)
        params["endTime"] = int(end_dt.timestamp() * 1000)

    url = f"{base_url}/api/v3/klines"
    # requests 타입 힌트가 까다로워서(IDE 경고) str/숫자/None만 포함하도록 변환
    params_req: dict[str, str | int] = {}
    for k, v in params.items():
        if v is None:
            continue
        params_req[k] = int(v) if isinstance(v, bool) else v  # type: ignore[assignment]
    r = requests.get(url, params=params_req, timeout=collector.cfg.timeout_sec)
    r.raise_for_status()
    data = r.json() or []

    print(f"[binance klines 1w] symbol={symbol} candles={len(data)}")
    if not data:
        print("(no rows)")
        return 0

    # kline columns (binance)
    # 0 openTime, 1 open, 2 high, 3 low, 4 close, 5 volume,
    # 6 closeTime, 7 quoteAssetVolume, 8 numTrades, 9 takerBuyBase, 10 takerBuyQuote, 11 ignore
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

    # open_time -> UTC dt
    df["open_dt_utc"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    # .dt 접근 보장을 위해 datetime64[ns, UTC]로 고정
    df["open_dt_utc"] = df["open_dt_utc"].astype("datetime64[ns, UTC]")
    df["open_date"] = df["open_dt_utc"].dt.date
    df["open_dow"] = df["open_dt_utc"].dt.day_name()
    df["open_hms"] = df["open_dt_utc"].dt.strftime("%H:%M:%S")

    # boundary check: Monday 00:00:00 UTC
    df["is_mon"] = df["open_dt_utc"].dt.dayofweek == 0
    df["is_midnight"] = df["open_hms"] == "00:00:00"
    df["boundary_ok"] = df["is_mon"] & df["is_midnight"]

    cols = ["open_dt_utc", "open_date", "open_dow", "open_hms", "boundary_ok"]
    print("\n[sample candles]")
    for _, row in df[cols].head(min(len(df), 20)).iterrows():
        ok = "OK" if bool(row["boundary_ok"]) else "WARNING"
        print(
            f"  {row['open_dt_utc'].isoformat()}  date={row['open_date']}  dow={row['open_dow']:<9}  hms={row['open_hms']}  boundary={ok}"
        )

    bad = int((~df["boundary_ok"]).sum())
    if bad:
        print(f"\n[RESULT] boundary mismatch candles={bad}/{len(df)}")
        # show unique patterns
        pats = df.loc[~df["boundary_ok"], ["open_dow", "open_hms"]].drop_duplicates()
        print("[mismatch patterns] dow/hms")
        for _, r2 in pats.iterrows():
            print(f"  dow={r2['open_dow']} hms={r2['open_hms']}")
        return 1

    print(f"\n[RESULT] boundary OK (UTC Monday 00:00:00) for {len(df)} candles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
