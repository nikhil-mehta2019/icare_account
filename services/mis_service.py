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

    def _calculate_segment_metrics(self, vouchers: List[any], segment: str) -> Dict:
        """
        Calculate metrics for a specific segment.
        Contains logic to handle:
        1. New Journal Vouchers (Entries list)
        2. New Purchase/Payroll Vouchers (Objects)
        3. Legacy Vouchers (Dicts/Objects with Account Codes)
        """
        metrics = {
            'gmv': 0.0, 'returns': 0.0, 'net_revenue': 0.0,
            'direct_costs': 0.0, 'allocated_costs': 0.0,
            'total_variable_cost': 0.0, 'gross_profit': 0.0, 'gross_margin': 0.0
        }

        target_segment = segment.lower().strip()

        for v in vouchers:
            # ---------------------------------------------------------
            # LOGIC TYPE A: New Journal Vouchers (Multiple Entries)
            # ---------------------------------------------------------
            if hasattr(v, 'entries') and v.entries:
                for entry in v.entries:
                    # Check Segment Match on Subcode
                    if entry.subcode and entry.subcode.lower().strip() == target_segment:
                        # Logic: classify based on Ledger Name keywords or Debit/Credit
                        if self._is_revenue(entry.ledger, is_credit=True):
                            metrics['gmv'] += entry.credit_amount
                        elif self._is_direct_cost(entry.ledger, is_debit=True):
                            metrics['direct_costs'] += entry.debit_amount
                        
                        # Fallback: If pure Journal, Credit to Segment is usually Revenue, Debit is Cost
                        elif entry.credit_amount > 0:
                             metrics['gmv'] += entry.credit_amount
                        elif entry.debit_amount > 0:
                             metrics['direct_costs'] += entry.debit_amount

            # ---------------------------------------------------------
            # LOGIC TYPE B: New Purchase Vouchers (Object with Business Unit)
            # ---------------------------------------------------------
            elif hasattr(v, 'business_unit') and v.business_unit:
                if v.business_unit.lower().strip() == target_segment:
                    # Purchases are usually Direct Costs
                    if self._is_direct_cost(getattr(v, 'expense_ledger', ''), is_debit=True):
                         metrics['direct_costs'] += v.base_amount
                    else:
                         metrics['direct_costs'] += v.base_amount # Default to direct cost for tagged purchase

            # ---------------------------------------------------------
            # LOGIC TYPE C: New Payroll Vouchers (Object with Salary Subcode)
            # ---------------------------------------------------------
            elif hasattr(v, 'salary_subcode') and v.salary_subcode:
                 if v.salary_subcode.lower().strip() == target_segment:
                      metrics['direct_costs'] += v.amount

            # ---------------------------------------------------------
            # LOGIC TYPE D: Legacy Vouchers (Dicts or Old Objects)
            # ---------------------------------------------------------
            else:
                # Check Segment
                v_seg = getattr(v, 'segment', '')
                if isinstance(v, dict): v_seg = v.get('segment', '')
                
                if v_seg and str(v_seg).lower().strip() == target_segment:
                    # Get Amount
                    amt = getattr(v, 'amount', 0)
                    if isinstance(v, dict): amt = v.get('amount', 0)
                    
                    # Get Identifiers for Logic
                    v_type = str(getattr(v, 'voucher_type', '')).lower()
                    if isinstance(v, dict): v_type = str(v.get('voucher_type', '')).lower()
                    
                    acc_name = getattr(v, 'account_name', '')
                    if isinstance(v, dict): acc_name = v.get('account_name', '')
                    
                    # Apply Logic
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
        """Determine if ledger represents revenue."""
        name = str(ledger_name).lower()
        if any(k in name for k in self.revenue_keywords):
            return True
        # If no keyword match, rely on context (is_credit passed from caller)
        return False

    def _is_direct_cost(self, ledger_name: str, is_debit: bool = False) -> bool:
        """Determine if ledger represents direct cost."""
        name = str(ledger_name).lower()
        if any(k in name for k in self.direct_cost_keywords):
            return True
        return True # Default assumption for tagged debits in this context if not revenue

    def _calculate_margin(self, metrics: Dict):
        """Helper to safely calculate gross margin percentage."""
        if metrics['net_revenue'] > 0:
            metrics['gross_margin'] = (metrics['gross_profit'] / metrics['net_revenue']) * 100
        else:
            metrics['gross_margin'] = 0.0

    def _filter_by_date(self, vouchers: List[any], start: datetime, end: datetime) -> List[any]:
        """
        Filter vouchers by date range.
        Handles datetime, date objects, and strings robustly.
        """
        if not start and not end:
            return vouchers
            
        filtered = []
        for v in vouchers:
            # Extract date from object or dict
            d = getattr(v, 'voucher_date', getattr(v, 'date', None))
            if isinstance(v, dict) and not d:
                d = v.get('voucher_date') or v.get('date')
            
            if not d:
                continue
            
            # Normalize to date object
            if isinstance(d, str):
                try:
                    d = datetime.strptime(d, "%Y-%m-%d").date()
                except ValueError:
                    continue # Skip invalid dates
            elif isinstance(d, datetime):
                d = d.date()
            
            # Normalize constraints
            s = start.date() if isinstance(start, datetime) else start
            e = end.date() if isinstance(end, datetime) else end
            
            # Compare
            if s and d < s:
                continue
            if e and d > e:
                continue
                
            filtered.append(v)
            
        return filtered

    def export_mis_excel(self, mis_data: Dict, output_path: str) -> str:
        """
        Export MIS report to Excel using XlsxWriter.
        Preserves original detailed formatting logic.
        """
        try:
            import xlsxwriter
            
            # Create workbook
            workbook = xlsxwriter.Workbook(output_path)
            worksheet = workbook.add_worksheet('MIS Report')
            
            # --- Define Styles (Restoring Original Look) ---
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#00A4A6', # Teal header
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            metric_label_format = workbook.add_format({
                'bold': True,
                'border': 1,
                'bg_color': '#f5f5f5'
            })
            
            currency_format = workbook.add_format({
                'num_format': '₹ #,##0.00',
                'border': 1
            })
            
            percent_format = workbook.add_format({
                'num_format': '0.00%',
                'border': 1,
                'bold': True
            })
            
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 16,
                'align': 'center',
                'valign': 'vcenter'
            })

            # --- Write Structure ---
            
            # 1. Title
            segment_names = list(mis_data.get('segments', {}).keys())
            total_cols = len(segment_names) + 2 # Label + Total + Segments
            worksheet.merge_range(0, 0, 0, total_cols - 1, 
                                'Management Accounting Dashboard (Segment-Wise)', title_format)
            
            # 2. Column Headers
            headers = ['Metric', 'Total Company'] + segment_names
            worksheet.set_row(2, 30) # Taller header row
            for col_num, header in enumerate(headers):
                worksheet.write(2, col_num, header, header_format)
            
            # 3. Data Rows
            rows_config = [
                ('GMV (Gross Sales)', 'gmv', currency_format),
                ('Less: Returns/Refunds', 'returns', currency_format),
                ('Net Revenue (A)', 'net_revenue', currency_format),
                ('Direct Costs (Directly Tagged)', 'direct_costs', currency_format),
                ('Allocated Shared Costs (Pool)', 'allocated_costs', currency_format),
                ('Total Variable Cost (B)', 'total_variable_cost', currency_format),
                ('GROSS PROFIT (A - B)', 'gross_profit', currency_format),
                ('Gross Margin %', 'gross_margin', percent_format)
            ]
            
            start_row = 3
            for i, (label, key, fmt) in enumerate(rows_config):
                current_row = start_row + i
                
                # Metric Name
                worksheet.write(current_row, 0, label, metric_label_format)
                
                # Total Value
                total_val = mis_data.get('total', {}).get(key, 0.0)
                if key == 'gross_margin': total_val /= 100
                worksheet.write(current_row, 1, total_val, fmt)
                
                # Segment Values
                for col_idx, seg in enumerate(segment_names, start=2):
                    seg_val = mis_data.get('segments', {}).get(seg, {}).get(key, 0.0)
                    if key == 'gross_margin': seg_val /= 100
                    worksheet.write(current_row, col_idx, seg_val, fmt)

            # 4. Adjust Layout
            worksheet.set_column(0, 0, 35) # Metric column width
            worksheet.set_column(1, total_cols - 1, 18) # Value columns width
            
            workbook.close()
            return output_path
            
        except ImportError:
            # Fallback if XlsxWriter not installed
            print("XlsxWriter not found, falling back to basic Pandas export")
            df_data = []
            for key in ['gmv', 'net_revenue', 'direct_costs', 'gross_profit']:
                row = {'Metric': key}
                row['Total'] = mis_data['total'][key]
                for seg, vals in mis_data['segments'].items():
                    row[seg] = vals[key]
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            df.to_excel(output_path, index=False)
            return output_path
        except Exception as e:
            print(f"Export Error: {e}")
            return None