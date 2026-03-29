from .base import BaseBuildingAnalyzer


class BuildingLevelAnalyzer(BaseBuildingAnalyzer):
    def __init__(self, db_config):
        super().__init__(
            db_config,
            floor_condition=None,
            log_table_name="analysis_log_building",
            table_comment="월별 건물단위(지번+건축년도) 연립다세대 거래 분석",
            log_comment="건물단위(지번+건축년도) 분석 작업 로그",
            analyzer_label="전체",
            avg_deal_column="avg_dealAmount",
            avg_deal_sql_type="BIGINT",
            parse_deal_amount=False,
        )
