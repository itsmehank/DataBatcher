# -*- coding: utf-8 -*-
"""
FDR KRX-DESC 세분류 섹터 로더

FinanceDataReader의 StockListing('KRX-DESC')를 사용하여
한국 주식의 세분류 섹터(Sector)와 산업(Industry) 정보를 가져옵니다.

주요 기능:
- KRX-DESC의 Sector → sector_detail (약 162개 세분류)
- KRX-DESC의 Industry → industry

작성일: 2026-02-08
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def fetch_fdr_krx_sectors() -> pd.DataFrame:
    """
    FDR KRX-DESC에서 세분류 섹터 및 산업 정보 조회

    Returns:
        DataFrame with columns:
        - Code: 종목코드 (str)
        - sector_detail: 세분류 섹터명 (str, 약 162개)
        - industry: 산업 분류 (str)

    Note:
        실패 시 빈 DataFrame 반환 (non-fatal)
    """
    try:
        import FinanceDataReader as fdr
    except ImportError:
        logger.warning("FinanceDataReader not installed, skipping KRX-DESC sector fetch")
        return pd.DataFrame(columns=['Code', 'sector_detail', 'industry'])

    try:
        logger.info("Fetching KRX-DESC listing from FDR...")
        df = fdr.StockListing('KRX-DESC')

        if df is None or df.empty:
            logger.warning("FDR KRX-DESC returned empty result")
            return pd.DataFrame(columns=['Code', 'sector_detail', 'industry'])

        # 컬럼명 확인 - FDR은 Code, Sector, Industry 컬럼 반환
        code_col = None
        for candidate in ['Code', 'code', 'Symbol', 'symbol']:
            if candidate in df.columns:
                code_col = candidate
                break

        if code_col is None:
            logger.warning(f"No code column found in KRX-DESC. Columns: {df.columns.tolist()}")
            return pd.DataFrame(columns=['Code', 'sector_detail', 'industry'])

        result = pd.DataFrame({'Code': df[code_col].astype(str)})

        # Sector → sector_detail
        sector_col = None
        for candidate in ['Sector', 'sector']:
            if candidate in df.columns:
                sector_col = candidate
                break
        result['sector_detail'] = df[sector_col].values if sector_col else None

        # Industry
        industry_col = None
        for candidate in ['Industry', 'industry']:
            if candidate in df.columns:
                industry_col = candidate
                break
        result['industry'] = df[industry_col].values if industry_col else None

        non_null_sector = result['sector_detail'].notna().sum()
        non_null_industry = result['industry'].notna().sum()
        logger.info(
            f"KRX-DESC: {len(result)} symbols, "
            f"sector_detail: {non_null_sector} non-null ({result['sector_detail'].nunique()} unique), "
            f"industry: {non_null_industry} non-null"
        )

        return result

    except Exception as e:
        logger.warning(f"Failed to fetch KRX-DESC sectors: {e}")
        return pd.DataFrame(columns=['Code', 'sector_detail', 'industry'])


__all__ = ['fetch_fdr_krx_sectors']
