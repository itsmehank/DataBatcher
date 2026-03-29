from project_config import get_db_config
from src.real_estate.processing import DataRecalculator


if __name__ == "__main__":
    recalculator = DataRecalculator(db_config=get_db_config())
    recalculator.recalculate_and_update_all()
