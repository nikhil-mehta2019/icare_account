"""MIS Service - Handles Management Information System report generation."""

from datetime import datetime
from typing import List, Dict, Optional, Any
import os
import pandas as pd

# Import models
from models.voucher import Voucher
from models.debit_voucher import JournalVoucher, PurchaseVoucher, PayrollVoucher, DebitVoucherType

class MISService:
    """
    Handles generation of Management Accounting reports.
    Preserves logic for both legacy Account Code checks and new Ledger Name matching.
    """
    
    def __init__(self, data_service):
        self.data_service = data_service
        
        # segments configuration
        self.segments = ['Retail', 'Kenya', 'India', 'Corporate', 'Placement']
        
        # Ledger keywords for classification (Restoring logic for text-based matching)
        self.revenue_keywords = ['sales', 'income', 'revenue', 'fees']
        self.direct_cost_keywords = ['purchase', 'cost of goods', 'direct', 'wages', 'salary', 'freight']
        self.indirect_cost_keywords = ['rent', 'electricity', 'internet', 'audit', 'legal', 'office']

    def calculate_mis(self, vouchers: List[any],
                     start_date: datetime = None,
                     end_date: datetime = None) -> Dict:
        """
        Calculate MIS report data with segment-wise breakdown.
        """
        # 1. Filter Vouchers
        filtered_vouchers = self._filter_by_date(vouchers, start_date, end_date)
        
        # 2. Initialize Report Structure
        result = {
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            },
            'segments': {},
            'total': {}
        }
        
        # 3. Initialize Metric Counters
        metric_keys = [
            'gmv', 'returns', 'net_revenue', 
            'direct_costs', 'allocated_costs', 
            'total_variable_cost', 'gross_profit'
        ]
        
        # Company-wide totals
        total_metrics = {k: 0.0 for k in metric_keys}

        # 4. Process Each Segment
        for segment in self.segments:
            # Calculate metrics for this specific segment
            metrics = self._calculate_segment_metrics(filtered_vouchers, segment)
            result['segments'][segment] = metrics
            
            # Add to company totals
            for key in metric_keys:
                total_metrics[key] += metrics.get(key, 0.0)
        
        # 5. Calculate Final Margins
        self._calculate_margin(total_metrics)
        result['total'] = total_metrics
        
        return result

    def get_gross_profit_summary(self, vouchers: List[any],
                                start_date: datetime = None,
                                end_date: datetime = None) -> Dict:
        """
        Get a simplified gross profit summary for dashboards.
        """
        mis_data = self.calculate_mis(vouchers, start_date, end_date)
        return {
            'total_revenue': mis_data['total']['net_revenue'],
            'total_costs': mis_data['total']['total_variable_cost'],
            'gross_profit': mis_data['total']['gross_profit'],
            'gross_margin': mis_data['total']['gross_margin']
        }

    def _get_val(self, obj, attr, default=None):
        """Safe accessor for Dict or Object."""
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    def _calculate_segment_metrics(self, vouchers: List[any], segment: str) -> Dict:
        """Calculate metrics for a specific segment."""
        metrics = {
            'gmv': 0.0, 'returns': 0.0, 'net_revenue': 0.0,
            'direct_costs': 0.0, 'allocated_costs': 0.0,
            'total_variable_cost': 0.0, 'gross_profit': 0.0, 'gross_margin': 0.0
        }

        target_segment = segment.lower().strip()

        for v in vouchers:
            # ---------------------------------------------------------
            # LOGIC TYPE A: New Journal Vouchers (Entries list)
            # ---------------------------------------------------------
            entries = self._get_val(v, 'entries')
            if entries:
                for entry in entries:
                    # Safe access for Entry (could be dict or obj)
                    subcode = self._get_val(entry, 'subcode', '')
                    if subcode and str(subcode).lower().strip() == target_segment:
                        ledger = self._get_val(entry, 'ledger', '')
                        cr = float(self._get_val(entry, 'credit_amount', 0))
                        dr = float(self._get_val(entry, 'debit_amount', 0))

                        # Logic: classify based on Ledger Name keywords or Debit/Credit
                        if self._is_revenue(ledger, is_credit=True):
                            metrics['gmv'] += cr
                        elif self._is_direct_cost(ledger, is_debit=True):
                            metrics['direct_costs'] += dr
                        
                        # Fallback
                        elif cr > 0: metrics['gmv'] += cr
                        elif dr > 0: metrics['direct_costs'] += dr

            # ---------------------------------------------------------
            # LOGIC TYPE B: New Purchase Vouchers (Business Unit)
            # ---------------------------------------------------------
            bu = self._get_val(v, 'business_unit')
            if bu and str(bu).lower().strip() == target_segment:
                exp_ledger = self._get_val(v, 'expense_ledger', '')
                base_amt = float(self._get_val(v, 'base_amount', 0))
                
                if self._is_direct_cost(exp_ledger, is_debit=True):
                     metrics['direct_costs'] += base_amt
                else:
                     metrics['direct_costs'] += base_amt 

            # ---------------------------------------------------------
            # LOGIC TYPE C: New Payroll Vouchers (Salary Subcode)
            # ---------------------------------------------------------
            sc = self._get_val(v, 'salary_subcode')
            if sc and str(sc).lower().strip() == target_segment:
                 metrics['direct_costs'] += float(self._get_val(v, 'amount', 0))

            # ---------------------------------------------------------
            # LOGIC TYPE D: Legacy Vouchers
            # ---------------------------------------------------------
            seg = self._get_val(v, 'segment')
            if seg and str(seg).lower().strip() == target_segment:
                amt = float(self._get_val(v, 'amount', 0))
                v_type = str(self._get_val(v, 'voucher_type', '')).lower()
                acc_name = self._get_val(v, 'account_name', '')
                
                if self._is_revenue(acc_name) or 'receipt' in v_type or 'credit' in v_type:
                    metrics['gmv'] += amt
                elif self._is_direct_cost(acc_name) or 'payment' in v_type or 'debit' in v_type:
                     metrics['direct_costs'] += amt
        
        # Calculate Derived Metrics
        metrics['net_revenue'] = metrics['gmv'] - metrics['returns']
        metrics['total_variable_cost'] = metrics['direct_costs'] + metrics['allocated_costs']
        metrics['gross_profit'] = metrics['net_revenue'] - metrics['total_variable_cost']
        self._calculate_margin(metrics)
        
        return metrics

    def _is_revenue(self, ledger_name: str, is_credit: bool = False) -> bool:
        name = str(ledger_name).lower()
        if any(k in name for k in self.revenue_keywords): return True
        return False

    def _is_direct_cost(self, ledger_name: str, is_debit: bool = False) -> bool:
        name = str(ledger_name).lower()
        if any(k in name for k in self.direct_cost_keywords): return True
        return True 

    def _calculate_margin(self, metrics: Dict):
        if metrics['net_revenue'] > 0:
            metrics['gross_margin'] = (metrics['gross_profit'] / metrics['net_revenue']) * 100
        else:
            metrics['gross_margin'] = 0.0

    def _filter_by_date(self, vouchers: List[any], start: datetime, end: datetime) -> List[any]:
        if not start and not end: return vouchers
        filtered = []
        for v in vouchers:
            # Safe date access
            d = self._get_val(v, 'voucher_date') or self._get_val(v, 'date')
            if not d: continue
            
            if isinstance(d, str):
                try: d = datetime.strptime(d, "%Y-%m-%d").date()
                except: continue
            elif isinstance(d, datetime):
                d = d.date()
            
            s = start.date() if isinstance(start, datetime) else start
            e = end.date() if isinstance(end, datetime) else end
            
            if s and d < s: continue
            if e and d > e: continue
            filtered.append(v)
        return filtered

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
                ('Gross Margin %', 'gross_margin', percent_format)
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