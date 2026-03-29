from project_config import get_db_config
from src.real_estate.processing import DataAnomalyCorrector


if __name__ == "__main__":
    corrector = DataAnomalyCorrector(db_config=get_db_config())
    corrector.correct_land_area_anomalies()
