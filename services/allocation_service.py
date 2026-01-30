"""Allocation Service - Handles POOL cost allocation across segments."""

from datetime import datetime
from typing import List, Dict, Optional
from decimal import Decimal, ROUND_HALF_UP

from models.voucher import Voucher
from models.account_head import VoucherType


class AllocationService:
    """
    Handles the allocation of POOL (shared) costs across business segments.
    
    Allocation is based on pro-rata share of Net Sales:
    - Calculate total net sales (codes 1000-1999) for each segment
    - Calculate each segment's percentage of total sales
    - Multiply POOL expenses by segment percentage
    """
    
    def __init__(self):
        """Initialize allocation service."""
        pass
    
    def allocate_pool_costs(self, vouchers: List[Voucher], 
                           start_date: datetime = None,
                           end_date: datetime = None) -> Dict[str, Dict]:
        """
        Allocate POOL costs across segments based on sales pro-rata.
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        
        Steps:
        A. Sum Total Net Sales (Codes 1000-1999)
        B. Calculate Segment % (e.g., Kenya Sales / Total Sales)
        C. Multiply the "POOL" expense by the Segment % to get Allocated Cost
        
        Args:
            vouchers: List of vouchers to process
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dict with allocation results per segment:
            {
                'Retail': {'sales': 1000, 'percentage': 50.0, 'allocated_cost': 500},
                'Kenya': {'sales': 600, 'percentage': 30.0, 'allocated_cost': 300},
                ...
            }
        """
        # TODO: BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        
        # Filter vouchers by date range if provided
        filtered = vouchers
        if start_date:
            filtered = [v for v in filtered if v.date >= start_date]
        if end_date:
            filtered = [v for v in filtered if v.date <= end_date]
        
        # Step A: Calculate net sales by segment (codes 1000-1999)
        segment_sales = self._calculate_segment_sales(filtered)
        
        # Step B: Calculate percentages
        total_sales = sum(segment_sales.values())
        segment_percentages = {}
        if total_sales > 0:
            for segment, sales in segment_sales.items():
                segment_percentages[segment] = (sales / total_sales) * 100
        
        # Step C: Get total POOL costs and allocate
        pool_costs = self._calculate_pool_costs(filtered)
        
        # Build result
        result = {}
        for segment in segment_sales.keys():
            percentage = segment_percentages.get(segment, 0)
            allocated = (pool_costs * percentage / 100) if percentage > 0 else 0
            
            result[segment] = {
                'sales': segment_sales.get(segment, 0),
                'percentage': round(percentage, 2),
                'allocated_cost': round(allocated, 2)
            }
        
        # Add total POOL costs to result
        result['_pool_total'] = pool_costs
        result['_total_sales'] = total_sales
        
        return result
    
    def _calculate_segment_sales(self, vouchers: List[Voucher]) -> Dict[str, float]:
        """
        Calculate total sales by segment.
        
        Only includes codes 1000-1999 (Operating Sales).
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        """
        # TODO: BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        segment_sales = {}
        
        for voucher in vouchers:
            # Check if this is a sales code (1000-1999)
            try:
                code = int(voucher.account_code)
                if 1000 <= code < 2000:
                    segment = voucher.segment
                    if segment and segment != 'POOL':
                        segment_sales[segment] = segment_sales.get(segment, 0) + voucher.amount
            except (ValueError, TypeError):
                continue
        
        return segment_sales
    
    def _calculate_pool_costs(self, vouchers: List[Voucher]) -> float:
        """
        Calculate total POOL costs.
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        """
        # TODO: BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        total = 0.0
        
        for voucher in vouchers:
            if voucher.segment == 'POOL' and voucher.voucher_type == VoucherType.DEBIT:
                total += voucher.amount
        
        return total
    
    def get_allocation_summary(self, vouchers: List[Voucher],
                              start_date: datetime = None,
                              end_date: datetime = None) -> Dict:
        """
        Get a summary of cost allocation.
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        """
        # TODO: BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        allocations = self.allocate_pool_costs(vouchers, start_date, end_date)
        
        return {
            'total_sales': allocations.get('_total_sales', 0),
            'total_pool_costs': allocations.get('_pool_total', 0),
            'allocations': {k: v for k, v in allocations.items() if not k.startswith('_')}
        }
    
    def validate_allocation(self, allocations: Dict) -> bool:
        """
        Validate that allocations sum correctly.
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        """
        # TODO: BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        total_allocated = sum(
            v.get('allocated_cost', 0) 
            for k, v in allocations.items() 
            if not k.startswith('_') and isinstance(v, dict)
        )
        pool_total = allocations.get('_pool_total', 0)
        
        # Allow for small rounding differences
        return abs(total_allocated - pool_total) < 0.01
