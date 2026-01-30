"""Segment Model - Represents business segments for cost allocation."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class SegmentType(Enum):
    """Predefined segment types for the accounting system."""
    RETAIL = "Retail"
    KENYA = "Kenya"
    INDIA = "India"
    CORPORATE = "Corporate"
    POOL = "POOL"  # Shared costs to be allocated


@dataclass
class Segment:
    """
    Represents a business segment for management accounting.
    
    Segments are used to track costs and revenues by business unit:
    - Retail: Direct Wix sales
    - Kenya: Kenya franchise operations
    - India: India franchise operations  
    - Corporate: B2B training sales
    - POOL: Shared costs to be allocated across segments
    """
    
    segment_id: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    allocation_percentage: float = 0.0  # Used for POOL cost allocation
    
    def __post_init__(self):
        """Validate segment data after initialization."""
        if not self.segment_id:
            raise ValueError("Segment ID cannot be empty")
        if not self.name:
            raise ValueError("Segment name cannot be empty")
    
    def to_dict(self) -> dict:
        """Convert segment to dictionary for serialization."""
        return {
            'segment_id': self.segment_id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'allocation_percentage': self.allocation_percentage
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Segment':
        """Create segment from dictionary."""
        return cls(
            segment_id=data.get('segment_id', ''),
            name=data.get('name', ''),
            description=data.get('description'),
            is_active=data.get('is_active', True),
            allocation_percentage=data.get('allocation_percentage', 0.0)
        )
    
    @staticmethod
    def get_default_segments() -> list:
        """Return the default segments for iCare accounting."""
        return [
            Segment('RETAIL', 'Retail (Wix)', 'Direct online sales via Wix platform'),
            Segment('KENYA', 'Franchise-Kenya', 'Kenya franchise operations'),
            Segment('INDIA', 'Franchise-India', 'India franchise operations'),
            Segment('CORPORATE', 'Corporate', 'B2B corporate training sales'),
            Segment('POOL', 'POOL (Shared)', 'Shared costs for pro-rata allocation')
        ]
