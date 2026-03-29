from src.real_estate.analyzers.above_ground import AboveGroundBuildingAnalyzer
from src.real_estate.analyzers.below_ground import BelowGroundBuildingAnalyzer
from src.real_estate.analyzers.building_level import BuildingLevelAnalyzer
from src.real_estate.analyzers.building_level_two import BuildingLevelAnalyzer as BuildingLevelAnalyzerTwo


def test_analyzer_floor_conditions():
    db_config = {"host": "localhost", "port": 3306, "user": "u", "password": "p", "database": "d"}

    assert AboveGroundBuildingAnalyzer(db_config).floor_condition == "floor >= 1"
    assert BelowGroundBuildingAnalyzer(db_config).floor_condition == "floor <= -1"
    assert BuildingLevelAnalyzer(db_config).floor_condition is None
    assert BuildingLevelAnalyzerTwo(db_config).floor_condition is None


def test_building_level_two_avg_deal_column():
    db_config = {"host": "localhost", "port": 3306, "user": "u", "password": "p", "database": "d"}
    analyzer = BuildingLevelAnalyzerTwo(db_config)
    assert analyzer.avg_deal_column == "avg_deal_amount"
    assert analyzer.parse_deal_amount is True
