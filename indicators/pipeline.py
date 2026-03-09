# indicators/pipeline.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Dict, Any
import pandas as pd
from indicators.registry import IndicatorRegistry
from indicators.base_indicator import IndicatorParams
from core.params import params_hash


@dataclass
class IndicatorSpec:
    name: str
    params: Dict[str, Any]
    save: bool = True


class IndicatorPipeline:
    def __init__(self, specs: Iterable[IndicatorSpec]):
        self.specs = list(specs)

    def warmup_days(self) -> int:
        max_warmup = 0
        for s in self.specs:
            cls = IndicatorRegistry.get(s.name)()
            max_warmup = max(max_warmup, cls.warmup(IndicatorParams(s.name, s.params)))
        return max_warmup

    def run(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        out: Dict[str, pd.Series] = {}
        for s in self.specs:
            ind = IndicatorRegistry.get(s.name)()
            p = IndicatorParams(s.name, s.params)
            res = ind.compute(df, p)
            if isinstance(res, dict):
                for k, series in res.items():
                    out[k] = series
            else:
                out[res.name] = res
        return out

    def to_long_dataframe(
        self,
        symbol: str,
        market: str,
        source: str,
        outputs: Dict[str, pd.Series],
        keep_nan: bool = False,
    ) -> pd.DataFrame:
        rows: list[pd.DataFrame] = []
        for key, series in outputs.items():
            # key는 보통 "sma_20_close" 같은 완성된 indicator 문자열.
            # 여기서 params_hash는 반드시 "실제 spec(params)" 기반으로 계산되어야 한다.
            # 기존 구현처럼 key prefix("sma")만으로 spec을 찾으면,
            # 여러 SMA(window=20/50/100/200)가 모두 같은 spec(params)을 매칭해
            # 동일 params_hash가 생성되고 PK(symbol,date,indicator,params_hash) 충돌로 저장이 누락된다.
            ind_name = key.split("_")[0]
            # key와 정확히 일치하는 spec을 우선 찾고, 없으면 name만 일치하는 첫 spec으로 fallback
            spec_match = next((s for s in self.specs if f"{s.name}_{s.params.get('window', '')}" in key), None)
            if spec_match is None:
                spec_match = next((s for s in self.specs if s.name == ind_name), None)
            p_hash = params_hash(ind_name, spec_match.params if spec_match else {})
            df_tmp = series.to_frame("value")
            df_tmp["symbol"] = symbol
            df_tmp["market"] = market
            df_tmp["source"] = source
            df_tmp["indicator"] = key
            df_tmp["params_hash"] = p_hash
            df_tmp = df_tmp.reset_index().rename(columns={df_tmp.index.name or "index": "date"})
            if "date" not in df_tmp.columns:
                # fallback if index name wasn't preserved
                df_tmp = df_tmp.rename(columns={df_tmp.columns[0]: "date"})
            rows.append(df_tmp[["symbol", "date", "indicator", "params_hash", "value", "market", "source"]])
        if not rows:
            return pd.DataFrame()
        result: pd.DataFrame = pd.concat(rows, axis=0, ignore_index=True)
        if not keep_nan:
            # Drop rows with NaN values (warmup period before indicator can be calculated)
            result = result.dropna(subset=["value"])
        return result
