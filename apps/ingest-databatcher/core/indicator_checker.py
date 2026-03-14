# core/indicator_checker.py
from __future__ import annotations
from datetime import date
from typing import List, Set
from sqlalchemy.engine import Engine
from sqlalchemy import text

from indicators.pipeline import IndicatorSpec
from core.params import params_hash as compute_params_hash


class IndicatorChecker:
    """
    특정 날짜의 지표 완료 여부를 확인하는 유틸리티.

    설정 파일의 지표 파이프라인에 정의된 모든 지표가
    특정 (symbol, date)에 대해 존재하는지 검증합니다.

    params_hash만으로 비교합니다.
    params_hash는 (indicator_name, params) 조합의 SHA1 해시이므로
    각 지표 설정별로 고유하며, DB의 indicator 컬럼명(sma_5_close 등)과
    무관하게 정확한 완료 여부를 판별할 수 있습니다.

    다양한 테이블/설정 키 지원:
    - KR 주식: table="stock_indicators", config_key="indicators"
    - KR 지수: table="kr_index_indicators", config_key="indicators_kr_index"
    - US 주식: table="us_stock_indicators", config_key="indicators_us"
    """

    def __init__(
        self,
        engine: Engine,
        cfg: dict,
        table: str = "stock_indicators",
        config_key: str = "indicators"
    ):
        self.engine = engine
        self.table = table
        self.config_key = config_key
        self.expected_hashes = self._build_expected_hashes(cfg, config_key)

    def _build_expected_hashes(self, cfg: dict, config_key: str) -> Set[str]:
        """
        설정에서 기대하는 params_hash 집합 생성.

        Args:
            cfg: 설정 dict
            config_key: 설정에서 파이프라인을 읽을 키

        Returns:
            {"fe263...", "b22ac...", ...}
        """
        specs_cfg = cfg.get(config_key, {}).get("pipeline", [])
        result = set()

        for spec_dict in specs_cfg:
            spec = IndicatorSpec(**spec_dict)
            if not spec.save:
                continue
            phash = compute_params_hash(spec.name, spec.params)
            result.add(phash)

        return result

    def get_expected_hashes(self) -> Set[str]:
        """기대하는 params_hash 집합 반환."""
        return self.expected_hashes.copy()

    def is_complete(self, symbol: str, target_date: date) -> bool:
        """
        특정 날짜의 모든 지표가 존재하는지 확인.

        DB에서 해당 (symbol, date)의 params_hash 목록을 조회하고,
        설정에서 기대하는 params_hash가 모두 존재하면 True.

        Args:
            symbol: 종목코드
            target_date: 확인할 날짜

        Returns:
            True: 모든 지표 존재
            False: 일부 또는 전체 지표 누락
        """
        if not self.expected_hashes:
            return True

        sql = text(f"""
            SELECT params_hash
            FROM {self.table}
            WHERE symbol = :symbol AND date = :date
        """)

        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                "symbol": symbol,
                "date": target_date
            })
            existing_hashes = set(row[0] for row in result)

        return self.expected_hashes.issubset(existing_hashes)