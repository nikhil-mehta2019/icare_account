from dataclasses import dataclass
from datetime import date, datetime
from typing import Union

@dataclass
class FinancialYear:
    start_date: date
    end_date: date
    code: str  # Format: YYYY-YY (e.g., 2024-25)

    @classmethod
    def from_date(cls, dt: Union[date, datetime, str]) -> 'FinancialYear':
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except ValueError:
                dt = datetime.now()

        if isinstance(dt, datetime):
            dt = dt.date()
            
        if dt.month >= 4:
            start_year = dt.year
        else:
            start_year = dt.year - 1
            
        end_year = start_year + 1
        code = f"{start_year}-{str(end_year)[-2:]}"
        
        return cls(
            start_date=date(start_year, 4, 1),
            end_date=date(end_year, 3, 31),
            code=code
        )