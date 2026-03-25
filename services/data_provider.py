from config.settings import USE_CENTRAL_DB
from services.data_service import DataService
from services.database_data_service import DatabaseDataService

class DataProvider:
    """Provides the active data service based on environment configuration."""
    _instance = None

    @classmethod
    def get_service(cls) -> DataService:
        if cls._instance is None:
            if USE_CENTRAL_DB:
                print("INIT: Using Centralized PostgreSQL Database")
                cls._instance = DatabaseDataService()
            else:
                print("INIT: Using Local JSON File Storage")
                cls._instance = DataService()
        return cls._instance