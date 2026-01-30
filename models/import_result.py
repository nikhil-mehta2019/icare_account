"""ImportResult Model - Represents results of CSV bulk import."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
from enum import Enum
import uuid

from .voucher import Voucher


class ImportStatus(Enum):
    """Status of an import operation."""
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    COMPLETED_WITH_ERRORS = "Completed with Errors"
    FAILED = "Failed"


@dataclass
class ImportError:
    """Represents an error encountered during import."""
    row_number: int
    column: Optional[str] = None
    error_type: str = ""
    error_message: str = ""
    raw_data: Optional[Dict] = None


@dataclass
class ImportResult:
    """
    Represents the result of a CSV bulk import operation.
    
    Tracks:
    - Import metadata (file, timestamp, user)
    - Successfully parsed vouchers
    - Errors encountered
    - Summary statistics
    """
    
    import_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filename: str = ""
    import_type: str = "CSV"  # "CSV", "Wix Export", "Excel"
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: ImportStatus = ImportStatus.PENDING
    imported_by: str = "System"
    
    # Results
    total_rows: int = 0
    successful_rows: int = 0
    failed_rows: int = 0
    skipped_rows: int = 0
    
    vouchers: List[Voucher] = field(default_factory=list)
    errors: List[ImportError] = field(default_factory=list)
    
    # Preview data (first N rows for display)
    preview_data: List[Dict] = field(default_factory=list)
    column_headers: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_rows == 0:
            return 0.0
        return (self.successful_rows / self.total_rows) * 100
    
    @property
    def has_errors(self) -> bool:
        """Check if import had any errors."""
        return len(self.errors) > 0
    
    @property
    def total_amount(self) -> float:
        """Calculate total amount of imported vouchers."""
        return sum(v.amount for v in self.vouchers)
    
    def add_voucher(self, voucher: Voucher) -> None:
        """Add a successfully parsed voucher."""
        self.vouchers.append(voucher)
        self.successful_rows += 1
    
    def add_error(self, row: int, error_type: str, message: str, 
                  column: str = None, raw_data: Dict = None) -> None:
        """Add an import error."""
        self.errors.append(ImportError(
            row_number=row,
            column=column,
            error_type=error_type,
            error_message=message,
            raw_data=raw_data
        ))
        self.failed_rows += 1
    
    def complete(self, status: ImportStatus = None) -> None:
        """Mark import as completed."""
        self.completed_at = datetime.now()
        if status:
            self.status = status
        elif self.has_errors and self.successful_rows > 0:
            self.status = ImportStatus.COMPLETED_WITH_ERRORS
        elif self.successful_rows > 0:
            self.status = ImportStatus.COMPLETED
        else:
            self.status = ImportStatus.FAILED
    
    def to_dict(self) -> dict:
        """Convert import result to dictionary."""
        return {
            'import_id': self.import_id,
            'filename': self.filename,
            'import_type': self.import_type,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status.value,
            'imported_by': self.imported_by,
            'total_rows': self.total_rows,
            'successful_rows': self.successful_rows,
            'failed_rows': self.failed_rows,
            'skipped_rows': self.skipped_rows,
            'vouchers': [v.to_dict() for v in self.vouchers],
            'errors': [
                {
                    'row_number': e.row_number,
                    'column': e.column,
                    'error_type': e.error_type,
                    'error_message': e.error_message
                } for e in self.errors
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ImportResult':
        """Create import result from dictionary."""
        started_at = data.get('started_at')
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)
        
        completed_at = data.get('completed_at')
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)
        
        status = data.get('status', 'Pending')
        if isinstance(status, str):
            status = ImportStatus(status)
        
        vouchers = [
            Voucher.from_dict(v) for v in data.get('vouchers', [])
        ]
        
        errors = [
            ImportError(
                row_number=e.get('row_number', 0),
                column=e.get('column'),
                error_type=e.get('error_type', ''),
                error_message=e.get('error_message', '')
            ) for e in data.get('errors', [])
        ]
        
        return cls(
            import_id=data.get('import_id', str(uuid.uuid4())),
            filename=data.get('filename', ''),
            import_type=data.get('import_type', 'CSV'),
            started_at=started_at or datetime.now(),
            completed_at=completed_at,
            status=status,
            imported_by=data.get('imported_by', 'System'),
            total_rows=data.get('total_rows', 0),
            successful_rows=data.get('successful_rows', 0),
            failed_rows=data.get('failed_rows', 0),
            skipped_rows=data.get('skipped_rows', 0),
            vouchers=vouchers,
            errors=errors
        )
