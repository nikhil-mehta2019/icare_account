"""Narration Model - Represents pre-approved narration templates."""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Narration:
    """
    Represents a pre-approved narration template.
    
    Narrations are linked to specific account heads and must be
    selected from dropdowns - users cannot type custom narrations.
    This ensures data consistency for Tally import.
    """
    
    narration_id: str
    account_code: str  # Linked account head code
    template: str  # The narration template text
    has_placeholder: bool = False  # Whether template has [ID] placeholder
    placeholder_label: Optional[str] = None  # Label for placeholder input
    is_active: bool = True
    
    def __post_init__(self):
        """Validate narration data after initialization."""
        if not self.narration_id:
            raise ValueError("Narration ID cannot be empty")
        if not self.template:
            raise ValueError("Narration template cannot be empty")
        
        # Check for placeholders in template
        if '[' in self.template and ']' in self.template:
            self.has_placeholder = True
    
    def format_narration(self, placeholder_value: str = "") -> str:
        """
        Format the narration by replacing placeholders.
        
        Args:
            placeholder_value: Value to replace [ID] or other placeholders
            
        Returns:
            Formatted narration string
        """
        if self.has_placeholder and placeholder_value:
            # Replace common placeholders
            result = self.template.replace('[ID]', placeholder_value)
            result = result.replace('[Client Name]', placeholder_value)
            return result
        return self.template
    
    def to_dict(self) -> dict:
        """Convert narration to dictionary for serialization."""
        return {
            'narration_id': self.narration_id,
            'account_code': self.account_code,
            'template': self.template,
            'has_placeholder': self.has_placeholder,
            'placeholder_label': self.placeholder_label,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Narration':
        """Create narration from dictionary."""
        return cls(
            narration_id=data.get('narration_id', ''),
            account_code=data.get('account_code', ''),
            template=data.get('template', ''),
            has_placeholder=data.get('has_placeholder', False),
            placeholder_label=data.get('placeholder_label'),
            is_active=data.get('is_active', True)
        )
