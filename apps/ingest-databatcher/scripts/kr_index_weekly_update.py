#!/usr/bin/env python3
"""
KR 지수(KOSPI/KOSDAQ) 주봉 증분 업데이트 스크립트

처리 흐름:
1. DB에서 최근 250주 일봉 데이터 조회 (kr_index_prices)
2. 주봉으로 집계
3. 주봉 가격 데이터 INSERT ONLY (kr_index_prices_weekly)
4. 주봉 지표 계산 (warmup 포함)
5. 최신 주부터 역순으로 처리, 완료된 주 만나면 중단

실행 예시:
    python scripts/kr_index_weekly_update.py --all
    python scripts/kr_index_weekly_update.py --all --market KOSPI
    python scripts/kr_index_weekly_update.py --symbols 1001 2001

주의:
    - kr_index_prices에 일봉 데이터가 먼저 존재해야 합니다
    - 매주 토요일 새벽 실행 권장 (금요일 장마감 데이터 확정 후)
"""
from __future__ import annotations

import argparse
import sys
from datetime import timedelta, date
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Add parent directory to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from core.date_utils import DateUtils
from core.kr_index_symbol_loader import load_kr_index_symbols_with_details
from core.weekly_aggregation import aggregate_daily_to_weekly_trading_days

# Import indicator modules to register them
from indicators.common import sma as _reg_sma  # noqa: F401
from indicators.common import ema as _reg_ema  # noqa: F401

from indicators.pipeline import IndicatorPipeline, IndicatorSpec
from savers.indicator_saver import IndicatorSaver


def build_weekly_pipeline(cfg) -> IndicatorPipeline:
    """주봉 지표 파이프라인 구성"""
    weekly_cfg = cfg.get("indicators_kr_index_weekly", cfg.get("indicators_kr_index", {})) or {}
    if not isinstance(weekly_cfg, dict):
        raise ValueError("[kr_index_weekly_update] indicators_kr_index_weekly 설정은 dict 형태여야 합니다.")

    specs_cfg = weekly_cfg.get("pipeline") or []
    if not isinstance(specs_cfg, list):
        raise ValueError("[kr_index_weekly_update] indicators_kr_index_weekly.pipeline 설정은 list 형태여야 합니다.")

    specs = [IndicatorSpec(**x) for x in specs_cfg]
    return IndicatorPipeline(specs)


def load_daily_data(engine: Engine, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
    """
    DB에서 kr_index_prices 일봉 데이터 조회 (adj_close 없음)
    """
    sql = """
        SELECT date, open, high, low, close, volume, market, source
        FROM kr_index_prices
        WHERE symbol = :symbol
          AND date >= :start
          AND date <= :end
        ORDER BY date ASC
    """

    with engine.connect() as conn:
        result = conn.execute(text(sql), {'symbol': symbol, 'start': start_date, 'end': end_date})
        rows = result.fetchall()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume', 'market', 'source'])


def save_weekly_prices_insert_only(engine: Engine, symbol: str, weekly_df: pd.DataFrame, market: str) -> int:
    """주봉 가격 데이터를 kr_index_prices_weekly에 INSERT ONLY로 저장 (adj_close 없음)."""
    if weekly_df is None or weekly_df.empty:
        return 0

    weekly_df = weekly_df.copy()
    weekly_df['symbol'] = symbol

    weekly_df['week_start'] = pd.to_datetime(weekly_df['week_start']).dt.strftime('%Y-%m-%d')
    weekly_df['week_end'] = pd.to_datetime(weekly_df['week_end']).dt.strftime('%Y-%m-%d')

    rows_saved = 0
    with engine.begin() as conn:
        for _, row in weekly_df.iterrows():
            sql = """
                INSERT IGNORE INTO kr_index_prices_weekly
                (symbol, week_start, week_end, open, high, low, close, volume, market, source)
                VALUES (:symbol, :week_start, :week_end, :open, :high, :low, :close, :volume, :market, :source)
            """
            result = conn.execute(text(sql), {
                'symbol': row['symbol'],
                'week_start': row['week_start'],
                'week_end': row['week_end'],
                'open': float(row['open']) if pd.notna(row['open']) else None,
                'high': float(row['high']) if pd.notna(row['high']) else None,
                'low': float(row['low']) if pd.notna(row['low']) else None,
                'close': float(row['close']) if pd.notna(row['close']) else None,
                'volume': int(row['volume']) if pd.notna(row['volume']) else None,
                'market': row.get('market', market),
                'source': row.get('source', 'yfinance'),
            })
            rows_saved += max(result.rowcount or 0, 0)

    return rows_saved


def drop_incomplete_latest_week(df_weekly: pd.DataFrame, symbol: str, end_date: date) -> pd.DataFrame:
    """주봉 최신 row의 week_end가 end_date와 다르면 최신 주를 제거한다."""
    if df_weekly is None or df_weekly.empty:
        return pd.DataFrame()

    df = df_weekly.copy()
    week_end_series = pd.to_datetime(df["week_end"]).dt.date
    latest_week_end = week_end_series.max()

    if latest_week_end == end_date:
        return df

    latest_mask = week_end_series == latest_week_end
    dropped_rows = int(latest_mask.sum())
    print(
        f"{symbol}: 최신 주 미완결로 스킵 "
        f"(latest_week_end={latest_week_end}, expected_end={end_date}, dropped={dropped_rows})"
    )
    return df.loc[~latest_mask].copy()


def check_weekly_indicators_complete(engine: Engine, symbol: str, week_start: str, market: str, expected_count: int) -> bool:
    """특정 (symbol, week_start, market)에 대해 kr_index_indicators_weekly row 수 >= expected spec 수 이면 완료."""
    sql = text(
        """
        SELECT COUNT(*) as cnt
        FROM kr_index_indicators_weekly
        WHERE symbol = :symbol AND week_start = :week_start AND market = :market
        """
    )

    with engine.connect() as conn:
        row = conn.execute(sql, {'symbol': symbol, 'week_start': week_start, 'market': market}).fetchone()
    return (row[0] >= expected_count) if row else False


def process_index(
    symbol: str,
    end_date: date,
    pipeline: IndicatorPipeline,
    saver: IndicatorSaver,
    engine: Engine,
    market: str,
    skip_latest_week: bool = True
) -> None:
    """
    단일 지수의 주봉 증분 업데이트

    흐름:
    1. 최근 250주(약 1750일) 일봉 데이터 조회
    2. 주봉으로 집계
    3. 주봉 가격 INSERT ONLY
    4. 주봉 지표 계산 (warmup 포함)
    5. 최신 주부터 역순 INSERT ONLY, 완료된 주 만나면 중단
    """
    # STEP 1: 최근 250주 일봉 데이터 조회 (약 1750일)
    start_nweeks = end_date - timedelta(days=250 * 7)

    df_daily = load_daily_data(engine, symbol, start_nweeks, end_date)

    if df_daily.empty:
        print(f"{symbol}: 일봉 데이터 없음, 스킵")
        return

    # STEP 2: 주봉으로 집계
    df_weekly = aggregate_daily_to_weekly_trading_days(df_daily, skip_latest_week=skip_latest_week)

    if not skip_latest_week:
        df_weekly = drop_incomplete_latest_week(df_weekly, symbol, end_date)

    if df_weekly.empty:
        print(f"{symbol}: 주봉 집계 실패")
        return

    # STEP 3: 주봉 가격 INSERT ONLY
    price_rows = save_weekly_prices_insert_only(engine, symbol, df_weekly, market)
    print(f"{symbol}: 주봉 가격 {price_rows}건 처리(insert-only)")

    if not pipeline.specs:
        print(f"{symbol}: 주봉 지표 설정 없음(pipeline 비어있음), 지표 스킵")
        return

    # STEP 4: 주봉 지표 계산
    warmup = pipeline.warmup_days()
    start_with_warmup = start_nweeks - timedelta(days=warmup * 7)  # 주 단위 warmup

    df_daily_full = load_daily_data(engine, symbol, start_with_warmup, end_date)

    if df_daily_full.empty:
        print(f"{symbol}: warmup 데이터 부족, 지표 스킵")
        return

    df_weekly_full = aggregate_daily_to_weekly_trading_days(df_daily_full, skip_latest_week=skip_latest_week)

    if df_weekly_full.empty:
        print(f"{symbol}: warmup 주봉 집계 실패")
        return

    indicator_df = df_weekly_full[['week_start', 'open', 'high', 'low', 'close', 'volume']].copy()
    indicator_df = indicator_df.rename(columns={'week_start': 'date'})
    indicator_df['date'] = pd.to_datetime(indicator_df['date']).dt.normalize()
    indicator_df.set_index('date', inplace=True)

    outputs = pipeline.run(indicator_df)

    if not outputs:
        print(f"{symbol}: 지표 계산 결과 없음")
        return

    # STEP 5: 최신 주부터 역순 INSERT-ONLY (완료된 주 만나면 중단)
    weeks_desc = sorted(pd.to_datetime(df_weekly['week_start']).dt.normalize().unique(), reverse=True)

    expected_indicator_count = len([spec for spec in pipeline.specs if spec.save])

    total_upserted = 0
    processed_weeks = 0

    for week_start in weeks_desc:
        week_start_date = pd.Timestamp(week_start).date()
        week_start_str = week_start_date.strftime('%Y-%m-%d')

        week_market = (
            df_weekly[pd.to_datetime(df_weekly['week_start']).dt.normalize() == pd.Timestamp(week_start).normalize()]['market'].iloc[0]
            if 'market' in df_weekly.columns and not df_weekly[pd.to_datetime(df_weekly['week_start']).dt.normalize() == pd.Timestamp(week_start).normalize()].empty
            else market
        )

        if check_weekly_indicators_complete(engine, symbol, week_start_str, week_market, expected_indicator_count):
            print(f"{symbol}: {week_start_str} 모든 지표 완료 → 중단")
            break

        week_dt = pd.Timestamp(week_start_date).normalize()
        if week_dt not in indicator_df.index:
            continue

        filtered = {}
        for key, series in outputs.items():
            series_idx = pd.DatetimeIndex(series.index).normalize()
            if week_dt in series_idx:
                val = series.reindex(series_idx).loc[week_dt]
                filtered[key] = pd.Series([val], index=[week_dt], name=series.name)
            else:
                filtered[key] = pd.Series([pd.NA], index=[week_dt], name=series.name)

        if not filtered:
            continue

        df_long = pipeline.to_long_dataframe(
            symbol=symbol,
            market=week_market,
            source='yfinance',
            outputs=filtered,
            keep_nan=True,
        )

        if df_long is None or df_long.empty:
            continue

        if 'value' in df_long.columns:
            df_long['value'] = df_long['value'].astype(object)
            df_long.loc[pd.isna(df_long['value']), 'value'] = None

        df_long = df_long.rename(columns={"date": "week_start"})
        df_long['week_start'] = pd.to_datetime(df_long['week_start']).dt.date

        rows = saver.save_long(df_long, mode="insert_only")
        total_upserted += rows
        processed_weeks += 1

    print(f"{symbol}: {processed_weeks}개 주 처리, 지표 {total_upserted}건 저장(insert-only)")


def should_skip_latest_week_kst(date_utils: DateUtils) -> bool:
    """KST 기준으로 평일에는 최신 주차를 스킵, 주말(토/일)에는 포함."""
    dow = date_utils.now().weekday()  # Monday=0 ... Sunday=6
    return dow < 5


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KR 지수 주봉 증분 업데이트")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="전체 지수 업데이트")
    group.add_argument("--symbols", nargs="+", help="특정 지수만 (예: 1001 2001)")

    parser.add_argument(
        "--market",
        choices=["KOSPI", "KOSDAQ", "ALL"],
        default="ALL",
        help="시장 필터 (기본값: ALL)"
    )

    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    # Load configuration
    cfg = load_settings()
    db_cfg = DBConfig(**cfg['database'])
    engine = DBManager.get_engine(db_cfg)

    tz_name = cfg.get('runtime', {}).get('timezone', 'Asia/Seoul')
    date_utils = DateUtils(tz_name)

    end_date = date_utils.get_last_business_day('XKRX')

    skip_latest_week = should_skip_latest_week_kst(date_utils)
    print(f"[kr_index_weekly_update] skip_latest_week={skip_latest_week} (KST weekend -> False)")
    print(f"[kr_index_weekly_update] 기준일: {end_date}")

    # Load indices
    if args.all:
        indices = load_kr_index_symbols_with_details(engine, market=args.market)
        print(f"[kr_index_weekly_update] 처리 대상: {len(indices)}개 지수")
    else:
        indices = []
        skipped = []
        for sym in args.symbols:
            sql = "SELECT symbol, name, market FROM kr_index_master WHERE symbol = :symbol AND status = 'ACTIVE'"
            with engine.connect() as conn:
                result = conn.execute(text(sql), {"symbol": sym})
                row = result.fetchone()
                if row:
                    indices.append({"symbol": row[0], "name": row[1], "market": row[2]})
                else:
                    print(f"Warning: {sym} not found in kr_index_master (or not ACTIVE), skipping", file=sys.stderr)
                    skipped.append(sym)

        if skipped:
            print(f"[kr_index_weekly_update] Skipped {len(skipped)} indices: {', '.join(skipped)}")
        print(f"[kr_index_weekly_update] 처리 대상: {len(indices)}개 지수")

    if not indices:
        print("[kr_index_weekly_update] 처리할 지수가 없습니다")
        return 0

    # Build weekly pipeline
    pipeline = build_weekly_pipeline(cfg)

    # Initialize saver (weekly table)
    weekly_cfg = cfg.get('indicators_kr_index_weekly', cfg.get('indicators_kr_index')) or {}
    table_name = weekly_cfg.get('materialization', {}).get('table_long', 'kr_index_indicators_weekly')
    saver = IndicatorSaver(engine, table_long=table_name)

    # Process each index (sequential, only 2 indices)
    for idx_info in indices:
        symbol = idx_info["symbol"]
        market = idx_info["market"]
        try:
            process_index(symbol, end_date, pipeline, saver, engine, market, skip_latest_week=skip_latest_week)
        except Exception as e:
            print(f"{symbol}: Error - {e}")

    print("[kr_index_weekly_update] 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
