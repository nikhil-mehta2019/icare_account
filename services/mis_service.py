"""MIS Service - Handles Management Information System report generation via PostgreSQL."""

from datetime import datetime
from typing import List, Dict, Optional, Any
import os
import pandas as pd

from services.data_provider import DataProvider

class MISService:
    """
    Handles generation of Management Accounting reports.
    Strictly queries PostgreSQL for aggregated data.
    """
    
    def __init__(self):
        self.db = DataProvider.get_service()
        
        # segments configuration
        self.segments = ['Retail', 'Kenya', 'India', 'Corporate', 'Placement']
        
        # Ledger keywords for classification
        self.revenue_keywords = ['sales', 'income', 'revenue', 'fees']
        self.direct_cost_keywords = ['purchase', 'cost of goods', 'direct', 'wages', 'salary', 'freight']
        self.indirect_cost_keywords = ['rent', 'electricity', 'internet', 'audit', 'legal', 'office']

    def calculate_mis(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Query DB and calculate MIS report data with segment-wise breakdown.
        """
        # 1. Fetch Flat Data from PostgreSQL
        query = """
            SELECT 
                COALESCE(v.segment, 'Unknown') as segment,
                h.name as ledger_name,
                v.voucher_type,
                v.amount
            FROM vouchers v
            LEFT JOIN master_account_heads h ON v.account_code = h.code
            WHERE v.voucher_date >= %s AND v.voucher_date <= %s
              AND v.status != 'Deleted'
        """
        rows = self.db.execute_read(query, (start_date, end_date))
        
        # 2. Initialize Report Structure
        result = {
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            },
            'segments': {seg: self._get_empty_metrics() for seg in self.segments},
            'total': self._get_empty_metrics()
        }
        
        # 3. Process Rows
        for row in rows:
            segment = str(row['segment']).strip().title()
            
            # Group unknown or missing segments into Corporate as fallback, or map dynamically
            if segment not in result['segments']:
                if segment not in self.segments:
                     segment = 'Corporate' # Default bucket
            
            metrics = result['segments'][segment]
            
            amt = float(row['amount'] or 0.0)
            ledger_name = str(row['ledger_name'] or '').lower()
            v_type = str(row['voucher_type'] or '').upper()

            # Classification Logic
            if self._is_revenue(ledger_name) or v_type in ['RECEIPT', 'CREDIT']:
                metrics['gmv'] += amt
                result['total']['gmv'] += amt
            elif self._is_direct_cost(ledger_name) or v_type in ['PAYMENT', 'PURCHASE', 'PAYROLL', 'DEBIT']:
                metrics['direct_costs'] += amt
                result['total']['direct_costs'] += amt

        # 4. Calculate Derived Metrics (Margins & Profits)
        self._calculate_derived_metrics(result['total'])
        for seg in self.segments:
            self._calculate_derived_metrics(result['segments'][seg])
            
        return result

    def get_gross_profit_summary(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Get a simplified gross profit summary for dashboards.
        """
        mis_data = self.calculate_mis(start_date, end_date)
        return {
            'total_revenue': mis_data['total']['net_revenue'],
            'total_costs': mis_data['total']['total_variable_cost'],
            'gross_profit': mis_data['total']['gross_profit'],
            'gross_margin': mis_data['total']['gross_margin']
        }

    def _get_empty_metrics(self) -> Dict[str, float]:
        return {
            'gmv': 0.0, 'returns': 0.0, 'net_revenue': 0.0,
            'direct_costs': 0.0, 'allocated_costs': 0.0,
            'total_variable_cost': 0.0, 'gross_profit': 0.0, 'gross_margin': 0.0
        }

    def _calculate_derived_metrics(self, metrics: Dict):
        """Calculate Net Revenue, Total Costs, and Margins in-place."""
        metrics['net_revenue'] = metrics['gmv'] - metrics['returns']
        metrics['total_variable_cost'] = metrics['direct_costs'] + metrics['allocated_costs']
        metrics['gross_profit'] = metrics['net_revenue'] - metrics['total_variable_cost']
        
        if metrics['net_revenue'] > 0:
            metrics['gross_margin'] = (metrics['gross_profit'] / metrics['net_revenue']) * 100
        else:
            metrics['gross_margin'] = 0.0

    def _is_revenue(self, ledger_name: str) -> bool:
        return any(k in ledger_name for k in self.revenue_keywords)

    def _is_direct_cost(self, ledger_name: str) -> bool:
        return any(k in ledger_name for k in self.direct_cost_keywords)

    def export_mis_excel(self, mis_data: Dict, output_path: str) -> str:
        try:
            import xlsxwriter
            workbook = xlsxwriter.Workbook(output_path)
            worksheet = workbook.add_worksheet('MIS Report')
            
            # Formats
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#00A4A6', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            metric_label_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#f5f5f5'})
            currency_fmt = workbook.add_format({'num_format': '₹ #,##0.00', 'border': 1})
            percent_fmt = workbook.add_format({'num_format': '0.00%', 'border': 1, 'bold': True})
            title_fmt = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'})

            # Title
            segment_names = list(mis_data.get('segments', {}).keys())
            total_cols = len(segment_names) + 2 
            worksheet.merge_range(0, 0, 0, total_cols - 1, 'Management Accounting Dashboard (Segment-Wise)', title_fmt)
            
            # Headers
            headers = ['Metric', 'Total Company'] + segment_names
            worksheet.set_row(2, 30)
            for col, header in enumerate(headers):
                worksheet.write(2, col, header, header_fmt)
            
            # Rows
            rows_config = [
                ('GMV (Gross Sales)', 'gmv', currency_fmt),
                ('Less: Returns/Refunds', 'returns', currency_fmt),
                ('Net Revenue (A)', 'net_revenue', currency_fmt),
                ('Direct Costs (Directly Tagged)', 'direct_costs', currency_fmt),
                ('Allocated Shared Costs (Pool)', 'allocated_costs', currency_fmt),
                ('Total Variable Cost (B)', 'total_variable_cost', currency_fmt),
                ('GROSS PROFIT (A - B)', 'gross_profit', currency_fmt),
                ('Gross Margin %', 'gross_margin', percent_fmt)
            ]
            
            for i, (label, key, fmt) in enumerate(rows_config):
                row = 3 + i
                worksheet.write(row, 0, label, metric_label_fmt)
                
                # Total
                total_val = mis_data.get('total', {}).get(key, 0.0)
                if key == 'gross_margin': total_val /= 100
                worksheet.write(row, 1, total_val, fmt)
                
                # Segments
                for col, seg in enumerate(segment_names, start=2):
                    val = mis_data.get('segments', {}).get(seg, {}).get(key, 0.0)
                    if key == 'gross_margin': val /= 100
                    worksheet.write(row, col, val, fmt)

            worksheet.set_column(0, 0, 35)
            worksheet.set_column(1, total_cols - 1, 18)
            workbook.close()
            return output_path
            
        except Exception as e:
            # Fallback
            df_data = []
            for key in ['gmv', 'net_revenue', 'direct_costs', 'gross_profit']:
                row = {'Metric': key, 'Total': mis_data['total'][key]}
                for seg, vals in mis_data['segments'].items():
                    row[seg] = vals[key]
                df_data.append(row)
            pd.DataFrame(df_data).to_excel(output_path, index=False)
            return output_path