from services.database_data_service import DatabaseDataService

class DataProvider:
    """Single point of entry for data persistence. Strictly PostgreSQL."""
    
    _db_service = None

    @classmethod
    def get_service(cls) -> DatabaseDataService:
        if cls._db_service is None:
            cls._db_service = DatabaseDataService()
        return cls._db_service