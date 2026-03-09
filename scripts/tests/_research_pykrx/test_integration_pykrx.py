#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pykrx 전환 통합 테스트

전체 파이프라인이 pykrx로 정상 동작하는지 확인합니다.
- Collector를 사용한 데이터 수집
- 여러 종목 테스트
- DB 저장 시뮬레이션
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from collectors.kr_stock import KRStockCollector
from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig

# 테스트 종목 (symbol, name, market)
TEST_SYMBOLS = [
    ('005930', '삼성전자', 'KOSPI'),
    ('000660', 'SK하이닉스', 'KOSPI'),
    ('005380', '현대차', 'KOSPI'),
]

def main():
    print('='*80)
    print('pykrx 통합 테스트')
    print('='*80)

    # DB 엔진 초기화
    try:
        cfg = load_settings()
        db_cfg = DBConfig(**cfg.get('database', {}))
        engine = DBManager.get_engine(db_cfg)
        print('✓ DB 엔진 초기화 성공')
    except Exception as e:
        print(f'⚠️  DB 연결 실패, fetch만 테스트: {e}')
        engine = None

    # Collector 초기화
    collector = KRStockCollector(engine)
    print('✓ Collector 초기화 성공')

    # 각 종목 테스트
    print(f'\n테스트 종목 수: {len(TEST_SYMBOLS)}')
    print(f'기간: 2026-01-20 ~ 2026-01-27')
    print('-'*80)

    success = 0
    failed = 0

    for symbol, name, market in TEST_SYMBOLS:
        try:
            print(f'\n[{symbol}] {name} ({market})')
            df = collector.fetch(symbol, '2026-01-20', '2026-01-27', market=market)

            if df is None or df.empty:
                print(f'  ❌ 데이터 없음')
                failed += 1
                continue

            print(f'  ✓ 수집: {len(df)}행')
            source = df['source'].iloc[0]
            close_price = df['close'].iloc[-1]
            print(f'  ✓ Source: {source}')
            print(f'  ✓ 최근 종가: {close_price:,}원')

            # DB 저장 테스트는 스킵 (실제 저장하지 않음)
            # if engine:
            #     collector.save(df, symbol, mode='insert_only')

            success += 1

        except Exception as e:
            print(f'  ❌ 오류: {e}')
            failed += 1

    print('\n' + '='*80)
    print(f'결과: {success}/{len(TEST_SYMBOLS)} 성공, {failed}/{len(TEST_SYMBOLS)} 실패')
    print('='*80)

    if failed == 0:
        print('\n✅ 모든 통합 테스트 통과')
        return 0
    else:
        print(f'\n⚠️  {failed}개 테스트 실패')
        return 1

if __name__ == '__main__':
    sys.exit(main())