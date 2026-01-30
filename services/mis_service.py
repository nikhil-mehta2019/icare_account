"""MIS Service - Handles Management Information System report generation."""

from datetime import datetime
from typing import List, Dict, Optional
import os

from models.voucher import Voucher
from models.account_head import VoucherType


class MISService:
    """
    Handles generation of Management Accounting reports.
    
    Generates:
    - Segment-wise Profitability Report
    - Gross Profit Analysis
    - Cost Allocation Summary
    """
    
    def __init__(self):
        """Initialize MIS service."""
        pass
    
    def calculate_mis(self, vouchers: List[Voucher],
                     start_date: datetime = None,
                     end_date: datetime = None) -> Dict:
        """
        Calculate MIS report data.
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        
        Report Format:
        | Metric                    | Total | Retail | Kenya | India |
        |---------------------------|-------|--------|-------|-------|
        | GMV (Gross Sales)         |       |        |       |       |
        | Less: Returns/Refunds     |       |        |       |       |
        | Net Revenue (A)           |       |        |       |       |
        | Direct Costs              |       |        |       |       |
        | Allocated Shared Costs    |       |        |       |       |
        | Total Variable Cost (B)   |       |        |       |       |
        | GROSS PROFIT (A - B)      |       |        |       |       |
        | Gross Margin %            |       |        |       |       |
        
        Args:
            vouchers: List of vouchers to analyze
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dict with MIS data structure
        """
        # TODO: BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        
        # Filter vouchers by date
        filtered = self._filter_by_date(vouchers, start_date, end_date)
        
        # Initialize segments
        segments = ['Retail', 'Kenya', 'India', 'Corporate']
        
        # Calculate metrics for each segment
        result = {
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            },
            'segments': {},
            'total': {}
        }
        
        total_metrics = {
            'gmv': 0,
            'returns': 0,
            'net_revenue': 0,
            'direct_costs': 0,
            'allocated_costs': 0,
            'total_variable_cost': 0,
            'gross_profit': 0,
            'gross_margin': 0
        }
        
        for segment in segments:
            metrics = self._calculate_segment_metrics(filtered, segment)
            result['segments'][segment] = metrics
            
            # Add to totals
            for key in total_metrics.keys():
                if key != 'gross_margin':
                    total_metrics[key] += metrics.get(key, 0)
        
        # Calculate total gross margin
        if total_metrics['net_revenue'] > 0:
            total_metrics['gross_margin'] = (
                total_metrics['gross_profit'] / total_metrics['net_revenue']
            ) * 100
        
        result['total'] = total_metrics
        
        return result
    
    def _calculate_segment_metrics(self, vouchers: List[Voucher], 
                                  segment: str) -> Dict:
        """
        Calculate metrics for a specific segment.
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        """
        # TODO: BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        
        segment_vouchers = [v for v in vouchers if v.segment == segment]
        
        # Calculate GMV (Gross Sales) - codes 1000-1999
        gmv = sum(
            v.amount for v in segment_vouchers
            if v.voucher_type == VoucherType.CREDIT
            and self._is_sales_code(v.account_code)
        )
        
        # Returns/Refunds (placeholder - would need specific code range)
        returns = 0  # TODO: Implement returns tracking
        
        # Net Revenue
        net_revenue = gmv - returns
        
        # Direct Costs (codes 5000-5999, directly tagged to segment)
        direct_costs = sum(
            v.amount for v in segment_vouchers
            if v.voucher_type == VoucherType.DEBIT
            and self._is_direct_cost_code(v.account_code)
        )
        
        # Allocated Costs (from POOL - placeholder)
        allocated_costs = 0  # TODO: Get from allocation service
        
        # Calculate derived metrics
        total_variable_cost = direct_costs + allocated_costs
        gross_profit = net_revenue - total_variable_cost
        gross_margin = (gross_profit / net_revenue * 100) if net_revenue > 0 else 0
        
        return {
            'gmv': round(gmv, 2),
            'returns': round(returns, 2),
            'net_revenue': round(net_revenue, 2),
            'direct_costs': round(direct_costs, 2),
            'allocated_costs': round(allocated_costs, 2),
            'total_variable_cost': round(total_variable_cost, 2),
            'gross_profit': round(gross_profit, 2),
            'gross_margin': round(gross_margin, 2)
        }
    
    def _is_sales_code(self, code: str) -> bool:
        """Check if code is in sales range (1000-1999)."""
        try:
            code_int = int(code)
            return 1000 <= code_int < 2000
        except (ValueError, TypeError):
            return False
    
    def _is_direct_cost_code(self, code: str) -> bool:
        """Check if code is in direct cost range (5000-5999)."""
        try:
            code_int = int(code)
            return 5000 <= code_int < 6000
        except (ValueError, TypeError):
            return False
    
    def _filter_by_date(self, vouchers: List[Voucher],
                       start_date: datetime = None,
                       end_date: datetime = None) -> List[Voucher]:
        """Filter vouchers by date range."""
        filtered = vouchers
        if start_date:
            filtered = [v for v in filtered if v.date >= start_date]
        if end_date:
            filtered = [v for v in filtered if v.date <= end_date]
        return filtered
    
    def export_mis_excel(self, mis_data: Dict, output_path: str) -> str:
        """
        Export MIS report to Excel file.
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        
        Args:
            mis_data: MIS data from calculate_mis()
            output_path: Path for output Excel file
            
        Returns:
            Path to generated Excel file
        """
        # TODO: BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        # Use openpyxl or XlsxWriter to create Excel file
        
        try:
            import xlsxwriter
            
            workbook = xlsxwriter.Workbook(output_path)
            worksheet = workbook.add_worksheet('MIS Report')
            
            # Formats
            header_fmt = workbook.add_format({
                'bold': True, 'bg_color': '#00A4A6', 'font_color': 'white',
                'border': 1, 'align': 'center'
            })
            money_fmt = workbook.add_format({'num_format': '₹ #,##0.00', 'border': 1})
            pct_fmt = workbook.add_format({'num_format': '0.00%', 'border': 1})
            label_fmt = workbook.add_format({'bold': True, 'border': 1})
            
            # Title
            worksheet.merge_range('A1:F1', 'Management Accounting Dashboard (Segment-Wise)', 
                                 workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'}))
            
            # Headers
            headers = ['Metric', 'Total Company', 'Retail (Wix)', 'Kenya Franchise', 
                      'India Franchise', 'Corporate']
            for col, header in enumerate(headers):
                worksheet.write(2, col, header, header_fmt)
            
            # Metrics
            metrics = [
                ('GMV (Gross Sales)', 'gmv'),
                ('Less: Returns/Refunds', 'returns'),
                ('Net Revenue (A)', 'net_revenue'),
                ('Direct Costs (Directly Tagged)', 'direct_costs'),
                ('Allocated Shared Costs (Pool)', 'allocated_costs'),
                ('Total Variable Cost (B)', 'total_variable_cost'),
                ('GROSS PROFIT (A - B)', 'gross_profit'),
                ('Gross Margin %', 'gross_margin')
            ]
            
            segments = ['total', 'Retail', 'Kenya', 'India', 'Corporate']
            
            for row_idx, (label, key) in enumerate(metrics, start=3):
                worksheet.write(row_idx, 0, label, label_fmt)
                
                for col_idx, segment in enumerate(segments, start=1):
                    if segment == 'total':
                        value = mis_data.get('total', {}).get(key, 0)
                    else:
                        value = mis_data.get('segments', {}).get(segment, {}).get(key, 0)
                    
                    if key == 'gross_margin':
                        worksheet.write(row_idx, col_idx, value / 100, pct_fmt)
                    else:
                        worksheet.write(row_idx, col_idx, value, money_fmt)
            
            # Adjust column widths
            worksheet.set_column(0, 0, 35)
            worksheet.set_column(1, 5, 18)
            
            workbook.close()
            return output_path
        
        except ImportError:
            # Fallback if xlsxwriter not available
            return None
        except Exception as e:
            print(f"Error creating Excel: {e}")
            return None
    
    def get_gross_profit_summary(self, vouchers: List[Voucher],
                                start_date: datetime = None,
                                end_date: datetime = None) -> Dict:
        """
        Get a simplified gross profit summary.
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        """
        # TODO: BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        mis_data = self.calculate_mis(vouchers, start_date, end_date)
        
        return {
            'total_revenue': mis_data['total']['net_revenue'],
            'total_costs': mis_data['total']['total_variable_cost'],
            'gross_profit': mis_data['total']['gross_profit'],
            'gross_margin': mis_data['total']['gross_margin']
        }
