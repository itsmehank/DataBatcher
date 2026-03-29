# Legacy Files

이 디렉토리는 현재 표준 실행 경로에서 사용하지 않는 구버전/실험 스크립트를 보관합니다.

## 원칙

- 기본 운영은 `python -m src.real_estate.cli ...` 경로를 사용합니다.
- legacy 파일은 기본 배포/운영 경로에 포함하지 않습니다.
- 필요 시 참고/비교 목적으로만 사용합니다.

## 하위 분류

- `legacy/analyzers/`: 과거 분석기 버전
- `legacy/detectors/`: 백업/원본 감지기 버전
- `legacy/maps/`: 지도 관련 백업/실험 스크립트
- `legacy/misc/`: 기타 실험성 유틸
- `legacy/processing/`: 이전 처리 스크립트 wrapper
- `legacy/wrappers/`: 루트 실행 호환 wrapper

## 현재 이동된 주요 파일

- `legacy/analyzers/RealEstateAnalyzerOld.py`
- `legacy/detectors/DistrictSurgeDetector_Back.py`
- `legacy/detectors/SurgeDetector_Original.py`
- `legacy/detectors/SurgeDetector.py`
- `legacy/detectors/FlexibleSurgeDetector.py`
- `legacy/detectors/ClusterSurgeDetector.py`
- `legacy/maps/map_utils_back.py`
- `legacy/maps/test.py`
- `legacy/maps/test2.py`
- `legacy/maps/test3.py`
- `legacy/maps/test4.py`
- `legacy/misc/api_test.py`
- `legacy/misc/check_land_size.py`
- `legacy/processing/DataAnomalyCorrector.py`
- `legacy/processing/DataRecalculator.py`
- `legacy/wrappers/RealEstateDataManager.py`
- `legacy/wrappers/RealEstateAnalyzer.py`
- `legacy/wrappers/CombinedSurgeDetector.py`
- `legacy/wrappers/DistrictSurgeDetector.py`
- `legacy/wrappers/AboveGroundBuildingAnalyzer.py`
- `legacy/wrappers/BelowGroundBuildingAnalyzer.py`
- `legacy/wrappers/BuildingLevelAnalyzer.py`
- `legacy/wrappers/BuildingLevelAnalyzerTwo.py`
