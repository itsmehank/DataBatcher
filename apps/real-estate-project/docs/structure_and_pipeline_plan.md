# Structure and Pipeline Plan

## Goal

Split the project into 4 operational domains plus legacy, then keep one standard runtime path via CLI.

## Standard Runtime Sequence

1. `python -m src.real_estate.cli validate-config --require-api-key`
2. `python -m src.real_estate.cli init-db`
3. `python -m src.real_estate.cli ingest --lawd-cds 11650 --start-ymd 202401 --end-ymd 202402`
4. Optional quality pass:
   - `python -m src.real_estate.cli clean-anomalies`
   - `python -m src.real_estate.cli recalculate-derived`
5. `python -m src.real_estate.cli analyze`
6. `python -m src.real_estate.cli serve-web --port 5001`

## What Each Processing File Produces

- `src/real_estate/ingestion/data_manager.py`
  - Source: Ministry API
  - Target tables: `rh_trade_analysis`, `data_ingestion_log`

- `src/real_estate/processing/anomaly_corrector.py`
  - Source: `rh_trade_analysis`
  - Action: updates anomalous `landAr`

- `src/real_estate/processing/recalculator.py`
  - Source: `rh_trade_analysis`
  - Action: recalculates `land_price_per_pyeong`, `land_share_ratio`

- `src/real_estate/analysis/monthly_dong.py`
  - Source: `rh_trade_analysis`
  - Target tables: `monthly_dong_analysis`, `analysis_log_dong`

- `src/real_estate/analyzers/above_ground.py`
  - Source: `rh_trade_analysis` (`floor >= 1`)
  - Target tables: `building_transaction_analysis_above_ground`, `analysis_log_building_above_ground`

- `src/real_estate/analyzers/below_ground.py`
  - Source: `rh_trade_analysis` (`floor <= -1`)
  - Target tables: `building_transaction_analysis_below_ground`, `analysis_log_building_below_ground`

- `src/real_estate/analyzers/building_level.py` / `src/real_estate/analyzers/building_level_two.py`
  - Source: `rh_trade_analysis` (all floors)
  - Target table: `building_transaction_analysis`
  - Status: optional/alternative analysis path, not required by the current default web flow

## 4-Domain Classification

### 1) Data Ingestion/Processing/Loading

- `src/real_estate/analyzers/*`
- `src/real_estate/ingestion/*`
- `src/real_estate/analysis/*`
- `src/real_estate/processing/*`
- `legacy/wrappers/*` (backward compatibility wrappers)

### 2) Backend

- `web_ui/app.py` (thin wrapper)
- `building_query/building_transaction_query.py`
- `src/real_estate/cli.py`
- `src/real_estate/backend/runtime.py`
- `src/real_estate/backend/web_app.py`
- `project_config.py`

### 3) Frontend

- `web_ui/templates/index_v2.html`
- `web_ui/templates/building_detail.html`
- `web_ui/static/*`
- `src/real_estate/frontend/*` (path helper)

### 4) Criteria-Based Extraction and Mapping

- `src/real_estate/detectors/combined.py`
- `src/real_estate/detectors/district.py`
- `map_drawing/map_utils.py`
- `src/real_estate/maps/*`

## Legacy Candidate Files

Moved in phase-1 segregation:

- `legacy/analyzers/RealEstateAnalyzerOld.py`
- `legacy/detectors/DistrictSurgeDetector_Back.py`
- `legacy/detectors/SurgeDetector_Original.py`
- `legacy/maps/map_utils_back.py`
- `legacy/maps/test.py`
- `legacy/maps/test2.py`
- `legacy/maps/test3.py`
- `legacy/maps/test4.py`
- `legacy/misc/api_test.py`
- `legacy/misc/check_land_size.py`

Moved in phase-2 segregation:

- `legacy/detectors/SurgeDetector.py`
- `legacy/detectors/FlexibleSurgeDetector.py`
- `legacy/detectors/ClusterSurgeDetector.py`

Map output consolidation:

- old `maps/` and `maps_kakao/` directories were consolidated into `map_images/`
- old files moved to:
  - `map_images/legacy_maps/seoul_map.html`
  - `map_images/legacy_maps_kakao/seoul_map_kakao.html`
- additional cleanup completed:
  - removed `map_drawing/maps/`
  - removed `map_drawing/maps_kakao/`
  - removed empty `disco/`
  - moved `data_processing/` to `legacy/processing/`

## Migration Gates

1. Baseline gate
   - `pytest -q tests -m "not db"`
2. DB gate
   - init-db succeeds
   - required tables exist
3. Data gate
   - `rh_trade_analysis` row count > 0
   - analysis tables row count > 0
4. Web gate
   - `GET /` returns 200
   - `/combined_analysis` returns success
   - `/district_analysis` returns success
5. Compatibility gate
   - legacy wrapper imports still work
