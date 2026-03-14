#!/usr/bin/env python3
"""
주봉 증분 업데이트 스크립트

처리 흐름:
1. DB에서 최근 250주 일봉 데이터 조회
2. 주봉으로 집계
3. 주봉 가격 데이터 INSERT ONLY
4. 주봉 지표 계산 (warmup 포함)
5. 최신 주부터 역순으로 처리, 완료된 주 만나면 중단

실행 예시:
    python scripts/weekly_update.py --all
    python scripts/weekly_update.py --all --market KOSPI --top 100
    python scripts/weekly_update.py --symbols 005930 000660

주의:
    - 일봉 데이터가 DB에 먼저 존재해야 합니다
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
from core.symbol_loader import load_symbols_with_details
from core.weekly_aggregation import aggregate_daily_to_weekly_trading_days

# Import indicator modules to register them
from indicators.common import sma as _reg_sma  # noqa: F401
from indicators.common import ema as _reg_ema  # noqa: F401

from indicators.pipeline import IndicatorPipeline, IndicatorSpec
from savers.indicator_saver import IndicatorSaver


def build_weekly_pipeline(cfg) -> IndicatorPipeline:
    """주봉 지표 파이프라인 구성"""
    weekly_cfg = cfg.get("indicators_weekly", cfg.get("indicators", {})) or {}
    if not isinstance(weekly_cfg, dict):
        raise ValueError("[weekly_update] indicators_weekly 설정은 dict 형태여야 합니다.")

    specs_cfg = weekly_cfg.get("pipeline") or []
    if not isinstance(specs_cfg, list):
        raise ValueError("[weekly_update] indicators_weekly.pipeline 설정은 list 형태여야 합니다.")

    specs = [IndicatorSpec(**x) for x in specs_cfg]
    return IndicatorPipeline(specs)


def load_daily_data_for_weeks(engine: Engine, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
    """
    DB에서 일봉 데이터 조회

    Args:
        engine: SQLAlchemy engine
        symbol: 종목 코드
        start_date: 시작일
        end_date: 종료일

    Returns:
        일봉 DataFrame
    """
    sql = """
        SELECT date, open, high, low, close, adj_close, volume, market, source
        FROM stock_prices
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

    return pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'adj_close', 'volume', 'market', 'source'])


def save_weekly_prices_insert_only(engine: Engine, symbol: str, weekly_df: pd.DataFrame, market: str) -> tuple[int, int]:
    """주봉 가격 데이터를 DB에 INSERT ONLY로 저장.

    기존 데이터가 존재하면 유지(갱신하지 않음).

    Returns:
        (시도 건수, 실제 INSERT 건수)
    """
    if weekly_df is None or weekly_df.empty:
        return 0, 0

    weekly_df = weekly_df.copy()
    weekly_df['symbol'] = symbol

    weekly_df['week_start'] = pd.to_datetime(weekly_df['week_start']).dt.strftime('%Y-%m-%d')
    weekly_df['week_end'] = pd.to_datetime(weekly_df['week_end']).dt.strftime('%Y-%m-%d')

    attempted_rows = 0
    inserted_rows = 0
    with engine.begin() as conn:
        for _, row in weekly_df.iterrows():
            sql = """
                INSERT IGNORE INTO stock_prices_weekly
                (symbol, week_start, week_end, open, high, low, close, adj_close, volume, market, source)
                VALUES (:symbol, :week_start, :week_end, :open, :high, :low, :close, :adj_close, :volume, :market, :source)
            """
            result = conn.execute(text(sql), {
                'symbol': row['symbol'],
                'week_start': row['week_start'],
                'week_end': row['week_end'],
                'open': float(row['open']) if pd.notna(row['open']) else None,
                'high': float(row['high']) if pd.notna(row['high']) else None,
                'low': float(row['low']) if pd.notna(row['low']) else None,
                'close': float(row['close']) if pd.notna(row['close']) else None,
                'adj_close': float(row['adj_close']) if 'adj_close' in row and pd.notna(row['adj_close']) else None,
                'volume': int(row['volume']) if pd.notna(row['volume']) else None,
                'market': row.get('market', market),
                'source': row.get('source', 'pykrx'),
            })
            attempted_rows += 1
            inserted_rows += max(result.rowcount or 0, 0)

    return attempted_rows, inserted_rows


def check_weekly_indicators_complete(engine: Engine, symbol: str, week_start: str, market: str, expected_count: int) -> bool:
    """특정 (symbol, week_start, market)에 대해 'row 수 >= expected spec 수'면 완료로 간주.

    요구사항(현재 범위):
    - 완료 체크는 "row 수 >= expected spec 수" 기준 유지
    - ETF/주식이 같은 symbol에서 섞여 오인되지 않도록 market으로 필터
    """
    sql = text(
        """
        SELECT COUNT(*) as cnt
        FROM stock_indicators_weekly
        WHERE symbol = :symbol AND week_start = :week_start AND market = :market
        """
    )

    with engine.connect() as conn:
        row = conn.execute(sql, {'symbol': symbol, 'week_start': week_start, 'market': market}).fetchone()
    return (row[0] >= expected_count) if row else False


def process_symbol(
    symbol: str,
    end_date: date,
    pipeline: IndicatorPipeline,
    saver: IndicatorSaver,
    engine: Engine,
    market: str,
    skip_latest_week: bool = True
) -> None:
    """
    단일 종목의 주봉 증분 업데이트

    Contract:
    - 입력: symbol의 최근 일봉(250주 + warmup)
    - 출력: price/indicator insert-only 처리 로그
    - 주봉 키 규칙: core.weekly_aggregation.aggregate_daily_to_weekly_trading_days 기준

    흐름:
    1. 최근 250주(약 1750일) 일봉 데이터 조회
    2. 주봉으로 집계
    3. 주봉 가격 INSERT ONLY
    4. 주봉 지표 계산 (warmup 포함하여 일봉에서 다시 조회 후 집계)
    5. 최신 주부터 역순 INSERT ONLY, 완료된 주 만나면 중단

    Args:
        symbol: 종목 코드
        end_date: 기준 종료일
        pipeline: IndicatorPipeline 인스턴스
        saver: IndicatorSaver 인스턴스
        engine: SQLAlchemy engine
        market: 시장 구분 (KOSPI/KOSDAQ/KONEX)
        skip_latest_week: 최신 주차 집계 스킵 여부
    """
    # ========================================
    # STEP 1: 최근 250주 일봉 데이터 조회 (약 1750일)
    # ========================================
    start_nweeks = end_date - timedelta(days=250 * 7)

    df_daily = load_daily_data_for_weeks(engine, symbol, start_nweeks, end_date)

    if df_daily.empty:
        print(f"{symbol}: 일봉 데이터 없음, 스킵")
        return

    # ========================================
    # STEP 2: 주봉으로 집계
    # ========================================
    df_weekly = aggregate_daily_to_weekly_trading_days(df_daily, skip_latest_week=skip_latest_week)

    if df_weekly.empty:
        print(f"{symbol}: 주봉 집계 실패")
        return

    # ========================================
    # STEP 3: 주봉 가격 INSERT ONLY
    # ========================================
    attempted_rows, inserted_rows = save_weekly_prices_insert_only(engine, symbol, df_weekly, market)
    print(f"{symbol}: 주봉 가격 시도 {attempted_rows}건, 신규 저장 {inserted_rows}건(insert-only)")

    if not pipeline.specs:
        print(f"{symbol}: 주봉 지표 설정 없음(pipeline 비어있음), 지표 스킵")
        return

    # ========================================
    # STEP 4: 주봉 지표 계산
    # ========================================
    warmup = pipeline.warmup_days()
    start_with_warmup = start_nweeks - timedelta(days=warmup * 7)  # 주 단위 warmup

    # Warmup을 위한 추가 일봉 데이터 로드
    df_daily_full = load_daily_data_for_weeks(engine, symbol, start_with_warmup, end_date)

    if df_daily_full.empty:
        print(f"{symbol}: warmup 데이터 부족, 지표 스킵")
        return

    # Warmup 포함 주봉 집계
    df_weekly_full = aggregate_daily_to_weekly_trading_days(df_daily_full, skip_latest_week=skip_latest_week)

    if df_weekly_full.empty:
        print(f"{symbol}: warmup 주봉 집계 실패")
        return

    # 지표 계산 준비
    indicator_df = df_weekly_full[['week_start', 'open', 'high', 'low', 'close', 'volume']].copy()
    indicator_df = indicator_df.rename(columns={'week_start': 'date'})
    # 핵심: 주차 키를 항상 00:00:00으로 정규화해서 (DB/집계 단계에서 시간 성분이 섞여도) 안정적으로 매칭되게 한다.
    indicator_df['date'] = pd.to_datetime(indicator_df['date']).dt.normalize()
    indicator_df.set_index('date', inplace=True)

    # 지표 계산
    outputs = pipeline.run(indicator_df)

    if not outputs:
        print(f"{symbol}: 지표 계산 결과 없음")
        return

    # ========================================
    # STEP 5: 최신 주부터 역순 INSERT-ONLY (완료된 주 만나면 중단)
    # ========================================
    # N주 구간의 week_start 목록 (역순)
    # df_weekly['week_start']에 시간 성분이 섞일 수 있으므로 normalize 후 정렬
    weeks_desc = sorted(pd.to_datetime(df_weekly['week_start']).dt.normalize().unique(), reverse=True)

    # 기대되는 지표 개수
    expected_indicator_count = len([spec for spec in pipeline.specs if spec.save])

    total_upserted = 0
    processed_weeks = 0

    for week_start in weeks_desc:
        # week_start는 이미 normalize된 Timestamp
        week_start_date = pd.Timestamp(week_start).date()
        week_start_str = week_start_date.strftime('%Y-%m-%d')

        # 해당 주의 market은 집계 결과(df_weekly)에서 가져온 값을 우선 사용(없으면 symbol_master market fallback)
        week_market = (
            df_weekly[pd.to_datetime(df_weekly['week_start']).dt.normalize() == pd.Timestamp(week_start).normalize()]['market'].iloc[0]
            if 'market' in df_weekly.columns and not df_weekly[pd.to_datetime(df_weekly['week_start']).dt.normalize() == pd.Timestamp(week_start).normalize()].empty
            else market
        )

        # 5-1. 해당 주의 모든 지표가 이미 완료되었는지 체크
        # 완료 체크는 "row 수 >= expected spec 수" 기준 유지.
        # 단, market이 다르면 다른 자산군(ETF/주식) 데이터가 섞일 수 있으므로 market을 포함해 카운트.
        # (indicator 문자열이 달라도 row 수 기준이면 충분하다는 현재 범위의 요구를 반영)
        if check_weekly_indicators_complete(engine, symbol, week_start_str, week_market, expected_indicator_count):
            print(f"{symbol}: {week_start_str} 모든 지표 완료 → 중단")
            break

        # indicator_df.index는 DatetimeIndex이므로 Timestamp(00:00:00)로 정규화
        week_dt = pd.Timestamp(week_start_date).normalize()
        if week_dt not in indicator_df.index:
            # 집계/정규화 문제로 해당 주 키가 없으면 스킵
            continue

        # 해당 주의 지표 값만 추출 (1-row time series로 만들어 long-form 변환)
        filtered = {}
        for key, series in outputs.items():
            series_idx = pd.DatetimeIndex(series.index).normalize()
            if week_dt in series_idx:
                 # NaN이어도 포함(keep_nan=True로 NULL 저장)
                val = series.reindex(series_idx).loc[week_dt]
                filtered[key] = pd.Series([val], index=[week_dt], name=series.name)
            else:
                 # 시리즈에 키가 없으면 NaN으로라도 row를 만들어 "계산 시도"를 기록
                filtered[key] = pd.Series([pd.NA], index=[week_dt], name=series.name)

        if not filtered:
            continue


        df_long = pipeline.to_long_dataframe(
            symbol=symbol,
            market=week_market,
            source='pykrx',
            outputs=filtered,
            keep_nan=True,
        )

        if df_long is None or df_long.empty:
            # keep_nan=True인데도 비었다면, 입력 filtered 자체가 비정상인 상황이므로 스킵
            continue

        # keep_nan=True인 경우에도 DB에 안전하게 NULL로 들어가도록 NaN/NA를 None으로 치환
        if 'value' in df_long.columns:
            df_long['value'] = df_long['value'].astype(object)
            df_long.loc[pd.isna(df_long['value']), 'value'] = None

        # weekly 테이블 PK는 week_start이므로 컬럼명 변환
        df_long = df_long.rename(columns={"date": "week_start"})
        df_long['week_start'] = pd.to_datetime(df_long['week_start']).dt.date

        rows = saver.save_long(df_long, mode="insert_only")
        total_upserted += rows
        processed_weeks += 1

    print(f"{symbol}: {processed_weeks}개 주 처리, 지표 {total_upserted}건 저장(insert-only)")


def should_skip_latest_week_kst(date_utils: DateUtils) -> bool:
    """KST 기준으로 평일에는 최신 주차를 스킵, 주말(토/일)에는 포함.

    - 평일(월~금): 미완성 주차 가능성이 있으므로 스킵(True)
    - 주말(토/일): 직전 금요일 종가까지 적재되었다는 가정 하에 최신 주차도 완성으로 간주(False)
    """
    dow = date_utils.now().weekday()  # Monday=0 ... Sunday=6
    return dow < 5


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="주봉 증분 업데이트")

    # 종목 선택 옵션
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="전체 종목 업데이트")
    group.add_argument("--symbols", nargs="+", help="특정 종목만 (예: 005930 000660)")

    # 필터링 옵션
    parser.add_argument(
        "--market",
        choices=["KOSPI", "KOSDAQ", "KONEX", "ETF", "ALL"],
        default="ALL",
        help="시장 필터 (기본값: ALL)"
    )
    parser.add_argument("--top", type=int, help="상위 N개 종목만")

    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    # Load configuration
    cfg = load_settings()
    db_cfg = DBConfig(**cfg['database'])
    engine = DBManager.get_engine(db_cfg)

    # Get end_date (today or market close date)
    tz_name = cfg.get('runtime', {}).get('timezone', 'Asia/Seoul')
    date_utils = DateUtils(tz_name)
    end_date = date_utils.get_last_business_day('XKRX')

    skip_latest_week = should_skip_latest_week_kst(date_utils)
    print(f"[weekly_update] skip_latest_week={skip_latest_week} (KST weekend -> False)")

    print(f"[weekly_update] 기준일: {end_date}")

    # Load symbols
    if args.all:
        symbols = load_symbols_with_details(
            engine=engine,
            market=args.market,
            top=args.top if hasattr(args, 'top') else None
        )
        print(f"[weekly_update] 처리 대상: {len(symbols)}개 종목")
    else:
        # 특정 종목만 - symbol_master에서 market 정보 조회
        from sqlalchemy import text
        symbols = []
        skipped = []
        for sym in args.symbols:
            sql = "SELECT symbol, name, market FROM symbol_master WHERE symbol = :symbol AND status = 'ACTIVE'"
            with engine.connect() as conn:
                result = conn.execute(text(sql), {"symbol": sym})
                row = result.fetchone()
                if row:
                    symbols.append({"symbol": row[0], "name": row[1], "market": row[2]})
                else:
                    print(f"Warning: {sym} not found in symbol_master (or not ACTIVE), skipping", file=sys.stderr)
                    skipped.append(sym)

        if skipped:
            print(f"[weekly_update] Skipped {len(skipped)} symbols: {', '.join(skipped)}")
        print(f"[weekly_update] 처리 대상: {len(symbols)}개 종목")

    if not symbols:
        print("[weekly_update] 처리할 종목이 없습니다")
        return 0

    # Build weekly pipeline
    pipeline = build_weekly_pipeline(cfg)

    # Initialize saver (weekly table)
    weekly_cfg = cfg.get('indicators_weekly', cfg.get('indicators')) or {}
    table_name = weekly_cfg.get('materialization', {}).get('table_long', 'stock_indicators_weekly')
    saver = IndicatorSaver(engine, table_long=table_name)

    # Process each symbol
    for symbol_info in symbols:
        symbol = symbol_info["symbol"]
        market = symbol_info["market"]
        try:
            process_symbol(symbol, end_date, pipeline, saver, engine, market, skip_latest_week=skip_latest_week)
        except Exception as e:
            print(f"{symbol}: Error - {e}")

    print("[weekly_update] 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
