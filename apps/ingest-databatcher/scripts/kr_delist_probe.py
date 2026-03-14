#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KR 종목 DELIST probe 스크립트.

목적:
- KIND fallback 기간에는 목록 기반 delist를 비활성화하고,
  pykrx 일봉 조회 결과를 기반으로 DELISTED를 판단한다.

로직:
1) symbol_master의 ACTIVE(KOSPI/KOSDAQ/KONEX/ETF) 종목 조회
2) 최근 N일(기본 14일) pykrx 일봉 조회
3) 빈 결과 심볼을 메모리에 누적
4) 전체 루프 종료 후 2중 게이트 통과 시에만 누적 심볼 DELISTED 일괄 반영

2중 게이트(기본):
- has_any_data_count >= 50
- has_any_data_ratio >= 0.05
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBConfig, DBManager


DEFAULT_MARKETS = ("KOSPI", "KOSDAQ", "KONEX", "ETF")


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="KR DELIST probe (pykrx 14일 조회 기반)")
    p.add_argument("--lookback-days", type=int, default=14, help="조회 lookback 일수 (기본 14)")
    p.add_argument("--min-success-count", type=int, default=50, help="게이트 최소 성공 심볼 수 (기본 50)")
    p.add_argument("--min-success-ratio", type=float, default=0.05, help="게이트 최소 성공 비율 (기본 0.05)")
    p.add_argument(
        "--markets",
        nargs="+",
        choices=["KOSPI", "KOSDAQ", "KONEX", "ETF"],
        default=list(DEFAULT_MARKETS),
        help="대상 마켓 목록",
    )
    p.add_argument("--limit", type=int, default=None, help="테스트용 상위 N개 심볼만 처리")
    p.add_argument("--dry-run", action="store_true", help="DB 상태 변경 없이 결과만 출력")
    return p.parse_args(argv)


def load_active_symbols(engine: Engine, markets: list[str]) -> list[dict[str, str]]:
    placeholders = ", ".join([f":m{i}" for i in range(len(markets))])
    sql = text(
        f"""
        SELECT symbol, market, name
        FROM symbol_master
        WHERE status = 'ACTIVE'
          AND market IN ({placeholders})
        ORDER BY symbol
        """
    )
    params = {f"m{i}": m for i, m in enumerate(markets)}

    with engine.connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [{"symbol": str(r[0]), "market": str(r[1]), "name": str(r[2] or "")} for r in rows]


def apply_delist(engine: Engine, symbols: list[str]) -> int:
    if not symbols:
        return 0

    sql = text(
        """
        UPDATE symbol_master
        SET status = 'DELISTED',
            updated_at = NOW()
        WHERE symbol = :symbol
          AND status = 'ACTIVE'
        """
    )

    params = [{"symbol": s} for s in symbols]
    with engine.begin() as conn:
        result = conn.execute(sql, params)
    return int(result.rowcount or 0)


def main(argv=None) -> int:
    args = parse_args(argv)

    cfg = load_settings()
    db_cfg = DBConfig(**cfg.get("database", {}))
    engine = DBManager.get_engine(db_cfg)

    try:
        from pykrx import stock
    except ImportError:
        print("Error: pykrx not installed", file=sys.stderr)
        return 2

    targets = load_active_symbols(engine, args.markets)
    if args.limit and args.limit > 0:
        targets = targets[: int(args.limit)]
    total = len(targets)
    if total == 0:
        print("[kr_delist_probe] 대상 ACTIVE 종목이 없습니다.")
        return 0

    end_d = date.today()
    start_d = end_d - timedelta(days=int(args.lookback_days))
    start_str = start_d.strftime("%Y%m%d")
    end_str = end_d.strftime("%Y%m%d")

    print(
        f"[kr_delist_probe] targets={total} markets={args.markets} "
        f"window={start_str}~{end_str} dry_run={args.dry_run}"
    )

    has_any_data = False
    has_any_data_count = 0
    empty_symbols: list[str] = []
    error_symbols: list[str] = []

    empty_by_market: dict[str, int] = {m: 0 for m in args.markets}
    success_by_market: dict[str, int] = {m: 0 for m in args.markets}

    for i, item in enumerate(targets, start=1):
        symbol = item["symbol"]
        market = item["market"]
        try:
            df = stock.get_market_ohlcv(start_str, end_str, symbol, adjusted=True)
            rows = 0 if df is None else len(df)
            if rows > 0:
                has_any_data = True
                has_any_data_count += 1
                success_by_market[market] = success_by_market.get(market, 0) + 1
            else:
                empty_symbols.append(symbol)
                empty_by_market[market] = empty_by_market.get(market, 0) + 1
        except Exception:
            # 예외는 delist 후보에 포함하지 않고 별도 집계
            error_symbols.append(symbol)

        if i % 500 == 0 or i == total:
            print(
                f"[kr_delist_probe] progress {i}/{total} "
                f"success={has_any_data_count} empty={len(empty_symbols)} error={len(error_symbols)}"
            )

    success_ratio = (has_any_data_count / total) if total else 0.0
    gate_pass = (has_any_data_count >= args.min_success_count) and (success_ratio >= args.min_success_ratio)

    print("[kr_delist_probe] summary")
    print(f"  has_any_data={has_any_data}")
    print(f"  success_count={has_any_data_count}")
    print(f"  success_ratio={success_ratio:.4f}")
    print(f"  empty_count={len(empty_symbols)}")
    print(f"  error_count={len(error_symbols)}")
    print(f"  success_by_market={success_by_market}")
    print(f"  empty_by_market={empty_by_market}")
    print(
        f"  gate=(count>={args.min_success_count} and ratio>={args.min_success_ratio}) "
        f"=> {gate_pass}"
    )

    if not gate_pass:
        print("[kr_delist_probe] gate 미통과: DELISTED 상태 변경을 수행하지 않습니다.")
        return 0

    # 예외 심볼은 delist 후보에서 제외
    error_set = set(error_symbols)
    delist_targets = sorted({s for s in empty_symbols if s not in error_set})

    if not delist_targets:
        print("[kr_delist_probe] DELISTED 대상이 없습니다.")
        return 0

    print(f"[kr_delist_probe] DELISTED 대상 후보: {len(delist_targets)}")
    print(f"  sample={delist_targets[:20]}")

    if args.dry_run:
        print("[kr_delist_probe] dry-run 모드: DB 업데이트를 건너뜁니다.")
        return 0

    updated = apply_delist(engine, delist_targets)
    print(f"[kr_delist_probe] DELISTED 반영 완료: {updated}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
